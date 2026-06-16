"""Harness unit tests for CSVTracker generated code file export."""

import sys
import tempfile
import unittest
from pathlib import Path

MCP_BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(MCP_BENCH))

from benchmark.csv_tracker import CSVTracker  # noqa: E402


class TestCSVTrackerGeneratedCode(unittest.TestCase):
    def test_writes_readable_py_file_for_ce_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = CSVTracker(output_dir=tmp, filename="test_results.csv")
            code = "async def main():\n    return (True, 'done')\n"

            tracker.add_task_result(
                task_id="unit_converter_000",
                server="Unit Converter",
                model="gpt-4.1-mini",
                agent_type="CE",
                agent_execution_time=1.0,
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                query="test query",
                answer="done",
                code=code,
            )

            code_path = Path(tmp) / "unit_converter_000_CE_generated.py"
            self.assertTrue(code_path.exists())
            contents = code_path.read_text(encoding="utf-8")
            self.assertIn("task_id: unit_converter_000", contents)
            self.assertIn("async def main():", contents)
            self.assertIn("return (True, 'done')", contents)

    def test_skips_py_file_when_code_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tracker = CSVTracker(output_dir=tmp, filename="test_results.csv")

            tracker.add_task_result(
                task_id="unit_converter_000",
                server="Unit Converter",
                model="gpt-4.1-mini",
                agent_type="MCP",
                agent_execution_time=1.0,
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                query="test query",
                answer="done",
                code=None,
            )

            self.assertFalse(list(Path(tmp).glob("*_generated.py")))


if __name__ == "__main__":
    unittest.main()
