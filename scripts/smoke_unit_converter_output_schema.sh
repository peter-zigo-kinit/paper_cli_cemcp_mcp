#!/usr/bin/env bash
# Smoke test for GitHub issue #16: Unit Converter outputSchema + harness propagation.
#
# Runs global_runner on unit_converter_000 with both cells:
#   - traditional (MCP-client)
#   - code_execution (CE-MCP)
#
# Prerequisites:
#   - Repo root .env with Azure/OpenAI credentials
#   - mcp-bench .venv (see docs/development.md)
#   - unit-converter-mcp: (cd mcp_servers/unit-converter-mcp && uv sync)
#
# Usage:
#   ./scripts/smoke_unit_converter_output_schema.sh
#   ./scripts/smoke_unit_converter_output_schema.sh --verbose
#
# Results land under results/smoke_unit_converter_output_schema/<timestamp>/
# (gitignored). Expect two evaluation rows (MCP + CE) in the JSON/CSV output.
# Full console log: runner.log in the same <timestamp> directory.
# CE generated code: <task_id>_CE_generated.py in the same directory.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MCP_BENCH="${REPO_ROOT}/cemcpsec-C1F2/Performance Evaluation/mcp-bench"
VENV_PY="${MCP_BENCH}/.venv/bin/python"
ENV_FILE="${REPO_ROOT}/.env"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="${REPO_ROOT}/results/smoke_unit_converter_output_schema/${TIMESTAMP}"
RUNNER_LOG="${OUTPUT_DIR}/runner.log"

if [[ ! -x "${VENV_PY}" ]]; then
  echo "error: harness venv not found at ${MCP_BENCH}/.venv" >&2
  echo "hint: see docs/development.md (Set up the vendored harness venv)" >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "error: missing ${ENV_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a && source "${ENV_FILE}" && set +a

cd "${MCP_BENCH}"

mkdir -p "${OUTPUT_DIR}"

echo "==> Issue #16 smoke: Unit Converter outputSchema (MCP-client + CE-MCP)"
echo "    output: ${OUTPUT_DIR}"
echo "    log:    ${RUNNER_LOG}"
echo

"${VENV_PY}" global_runner.py \
  --tasks-file tasks/mcpbench_tasks_single_runner_format.json \
  --servers "Unit Converter" \
  --models gpt-4.1-mini \
  --task-limit 1 \
  --output-dir "${OUTPUT_DIR}" \
  "$@" 2>&1 | tee "${RUNNER_LOG}"

echo
echo "==> Done. Check ${OUTPUT_DIR} for global_evaluation_*.json, runner.log, and *_CE_generated.py"
echo "    Expect agent_type MCP (traditional) and CE (code_execution) rows."
echo "    After #16: prompts should include Output Schema for convert_batch."
