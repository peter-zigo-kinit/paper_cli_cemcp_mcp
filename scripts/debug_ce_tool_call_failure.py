#!/usr/bin/env python3
"""Reproduce CE-MCP completion despite failed real MCP tool calls.

This script is a focused harness for issue #13. It starts the Unit Converter
MCP server, executes a code-execution snippet that calls a nonexistent tool,
and reports whether the executor still marks the run as successful/complete.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MCP_BENCH_DIR = REPO_ROOT / "cemcpsec-C1F2" / "Performance Evaluation" / "mcp-bench"
MCP_SERVERS_DIR = MCP_BENCH_DIR / "mcp_servers"
DEFAULT_RESULT_JSON = (
    REPO_ROOT
    / "results"
    / "full_vendored_eval"
    / "20260601_142646"
    / "single"
    / "global_evaluation_20260601_142647.json"
)


DEFAULT_REPRO_CODE = r'''
async def main():
    async def convert(value, from_unit, to_unit):
        try:
            await server_manager.call_tool(
                "UnitConversionServer:convert_units",
                {"value": value, "from_unit": from_unit, "to_unit": to_unit},
            )
        except Exception:
            return None

    converted = await convert(350, "degF", "degC")
    answer = (
        "Converted value: "
        f"{converted if converted is not None else 'N/A'} degC. "
        "This intentionally mirrors the corrupted CE result shape."
    )
    return True, answer
'''

DEFAULT_PROMPT_INSPECTION_TASK = (
    "Convert unit converter sensor readings. Use Unit Converter tools to list "
    "supported units, convert temperature, pressure, length, and batch unit requests."
)


def add_mcp_bench_to_path() -> None:
    sys.path.insert(0, str(MCP_BENCH_DIR))


def load_code_from_result(path: Path, server: str, agent_type: str, contains: str | None) -> str:
    if not path.is_file():
        raise SystemExit(
            f"Result JSON not found: {path}\n"
            "Pass --result-json /path/to/global_evaluation_*.json, or omit "
            "--code-from-result to use the built-in minimal repro."
        )

    with path.open("r", encoding="utf-8") as handle:
        rows = json.load(handle)

    for row in rows:
        if row.get("server") != server:
            continue
        if row.get("agent_type") != agent_type:
            continue
        if contains and contains not in row.get("query", ""):
            continue
        code = row.get("code")
        if code:
            return code

    criteria = f"server={server!r}, agent_type={agent_type!r}"
    if contains:
        criteria += f", query contains {contains!r}"
    raise SystemExit(f"No result row with code matched {criteria} in {path}")


def build_unit_converter_config() -> dict[str, Any]:
    commands_path = MCP_SERVERS_DIR / "commands.json"
    with commands_path.open("r", encoding="utf-8") as handle:
        commands = json.load(handle)

    server_config = commands["Unit Converter"]
    cwd_name = server_config["cwd"].removeprefix("../").removeprefix("./")
    cwd = MCP_SERVERS_DIR / cwd_name

    if not cwd.is_dir():
        raise SystemExit(f"Unit Converter cwd does not exist: {cwd}")

    resolved_config = {
        "name": "Unit Converter",
        "command": server_config["cmd"].split(),
        "env": {
            key: os.environ[key]
            for key in server_config.get("env", [])
            if key in os.environ
        },
        "cwd": str(cwd),
        "transport": server_config.get("transport", "stdio"),
        "port": server_config.get("port"),
        "endpoint": server_config.get("endpoint", "/mcp"),
    }
    return resolved_config


def summarize_execution(result: dict[str, Any], tool_calls: list[dict[str, Any]], full_output: bool) -> dict[str, Any]:
    failed_calls = [call for call in tool_calls if not call.get("success")]
    output = result.get("output", "")
    summary = {
        "executor_success": result.get("success"),
        "executor_complete": result.get("complete"),
        "executor_error": result.get("error"),
        "final_answer": result.get("final_answer"),
        "tool_call_count": len(tool_calls),
        "failed_tool_call_count": len(failed_calls),
        "failed_tools": [
            {"tool": call.get("tool"), "error": call.get("error")}
            for call in failed_calls
        ],
        "bug_reproduced": bool(failed_calls)
        and result.get("success") is True
        and result.get("complete") is True,
        "output": output if full_output else output[:2000],
    }
    if not full_output and len(output) > 2000:
        summary["output_truncated"] = len(output) - 2000
    return summary


async def run(args: argparse.Namespace) -> int:
    add_mcp_bench_to_path()

    from agent.code_execution_executor import CodeExecutionTaskExecutor
    from benchmark.runner import ConnectionManager

    code = DEFAULT_REPRO_CODE
    if args.code_from_result:
        code = load_code_from_result(
            args.result_json,
            server=args.server,
            agent_type=args.agent_type,
            contains=args.query_contains,
        )

    server_config = build_unit_converter_config()

    async with ConnectionManager([server_config]) as connection:
        assert connection.server_manager is not None
        tools = sorted(connection.server_manager.all_tools.keys())
        print("Connected MCP tools:")
        print(json.dumps(tools, indent=2))
        print()

        invalid_tool = "UnitConversionServer:convert_units"
        if invalid_tool in connection.server_manager.all_tools:
            raise SystemExit(f"Unexpectedly found invalid repro tool: {invalid_tool}")

        executor = CodeExecutionTaskExecutor(
            server_manager=connection.server_manager,
            openai_api_key=args.openai_api_key,
            model=args.model,
            max_turns=1,
            mcp_servers_dir=str(MCP_SERVERS_DIR),
        )

        prompt_tools = executor._discover_tools_for_prompt(DEFAULT_PROMPT_INSPECTION_TASK)
        executor.all_tools = prompt_tools

        result = await executor._execute_code(code, turn=1)
        summary = summarize_execution(result, executor.tool_calls, args.full_output)

        print("CE execution summary:")
        print(json.dumps(summary, indent=2, default=str))

        if summary["bug_reproduced"]:
            print("\nBUG_REPRODUCED: failed real MCP tool calls still produced success=True and complete=True.")
            return 1 if args.fail_on_reproduced else 0

        print("\nBUG_NOT_REPRODUCED: executor did not mark failed tool calls as successful completion.")
        return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--code-from-result",
        action="store_true",
        help="Replay the generated code from the vendored evaluation JSON instead of the built-in minimal repro.",
    )
    parser.add_argument(
        "--result-json",
        type=Path,
        default=DEFAULT_RESULT_JSON,
        help="Evaluation JSON to read when --code-from-result is set.",
    )
    parser.add_argument("--server", default="Unit Converter")
    parser.add_argument("--agent-type", default="CE")
    parser.add_argument(
        "--query-contains",
        default="unit_converter_000",
        help="Substring used to select the result row when --code-from-result is set.",
    )
    parser.add_argument("--model", default="debug-model")
    parser.add_argument(
        "--openai-api-key",
        default=os.environ.get("OPENAI_API_KEY", "debug-key-not-used"),
        help="Only needed to construct CodeExecutionTaskExecutor; _execute_code does not call the LLM.",
    )
    parser.add_argument(
        "--full-output",
        action="store_true",
        help="Print the full captured executor output instead of truncating it.",
    )
    parser.add_argument(
        "--fail-on-reproduced",
        action="store_true",
        help="Exit 1 when the current bug is reproduced, useful for turning this into a failing check.",
    )
    return parser.parse_args()


def main() -> int:
    return asyncio.run(run(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
