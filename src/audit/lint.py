#!/usr/bin/env python3
"""Mechanical code-quality checks via AST analysis.

Catches things grep can't reliably find: nesting depth, function length,
magic numbers in logic, missing docstrings, and near-duplicate code blocks.

Usage:
    audit-lint <directory> [--lang python|typescript|all]

Output is JSON lines — one object per finding, sorted by file then line.
Designed to be consumed by the /audit skill's dimension agents.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import tokenize
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from io import StringIO
from pathlib import Path
from typing import Iterator

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    ".tox",
    "egg-info",
    "site-packages",
}

SKIP_PATTERNS = {
    "migrations",
    "generated",
    "vendor",
    "vendored",
}

MAX_FUNCTION_LINES = 50
MAX_NESTING_DEPTH = 4
MAX_PARAMS = 5
MIN_DUPLICATE_LINES = 6
MAGIC_NUMBER_WHITELIST = frozenset({0, 1, -1, 2, 10, 100, 0.0, 1.0, 0.5})
MAGIC_STRING_WHITELIST = frozenset({"", " ", "\n", "\t", ",", ".", "/", "utf-8", "utf8", "ascii", "rb", "wb", "r", "w", "a"})


@dataclass
class Finding:
    file: str
    line: int
    end_line: int | None
    check: str
    severity: str
    description: str

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["end_line"] is None:
            del d["end_line"]
        return d


@dataclass
class AuditState:
    findings: list[Finding] = field(default_factory=list)
    code_blocks: dict[str, list[tuple[str, int]]] = field(default_factory=lambda: defaultdict(list))

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    for part in path.parts:
        low = part.lower()
        if any(p in low for p in SKIP_PATTERNS):
            return True
    return False


def collect_python_files(root: Path) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        dp = Path(dirpath)
        if should_skip(dp):
            continue
        for f in filenames:
            if f.endswith(".py"):
                fp = dp / f
                if not should_skip(fp):
                    files.append(fp)
    return sorted(files)


def collect_ts_files(root: Path) -> list[Path]:
    files = []
    exts = {".ts", ".tsx", ".js", ".jsx"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        dp = Path(dirpath)
        if should_skip(dp):
            continue
        for f in filenames:
            if any(f.endswith(ext) for ext in exts):
                fp = dp / f
                if not should_skip(fp):
                    files.append(fp)
    return sorted(files)


def collect_shell_files(root: Path) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        dp = Path(dirpath)
        if should_skip(dp):
            continue
        for f in filenames:
            fp = dp / f
            if f.endswith((".sh", ".bash")) or (not f.endswith(tuple(f".{e}" for e in "py ts tsx js jsx go rs c cpp h".split()))):
                if fp.is_file():
                    try:
                        with open(fp, "rb") as fh:
                            first_line = fh.readline(256)
                            if first_line.startswith(b"#!") and (b"bash" in first_line or b"/sh" in first_line):
                                files.append(fp)
                                continue
                    except (OSError, PermissionError):
                        pass
                if f.endswith((".sh", ".bash")):
                    files.append(fp)
    return sorted(set(files))


# ── Python checks ──────────────────────────────────────────────────────

def _nesting_depth(node: ast.AST, current: int = 0) -> int:
    """Return the max logic-nesting depth inside a node."""
    nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)
    if sys.version_info >= (3, 11):
        nesting_nodes = (*nesting_nodes, ast.TryStar)

    max_depth = current
    for child in ast.iter_child_nodes(node):
        if isinstance(child, nesting_nodes):
            child_depth = _nesting_depth(child, current + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = _nesting_depth(child, current)
            max_depth = max(max_depth, child_depth)
    return max_depth


def _function_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Approximate the body line count of a function."""
    if not node.body:
        return 0
    first = node.body[0].lineno
    last = node.body[-1].end_lineno or node.body[-1].lineno
    return last - first + 1


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    if not node.body:
        return False
    first = node.body[0]
    return isinstance(first, ast.Expr) and isinstance(first.value, (ast.Constant, ast.Str))


def _is_magic_number(node: ast.Constant) -> bool:
    if not isinstance(node.value, (int, float)):
        return False
    return node.value not in MAGIC_NUMBER_WHITELIST


