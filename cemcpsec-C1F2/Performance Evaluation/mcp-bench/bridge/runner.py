"""
Bridge Runner for executing mcp-bench tasks using AI_Code_Execution_with_MCP agents.

This module orchestrates the execution of mcp-bench tasks using the Traditional MCP
and Code Execution MCP agents, while leveraging mcp-bench's evaluation system.
"""

import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add AI_Code_Execution_with_MCP to path
project_root = Path(__file__).parent.parent.parent
aicode_path = project_root / "AI_Code_Execution_with_MCP"
if aicode_path.exists():
    sys.path.insert(0, str(aicode_path))

# Import mcp-bench components
from benchmark.evaluator import TaskEvaluator
from benchmark.results_aggregator import ResultsAggregator
from benchmark.results_formatter import ResultsFormatter
from utils.local_server_config import LocalServerConfigLoader
import config.config_loader as config_loader

# Import bridge components
from .task_adapter import TaskAdapter
from .result_adapter import ResultAdapter
from .mcp_config_adapter import MCPConfigAdapter

logger = logging.getLogger(__name__)


class BridgeRunner:
    """Runner for executing mcp-bench tasks with AI_Code_Execution_with_MCP agents."""
    
    def __init__(
        self,
        tasks_file: Optional[str] = None,
        agent_type: str = "traditional",  # "traditional", "code_execution", or "both"
        use_fuzzy_descriptions: bool = False,
        enable_judge_stability: bool = False,
        server_filter: Optional[List[str]] = None,
        openai_model: Optional[str] = None
    ):
        """
        Initialize the bridge runner.
        
        Args:
            tasks_file: Path to tasks JSON file
            agent_type: Which agent to use ("traditional", "code_execution", or "both")
            use_fuzzy_descriptions: Whether to use fuzzy task descriptions
            enable_judge_stability: Whether to enable judge stability checks
        """
        self.tasks_file = tasks_file or config_loader.get_tasks_file()
        self.agent_type = agent_type
        self.use_fuzzy_descriptions = use_fuzzy_descriptions
        self.enable_judge_stability = enable_judge_stability
        self.server_filter = server_filter  # List of server names to filter tasks
        self.openai_model = openai_model  # OpenAI model for code execution agent (e.g., "gpt-4.1-mini")
        
        # Get mcp-bench directory for resolving paths
        self.mcp_bench_dir = Path(__file__).parent.parent
        
        # Initialize adapters with correct paths
        commands_json_path = self.mcp_bench_dir / "mcp_servers" / "commands.json"
        api_key_path = self.mcp_bench_dir / "mcp_servers" / "api_key"
        
        self.task_adapter = TaskAdapter(use_fuzzy_descriptions=use_fuzzy_descriptions)
        self.result_adapter = ResultAdapter()
        self.mcp_config_adapter = MCPConfigAdapter(
            commands_json_path=str(commands_json_path),
            api_key_path=str(api_key_path)
        )
        
        # Initialize mcp-bench components with correct paths
        self.local_config_loader = LocalServerConfigLoader(
            commands_json_path=str(commands_json_path),
            api_key_path=str(api_key_path)
        )
        self.aggregator = ResultsAggregator()
        self.formatter = ResultsFormatter()
        
        # Initialize judge provider (will be created when needed)
        self._judge_provider = None
        
        # Track results
        self.results: List[Dict[str, Any]] = []
    
    async def load_tasks(self) -> List[Dict[str, Any]]:
        """
        Load tasks from mcp-bench task file.
        
        Returns:
            List of task dictionaries
        """
        # Resolve task file path relative to mcp-bench directory
        if self.tasks_file:
            if os.path.isabs(self.tasks_file):
                task_file_path = Path(self.tasks_file)
            else:
                task_file_path = self.mcp_bench_dir / self.tasks_file
        else:
            # Use default from config, or fallback to first task file
            default_file = config_loader.get_tasks_file()
            if default_file and default_file != 'None':
                if os.path.isabs(default_file):
                    task_file_path = Path(default_file)
                else:
                    task_file_path = self.mcp_bench_dir / default_file
            else:
                # Use first task file from all_task_files as default
                all_task_files = config_loader.get_all_task_files()
                if all_task_files:
                    default_file = all_task_files[0]
                    if os.path.isabs(default_file):
                        task_file_path = Path(default_file)
                    else:
                        task_file_path = self.mcp_bench_dir / default_file.lstrip('./')
                else:
                    # Final fallback to a common task file
                    task_file_path = self.mcp_bench_dir / "tasks" / "mcpbench_tasks_single_runner_format.json"
        
        logger.info(f"Loading tasks from {task_file_path}")
        
        try:
            import json
            with open(task_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different task file formats
            if 'server_tasks' in data:
                tasks = []
                for server_group in data['server_tasks']:
                    server_name = server_group.get('server_name', '')
                    if 'task' in server_group:
                        tasks.append({
                            'server_name': server_name,
                            'task': server_group['task']
                        })
                    elif 'tasks' in server_group:
                        for task in server_group.get('tasks', []):
                            tasks.append({
                                'server_name': server_name,
                                'task': task
                            })
            elif 'tasks' in data:
                tasks = data['tasks']
            else:
                tasks = data
            
            logger.info(f"Loaded {len(tasks)} tasks")
            
            # Filter by server names if specified
            if self.server_filter:
                original_count = len(tasks)
                filtered_tasks = []
                for task in tasks:
                    server_name = task.get('server_name', '')
                    # Check if server name matches any filter (case-insensitive, partial match)
                    if any(filter_name.lower() in server_name.lower() for filter_name in self.server_filter):
                        filtered_tasks.append(task)
                tasks = filtered_tasks
                logger.info(f"Filtered to {len(tasks)} tasks matching servers: {self.server_filter} (from {original_count} total)")
            
            return tasks
            
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            raise
    
    async def _get_judge_provider(self):
        """Get or create judge provider for evaluation.
        
        Tries Azure OpenAI first, falls back to regular OpenAI if Azure credentials are not available.
        Returns None if no credentials are available (evaluation will be skipped).
        """
        if self._judge_provider is None:
            from openai import AsyncAzureOpenAI, AsyncOpenAI
            from llm.provider import LLMProvider
            
            # Try Azure OpenAI first
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            
            if azure_endpoint and azure_api_key:
                try:
                    azure_client = AsyncAzureOpenAI(
                        azure_endpoint=azure_endpoint,
                        api_key=azure_api_key,
                        api_version=config_loader.get_azure_api_version()
                    )
                    self._judge_provider = LLMProvider(azure_client, "o4-mini", "azure")
                    logger.info("Using Azure OpenAI for judge evaluation")
                    return self._judge_provider
                except Exception as e:
                    logger.warning(f"Failed to initialize Azure OpenAI judge: {e}")
            
            # Fall back to regular OpenAI
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if openai_api_key:
                try:
                    openai_client = AsyncOpenAI(api_key=openai_api_key)
                    # Use gpt-4o-mini for judge (similar to o4-mini)
                    # Use "openai_compatible" as provider type since LLMProvider supports it
                    self._judge_provider = LLMProvider(openai_client, "gpt-4o-mini", "openai_compatible")
                    logger.info("Using OpenAI (fallback) for judge evaluation")
                    return self._judge_provider
                except Exception as e:
                    logger.warning(f"Failed to initialize OpenAI judge: {e}")
            
            # No credentials available
            logger.warning("No judge provider credentials available. Evaluation will be skipped.")
            return None
        
        return self._judge_provider
    
    async def _prepare_mcp_config(self, task_info: Dict[str, Any]) -> Optional[str]:
        """
        Prepare MCP config file for the task.
        
        Args:
            task_info: Task information with server_name
        
        Returns:
            Path to created mcp_config.json file, or None if failed
        """
        server_name = task_info.get('server_name', '')
        
        # Parse multi-server names (e.g., "Server1+Server2")
        if '+' in server_name:
            server_names = [s.strip() for s in server_name.split('+')]
        else:
            server_names = [server_name]
        
        # Load commands config (use path from mcp-bench directory)
        commands_config_path = self.mcp_bench_dir / "mcp_servers" / "commands.json"
        if not commands_config_path.exists():
            logger.error(f"commands.json not found at {commands_config_path}")
            return None
        
        import json
        with open(commands_config_path, 'r') as f:
            commands_config = json.load(f)
        
        # Convert server configs (use mcp_servers as base path)
        base_path = str(self.mcp_bench_dir / "mcp_servers")
        converted_configs = self.mcp_config_adapter.convert_servers_for_task(
            server_names, commands_config, base_path=base_path
        )
        
        if not converted_configs:
            logger.error(f"Failed to convert server configs for {server_name}")
            return None
        
        # Create temporary mcp_config.json in mcp-bench directory
        temp_config_path = str(self.mcp_bench_dir / "mcp_config_temp.json")
        self.mcp_config_adapter.create_mcp_config_json(converted_configs, temp_config_path)
        
        return temp_config_path
    
    async def _execute_with_traditional_agent(self, task_query: str, 
                                             mcp_config_path: str) -> Dict[str, Any]:
        """
        Execute task using Traditional MCP agent.
        
        Args:
            task_query: Task query string
            mcp_config_path: Path to mcp_config.json
        
        Returns:
            Agent execution result
        """
        try:
            from app.benchmarks.traditional_mcp import TraditionalMCPBenchmark
            
            benchmark = TraditionalMCPBenchmark()
            await benchmark.initialize_async()
            
            result = await benchmark.run_benchmark_async(task_query)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing with Traditional MCP agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "time": 0,
                "llm_calls": [],
                "tokens": {"input": 0, "output": 0, "total": 0}
            }
    
    async def _execute_with_code_execution_agent(self, task_query: str,
                                                 mcp_config_path: str,
                                                 openai_model: str = None) -> Dict[str, Any]:
        """
        Execute task using Code Execution MCP agent.
        
        Args:
            task_query: Task query string
            mcp_config_path: Path to mcp_config.json
        
        Returns:
            Agent execution result
        """
        try:
            from app.benchmarks.code_execution_mcp import CodeExecutionBenchmark
            from app.core.mcp_client import reset_mcp_client
            import app.core.mcp_client as mcp_client_module
            
            # Close existing client if it exists and is initialized
            if mcp_client_module._mcp_client_instance and mcp_client_module._mcp_client_instance.initialized:
                try:
                    await mcp_client_module._mcp_client_instance.close()
                except Exception as e:
                    logger.warning(f"Error closing existing MCP client: {e}")
            
            # Reset the global MCP client to ensure we use the new config
            reset_mcp_client()
            
            benchmark = CodeExecutionBenchmark(mcp_config_path=mcp_config_path, openai_model=openai_model)
            
            # Initialize and check if servers connected
            try:
                print("🔌 Initializing MCP connections...")
                await benchmark.initialize_async()
                print("✅ MCP connections initialized")
            except RuntimeError as e:
                # If initialization fails due to no servers, return error result
                error_msg = str(e)
                print(f"❌ Initialization failed: {error_msg}")
                logger.error(f"Initialization failed: {error_msg}")
                
                # Try to get more detailed error information from the orchestrator's MCP client
                try:
                    if hasattr(benchmark, 'orchestrator') and hasattr(benchmark.orchestrator, 'mcp_client'):
                        failed_servers = []
                        for server_name in benchmark.orchestrator.mcp_client.get_available_servers():
                            if not benchmark.orchestrator.mcp_client.is_server_connected(server_name):
                                failed_servers.append(server_name)
                        
                        if failed_servers:
                            print(f"\n⚠️  Failed to connect to server(s): {', '.join(failed_servers)}")
                            print("Common causes:")
                            print("  1. Server dependencies not installed (check requirements.txt)")
                            print("  2. Python/Node command not found in PATH")
                            print("  3. Server startup error (check server logs)")
                            print("  4. Missing environment variables or API keys")
                except Exception as detail_err:
                    logger.debug(f"Could not get detailed error info: {detail_err}")
                
                # Try to read the log file to get more details
                log_file = Path("AI_Code_Execution_with_MCP") / "logs" / "app.log"
                if log_file.exists():
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            log_lines = f.readlines()
                            # Get last 50 lines that might contain error info (more context)
                            recent_logs = log_lines[-50:] if len(log_lines) > 50 else log_lines
                            error_details = ''.join(recent_logs)
                            if error_details.strip():
                                print(f"\n📋 Recent logs from app.log:")
                                print(f"{'-'*80}")
                                print(error_details)
                                print(f"{'-'*80}")
                    except Exception as log_err:
                        logger.warning(f"Could not read log file: {log_err}")
                
                return {
                    "success": False,
                    "error": error_msg,
                    "output": "",
                    "time": 0,
                    "llm_calls": [],
                    "tokens": {"input": 0, "output": 0, "total": 0}
                }
            except Exception as init_err:
                # Catch any other initialization errors
                error_msg = f"Initialization error: {str(init_err)}"
                print(f"❌ Initialization failed: {error_msg}")
                logger.error(f"Initialization failed: {error_msg}", exc_info=True)
                return {
                    "success": False,
                    "error": error_msg,
                    "output": "",
                    "time": 0,
                    "llm_calls": [],
                    "tokens": {"input": 0, "output": 0, "total": 0}
                }
            
            result = await benchmark.run_benchmark_async(task_query, max_turns=3)
            
            await benchmark.cleanup_async()
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing with Code Execution MCP agent: {e}")
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "time": 0,
                "llm_calls": [],
                "tokens": {"input": 0, "output": 0, "total": 0}
            }
    
    async def execute_task(self, task_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single task with the selected agent(s).
        
        Args:
            task_info: Task information from mcp-bench format
        
        Returns:
            Execution result in mcp-bench format
        """
        # Extract task query
        task_query = self.task_adapter.extract_task_query(task_info)
        if not task_query:
            return {
                'status': 'failed',
                'error': 'No task query found',
                'execution_time': 0
            }
        
        # Get task metadata
        task_metadata = self.task_adapter.get_task_metadata(task_info)
        task_id = task_metadata['task_id']
        server_name = task_metadata['server_name']
        
        # Print task header
        print(f"\n{'='*80}")
        print(f"TASK {task_id}")
        print(f"{'='*80}")
        print(f"Server: {server_name}")
        print(f"Agent: {self.agent_type}")
        print(f"\n📋 TASK QUERY:")
        print(f"{'-'*80}")
        print(task_query[:500] + ("..." if len(task_query) > 500 else ""))
        print(f"{'-'*80}\n")
        
        logger.info(f"Executing task {task_id} with {self.agent_type} agent(s)")
        
        # Prepare MCP config
        mcp_config_path = await self._prepare_mcp_config(task_info)
        if not mcp_config_path:
            return {
                'task_id': task_id,
                'server_name': server_name,
                'status': 'failed',
                'error': 'Failed to prepare MCP config',
                'execution_time': 0
            }
        
        try:
            # Execute with selected agent(s)
            execution_results = {}
            
            if self.agent_type in ["traditional", "both"]:
                print("🤖 Executing with Traditional MCP agent...")
                logger.info(f"Executing with Traditional MCP agent...")
                traditional_result = await self._execute_with_traditional_agent(
                    task_query, mcp_config_path
                )
                execution_results['traditional'] = traditional_result
                
                # Show traditional MCP details
                if traditional_result.get('success'):
                    print("✅ Traditional MCP completed successfully")
                else:
                    print(f"❌ Traditional MCP failed: {traditional_result.get('error', 'Unknown error')}")
            
            if self.agent_type in ["code_execution", "both"]:
                print("🤖 Executing with Code Execution MCP agent...")
                logger.info(f"Executing with Code Execution MCP agent...")
                # Use model from BridgeRunner config or fall back to environment variable
                code_exec_model = self.openai_model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
                if code_exec_model:
                    logger.info(f"Using OpenAI model: {code_exec_model}")
                code_exec_result = await self._execute_with_code_execution_agent(
                    task_query, mcp_config_path, openai_model=code_exec_model
                )
                execution_results['code_execution'] = code_exec_result
                
                # Show code execution details if available
                if code_exec_result.get('success'):
                    print("✅ Code Execution completed successfully")
                    # Show LLM calls info with reasoning
                    llm_calls = code_exec_result.get('llm_calls', [])
                    if llm_calls:
                        print(f"   Generated {len(llm_calls)} code execution turn(s)")
                        for i, call in enumerate(llm_calls, 1):
                            tokens = call.get('tokens', {})
                            reasoning = call.get('reasoning', '')
                            code = call.get('code', '')
                            
                            print(f"\n   🔄 Turn {i}/{len(llm_calls)}:")
                            if tokens:
                                print(f"      Tokens: {tokens.get('total_tokens', 0)} (prompt: {tokens.get('prompt_tokens', 0)}, output: {tokens.get('completion_tokens', 0)})")
                            
                            if reasoning:
                                reasoning_preview = reasoning[:300] + ("..." if len(reasoning) > 300 else "")
                                print(f"      Reasoning: {reasoning_preview}")
                            
                            if code:
                                code_preview = code[:200] + ("..." if len(code) > 200 else "")
                                print(f"      Code preview: {code_preview}")
                    
                    # Show output preview
                    output = code_exec_result.get('output', '')
                    if output:
                        preview = output[:200] + ("..." if len(output) > 200 else "")
                        print(f"\n📄 Execution Output Preview:")
                        print(f"{'-'*80}")
                        print(preview)
                        print(f"{'-'*80}")
                else:
                    error_msg = code_exec_result.get('error', 'Unknown error')
                    print(f"❌ Code Execution failed")
                    
                    # Show all turns with reasoning and code
                    llm_calls = code_exec_result.get('llm_calls', [])
                    if llm_calls:
                        print(f"\n   Attempted {len(llm_calls)} turn(s):")
                        for i, call in enumerate(llm_calls, 1):
                            reasoning = call.get('reasoning', '')
                            generated_code = call.get('code', '')
                            call_error = call.get('error', '')
                            
                            print(f"\n   🔄 Turn {i}/{len(llm_calls)}:")
                            
                            if reasoning:
                                reasoning_preview = reasoning[:300] + ("..." if len(reasoning) > 300 else "")
                                print(f"      Reasoning: {reasoning_preview}")
                            
                            if generated_code:
                                code_preview = generated_code[:400] + ("..." if len(generated_code) > 400 else "")
                                print(f"      Generated Code:")
                                print(f"      {code_preview}")
                            
                            if call_error:
                                error_preview = call_error[:300] + ("..." if len(call_error) > 300 else "")
                                print(f"      Error: {error_preview}")
                    else:
                        # No LLM calls means code generation failed
                        print(f"\n   ⚠️  Code generation failed - no turns executed")
                    
                    # Show final error details
                    error_preview = error_msg[:500] + ("..." if len(error_msg) > 500 else "")
                    print(f"\n⚠️  Final Error Details:")
                    print(f"{'-'*80}")
                    print(error_preview)
                    print(f"{'-'*80}")
            
            # Convert results to mcp-bench format
            if self.agent_type == "both":
                # Use the first successful result, or traditional if both succeed
                if execution_results.get('traditional', {}).get('success'):
                    agent_result = execution_results['traditional']
                    agent_name = 'traditional'
                elif execution_results.get('code_execution', {}).get('success'):
                    agent_result = execution_results['code_execution']
                    agent_name = 'code_execution'
                else:
                    # Both failed, use traditional
                    agent_result = execution_results.get('traditional', {})
                    agent_name = 'traditional'
            elif self.agent_type == "traditional":
                agent_result = execution_results.get('traditional', {})
                agent_name = 'traditional'
            else:
                agent_result = execution_results.get('code_execution', {})
                agent_name = 'code_execution'
            
            # Convert result format
            if agent_name == "traditional":
                converted_result = self.result_adapter.convert_traditional_mcp_result(
                    agent_result, task_metadata
                )
            else:
                converted_result = self.result_adapter.convert_code_execution_result(
                    agent_result, task_metadata
                )
            
            # Add available tools (empty for now, could be populated from MCP client)
            converted_result['available_tools'] = self.result_adapter.get_available_tools()
            
            # Evaluate result (if judge provider is available)
            evaluation = None
            evaluation_time = 0.0
            judge_provider = await self._get_judge_provider()
            
            if judge_provider:
                try:
                    # Always disable judge stability to run evaluation only once
                    evaluator = TaskEvaluator(judge_provider, enable_judge_stability=False)
                    
                    evaluation_start_time = time.time()
                    evaluation = await evaluator.evaluate(
                        task=task_query,
                        execution_results=converted_result.get('execution_results', []),
                        final_solution=converted_result.get('solution', ''),
                        total_rounds=converted_result.get('total_rounds', 0),
                        available_tools=converted_result.get('available_tools', {}),
                        planning_json_compliance=1.0,  # Not applicable for these agents
                        accumulated_information=converted_result.get('accumulated_information', ''),
                        concrete_task_description=task_metadata.get('concrete_task_description')
                    )
                    evaluation_time = time.time() - evaluation_start_time
                except Exception as e:
                    logger.warning(f"Evaluation failed: {e}. Continuing without evaluation score.")
                    evaluation = None
            else:
                logger.info("Skipping evaluation (no judge provider available)")
                # Create a minimal evaluation result
                evaluation = {
                    'overall_score': None,
                    'note': 'Evaluation skipped - no judge provider credentials available'
                }
            
            # Format final result
            final_result = {
                'task_id': task_id,
                'server_name': server_name,
                'model_name': f"{agent_name}_mcp",
                'task_description': task_query,
                'status': 'completed',
                'execution_time': agent_result.get('time', 0),
                'agent_execution_time': agent_result.get('time', 0),
                'evaluation_time': evaluation_time,
                'execution_results': converted_result.get('execution_results', []),
                'final_solution': converted_result.get('solution', ''),
                'total_rounds': converted_result.get('total_rounds', 0),
                'evaluation': evaluation,
                'total_output_tokens': converted_result.get('total_output_tokens', 0),
                'total_prompt_tokens': converted_result.get('total_prompt_tokens', 0),
                'total_tokens': converted_result.get('total_tokens', 0)
            }
            
            # Print task summary
            self._print_task_summary(final_result, agent_result, converted_result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'task_id': task_id,
                'server_name': server_name,
                'status': 'failed',
                'error': str(e),
                'execution_time': 0
            }
        finally:
            # Clean up temp config file
            if mcp_config_path and os.path.exists(mcp_config_path):
                try:
                    os.remove(mcp_config_path)
                except Exception as e:
                    logger.warning(f"Failed to remove temp config file: {e}")
    
    async def run_benchmark(self, task_limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Run benchmark on all tasks.
        
        Args:
            task_limit: Limit number of tasks to run (None for all)
        
        Returns:
            Aggregated metrics
        """
        # Load tasks
        tasks = await self.load_tasks()
        
        if task_limit:
            tasks = tasks[:task_limit]
            logger.info(f"Limited to {task_limit} tasks")
        
        logger.info(f"Running benchmark on {len(tasks)} tasks with {self.agent_type} agent(s)")
        
        # Execute each task
        for i, task_info in enumerate(tasks, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Task {i}/{len(tasks)}")
            logger.info(f"{'='*80}")
            
            result = await self.execute_task(task_info)
            self.results.append(result)
            
            # Display current metrics
            if result.get('status') == 'completed':
                try:
                    current_metrics = self.aggregator.aggregate_current_metrics(self.results)
                    # Use relative path for display
                    tasks_file_display = self.tasks_file or config_loader.get_tasks_file()
                    self.formatter.format_current_metrics(
                        f"{self.agent_type}_mcp",
                        len([r for r in self.results if r.get('status') == 'completed']),
                        len(tasks),
                        current_metrics,
                        tasks_file_display
                    )
                except Exception as e:
                    logger.error(f"Error calculating metrics: {e}")
            
            # Small delay between tasks
            await asyncio.sleep(1)
        
        # Return final metrics
        if self.results:
            try:
                final_metrics = self.aggregator.aggregate_current_metrics(self.results)
                return final_metrics
            except Exception as e:
                logger.error(f"Error calculating final metrics: {e}")
                return {}
        else:
            return {}
    
    def _print_task_summary(self, final_result: Dict[str, Any], agent_result: Dict[str, Any], 
                           converted_result: Dict[str, Any]) -> None:
        """Print detailed summary after each task."""
        print(f"\n{'='*80}")
        print(f"📊 TASK SUMMARY: {final_result['task_id']}")
        print(f"{'='*80}")
        
        # Status
        status = final_result.get('status', 'unknown')
        status_icon = "✅" if status == 'completed' else "❌"
        print(f"{status_icon} Status: {status.upper()}")
        
        # Execution time
        exec_time = final_result.get('execution_time', 0)
        eval_time = final_result.get('evaluation_time', 0)
        total_time = exec_time + eval_time
        print(f"⏱️  Execution Time: {exec_time:.2f}s")
        print(f"⏱️  Evaluation Time: {eval_time:.2f}s")
        print(f"⏱️  Total Time: {total_time:.2f}s")
        
        # Token usage
        prompt_tokens = final_result.get('total_prompt_tokens', 0)
        output_tokens = final_result.get('total_output_tokens', 0)
        total_tokens = final_result.get('total_tokens', 0)
        print(f"\n💬 Token Usage:")
        print(f"   Prompt tokens: {prompt_tokens:,}")
        print(f"   Output tokens: {output_tokens:,}")
        print(f"   Total tokens: {total_tokens:,}")
        
        # Rounds
        rounds = final_result.get('total_rounds', 0)
        print(f"\n🔄 Execution Rounds: {rounds}")
        
        # Solution preview
        solution = final_result.get('final_solution', '')
        if solution:
            print(f"\n📝 Solution Preview:")
            print(f"{'-'*80}")
            preview = solution[:300] + ("..." if len(solution) > 300 else "")
            print(preview)
            print(f"{'-'*80}")
        
        # Evaluation score if available
        evaluation = final_result.get('evaluation')
        if evaluation and isinstance(evaluation, dict):
            overall_score = evaluation.get('overall_score')
            if overall_score is not None:
                print(f"\n⭐ Overall Score: {overall_score:.2f}/10.0")
        
        print(f"{'='*80}\n")

