"""
FastAPI routes for MCP benchmark comparison dashboard.

This module defines all API endpoints for running benchmarks,
retrieving results, and serving the web interface.
"""
import os
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.models import (
    QueryRequest,
    BenchmarkResponse,
    ComparisonResponse,
    HealthResponse,
    MultiTaskRequest,
    MultiTaskResponse,
    TaskResult
)
from app.benchmarks.benchmark_runner import BenchmarkRunner
# Create single benchmark runner instance - it manages both benchmark instances internally
benchmarkRunner = BenchmarkRunner()
from app.utils import BenchmarkStorage
from app.app_logging.logger import setup_logger

# Initialize logger for tracking API operations
logger = setup_logger(__name__)

# Initialize benchmark storage handler
storage = BenchmarkStorage()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown.
    
    Startup: Log server initialization
    Shutdown: Cleanup MCP connections and Docker containers
    """
    # Startup
    logger.info("=" * 80)
    logger.info("FastAPI Application Starting Up")
    logger.info("=" * 80)
    logger.info(f"DEV_MODE: {os.getenv('DEV_MODE')}")
    # Initialize benchmark runner once - it will initialize both benchmark instances internally
    await benchmarkRunner.initialize_async()

    yield
    
    # Shutdown
    logger.info("=" * 80)
    logger.info("FastAPI Application Shutting Down")
    logger.info("Cleaning up resources...")
    logger.info("=" * 80)
    
    try:
        # Cleanup benchmark runner - it will cleanup both benchmark instances internally
        await benchmarkRunner.cleanup_async()
        logger.info("Server shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {str(e)}")

# Create FastAPI application instance with metadata and lifecycle management
app = FastAPI(
    title="MCP Benchmark Dashboard API",
    description="Compare Traditional MCP vs Code Execution MCP performance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define directory paths for static files and data storage
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

# Define JSON file paths for storing benchmark results
TRADITIONAL_RESULTS_PATH = DATA_DIR / "traditional_mcp_results.json"
CODE_EXEC_RESULTS_PATH = DATA_DIR / "code_execution_results.json"

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Mount static files directory if it exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=FileResponse)
async def serve_dashboard():
    """
    Serve the main dashboard HTML page.
    
    Returns:
        HTML file response with the dashboard interface
    """
    # Construct path to HTML file
    html_path = STATIC_DIR / "index.html"
    
    # Check if HTML file exists
    if not html_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard HTML file not found"
        )
    
    # Return HTML file as response
    return FileResponse(html_path)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify API is running.
    
    Returns:
        HealthResponse with current status and timestamp
    """
    # Return health status with current timestamp
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="1.0.0"
    )


@app.post("/traditional-mcp", response_model=BenchmarkResponse)
async def run_traditional_mcp_benchmark(request: QueryRequest):
    """
    Execute Traditional MCP benchmark for the given query.
    
    This endpoint:
    1. Initializes Traditional MCP benchmark
    2. Runs the benchmark with the provided query
    3. Saves results to JSON file
    4. Returns benchmark results
    
    Args:
        request: QueryRequest containing the user query
        
    Returns:
        BenchmarkResponse with execution results
        
    Raises:
        HTTPException: If benchmark execution fails
    """
    try:
        # Log the benchmark request
        logger.info(f"Running Traditional MCP benchmark for query: {request.query}")
        
        
        # Run the benchmark with user query using benchmarkRunner's instance
        result = await benchmarkRunner.traditional_benchmark.run_benchmark_async(request.query)
        
        # Save benchmark results to JSON file
        storage.save_result(
            file_path=TRADITIONAL_RESULTS_PATH,
            query=request.query,
            result=result
        )
        
        # Format result to match response model
        formatted_result = storage.format_result(result)
        
        # Return successful response with results
        return BenchmarkResponse(
            success=True,
            approach="traditional_mcp",
            result=formatted_result,
            message="Traditional MCP benchmark completed successfully"
        )
        
    except Exception as e:
        # Log error and raise HTTP exception
        logger.error(f"Traditional MCP benchmark error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}"
        )


@app.post("/code-execution-mcp", response_model=BenchmarkResponse)
async def run_code_execution_mcp_benchmark(request: QueryRequest):
    """
    Execute Code Execution MCP benchmark for the given query.
    
    This endpoint:
    1. Initializes Code Execution MCP benchmark
    2. Runs the benchmark with the provided query
    3. Saves results to JSON file
    4. Returns benchmark results
    
    Args:
        request: QueryRequest containing the user query and use_judge flag
        
    Returns:
        BenchmarkResponse with execution results
        
    Raises:
        HTTPException: If benchmark execution fails
    """
    try:
        # Log the benchmark request
        logger.info(f"Running Code Execution MCP benchmark for query: {request.query}, use_judge: {request.use_judge}")
        
        # Run the benchmark with user query using benchmarkRunner's instance
        result = await benchmarkRunner.code_execution_benchmark.run_benchmark_async(
            query=request.query,
            use_judge=request.use_judge
        )
        
        # Save benchmark results to JSON file
        storage.save_result(
            file_path=CODE_EXEC_RESULTS_PATH,
            query=request.query,
            result=result
        )
        
        # Format result to match response model
        formatted_result = storage.format_result(result)
        
        # Return successful response with results
        return BenchmarkResponse(
            success=True,
            approach="code_execution_mcp",
            result=formatted_result,
            message="Code Execution MCP benchmark completed successfully"
        )
        
    except Exception as e:
        # Log error with full traceback
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Code Execution MCP benchmark error:\n{error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}"
        )


