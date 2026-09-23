# Audit

Deep code quality audit tool — mechanical AST linter + Claude Code skill for LLM-powered analysis.

## Structure

- `SKILL.md` — Claude Code skill definition. This checkout is canonical; `~/.claude/skills/audit` is a symlink to it
- `CHECKS.md` — Check catalogue: what each dimension agent looks for
- `STANDARDS.md` — Authoritative standards catalogue (OWASP, CWE, PEP, Effective Go, Rust API Guidelines, and the reference books)
- `src/audit/lint.py` — Mechanical linter (Python via AST; TS and shell via line regex)
- `tests/test_lint.py` — Regression tests, one per fixed bug

## Usage

### As a Claude Code skill

```
/audit
```

Runs in the current working directory. Spawns parallel agents per check dimension.

### Mechanical linter only

```bash
uv run audit-lint <directory> [--lang python|typescript|shell|all] [--summary]
```

## Development

```bash
uv sync
uv run audit-lint . --summary
uv run ruff check src/
```