def _is_in_assignment_target(node: ast.AST, parent_map: dict) -> bool:
    """Check if a node is in an assignment context (defining a constant)."""
    parent = parent_map.get(id(node))
    while parent is not None:
        if isinstance(parent, ast.Assign):
            for target in parent.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    return True
        if isinstance(parent, (ast.AnnAssign,)):
            if isinstance(parent.target, ast.Name) and parent.target.id.isupper():
                return True
        parent = parent_map.get(id(parent))
    return False


def _is_in_decorator_or_default(node: ast.AST, parent_map: dict) -> bool:
    parent = parent_map.get(id(node))
    while parent is not None:
        if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node in getattr(parent, "decorator_list", []):
                return True
            for arg in parent.args.defaults + parent.args.kw_defaults:
                if arg is node:
                    return True
        parent = parent_map.get(id(parent))
    return False


def _build_parent_map(tree: ast.AST) -> dict:
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _param_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    args = node.args
    count = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
    if args.vararg:
        count += 1
    if args.kwarg:
        count += 1
    if args.args and args.args[0].arg in ("self", "cls"):
        count -= 1
    return count


def _check_early_return_opportunity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if the function's body is a single if/else that could use an early return."""
    body = node.body
    if _has_docstring(node) and len(body) == 2:
        body = body[1:]
    elif len(body) != 1:
        return False

    stmt = body[0] if body else None
    if not isinstance(stmt, ast.If) or not stmt.orelse:
        return False

    if_lines = (stmt.body[-1].end_lineno or stmt.body[-1].lineno) - stmt.body[0].lineno + 1
    else_lines = (stmt.orelse[-1].end_lineno or stmt.orelse[-1].lineno) - stmt.orelse[0].lineno + 1

    return max(if_lines, else_lines) > 5 and min(if_lines, else_lines) <= 5


def _check_string_enum_candidates(tree: ast.AST, rel: str, state: AuditState, parent_map: dict) -> None:
    """Detect string literals passed as function arguments that should be enums/constants.

    Tracks which string values appear as arguments across the file. If the same
    string appears in 2+ call sites, or a function receives multiple different
    short string literals that look like variant selectors, flag it.
    """
    # Collect: for each (func_name, arg_position), what string values appear?
    call_strings: dict[str, list[tuple[int, str]]] = defaultdict(list)
    # Also collect all string args to any function for cross-file frequency
    all_string_args: dict[str, list[int]] = defaultdict(list)

    IGNORE_VALUES = frozenset({
        "", " ", "\n", "\t", ",", ".", "/", "\\",
        "utf-8", "utf8", "ascii", "latin-1",
        "r", "w", "a", "rb", "wb", "ab", "r+", "w+",
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS",
        "http", "https", "ws", "wss",
        "true", "false", "null", "none",
        "index", "default",
    })

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = _call_name(node)
        if not func_name:
            continue
        # Skip common functions where string args are expected
        if func_name in ("print", "log", "logger", "info", "debug", "warning", "error",
                         "critical", "success", "_log", "emit",
                         "format", "join", "split", "replace",
                         "startswith", "endswith", "strip", "encode", "decode",
                         "isinstance", "issubclass", "hasattr", "getattr", "setattr",
                         "open", "Path", "get", "post", "put", "delete",
                         "getLogger", "basicConfig", "setLevel",
                         "add_argument", "add_parser"):
            continue
        for i, arg in enumerate(node.args):
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                val = arg.value
                if val in IGNORE_VALUES or len(val) > 30 or len(val) < 2:
                    continue
                # Skip if it looks like a sentence/message (has spaces + lowercase start)
                if " " in val and val[0].islower() and len(val) > 15:
                    continue
                key = f"{func_name}:arg{i}"
                call_strings[key].append((node.lineno, val))
                all_string_args[val].append(node.lineno)

        for kw in node.keywords:
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                val = kw.value.value
                if val in IGNORE_VALUES or len(val) > 30 or len(val) < 2:
                    continue
                if " " in val and val[0].islower() and len(val) > 15:
                    continue
                key = f"{func_name}:{kw.arg}"
                call_strings[key].append((node.lineno, val))
                all_string_args[val].append(node.lineno)

    # Flag: same positional arg of same function gets different string values → enum candidate
    for key, occurrences in call_strings.items():
        values = {v for _, v in occurrences}
        if len(values) >= 2 and all(_looks_like_enum_value(v) for v in values):
            first_line = occurrences[0][0]
            func = key.split(":")[0]
            state.add(Finding(
                file=rel,
                line=first_line,
                end_line=None,
                check="string-enum",
                severity="minor" if len(values) < 4 else "major",
                description=f"`{func}()` receives {len(values)} different string variants ({', '.join(repr(v) for v in sorted(values)[:4])}) — use an enum or literal union",
            ))

    # Flag: same string value passed to 3+ different call sites
    for val, lines_list in all_string_args.items():
        if len(lines_list) >= 3 and _looks_like_enum_value(val):
            state.add(Finding(
                file=rel,
                line=lines_list[0],
                end_line=None,
                check="string-enum",
                severity="major",
                description=f"String `\"{val}\"` passed as argument in {len(lines_list)} call sites — define as a constant or enum member",
            ))


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _looks_like_enum_value(val: str) -> bool:
    """Heuristic: short, no spaces (or snake_case/kebab-case), looks like a variant selector."""
    if len(val) > 25 or len(val) < 2:
        return False
    if re.match(r"^[a-z][a-z0-9_-]*$", val):
        return True
    if re.match(r"^[A-Z][A-Z0-9_]*$", val):
        return True
    if re.match(r"^[a-z]+[A-Z][a-zA-Z]*$", val):
        return True
    return False


