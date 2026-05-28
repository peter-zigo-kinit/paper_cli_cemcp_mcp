# Development setup

This repo holds two Python projects that must stay environmentally isolated:

- **Vendored harness** — `cemcpsec-C1F2/Performance Evaluation/mcp-bench/`. The starting-point CE-MCP implementation. Pinned by its own `requirements.txt`.
- **Fresh implementation** — `src/` at the repo root. Our calibration wrapper, report generator, and later the CLI-wrapper cell + LangChain swap. Pinned by `pyproject.toml` at the repo root (added when Slice 2 lands).

Each project has its own venv at its own root. The primary reason is dependency-conflict avoidance: the fresh implementation will eventually pull in LangChain and other libraries that have no business living next to the vendored pins. A secondary reason is reproducibility — the vendored baseline's environment is whatever `requirements.txt` resolves to, full stop.

| | Vendored harness | Fresh implementation |
| --- | --- | --- |
| Venv location | `cemcpsec-C1F2/Performance Evaluation/mcp-bench/.venv` | `.venv` at repo root |
| Dependency source | `cemcpsec-C1F2/Performance Evaluation/mcp-bench/requirements.txt` | `pyproject.toml` at repo root (when introduced) |
| Tooling | `python -m venv` + `pip` | `uv` |
| Code lives in | `cemcpsec-C1F2/Performance Evaluation/mcp-bench/` | `src/` |

The fresh implementation invokes the vendored harness via `subprocess` (not `import`). The two venvs never need to see each other.

A single `.env` at the repo root carries the credentials (`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION`, optional `AZURE_JUDGE_DEPLOYMENT` and `AZURE_AGENT_DEPLOYMENT`). The vendored runner reads them from the shell environment; the fresh-impl wrapper will load them via `python-dotenv`.

## Set up the vendored harness venv

```bash
cd "cemcpsec-C1F2/Performance Evaluation/mcp-bench"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

One-off installs needed by the smoke run:

```bash
# Math MCP (Node)
(cd mcp_servers/math-mcp && npm install && npm run build)

# Unit Converter MCP (uv — its own self-contained venv, separate from the harness venv)
(cd mcp_servers/unit-converter-mcp && uv sync)

# Loader expects this file to exist; contents irrelevant for Math MCP + Unit Converter
touch mcp_servers/api_key
```

## Run the Phase 1 smoke

From the repo root:

```bash
set -a && source .env && set +a
cd "cemcpsec-C1F2/Performance Evaluation/mcp-bench"
source .venv/bin/activate
python3 global_runner.py \
    --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
    --servers "Math MCP" \
    --models gpt-4.1-mini \
    --task-limit 1 \
    --output-dir ./results/smoke
```

A successful run produces a CSV + JSON under `results/smoke/` with one row per (cell, task) — both `MCP` (MCP-client) and `CE` (CE-MCP) cells, each with non-zero `total_tokens` and judge scores.

## Set up the fresh-implementation venv

Not yet — `pyproject.toml` lands with Slice 2. When it does:

```bash
cd /home/peter/organizations/paper_cli_mcp_cemcp
uv sync
```

## Path note

`Performance Evaluation` contains a space. Always quote paths into the vendored project (`"cemcpsec-C1F2/Performance Evaluation/mcp-bench"`). Scripts that hardcode the path must use quotes; unquoted globs will silently drop the second word.
