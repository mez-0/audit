# audit

Deep code quality audit tool for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Combines a mechanical AST linter with LLM-powered analysis across 17 check dimensions, every finding bound to an authoritative standard.

This isn't a linter pass. It's a senior engineer reviewing your codebase with fresh eyes — hunting magic values, deep nesting, missing early returns, copy-paste code, god functions, dead code, security holes, and every other pattern that makes code harder to read, change, and trust.

## Install

Clone the repo and symlink it into your Claude Code skills directory:

```bash
git clone git@github.com:mez-0/audit.git ~/.claude/skills/audit
```

Install the mechanical linter (stdlib only, no external deps):

```bash
cd ~/dev/audit
uv sync
```

That's it. `/audit` is now available globally in every Claude Code session.

## Usage

### Full audit (Claude Code skill)

From any project directory:

```
/audit
```

This runs the full four-phase audit:

1. **Reconnaissance** — reads project style guides, detects languages, runs the mechanical linter, selects applicable standards
2. **Deep analysis** — fans out one LLM agent per check dimension in parallel
3. **Cross-verification** — deduplicates, verifies borderline findings, ranks by severity
4. **Report** — writes a dated report to `docs/audit/YYYYMMDD_audit.md` with findings grouped by file

Requires Opus 4.6 and max effort. It's thorough — expect it to take a few minutes on a medium codebase.

### Mechanical linter only

```bash
# JSON lines output (one finding per line)
audit-lint <directory>

# Summary stats
audit-lint <directory> --summary

# Single language
audit-lint <directory> --lang python
audit-lint <directory> --lang typescript
audit-lint <directory> --lang shell
```

The linter catches things grep can't reliably find via AST analysis: nesting depth, function length, magic numbers in logic, missing docstrings, duplicate code blocks, string-enum candidates, isinstance chains, and stringly-typed access patterns.

## What it checks

### Python

| Dimension | What it hunts |
|-----------|--------------|
| **Magic values** | Numeric/string literals that should be named constants. Same literal in 2+ places escalates to major. |
| **Nesting & flow** | Logic nesting >3 levels deep, missing early returns/guard clauses, complex boolean expressions, nested ternaries. |
| **Abstraction** | God functions (>50 lines, >5 params), copy-paste code, dict-as-struct, registry-vs-elif, isinstance chains, `**kwargs` that hide interfaces. |
| **Documentation** | Missing/misleading docstrings, phantom parameters, names that lie about what the code does. |
| **Type safety** | Missing type hints, `Any` abuse, `# type: ignore` without codes, `Optional` without None checks, dict-as-struct at API boundaries. |
| **Dead code** | Unreachable branches, unused functions/imports/variables, commented-out code, dead feature flags. |

### TypeScript / JavaScript

| Dimension | What it hunts |
|-----------|--------------|
| **TS patterns** | `any` usage, missing discriminated unions, `@ts-ignore` instead of `@ts-expect-error`, raw untyped `.json()` responses, boolean flag states that should be a status union. |
| **React patterns** | Derived state in `useState`, wrong `useEffect` usage (data transform, event handling, derived state), prop drilling through 3+ levels, missing error boundaries, stale closure bugs. |
| **TS structure** | Barrel files that break tree-shaking, deep relative imports, inline style objects not hoisted, direct modification of UI library files. |

### C / C++

| Dimension | What it hunts |
|-----------|--------------|
| **Safety** | Buffer overflows, use-after-free, double-free, null derefs, uninitialised memory, integer overflow, undefined behaviour, format string vulnerabilities, unsafe string functions (`strcpy`, `sprintf`, `gets`). |
| **Quality** | Functions >60 lines (NASA Rule 4), assertion density (NASA Rule 5), variable scope (Rule 6), unchecked return values (Rule 7), preprocessor abuse (Rule 8), pointer depth (Rule 9), `goto`/`setjmp`/recursion (Rule 1). |

### Go