@app.get("/compare", response_model=ComparisonResponse)
async def get_benchmark_comparison():
    """
    Retrieve and compare all benchmark results from both approaches.
    
    This endpoint:
    1. Loads Traditional MCP results from JSON
    2. Loads Code Execution MCP results from JSON
    3. Returns combined comparison data
    
    Returns:
        ComparisonResponse with all benchmark results
        
    Raises:
        HTTPException: If loading results fails
    """
    try:
        # Log comparison data request
        logger.info("Loading benchmark comparison data")
        
        # Load results from both approaches
        traditional_results = storage.load_results(TRADITIONAL_RESULTS_PATH)
        code_exec_results = storage.load_results(CODE_EXEC_RESULTS_PATH)
        
        # Return combined results with counts
        return ComparisonResponse(
            success=True,
            traditional_mcp=traditional_results,
            code_execution_mcp=code_exec_results,
            total_count={
                "traditional_mcp": len(traditional_results),
                "code_execution_mcp": len(code_exec_results)
            }
        )
        
    except Exception as e:
        # Log error and raise HTTP exception
        logger.error(f"Comparison data loading error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load comparison data: {str(e)}"
        )


@app.post(
    "/api/benchmarks/run-multiple",
    response_model=MultiTaskResponse,
    response_model_exclude_none=False,
    summary="Run Multiple Benchmark Tasks",
    description="Execute multiple benchmark tasks comparing both approaches"
)
async def run_multiple_benchmarks(request: MultiTaskRequest):
    """
    Run multiple benchmark tasks and compare both approaches.
    
    This endpoint allows running a batch of tasks and collecting results
    from both Code Execution MCP and Traditional MCP approaches.
    
    Args:
        request: Multi-task request containing list of tasks and config
        
    Returns:
        MultiTaskResponse with results and aggregate statistics
        
    Raises:
        HTTPException: If benchmark execution fails
    """
    try:
        logger.info(f"Starting multi-task benchmark with {len(request.tasks)} tasks")
        
        # Convert Pydantic models to dicts for the runner
        tasks = [task.model_dump() for task in request.tasks]
        
        # Run all tasks with selected approaches
        results = await benchmarkRunner.run_all_tasks(
            tasks=tasks,
            max_turns=request.max_turns,
            approaches=request.approaches,
            use_judge=request.use_judge
        )
        
        # Calculate summary statistics
        code_exec_times = []
        traditional_times = []
        code_exec_tokens = []
        traditional_tokens = []
        code_exec_successes = 0
        traditional_successes = 0
        
        for result in results:
            if "error" not in result:
                comparison = result.get("comparison", {})
                
                if comparison.get("code_exec_success"):
                    code_exec_successes += 1
                    code_exec_times.append(comparison.get("code_exec_time", 0))
                    code_exec_tokens.append(comparison.get("code_exec_total_tokens", 0))
                    
                if comparison.get("traditional_success"):
                    traditional_successes += 1
                    traditional_times.append(comparison.get("traditional_time", 0))
                    traditional_tokens.append(comparison.get("traditional_total_tokens", 0))
        
        # Compute averages
        avg_code_exec_time = sum(code_exec_times) / len(code_exec_times) if code_exec_times else 0
        avg_traditional_time = sum(traditional_times) / len(traditional_times) if traditional_times else 0
        avg_code_exec_tokens = sum(code_exec_tokens) / len(code_exec_tokens) if code_exec_tokens else 0
        avg_traditional_tokens = sum(traditional_tokens) / len(traditional_tokens) if traditional_tokens else 0
        
        summary = {
            "total_tasks": len(request.tasks),
            "code_exec_successes": code_exec_successes,
            "traditional_successes": traditional_successes,
            "avg_code_exec_time": round(avg_code_exec_time, 2),
            "avg_traditional_time": round(avg_traditional_time, 2),
            "avg_code_exec_tokens": round(avg_code_exec_tokens, 0),
            "avg_traditional_tokens": round(avg_traditional_tokens, 0),
            "time_improvement": round(
                ((avg_traditional_time - avg_code_exec_time) / avg_traditional_time * 100)
                if avg_traditional_time > 0 else 0,
                1
            ),
            "token_reduction": round(
                ((avg_traditional_tokens - avg_code_exec_tokens) / avg_traditional_tokens * 100)
                if avg_traditional_tokens > 0 else 0,
                1
            )
        }
        
        logger.info(f"Multi-task benchmark completed: {code_exec_successes}/{len(request.tasks)} code exec success, "
                   f"{traditional_successes}/{len(request.tasks)} traditional success")
        
        # Debug: Log if turn_details is present in results
        for i, result in enumerate(results):
            has_code_turn_details = "turn_details" in result.get("code_execution_mcp", {})
            has_trad_turn_details = "turn_details" in result.get("traditional_mcp", {})
            logger.info(f"Result {i}: code_exec turn_details={has_code_turn_details}, traditional turn_details={has_trad_turn_details}")
            if has_code_turn_details:
                logger.info(f"  Code exec turn_details count: {len(result['code_execution_mcp']['turn_details'])}")
            if has_trad_turn_details:
                logger.info(f"  Traditional turn_details count: {len(result['traditional_mcp']['turn_details'])}")
        
        return MultiTaskResponse(
            success=True,
            results=results,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Multi-task benchmark error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run multi-task benchmark: {str(e)}"
        )
