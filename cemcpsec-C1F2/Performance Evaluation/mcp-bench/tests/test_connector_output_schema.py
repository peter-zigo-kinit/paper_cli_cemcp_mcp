"""Harness unit tests for output_schema propagation into prompts."""

import json
import sys
import unittest
from pathlib import Path

MCP_BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MCP_BENCH))

from mcp_modules.connector import MCPConnector  # noqa: E402


def _sample_output_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "batch_results": {"type": "array"},
            "summary": {
                "type": "object",
                "properties": {
                    "total_requests": {"type": "integer"},
                    "successful_conversions": {"type": "integer"},
                    "failed_conversions": {"type": "integer"},
                },
            },
        },
        "required": ["batch_results", "summary"],
    }


class TestConnectorOutputSchema(unittest.TestCase):
    """Verify format_tools_for_prompt includes Output Schema when present."""

    def test_format_tools_includes_output_schema(self):
        tools = {
            "Unit Converter:convert_batch": {
                "name": "convert_batch",
                "server": "Unit Converter",
                "description": "Perform multiple unit conversions in a single batch request.",
                "input_schema": {"type": "object", "properties": {"requests": {"type": "array"}}},
                "output_schema": _sample_output_schema(),
            }
        }

        prompt = MCPConnector.format_tools_for_prompt(tools)

        self.assertIn("Output Schema:", prompt)
        self.assertIn("batch_results", prompt)
        self.assertIn("summary", prompt)
        self.assertIn("Input Schema:", prompt)

    def test_format_tools_omits_output_schema_when_missing(self):
        tools = {
            "Unit Converter:convert_length": {
                "name": "convert_length",
                "server": "Unit Converter",
                "description": "Convert length between units.",
                "input_schema": {"type": "object"},
            }
        }

        prompt = MCPConnector.format_tools_for_prompt(tools)

        self.assertIn("Input Schema:", prompt)
        self.assertNotIn("Output Schema:", prompt)

    def test_estimate_tools_token_count_includes_output_schema(self):
        tools = {
            "Unit Converter:convert_batch": {
                "name": "convert_batch",
                "server": "Unit Converter",
                "description": "Batch conversions.",
                "input_schema": {"type": "object"},
                "output_schema": _sample_output_schema(),
            }
        }

        stats = MCPConnector.estimate_tools_token_count(tools)

        self.assertGreater(stats["output_schema_tokens"], 0)
        self.assertGreater(
            stats["per_tool_tokens"]["Unit Converter:convert_batch"]["output_schema"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