def _check_isinstance_chains(tree: ast.AST, rel: str, state: AuditState) -> None:
    """Detect isinstance chains that suggest missing polymorphism or registry dispatch."""
    for node in ast.walk(tree):
        # isinstance(x, (A, B, C, D)) with 4+ types
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance":
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Tuple):
                type_count = len(node.args[1].elts)
                if type_count >= 4:
                    state.add(Finding(
                        file=rel,
                        line=node.lineno,
                        end_line=None,
                        check="isinstance-chain",
                        severity="minor" if type_count < 6 else "major",
                        description=f"`isinstance()` checks {type_count} types — consider a registry or protocol",
                    ))

        # if/elif chains where each branch is an isinstance check
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if isinstance(child, ast.If):
                    chain_len = _isinstance_elif_chain_length(child)
                    if chain_len >= 3:
                        state.add(Finding(
                            file=rel,
                            line=child.lineno,
                            end_line=None,
                            check="isinstance-chain",
                            severity="minor" if chain_len < 5 else "major",
                            description=f"if/elif chain with {chain_len} `isinstance` branches — consider registry-driven dispatch",
                        ))


def _isinstance_elif_chain_length(node: ast.If) -> int:
    """Count consecutive if/elif branches that test isinstance."""
    count = 0
    current = node
    while current is not None:
        if _test_is_isinstance(current.test):
            count += 1
        else:
            break
        if current.orelse and len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
        else:
            break
    return count


def _test_is_isinstance(node: ast.expr) -> bool:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "isinstance":
        return True
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
        return any(_test_is_isinstance(v) for v in node.values)
    return False


def _check_stringly_typed_access(tree: ast.AST, rel: str, state: AuditState, parent_map: dict) -> None:
    """Detect kwargs.get('key'), dict string-key access patterns that should be typed."""
    seen_lines: set[int] = set()
    for node in ast.walk(tree):
        # x.get("some_key") or x.get("some_key", default)
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            obj = node.func.value
            # kwargs.get(...) or options.get(...) or config.get(...) or params.get(...)
            if isinstance(obj, ast.Name) and obj.id in ("kwargs", "options", "params", "args", "config", "opts", "kw"):
                if node.lineno not in seen_lines:
                    seen_lines.add(node.lineno)
                    state.add(Finding(
                        file=rel,
                        line=node.lineno,
                        end_line=None,
                        check="stringly-typed",
                        severity="minor",
                        description=f"`{obj.id}.get(\"{node.args[0].value}\")` — stringly-typed access, use explicit parameters or a dataclass",
                    ))

        # getattr(obj, "string_literal") — skip dunder attrs (legitimate reflection)
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "getattr"
                and len(node.args) >= 2
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)):
            attr_name = node.args[1].value
            if not (attr_name.startswith("__") and attr_name.endswith("__")):
                if node.lineno not in seen_lines:
                    seen_lines.add(node.lineno)
                    state.add(Finding(
                        file=rel,
                        line=node.lineno,
                        end_line=None,
                        check="stringly-typed",
                        severity="minor",
                        description=f"`getattr(_, \"{attr_name}\")` — stringly-typed attribute access",
                    ))


