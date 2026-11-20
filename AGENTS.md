## Agent guidance

### Agent skills

Project skills live in `.agents/skills/` (source of truth). For Claude Code, `.claude/skills/<name>` is a relative symlink to `../../.agents/skills/<name>/`; when you add a skill, add its symlink too and never copy files into `.claude/skills/`. Do not create `.cursor/skills/`. `CLAUDE.md` is a symlink to this file.

### Issue tracker

Issues are tracked in GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default canonical label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Diagrams (Excalidraw)

For architecture or workflow diagrams as `.excalidraw` files, use the `excalidraw-diagram` skill (from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill)). Renderer setup: `cd .agents/skills/excalidraw-diagram/references && uv sync && uv run playwright install chromium`.

### Development setup

Per-project venv layout (vendored harness vs fresh implementation), harness setup, and how to run the Phase 1 smoke. See `docs/development.md`.
