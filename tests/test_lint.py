"""Regression tests for the mechanical linter.

Every test here pins a bug that shipped. The two in `TestSilentFailure` matter
most: a linter that reports nothing is indistinguishable from a clean codebase,
so a regression there is invisible in exactly the situation you need it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def run_lint(target: Path) -> list[dict]:
    """Run the linter over `target` and return its findings."""
    proc = subprocess.run(
        [sys.executable, "-m", "audit.lint", str(target)],
        capture_output=True,
        text=True,
        cwd=REPO / "src",
    )
    assert proc.returncode == 0, proc.stderr
    return [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]


def checks(findings: list[dict]) -> set[str]:
    return {f["check"] for f in findings}


def descriptions(findings: list[dict]) -> str:
    return " ".join(f["description"] for f in findings)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    src = tmp_path / "proj"
    src.mkdir()
    return src


class TestSilentFailure:
    """A file that cannot be analysed must never look like a clean file."""

    @pytest.mark.parametrize("ancestor", ["build", "dist", "node_modules", "vendor-tools"])
    def test_skip_word_in_ancestor_does_not_silence_the_run(self, tmp_path, ancestor):
        # should_skip judged every component of an absolute path, so a project
        # checked out under ~/build/ audited to zero findings and exited 0.
        nested = tmp_path / ancestor / "proj"
        nested.mkdir(parents=True)
        (nested / "m.py").write_text('def f(a, b, c, d, e, g, h):\n    return 9999\n')
        assert run_lint(nested), f"ancestor {ancestor!r} silenced the whole run"

    def test_skip_dir_inside_the_project_is_still_skipped(self, project):
        (project / "keep.py").write_text('def f():\n    return 9999\n')
        generated = project / "build"
        generated.mkdir()
        (generated / "gen.py").write_text('def g():\n    return 8888\n')
        files = {f["file"] for f in run_lint(project)}
        assert not any("build" in f for f in files)

    def test_unparseable_file_is_reported(self, project):
        (project / "broken.py").write_text("def broken(:\n    pass\n")
        assert "unparseable-file" in checks(run_lint(project))

    def test_non_utf8_file_is_reported(self, project):
        (project / "latin.py").write_bytes(b'# \xff\xfe caf\xe9\nx = 1\n')
        assert "unreadable-file" in checks(run_lint(project))


class TestMagicNumbers:
    def test_constant_inside_decorator_call_is_not_magic(self, project):
        (project / "m.py").write_text(
            '"""M."""\nfrom functools import lru_cache\n\n\n'
            '@lru_cache(maxsize=256)\ndef cached(x: int) -> int:\n    """C."""\n    return x\n'
        )
        assert "256" not in descriptions(run_lint(project))

    def test_negative_literal_reports_its_actual_value(self, project):
        (project / "m.py").write_text('"""M."""\n\n\ndef f() -> int:\n    """F."""\n    return -7\n')
        desc = descriptions(run_lint(project))
        assert "`-7`" in desc and "number `7`" not in desc

    def test_negative_one_is_whitelisted(self, project):
        (project / "m.py").write_text('"""M."""\n\n\ndef f() -> int:\n    """F."""\n    return -1\n')
        assert "magic-number" not in checks(run_lint(project))

    def test_version_tuple_is_not_magic(self, project):
        # sys.version_info >= (3, 11) was reported as two magic numbers.
        (project / "m.py").write_text(
            '"""M."""\nimport sys\n\nNEWER = sys.version_info >= (3, 11)\n'
        )
        assert "magic-number" not in checks(run_lint(project))


class TestStubsAndOverloads:
    def test_overload_with_kwargs_is_not_flagged(self, project):
        (project / "m.py").write_text(
            '"""M."""\nfrom typing import overload\n\n\n'
            '@overload\ndef api(a: int, **kwargs: str) -> None: ...\n'
        )
        assert "kwargs-signature" not in checks(run_lint(project))

    def test_protocol_stub_needs_no_docstring(self, project):
        (project / "m.py").write_text(
            '"""M."""\nfrom typing import Protocol\n\n\n'
            'class Reader(Protocol):\n    """R."""\n\n    def read(self) -> bytes: ...\n'
        )
        assert "missing-docstring" not in checks(run_lint(project))


class TestDuplicateDetection:
    def test_one_finding_per_duplicated_region(self, project):
        block = "\n".join(f"    v{i} = compute({i}) + offset({i})" for i in range(10))
        (project / "m.py").write_text(
            f'"""M."""\n\n\ndef alpha() -> None:\n    """A."""\n{block}\n\n\n'
            f'def beta() -> None:\n    """B."""\n{block}\n'
        )
        # Overlapping sliding windows previously emitted one finding each.
        dupes = [f for f in run_lint(project) if f["check"] == "duplicate-code"]
        assert len(dupes) == 1
        assert "10-line" in dupes[0]["description"]


class TestLiteralAwareness:
    """Line-regex checks must not match inside string literals."""

    def test_any_inside_a_string_is_not_a_type(self, project):
        (project / "a.ts").write_text('const label = "type: any";\n')
        assert "ts-any" not in checks(run_lint(project))

    def test_real_any_annotation_is_still_flagged(self, project):
        (project / "a.ts").write_text("let bad: any;\n")
        assert "ts-any" in checks(run_lint(project))

    def test_braces_in_strings_do_not_accumulate_nesting(self, project):
        (project / "a.ts").write_text("".join(f'const o{i} = "{{";\n' for i in range(8)))
        assert "deep-nesting" not in checks(run_lint(project))

    def test_quoted_shell_variable_is_not_unquoted(self, project):
        (project / "s.sh").write_text('#!/bin/bash\ncount=3\necho "Total: $count files"\n')
        unquoted = [f for f in run_lint(project) if f["check"] == "unquoted-var"]
        assert not any("count" in f["description"] for f in unquoted)

    def test_genuinely_unquoted_shell_variable_is_flagged(self, project):
        (project / "s.sh").write_text('#!/bin/bash\nrm $target_path\n')
        assert "unquoted-var" in checks(run_lint(project))
