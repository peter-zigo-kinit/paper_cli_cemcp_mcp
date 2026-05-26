"""
Benchmark Runner for executing both approaches on multiple tasks.

This module provides functionality to run both Code Execution MCP and
Traditional MCP benchmarks on a set of tasks and collect results.
"""
import json
import os
from typing import Dict, Any, List
from datetime import datetime
import sys
from pathlib import Path
from app.benchmarks.code_execution_mcp import CodeExecutionBenchmark
from app.benchmarks.traditional_mcp import TraditionalMCPBenchmark
from app.app_logging.logger import setup_logger
from costume_mcp_servers import reset_shared_db

logger = setup_logger(__name__)


class BenchmarkRunner:
    """
    Runner for executing both benchmark approaches on multiple tasks.
    """
    
    def __init__(self):
        """Initialize both benchmark instances."""
        self.code_execution_benchmark = CodeExecutionBenchmark()
        self.traditional_benchmark = TraditionalMCPBenchmark()
        self.initialized = False
    
    async def initialize_async(self):
        """Initialize both benchmarks."""
        if self.initialized:
            logger.info("Benchmark runner already initialized")
            return
        
        await self.code_execution_benchmark.initialize_async()
        
        await self.traditional_benchmark.initialize_async()
        
        self.initialized = True
        logger.info("Benchmark runner initialized successfully")
    
    async def run_task_on_both_benchmarks(
        self, 
        task: Dict[str, Any],
        max_turns: int = 3,
        approaches: List[str] = None,
        use_judge: bool = False
    ) -> Dict[str, Any]:
        """
        Run a single task on selected benchmarks and return comparison results.
        
        Args:
            task: Task dictionary with task_id, user_query, expected_behaviour, expected_output
            max_turns: Maximum number of LLM turns for code execution approach
            approaches: List of approaches to run - ["code_execution"], ["traditional"], or both
            
        Returns:
            Dictionary containing results from selected benchmarks
        """
        if not self.initialized:
            raise RuntimeError(
                "BenchmarkRunner must be initialized before running tasks. "
                "Call await runner.initialize_async() first."
            )
        
        # Default to both if not specified
        if approaches is None:
            approaches = ["code_execution", "traditional"]
        
        task_id = task.get("task_id")
        user_query = task.get("user_query")
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"RUNNING TASK {task_id}: {user_query}")
        logger.info(f"Selected approaches: {approaches}")
        logger.info(f"{'=' * 80}\n")
        
        # CRITICAL: Reset database ONCE at the start of each task
        await self.reset_database()

        # Initialize result placeholders
        code_exec_result = None
        traditional_result = None
        
        # Run Code Execution MCP benchmark if selected
        if "code_execution" in approaches:
            logger.info(f"Running Code Execution MCP approach... (use_judge: {use_judge})")
            code_exec_result = await self.code_execution_benchmark.run_benchmark_async(
                task=task,
                max_turns=max_turns,
                use_judge=use_judge
            )
        else:
            logger.info("Skipping Code Execution MCP approach")
            code_exec_result = {
                "success": False,
                "output": "",
                "error": "Not executed (approach not selected)",
                "time": 0,
                "llm_calls": [],
                "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "conversation_history": [],
                "turn_details": []
            }
        
        # Run Traditional MCP benchmark if selected
        if "traditional" in approaches:
            logger.info("Running Traditional MCP approach...")
            traditional_result = await self.traditional_benchmark.run_benchmark_async(
                query=user_query
            )
        else:
            logger.info("Skipping Traditional MCP approach")
            traditional_result = {
                "success": False,
                "output": "",
                "error": "Not executed (approach not selected)",
                "time": 0,
                "llm_calls": [],
                "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "conversation_history": [],
                "turn_details": []
            }
        
        # Compile results
        result = {
            "task_id": task_id,
            "user_query": user_query,
            "expected_behaviour": task.get("expected_behaviour", ""),
            "expected_output": task.get("expected_output", ""),
            "timestamp": datetime.now().isoformat(),
            "code_execution_mcp": code_exec_result,
            "traditional_mcp": traditional_result,
            "comparison": {
                "code_exec_success": code_exec_result.get("success", False),
                "traditional_success": traditional_result.get("success", False),
                "code_exec_time": code_exec_result.get("time", 0),
                "traditional_time": traditional_result.get("time", 0),
                "code_exec_llm_calls": len(code_exec_result.get("llm_calls", [])),
                "traditional_llm_calls": len(traditional_result.get("llm_calls", [])),
                "code_exec_total_tokens": code_exec_result.get("tokens", {}).get("total_tokens", 0),
                "traditional_total_tokens": traditional_result.get("tokens", {}).get("total_tokens", 0),
                "time_diff": code_exec_result.get("time", 0) - traditional_result.get("time", 0),
                "llm_calls_diff": len(code_exec_result.get("llm_calls", [])) - len(traditional_result.get("llm_calls", [])),
                "tokens_diff": code_exec_result.get("tokens", {}).get("total_tokens", 0) - traditional_result.get("tokens", {}).get("total_tokens", 0),
            }
        }
        
        logger.info(f"\nTask {task_id} completed!")
        if "code_execution" in approaches:
            logger.info(f"Code Execution: {code_exec_result.get('time', 0):.2f}s, "
                       f"{len(code_exec_result.get('llm_calls', []))} LLM calls, "
                       f"{code_exec_result.get('tokens', {}).get('total_tokens', 0)} tokens")
        if "traditional" in approaches:
            logger.info(f"Traditional: {traditional_result.get('time', 0):.2f}s, "
                       f"{len(traditional_result.get('llm_calls', []))} LLM calls, "
                       f"{traditional_result.get('tokens', {}).get('total_tokens', 0)} tokens")
        
        return result
    
    async def run_all_tasks(
        self,
        tasks: List[Dict[str, Any]],
        max_turns: int = 3,
        approaches: List[str] = None,
        use_judge: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Run all tasks on selected benchmarks.
        
        Args:
            tasks: List of task dictionaries
            max_turns: Maximum number of LLM turns for code execution approach
            approaches: List of approaches to run - ["code_execution"], ["traditional"], or both
            use_judge: Whether to use LLM as judge for code execution (CE only)
            
        Returns:
            List of result dictionaries for each task
        """
        if not self.initialized:
            raise RuntimeError(
                "BenchmarkRunner must be initialized before running tasks. "
                "Call await runner.initialize_async() first."
            )
        
        # Default to both if not specified
        if approaches is None:
            approaches = ["code_execution", "traditional"]
        
        results = []
        
        for task in tasks:
            try:
                result = await self.run_task_on_both_benchmarks(task, max_turns, approaches, use_judge)
                results.append(result)
            except Exception as e:
                logger.error(f"Error running task {task.get('task_id')}: {str(e)}")
                # Create error result with all required fields for TaskResult model
                error_result = {
                    "task_id": task.get("task_id"),
                    "user_query": task.get("user_query"),
                    "expected_behaviour": task.get("expected_behaviour", ""),
                    "expected_output": task.get("expected_output", ""),
                    "timestamp": datetime.now().isoformat(),
                    "code_execution_mcp": {
                        "success": False,
                        "output": "",
                        "error": str(e),
                        "time": 0,
                        "llm_calls": [],
                        "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        "conversation_history": [],
                        "turn_details": []
                    },
                    "traditional_mcp": {
                        "success": False,
                        "output": "",
                        "error": str(e),
                        "time": 0,
                        "llm_calls": [],
                        "tokens": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        "conversation_history": [],
                        "turn_details": []
                    },
                    "comparison": {
                        "code_exec_success": False,
                        "traditional_success": False,
                        "code_exec_time": 0,
                        "traditional_time": 0,
                        "code_exec_llm_calls": 0,
                        "traditional_llm_calls": 0,
                        "code_exec_total_tokens": 0,
                        "traditional_total_tokens": 0,
                        "time_diff": 0,
                        "llm_calls_diff": 0,
                        "tokens_diff": 0,
                    }
                }
                results.append(error_result)
        
        return results
    
    def load_tasks_from_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load tasks from a JSON file.
        
        Args:
            file_path: Path to JSON file containing tasks
            
        Returns:
            List of task dictionaries
        """
        if not os.path.exists(file_path):
            logger.error(f"Task file not found: {file_path}")
            return []
        
        with open(file_path, 'r') as f:
            tasks = json.load(f)
        
        logger.info(f"Loaded {len(tasks)} tasks from {file_path}")
        return tasks

    async def reset_database(self):
        """Reset the database to original state."""
        # This ensures both approaches start with a clean database state
        logger.info("Resetting database to original state for new task...")
        try:
            reset_shared_db()
            # Small delay to ensure file system sync and MCP server process detection
            import asyncio
            await asyncio.sleep(0.2)
            logger.info("Database reset complete. Fresh database ready for benchmarks.\n")
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            # Continue anyway - the reset might have partially succeeded
            logger.warning("Continuing with benchmark despite reset error...\n")
        
    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """
        Save benchmark results to a JSON file.
        
        Args:
            results: List of result dictionaries
            output_path: Path to output JSON file
        """
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Results saved to {output_path}")
    
    async def cleanup_async(self):
        """Cleanup benchmark resources."""
        logger.info("Cleaning up benchmark runner...")
        await self.code_execution_benchmark.cleanup_async()
        await self.traditional_benchmark.cleanup_async()
        logger.info("Benchmark runner cleanup complete")