def _check_kwargs_signatures(tree: ast.AST, rel: str, state: AuditState) -> None:
    """Detect **kwargs in function signatures that hide the real interface."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.args.kwarg:
            continue
        # Skip dunder methods and decorators like @overload — kwargs are expected there
        if node.name.startswith("__") and node.name.endswith("__"):
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id in ("overload", "abstractmethod"):
                continue
            if isinstance(dec, ast.Attribute) and dec.attr in ("overload", "abstractmethod"):
                continue
        state.add(Finding(
            file=rel,
            line=node.lineno,
            end_line=None,
            check="kwargs-signature",
            severity="minor",
            description=f"`{node.name}()` accepts `**{node.args.kwarg.arg}` — hides the real interface, use explicit params or a dataclass",
        ))


def audit_python_file(filepath: Path, state: AuditState, root: Path) -> None:
    rel = str(filepath.relative_to(root))
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        return

    parent_map = _build_parent_map(tree)
    lines = source.splitlines()

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            body_lines = _function_lines(node)
            if body_lines > MAX_FUNCTION_LINES:
                state.add(Finding(
                    file=rel,
                    line=node.lineno,
                    end_line=node.end_lineno,
                    check="long-function",
                    severity="major",
                    description=f"`{node.name}()` is {body_lines} lines (threshold: {MAX_FUNCTION_LINES})",
                ))

            depth = _nesting_depth(node)
            if depth > MAX_NESTING_DEPTH:
                state.add(Finding(
                    file=rel,
                    line=node.lineno,
                    end_line=node.end_lineno,
                    check="deep-nesting",
                    severity="major" if depth > 5 else "minor",
                    description=f"`{node.name}()` has nesting depth {depth} (threshold: {MAX_NESTING_DEPTH})",
                ))

            pcount = _param_count(node)
            if pcount > MAX_PARAMS:
                state.add(Finding(
                    file=rel,
                    line=node.lineno,
                    end_line=None,
                    check="too-many-params",
                    severity="major" if pcount > 7 else "minor",
                    description=f"`{node.name}()` has {pcount} parameters (threshold: {MAX_PARAMS})",
                ))

            if not _has_docstring(node) and not node.name.startswith("_"):
                state.add(Finding(
                    file=rel,
                    line=node.lineno,
                    end_line=None,
                    check="missing-docstring",
                    severity="minor",
                    description=f"Public function `{node.name}()` has no docstring",
                ))

            if _check_early_return_opportunity(node):
                state.add(Finding(
                    file=rel,
                    line=node.lineno,
                    end_line=node.end_lineno,
                    check="early-return",
                    severity="minor",
                    description=f"`{node.name}()` wraps its body in if/else — consider an early return for the short branch",
                ))

            if node.returns is None and not node.name.startswith("_"):
                if not (isinstance(node, ast.FunctionDef) and node.name in ("__init__", "__post_init__", "__del__", "__enter__", "__exit__")):
                    state.add(Finding(
                        file=rel,
                        line=node.lineno,
                        end_line=None,
                        check="missing-return-type",
                        severity="minor",
                        description=f"Public function `{node.name}()` has no return type annotation",
                    ))

        elif isinstance(node, ast.ClassDef):
            if not _has_docstring(node) and not node.name.startswith("_"):
                state.add(Finding(
                    file=rel,
                    line=node.lineno,
                    end_line=None,
                    check="missing-docstring",
                    severity="minor",
                    description=f"Class `{node.name}` has no docstring",
                ))

        elif isinstance(node, ast.Constant):
            if _is_magic_number(node):
                if not _is_in_assignment_target(node, parent_map) and not _is_in_decorator_or_default(node, parent_map):
                    parent = parent_map.get(id(node))
                    if not isinstance(parent, (ast.Slice, ast.Index)):
                        state.add(Finding(
                            file=rel,
                            line=node.lineno,
                            end_line=None,
                            check="magic-number",
                            severity="minor",
                            description=f"Magic number `{node.value}` — consider a named constant",
                        ))

    # ── String literal enum candidates ──
    _check_string_enum_candidates(tree, rel, state, parent_map)

    # ── isinstance chain detection ──
    _check_isinstance_chains(tree, rel, state)

    # ── kwargs.get / stringly-typed access detection ──
    _check_stringly_typed_access(tree, rel, state, parent_map)

    # ── **kwargs in signatures ──
    _check_kwargs_signatures(tree, rel, state)

    # ── Duplicate block detection ──
    if len(lines) > MIN_DUPLICATE_LINES:
        for i in range(len(lines) - MIN_DUPLICATE_LINES + 1):
            block_lines = lines[i : i + MIN_DUPLICATE_LINES]
            block = "\n".join(line.strip() for line in block_lines)
            if block.strip() and not _is_trivial_block(block_lines):
                block_hash = hashlib.md5(block.encode()).hexdigest()
                state.code_blocks[block_hash].append((rel, i + 1))

    # ── Commented-out code detection ──
    comment_block_start = None
    comment_block_count = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#") and not stripped.startswith("#!"):
            inner = stripped.lstrip("#").strip()
            if _looks_like_code(inner):
                if comment_block_start is None:
                    comment_block_start = i
                    comment_block_count = 1
                else:
                    comment_block_count += 1
            else:
                if comment_block_count >= 3:
                    state.add(Finding(
                        file=rel,
                        line=comment_block_start,
                        end_line=comment_block_start + comment_block_count - 1,
                        check="commented-code",
                        severity="minor",
                        description=f"{comment_block_count} lines of commented-out code",
                    ))
                comment_block_start = None
                comment_block_count = 0
        else:
            if comment_block_count >= 3:
                state.add(Finding(
                    file=rel,
                    line=comment_block_start,
                    end_line=comment_block_start + comment_block_count - 1,
                    check="commented-code",
                    severity="minor",
                    description=f"{comment_block_count} lines of commented-out code",
                ))
            comment_block_start = None
            comment_block_count = 0

    if comment_block_count >= 3:
        state.add(Finding(
            file=rel,
            line=comment_block_start,
            end_line=comment_block_start + comment_block_count - 1,
            check="commented-code",
            severity="minor",
            description=f"{comment_block_count} lines of commented-out code",
        ))


def _looks_like_code(text: str) -> bool:
    """Heuristic: does a comment body look like disabled code rather than prose?"""
    if not text:
        return False
    code_patterns = [
        r"^\s*(def |class |import |from |if |elif |else:|for |while |return |raise |try:|except |with |async )",
        r"^\s*\w+\s*[=!<>]+",
        r"^\s*\w+\.\w+\(",
        r"^\s*\w+\(",
        r"^\s*(pass|break|continue)\s*$",
    ]
    return any(re.match(p, text) for p in code_patterns)


def _check_ts_string_enum_candidates(lines: list[str], rel: str, state: AuditState) -> None:
    """Detect repeated string literals in function calls that should be union types or enums."""
    # Track string args: value → list of line numbers
    string_args: dict[str, list[int]] = defaultdict(list)

    IGNORE_TS = frozenset({
        "GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS",
        "click", "change", "submit", "input", "focus", "blur",
        "utf-8", "utf8", "text", "json", "blob", "arraybuffer",
        "http", "https",
        "true", "false", "null", "undefined",
        "div", "span", "button", "input", "form", "a", "p", "h1", "h2", "h3",
    })

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
            continue
        # Find string literals inside function calls: func("value") or func(arg, "value")
        for m in re.finditer(r"""(?:[\w.]+)\(\s*(?:[^)]*?,\s*)?['"]([\w_-]+)['"]""", stripped):
            val = m.group(1)
            if val in IGNORE_TS or len(val) < 2 or len(val) > 25:
                continue
            string_args[val].append(i)

    for val, line_nums in string_args.items():
        if len(line_nums) >= 3:
            state.add(Finding(
                file=rel,
                line=line_nums[0],
                end_line=None,
                check="string-enum",
                severity="minor" if len(line_nums) < 5 else "major",
                description=f"String `\"{val}\"` used as argument in {len(line_nums)} calls — use a union type or const",
            ))