| Dimension | What it hunts |
|-----------|--------------|
| **Patterns** | Unchecked error returns, bare `return err` without wrapping context, goroutine leaks (no cancellation/done channel), `Get`-prefixed getters, stuttering package names, large interfaces, `init()` functions, `panic` in library code. |

### Rust

| Dimension | What it hunts |
|-----------|--------------|
| **Patterns** | `unwrap()`/`expect()` outside tests, `unsafe` blocks without `// SAFETY:` comments, missing `#[must_use]`, stringly-typed APIs, `clone()` to satisfy the borrow checker, `&String`/`&Vec<T>` in parameters. |

### Shell / Bash

| Dimension | What it hunts |
|-----------|--------------|
| **Patterns** | Unquoted variables, missing `set -euo pipefail`, unchecked commands, `eval` usage, temp files without `mktemp`, `[` instead of `[[`, parsing `ls` output. |

### Universal (all languages)

| Dimension | What it hunts |
|-----------|--------------|
| **Naming** | Inconsistent conventions (mixed `snake_case`/`camelCase`), misleading names (`handle_error` that just logs), `utils.py` grab-bags, variables named after implementation instead of meaning. |
| **Error handling** | Bare `except:`/`catch` with `pass`, swallowed errors, missing error context (`raise ValueError("invalid")` — invalid what?), wrong granularity, `assert` for runtime validation. |
| **Security** | SQL/command/HTML injection, hardcoded secrets, path traversal, SSRF, missing auth checks, IDOR, weak crypto, `random` for security. Every finding cites OWASP Top 10 + CWE number. |
| **Architecture & coupling** | Where the seams are, between modules rather than inside one: framework/vendor types reaching into domain code, domain types doing I/O, handlers that aren't thin, one model serving as both stored record and API shape, collaborators constructed instead of injected, scattered construction, config read at the use site. Reported as proposals unless the project declares the rule itself. |

### Offensive tooling (when detected)

| Dimension | What it hunts |
|-----------|--------------|
| **OPSEC** | String artefacts that fingerprint the tool, direct Win32 API imports (should be dynamic resolution), secrets not zeroed after use, RWX memory regions, hardcoded C2 addresses, fixed callback intervals without jitter, debug symbols in release builds, PDB paths in binaries. Cites MITRE ATT&CK technique IDs. |

## Standards referenced

Every finding is bound to an authoritative standard where one exists. The full catalogue is in [STANDARDS.md](STANDARDS.md). Key references:

### Safety-critical

