#!/usr/bin/env bash
# List MCP tool inputSchema and outputSchema via the harness ConnectionManager.
#
# Prerequisites:
#   - mcp-bench .venv (see docs/development.md)
#   - target MCP server deps installed (e.g. unit-converter-mcp: uv sync)
#
# Usage:
#   ./scripts/list_mcp_tool_schemas.sh
#   ./scripts/list_mcp_tool_schemas.sh --server "Unit Converter"

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_BENCH="${REPO_ROOT}/cemcpsec-C1F2/Performance Evaluation/mcp-bench"
VENV_PY="${MCP_BENCH}/.venv/bin/python"
SERVER="Unit Converter"

usage() {
  cat <<'EOF'
Usage: list_mcp_tool_schemas.sh [--server NAME]

List inputSchema and outputSchema for every tool on an MCP server.

Options:
  --server NAME   Server from mcp_servers/commands.json (default: "Unit Converter")
  -h, --help      Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --server)
      if [[ $# -lt 2 ]]; then
        echo "error: --server requires a value" >&2
        exit 1
      fi
      SERVER="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -x "${VENV_PY}" ]]; then
  echo "error: harness venv not found at ${MCP_BENCH}/.venv" >&2
  echo "hint: see docs/development.md (Set up the vendored harness venv)" >&2
  exit 1
fi

cd "${MCP_BENCH}"

"${VENV_PY}" - "${SERVER}" <<'PY'
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, ".")
from benchmark.runner import ConnectionManager

server_name = sys.argv[1]
commands = json.load(open("mcp_servers/commands.json"))
if server_name not in commands:
    known = ", ".join(sorted(commands))
    raise SystemExit(f"Unknown server {server_name!r}. Known servers: {known}")

sc = commands[server_name]
cwd = Path("mcp_servers") / sc["cwd"].removeprefix("../").removeprefix("./")
cfg = {
    "name": server_name,
    "command": sc["cmd"].split(),
    "cwd": str(cwd),
    "env": {key: os.environ[key] for key in sc.get("env", []) if key in os.environ},
    "transport": sc.get("transport", "stdio"),
    "port": sc.get("port"),
    "endpoint": sc.get("endpoint", "/mcp"),
}

async def main() -> None:
    async with ConnectionManager([cfg]) as conn:
        session = conn.server_manager.sessions[server_name]
        for tool in sorted((await session.list_tools()).tools, key=lambda t: t.name):
            print(f"\n=== {tool.name} ===")
            print("INPUT:", json.dumps(tool.inputSchema, indent=2))
            print("OUTPUT:", json.dumps(getattr(tool, "outputSchema", None), indent=2))

asyncio.run(main())
PY