def _is_trivial_block(lines_slice: list[str]) -> bool:
    """Filter out import-only blocks, blank-heavy blocks, and comment-only blocks from duplicate detection."""
    stripped = [l.strip() for l in lines_slice]
    if all(l.startswith(("#", "//", "/*", "*")) or not l for l in stripped):
        return True
    non_empty = [l for l in stripped if l]
    if not non_empty:
        return True
    if all(l.startswith(("import ", "from ", "export ")) for l in non_empty):
        return True
    if sum(1 for l in stripped if not l) > len(stripped) // 2:
        return True
    return False


# ── TypeScript/JavaScript checks ──────────────────────────────────────

def audit_ts_file(filepath: Path, state: AuditState, root: Path) -> None:
    """Regex-based TS/JS checks (no AST parser dependency)."""
    rel = str(filepath.relative_to(root))
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return

    lines = source.splitlines()

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if re.search(r"\bany\b", stripped) and not stripped.startswith("//") and not stripped.startswith("*"):
            if re.search(r":\s*any\b|<any>|\bas\s+any\b|any\[\]", stripped):
                state.add(Finding(
                    file=rel, line=i, end_line=None,
                    check="ts-any",
                    severity="major",
                    description="`any` type usage — use `unknown` + type guard or a specific type",
                ))

        if "@ts-ignore" in stripped:
            state.add(Finding(
                file=rel, line=i, end_line=None,
                check="ts-ignore",
                severity="major",
                description="`@ts-ignore` — use `@ts-expect-error` with a reason comment",
            ))

        if re.search(r"\.json\(\)\s*[;)]", stripped) and "as " not in stripped and ": " not in stripped:
            state.add(Finding(
                file=rel, line=i, end_line=None,
                check="untyped-json",
                severity="minor",
                description="`.json()` call without type annotation — response is `any`",
            ))

        # TS/JS function with too many parameters
        fn_match = re.match(r"^(?:export\s+)?(?:async\s+)?(?:function\s+\w+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?)\s*\(([^)]*)\)", stripped)
        if fn_match:
            params_str = fn_match.group(1).strip()
            if params_str:
                param_count = len([p for p in params_str.split(",") if p.strip()])
                if param_count > MAX_PARAMS:
                    state.add(Finding(
                        file=rel, line=i, end_line=None,
                        check="too-many-params",
                        severity="major" if param_count > 7 else "minor",
                        description=f"Function has {param_count} parameters (threshold: {MAX_PARAMS}) — bundle into an options object",
                    ))

    # ── String literal enum candidates (TS) ──
    _check_ts_string_enum_candidates(lines, rel, state)

    # nesting depth (brace-counting heuristic)
    depth = 0
    max_depth = 0
    max_depth_line = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue
        opens = stripped.count("{") - stripped.count("}")
        depth += opens
        if depth > max_depth:
            max_depth = depth
            max_depth_line = i

    if max_depth > 6:
        state.add(Finding(
            file=rel, line=max_depth_line, end_line=None,
            check="deep-nesting",
            severity="major" if max_depth > 8 else "minor",
            description=f"Max brace nesting depth: {max_depth} (threshold: 6)",
        ))

    # Duplicate block detection for TS too
    if len(lines) > MIN_DUPLICATE_LINES:
        for i in range(len(lines) - MIN_DUPLICATE_LINES + 1):
            block_lines = lines[i : i + MIN_DUPLICATE_LINES]
            block = "\n".join(line.strip() for line in block_lines)
            if block.strip() and not _is_trivial_block(block_lines):
                block_hash = hashlib.md5(block.encode()).hexdigest()
                state.code_blocks[block_hash].append((rel, i + 1))