- **[NASA/JPL Power of 10](https://spinroot.com/gerard/pdf/P10.pdf)** — ten rules for safety-critical C. Function length limits, assertion density, scope discipline, preprocessor restrictions, pointer depth.
- **[MISRA C:2012](https://www.misra.org.uk/misra-c/)** — motor industry standard (also used in aerospace, medical, rail). Mandatory/required/advisory rules covering undefined behaviour, type safety, control flow.
- **[CERT C](https://wiki.sei.cmu.edu/confluence/display/c/SEI+CERT+C+Coding+Standard)** / **[CERT C++](https://wiki.sei.cmu.edu/confluence/display/cplusplus/SEI+CERT+C%2B%2B+Coding+Standard)** — Carnegie Mellon's secure coding rules. Memory safety, integer safety, string handling, concurrency.

### Security

- **[OWASP Top 10 (2021)](https://owasp.org/Top10/)** — the backbone of the security dimension. Every security finding maps to one of the ten categories.
- **[OWASP ASVS v4.0](https://owasp.org/www-project-application-security-verification-standard/)** — three verification levels (L1/L2/L3), more granular than Top 10. Authentication, session management, access control, input validation, cryptography.
- **[CWE Top 25](https://cwe.mitre.org/top25/archive/2023/2023_top25_list.html)** — most dangerous software weaknesses. Out-of-bounds write, XSS, SQL injection, use-after-free, command injection.
- **[OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)** — concrete remediation per vulnerability class.

### Language-specific

- **Python:** [PEP 8](https://peps.python.org/pep-0008/), [PEP 257](https://peps.python.org/pep-0257/), [PEP 484/526/585/604](https://peps.python.org/pep-0484/) (type hints), [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html), [Ruff rules](https://docs.astral.sh/ruff/rules/)
- **Go:** [Effective Go](https://go.dev/doc/effective_go), [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments), [Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md), [Google Go Style Guide](https://google.github.io/styleguide/go/)
- **Rust:** [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/), [Clippy lint categories](https://rust-lang.github.io/rust-clippy/master/), [ANSSI Rust Secure Coding](https://anssi-fr.github.io/rust-guide/)
- **TypeScript:** [Google TS Style Guide](https://google.github.io/styleguide/tsguide.html), [React docs](https://react.dev/learn/you-might-not-need-an-effect) (useEffect anti-patterns, state structure), [Bulletproof React](https://github.com/alan2207/bulletproof-react)
- **Shell:** [ShellCheck wiki](https://www.shellcheck.net/wiki/), [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html), [Bash Pitfalls](https://mywiki.wooledge.org/BashPitfalls)

### Architecture

- **[SOLID](https://en.wikipedia.org/wiki/SOLID)** — single responsibility, open/closed, Liskov substitution, interface segregation, dependency inversion
- **[12-Factor App](https://12factor.net/)** — config in environment, stateless processes, logs as event streams
- **[A Philosophy of Software Design](https://www.amazon.com/Philosophy-Software-Design-John-Ousterhout/dp/1732102201)** (Ousterhout) — deep vs shallow modules, pass-through methods, information leakage
- **[Domain-Driven Design](https://www.domainlanguage.com/ddd/reference/)** — tactical patterns: layering, application services, repositories, keeping persistence and wire shapes distinct
- **[Cognitive Complexity](https://www.sonarsource.com/docs/CognitiveComplexity.pdf)** (SonarSource) — better nesting metric than cyclomatic complexity

### Signal sources

A standard tells you *what is authoritative*; it rarely tells you *what to grep for*. The
architecture-and-coupling checks close that gap using signals drawn from a survey of
[ArjanCodes](https://www.youtube.com/@ArjanCodes)' architecture and design videos
(2021–2026) — thin handlers, models serving two roles, collaborators built in place,
test pain as evidence of missing injection.

**The survey supplies signals; the standards above supply the authority.** No finding
cites the survey. Where a check has no standard behind it, it is reported as a proposal
to adopt a convention, never as a defect — see the `authority` field in
[SKILL.md](SKILL.md).

### Offensive tooling

- **[MITRE ATT&CK](https://attack.mitre.org/)** — technique IDs for what the code implements (T1055 process injection, T1071 C2 protocol, etc.)
- **[Elastic Detection Rules](https://github.com/elastic/detection-rules)**, **[Sigma Rules](https://github.com/SigmaHQ/sigma)**, **[YARA Rules](https://github.com/Yara-Rules/rules)** — what defenders look for, cross-referenced when a pattern would trigger a known rule

## Severity levels

| Level | Meaning |
|-------|---------|
| `critical` | Will cause bugs, security vulnerabilities, or operational failures |
| `major` | Significantly harms readability or maintainability |
| `minor` | Style/preference, but a consistent pattern across the codebase |

## Report format

Reports land in `docs/audit/YYYYMMDD_audit.md` with YAML frontmatter (date, scope, languages, standards applied, finding counts), findings grouped by file, systemic patterns, and recommended fix priority. An index at `docs/audit/README.md` tracks audit history.

## Project structure

```
.
├── SKILL.md         # Claude Code skill definition
├── CHECKS.md        # Check catalogue (what each dimension agent looks for)
├── STANDARDS.md     # Authoritative standards catalogue
├── CLAUDE.md        # Project docs for Claude Code
├── pyproject.toml   # Python package config
└── src/audit/
    ├── __init__.py
    └── lint.py      # Mechanical AST linter (stdlib only)
```
