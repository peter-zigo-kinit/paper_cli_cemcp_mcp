"""
Code Execution MCP Benchmark wrapper.

This module provides a benchmark wrapper around the Code Execution MCP approach,
where the LLM generates code that makes MCP calls programmatically.
"""
from typing import Dict, Any

from app.core.orchestrator import RealMCPOrchestrator
from app.app_logging.logger import setup_logger
from app.utils import BenchmarkStorage


# Initialize logger for tracking benchmark operations
logger = setup_logger(__name__)

# Initialize benchmark storage handler
storage = BenchmarkStorage()


# Define directory paths for code execution results data storage
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CODE_EXEC_RESULTS_PATH = DATA_DIR / "code_execution_results.json"
if not CODE_EXEC_RESULTS_PATH.exists():
    CODE_EXEC_RESULTS_PATH.touch()

class CodeExecutionBenchmark:
    """
    Wrapper for Code Execution MCP benchmark.
    
    This class wraps the RealMCPOrchestrator to provide a consistent
    interface with the TraditionalMCPBenchmark for API usage.
    
    The code execution approach:
    1. LLM generates Python code
    2. Code makes MCP calls programmatically
    3. Code is executed in sandbox
    4. Results are returned
    """
    
    def __init__(self, mcp_config_path: str = None):
        """
        Initialize Code Execution Benchmark.
        
        Args:
            mcp_config_path: Path to MCP configuration file (optional)
        """
        # Create orchestrator instance with optional config path
        self._orchestrator = RealMCPOrchestrator()
        
        # Log initialization
        logger.info("Code Execution MCP Benchmark initialized")
    
    async def initialize_async(self):
        """
        Initialize MCP connections asynchronously.
        
        This method initializes the underlying orchestrator which:
        1. Connects to MCP servers
        2. Discovers available tools
        3. Prepares code executor
        """
        # Log initialization start
        logger.info("Initializing Code Execution MCP Benchmark")
        
        # Initialize the orchestrator
        await self._orchestrator.initialize_async()

    
    async def run_benchmark_async(self, task: Dict[str, Any], max_turns: int = 5, use_judge: bool = False) -> Dict[str, Any]:
        """
        Run code execution MCP benchmark for the given query.
        
        This method:
        1. Passes query to orchestrator
        2. Orchestrator runs multi-turn conversation
        3. Returns formatted benchmark results
        
        Args:
            query: User query to process
            max_turns: Maximum number of LLM turns allowed
            use_judge: Whether to use LLM as judge for code safety checks
            
        Returns:
            Dictionary with benchmark results:
                - success: Execution success status
                - output: Final output from code execution
                - error: Error message if any
                - time: Total execution time in seconds
                - llm_calls: List of LLM call details with tokens
                - tokens: Total token usage across all calls
        """
        query = task.get("user_query")
        # Log benchmark start
        logger.info(f"Running Code Execution MCP benchmark for query: {query}, use_judge: {use_judge}")
        
        # Run multi-turn conversation through orchestrator
        result = await self._orchestrator.run_multi_turn_code_async(
            task=task,
            max_turns=max_turns,
            use_judge=use_judge
        )
        
        # Log benchmark completion
        logger.info("Code Execution MCP benchmark completed")
        
        # Save benchmark results to JSON file
        storage.save_result(
            file_path=CODE_EXEC_RESULTS_PATH,
            query=query,
            result=result
        )
        
        # Return results
        return result
    
    async def cleanup_async(self):
        """
        Cleanup benchmark resources after task completion.
        
        NOTE: MCP connections and Docker container remain active for reuse
        across multiple benchmark runs for better performance.
        """
        # Log cleanup start
        logger.info("Cleaning up Code Execution MCP Benchmark")
        
        # Signal orchestrator that task is complete (doesn't close shared resources)
        await self._orchestrator.cleanup_async()