# ── Shell checks ──────────────────────────────────────────────────────

def audit_shell_file(filepath: Path, state: AuditState, root: Path) -> None:
    rel = str(filepath.relative_to(root))
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return

    lines = source.splitlines()

    has_set_e = False
    has_set_pipefail = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if "set -e" in stripped or "set -euo" in stripped or "set -o errexit" in stripped:
            has_set_e = True
        if "set -o pipefail" in stripped or "set -euo" in stripped:
            has_set_pipefail = True

        # Unquoted variable in non-assignment context
        if re.search(r'(?<!")\$\{?\w+\}?(?!")', stripped) and not stripped.startswith("#"):
            if not re.search(r'"\$', stripped) and "$" in stripped:
                var_match = re.search(r'\$(\{?\w+\}?)', stripped)
                if var_match and var_match.group(1) not in ("?", "!", "#", "@", "*", "$", "0"):
                    if "=" not in stripped.split("$")[0] or "[" in stripped:
                        state.add(Finding(
                            file=rel, line=i, end_line=None,
                            check="unquoted-var",
                            severity="minor",
                            description=f"Potentially unquoted variable `${var_match.group(1)}` — quote to prevent word splitting",
                        ))

        if stripped.startswith("eval "):
            state.add(Finding(
                file=rel, line=i, end_line=None,
                check="shell-eval",
                severity="major",
                description="`eval` usage — potential injection vector, consider alternatives",
            ))

    if not has_set_e and len(lines) > 5:
        state.add(Finding(
            file=rel, line=1, end_line=None,
            check="missing-set-e",
            severity="minor",
            description="Missing `set -e` (or `set -euo pipefail`) — script won't exit on error",
        ))


