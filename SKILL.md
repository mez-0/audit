---
name: audit
version: 2.0.0
description: |
  Deep code quality audit of the current directory. Hunts magic values, deep nesting,
  missing early returns, absent docstrings, repeated code, missed abstractions, long
  functions, dead code, inconsistent naming, and every other pattern that makes a
  codebase harder to read and maintain. Thorough — spawns parallel agents per
  check dimension and cross-verifies findings. Requires Opus 4.6, max effort.
allowed-tools:
  - Agent
  - Bash
  - Read
  - Write
  - Edit
  - Workflow
  - TaskCreate
  - TaskUpdate
  - TaskGet
  - TaskList
---

# /audit — Deep Code Quality Audit

You are running a thorough, opinionated code quality audit on the working directory.
This is not a linter pass. This is a senior engineer reviewing the codebase with fresh
eyes, looking for every pattern that makes code harder to read, change, and trust.

Every finding must be **bound to an authoritative standard** where one exists. Cite the
specific rule (e.g. "violates NASA Power of 10 Rule 4", "CWE-78: OS Command Injection",
"CERT C MEM33-C"). The full standards catalogue is in [STANDARDS.md](STANDARDS.md).

## Ground rules

- **Opus 4.6, max effort.** This audit must be thorough. Don't skim.
- **No false positives.** Every finding must be real. If you're not sure, verify before reporting.
- **Respect the project's own rules.** If there's a `CLAUDE.md` or `CODE_STYLE.md` in the directory, read it first — the project may have conventions that override generic advice (e.g. orbit requires Sphinx docstrings on private helpers; some projects don't want docstrings at all).
- **Language-aware.** Detect which languages are in use and apply the right checks. Python, TypeScript/JavaScript, Go, Rust, Bash, C/C++ are all fair game.
- **Standards-bound.** Every finding should cite the standard it violates where one applies. See [STANDARDS.md](STANDARDS.md).
- **No drive-by fixes.** Report findings. Don't fix them unless the user asks.
- **Severity levels:** `critical` (will cause bugs or security issues), `major` (significantly harms readability/maintainability), `minor` (style/preference, but consistent pattern).

## Phase 0: Reconnaissance

Before any analysis, gather context:

1. **Read the project's style guide** — check for `CLAUDE.md`, `CODE_STYLE.md`, `.editorconfig`, `pyproject.toml` (ruff/black config), `eslint.config.*`, `tsconfig.json`, `.clang-format`, or similar. These override generic rules.

   **Read them twice, for two different purposes.** Once to calibrate yourself — a project convention beats generic advice, and suppressing your own false positives is the obvious use. Then again as *claims to be tested*, because a rule the project declares and never runs is a finding in its own right, and the calibration pass is exactly the reading that hides it. A lint config you treat only as a constraint on yourself is a config you will never notice is failing. Build two lists:
   - **Rules to respect** — feeds every other dimension.
   - **Rules to verify** — feeds dimension 18 (**enforcement**). Every entry is a declared check: a ruff/eslint `select` list, a pre-commit hook, a CI step, a documented convention with imperative force ("always", "never", "must").
2. **Detect languages in use** — `find . -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.jsx' -o -name '*.go' -o -name '*.rs' -o -name '*.sh' -o -name '*.c' -o -name '*.cpp' -o -name '*.h' \) | head -200` to get the lay of the land.
3. **Understand the structure** — `find . -type d -not -path '*/\.*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/venv/*' -not -path '*/.venv/*' | head -100`
4. **Run the mechanical linter** — execute `uv run --project ~/dev/audit audit-lint .` to get AST-level findings (nesting depth, function length, magic numbers, missing docstrings, duplicate blocks). This gives you a baseline of mechanical issues before the deep analysis.
5. **Select applicable standards** — based on the languages detected, read the relevant sections of [STANDARDS.md](STANDARDS.md). Build a list of which standards apply to this codebase. If the codebase is offensive tooling (C2, implant, loader, post-exploitation — check `CLAUDE.md`, imports, and project structure for indicators), include the **Offensive Tooling & OPSEC** standards.
6. **Prepare the audit directory** — run `mkdir -p docs/audit` in the project root.

## Phase 1: Deep analysis (parallel agents)

Launch a **Workflow** that fans out one agent per check dimension. Each agent reads the full check specification from [CHECKS.md](CHECKS.md) for its dimension, plus the applicable standards from [STANDARDS.md](STANDARDS.md), then audits the codebase.

The dimensions are:

### Python dimensions (if Python files present)
1. **magic-values** — Numeric/string literals that should be named constants
2. **nesting-and-flow** — Deep indentation, missing early returns, complex conditionals
3. **abstraction** — Missed class opportunities, god functions, copy-paste code, functions doing too many things
4. **documentation** — Missing/misleading docstrings, undocumented parameters, misleading names
5. **type-safety** — Missing type hints, `Any` usage, untyped returns, dict-as-struct
6. **dead-code** — Unreachable branches, unused imports/variables/functions, commented-out code

### TypeScript/JavaScript dimensions (if TS/JS files present)
7. **ts-patterns** — `any` usage, missing discriminated unions, boolean flag states, raw JSON, missing types
8. **react-patterns** — Derived state in useState, wrong useEffect usage, missing error boundaries, prop drilling
9. **ts-structure** — Barrel files, missing path aliases, component splitting without symptoms

### C/C++ dimensions (if C/C++ files present)
10. **c-safety** — Memory safety (buffer overflows, use-after-free, double-free, null derefs), integer overflow, undefined behaviour. Cite CERT C MEM/INT/ARR rules, MISRA rules, NASA Power of 10.
11. **c-quality** — Function length (NASA Rule 4: 60 lines max), nesting depth, assertion density (NASA Rule 5), preprocessor discipline (NASA Rule 8), pointer depth (NASA Rule 9). Cite NASA Power of 10 rules.

> **The NASA Power of 10 rules are C rules and stay in this dimension.** Rule 4's
> 60-line limit, Rule 5's assertion density and Rule 9's pointer depth do not
> apply to a Python or TypeScript codebase and must not be cited against one.
> This leaked once and cost real work: a Python-only project was issued a
> "two functions exceed the NASA Rule 4 / 60-line bar" ticket that survived
> three months before measurement showed the codebase held 97 such functions
> and had never adopted the rule. Python's own length signal is
> `MAX_FUNCTION_LINES = 50` in `src/audit/lint.py` (measured on body lines),
> reported under dimension 3 **abstraction** as a god-function smell — a
> *symptom to investigate*, not a threshold to enforce. If a project wants a
> length rule it must write one into its own style guide; absent that, report
> length only where it is evidence for a different finding.

### Go dimensions (if Go files present)
12. **go-patterns** — Error handling (check returns, wrap with context), goroutine leaks, interface compliance, naming conventions. Cite Effective Go, Uber Go Style Guide.

### Rust dimensions (if Rust files present)
13. **rust-patterns** — Unsafe block discipline, error handling (Result/Option usage), API design, clippy categories. Cite Rust API Guidelines, ANSSI Rust Secure Coding.

### Universal dimensions (always run)
14. **naming** — Inconsistent naming conventions, misleading names, abbreviations without context
15. **error-handling** — Bare except/catch, swallowed errors, missing error context, panic in library code
16. **security** — Hardcoded secrets, SQL injection, command injection, path traversal, XSS, SSRF. Every finding MUST cite the OWASP Top 10 category AND the CWE number. Reference OWASP ASVS verification level where applicable.
18. **enforcement** — Rules the project *declares* and does not *enforce*. Every other dimension finds code that breaks a rule; this one finds rules that break nothing. See [CHECKS.md](CHECKS.md) §18. **Run the declared checks — do not read the config and assume it passes.**
19. **architecture-coupling** — Where the seams are: module dependency direction, framework/vendor types leaking into domain code, handlers that aren't thin, one model serving two roles, collaborators constructed rather than injected, scattered construction, config read where it's used. See [CHECKS.md](CHECKS.md) §19 *Architecture & Coupling*. Works between modules; §3 **abstraction** works inside one. **Nearly every finding here is `authority: external` — a layering rule the project never wrote down is a proposal, not a defect.** Cites SOLID (DIP/ISP), Ousterhout, DDD tactical patterns, 12-Factor III.

### Offensive tooling dimension (if offensive tooling detected in Phase 0)
17. **opsec** — String artefacts, API usage patterns, memory hygiene, network OPSEC, build/release hygiene. Cite MITRE ATT&CK technique IDs where relevant. Cross-reference Elastic/Sigma/YARA detection rules if a pattern would trigger known detections.

Each agent MUST:
- Read the relevant section of [CHECKS.md](CHECKS.md) for detailed guidance on what to look for
- Read the applicable sections of [STANDARDS.md](STANDARDS.md) for the authoritative rules
- Read any project-specific style guide found in Phase 0
- Read the `lint_assist.py` output for mechanical findings in their dimension
- Search the codebase methodically — don't just spot-check
- Return structured findings: `{file, line, check, severity, description, standard, suggestion, authority}`
  - `standard` is the specific rule cited (e.g. "NASA Power of 10 Rule 4", "CWE-78", "CERT C MEM33-C", "OWASP A03:2021")
  - `authority` is either **`project`** (the rule is written in this project's own `CLAUDE.md` / style guide — quote the line) or **`external`** (it comes only from STANDARDS.md). Security and memory-safety findings are always actionable regardless. For everything else the distinction is load-bearing: an `external`-only finding is a **proposal to adopt a convention**, not a defect, and must be reported as one. Filing it as a defect is how a codebase acquires rules nobody agreed to and then acquires tickets to enforce them.

## Phase 2: Cross-verification

After all dimension agents report back:

1. **Deduplicate** — same file+line reported by multiple dimensions → merge into one finding, keep all cited standards
2. **Verify** — for any finding that seems borderline, read the actual code and confirm it's real
3. **Rank** — sort by severity (critical → major → minor), then by file path for grouping

## Phase 3: Report

Generate a dated filename: `YYYYMMDD_audit.md` using today's date.

Write the full report to **`docs/audit/YYYYMMDD_audit.md`** in the project root.

The report format:

```markdown
---
date: YYYY-MM-DD
scope: <directory audited>
languages:
  - python
  - typescript
standards_applied:
  - "NASA/JPL Power of 10"
  - "CERT C"
  - "OWASP Top 10 (2021)"
  - "..."
findings:
  critical: N
  major: N
  minor: N
  total: N
---

# Audit Report — YYYY-MM-DD

> Audited `<directory>` on <date>

## Summary

| Severity | Count |
|----------|-------|
| Critical | N     |
| Major    | N     |
| Minor    | N     |

### Standards referenced

| Standard | Findings | URL |
|----------|----------|-----|
| OWASP A03:2021 — Injection | 3 | https://owasp.org/Top10/A03_2021-Injection/ |
| NASA Power of 10 Rule 4 | 5 | https://spinroot.com/gerard/pdf/P10.pdf |
| ... | ... | ... |

### Systemic patterns

1. ...
2. ...
3. ...

### Recommended fix priority

1. ...
2. ...
3. ...

---

## Findings by file

### path/to/file.py

- **[CRITICAL]** Line 42: SQL query built with f-string interpolation — use parameterised queries
  - *Standard: OWASP A03:2021 — Injection, CWE-89*
- **[MAJOR]** Lines 15-89: `process_data()` is 74 lines with 6 levels of nesting — extract early returns and split into helpers
  - *Standard: NASA Power of 10 Rule 4, Cognitive Complexity*
- **[MINOR]** Line 7: Magic number `86400` — use `SECONDS_PER_DAY = 86400`
  - *Standard: PEP 8 — Constants*

### path/to/other.py

- ...
```

### Update the audit index

After writing the audit report, update (or create) `docs/audit/README.md`:

```markdown
# Audit History

| Date | Scope | Critical | Major | Minor | Total | Report |
|------|-------|----------|-------|-------|-------|--------|
| 2026-07-31 | `src/` | 2 | 14 | 23 | 39 | [20260731_audit.md](20260731_audit.md) |
| ... | ... | ... | ... | ... | ... | ... |
```

Append the new row. If the file doesn't exist, create it with the header and first row.
Keep rows in reverse chronological order (newest first).

After writing the report and index, print a one-line confirmation: the path and the finding counts by severity.

## Phase 4: Memory extraction

After the report is written, review the **systemic patterns** section and decide what's
worth remembering for future work on this codebase. Save memories using the standard
memory system at `~/.claude/projects/<project-path>/memory/`.

### What to save as memories

**Project memories** (type: `project`) — codebase-specific patterns that would inform
future audits or development:
- Recurring architectural smells (e.g. "service layer consistently has god functions mixing I/O and logic")
- Systematic gaps (e.g. "no type hints anywhere in the API boundary layer")
- Security posture observations (e.g. "all SQL queries use parameterised queries except the reporting module")
- Standards compliance patterns (e.g. "codebase follows CERT C closely but ignores NASA Power of 10 function length limits")

**Feedback memories** (type: `feedback`) — learnings about how to audit this project
better next time:
- What the project's `CLAUDE.md` said that overrode default rules
- Which check dimensions produced the most/fewest findings (focus future effort)
- Any false positive patterns that should be excluded next time

### How to save

🚨 **`/prep-compact` Phase 4 is the canonical memory-writing spec — follow it, do not
restate it here.** It owns the directory convention (the cwd with `/` → `-`), the
nested-`metadata:` frontmatter dialect, and the duplicate check. Three commands used
to write memories with three different specs; per CODE_STYLE rule 46, same language
and same process means **extract**, not three copies that agree today and drift
tomorrow.

Audit-specific parts, which are the only things that belong here:

- **Name them `audit-<project>-<topic>`** so a later audit can find its predecessors.
- **`metadata.type` is `project`** for codebase patterns, `feedback` for
  audit-method learnings.
- **2–5 memories maximum per audit.** An audit generates hundreds of findings; the
  report holds those. Only systemic, recurring themes are memories.
- Body carries `**Why:**` and `**How to apply:**` lines.

⚠️ **Before adding a `MEMORY.md` pointer, measure it.** `MEMORY.md` has a hard cap
that **truncates from the bottom, silently**, and an audit arrives with 2–5 pointers
at once — enough to push a near-full index over and destroy its newest entries with
no error anywhere. Run the project's `.claude/hooks/doctrine-measure.sh` if it has
one, or `wc -c` the index. If it is at cap, the pointers do not go in until
something comes out; the memory FILES are still written either way.

## What NOT to report

- Style issues already caught by the project's configured linter (ruff, eslint, etc.)
- Opinions that contradict the project's explicit style guide
- One-off deviations in test files (test code has different standards)
- Generated code, vendored dependencies, or `node_modules`/`venv`
- Things that are clearly intentional based on comments or context
