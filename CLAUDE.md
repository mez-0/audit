# Audit

Deep code quality audit tool — mechanical AST linter + Claude Code skill for LLM-powered analysis.

## Structure

- `SKILL.md` — Claude Code skill definition (symlinked from `~/.claude/skills/audit/`)
- `CHECKS.md` — Check catalogue: what each dimension agent looks for
- `STANDARDS.md` — Authoritative standards catalogue (OWASP, CERT, NASA, PEP, etc.)
- `src/audit/lint.py` — Mechanical linter (AST-based, zero dependencies beyond stdlib)

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