# ── Duplicate reporting ───────────────────────────────────────────────

def report_duplicates(state: AuditState) -> None:
    for block_hash, locations in state.code_blocks.items():
        if len(locations) < 2:
            continue
        # Skip if all locations are in the same file within 10 lines (likely same function)
        files = {loc[0] for loc in locations}
        if len(files) == 1:
            lines = sorted(loc[1] for loc in locations)
            if all(lines[i + 1] - lines[i] < MIN_DUPLICATE_LINES + 2 for i in range(len(lines) - 1)):
                continue

        loc_strs = [f"{f}:{l}" for f, l in locations[:5]]
        first_file, first_line = locations[0]
        state.add(Finding(
            file=first_file,
            line=first_line,
            end_line=first_line + MIN_DUPLICATE_LINES - 1,
            check="duplicate-code",
            severity="major" if len(locations) > 2 else "minor",
            description=f"Duplicate {MIN_DUPLICATE_LINES}-line block found in {len(locations)} locations: {', '.join(loc_strs)}",
        ))


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Mechanical code quality checks")
    parser.add_argument("directory", type=Path, help="Directory to audit")
    parser.add_argument("--lang", choices=["python", "typescript", "shell", "all"], default="all")
    parser.add_argument("--json", action="store_true", default=True, help="Output as JSON lines (default)")
    parser.add_argument("--summary", action="store_true", help="Print summary stats instead of findings")
    args = parser.parse_args()

    root = args.directory.resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    state = AuditState()

    if args.lang in ("python", "all"):
        py_files = collect_python_files(root)
        for f in py_files:
            audit_python_file(f, state, root)

    if args.lang in ("typescript", "all"):
        ts_files = collect_ts_files(root)
        for f in ts_files:
            audit_ts_file(f, state, root)

    if args.lang in ("shell", "all"):
        sh_files = collect_shell_files(root)
        for f in sh_files:
            audit_shell_file(f, state, root)

    report_duplicates(state)

    # Sort by file, then line
    state.findings.sort(key=lambda f: (f.file, f.line))

    if args.summary:
        by_check = defaultdict(int)
        by_severity = defaultdict(int)
        for f in state.findings:
            by_check[f.check] += 1
            by_severity[f.severity] += 1

        summary = {
            "total": len(state.findings),
            "by_severity": dict(by_severity),
            "by_check": dict(sorted(by_check.items(), key=lambda x: -x[1])),
        }
        print(json.dumps(summary, indent=2))
    else:
        for finding in state.findings:
            print(json.dumps(finding.to_dict()))


if __name__ == "__main__":
    main()
