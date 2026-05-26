#!/usr/bin/env python3
"""
Global Runner for Comprehensive Evaluation

This runner executes tasks across multiple models and agents (MCP/CE) using
mcp-bench agents directly, with optimized server connections - connecting once
per server group and running all related tasks, models, and agents before disconnecting.
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from benchmark.csv_tracker import CSVTracker
from benchmark.evaluator import TaskEvaluator
from benchmark.runner import ConnectionManager, BenchmarkRunner
from agent.executor import TaskExecutor
from agent.code_execution_executor import CodeExecutionTaskExecutor
from llm.provider import LLMProvider
from llm.factory import LLMFactory
from utils.local_server_config import LocalServerConfigLoader
import config.config_loader as config_loader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Suppress noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)


class GlobalRunner:
    """Global runner for comprehensive evaluation across tasks, models, and agents."""
    
    def __init__(
        self,
        tasks_file: str,
        task_limit: Optional[int] = None,
        server_filter: Optional[List[str]] = None,
        model_filter: Optional[List[str]] = None,
        output_dir: str = "./results"
    ):
        """
        Initialize global runner.
        
        Args:
            tasks_file: Path to tasks JSON file (mandatory)
            task_limit: Limit number of tasks to run (None for all)
            server_filter: List of server names to filter (None for all)
            model_filter: List of model names to filter (None for all available)
            output_dir: Directory for output files
        """
        self.tasks_file = tasks_file
        self.task_limit = task_limit
        self.server_filter = server_filter
        self.model_filter = model_filter
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize CSV tracker
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_tracker = CSVTracker(
            output_dir=str(self.output_dir),
            filename=f"global_evaluation_{timestamp}.csv"
        )
        
        # Initialize benchmark runner components (for server config and evaluation)
        self.mcp_bench_dir = Path(__file__).parent
        commands_json_path = self.mcp_bench_dir / "mcp_servers" / "commands.json"
        api_key_path = self.mcp_bench_dir / "mcp_servers" / "api_key"
        
        self.local_config_loader = LocalServerConfigLoader(
            commands_json_path=str(commands_json_path),
            api_key_path=str(api_key_path)
        )
        
        # Initialize benchmark runner for helper methods
        # Set server_filter to skip resident servers (we only want requested servers)
        # Use same config settings as benchmark runner
        filter_problematic_tools = config_loader.is_problematic_tools_filter_enabled()
        use_fuzzy_descriptions = config_loader.use_fuzzy_descriptions()
        self.benchmark_runner = BenchmarkRunner(
            server_filter=server_filter or [],
            filter_problematic_tools=filter_problematic_tools,
            use_fuzzy_descriptions=use_fuzzy_descriptions
        )
        
        # Initialize commands_config (needed for _prepare_server_configs)
        self.benchmark_runner.commands_config = None  # Will be loaded when needed
        
        # Store config values for use in task extraction
        self.filter_problematic_tools = filter_problematic_tools
        self.use_fuzzy_descriptions = use_fuzzy_descriptions
        
        # Initialize judge provider (will be created when needed)
        self._judge_provider = None
        
        # Track results
        self.all_results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        
        # Statistics
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'total_combinations': 0,
            'completed_combinations': 0,
            'failed_combinations': 0
        }
    
    async def load_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks from file."""
        try:
            task_file_path = Path(self.tasks_file)
            if not task_file_path.is_absolute():
                # Remove mcp-bench/ prefix if present (handles paths from project root)
                tasks_file_str = str(self.tasks_file)
                if tasks_file_str.startswith('mcp-bench/'):
                    tasks_file_str = tasks_file_str[10:]  # Remove 'mcp-bench/' prefix
                
                # Try relative to mcp-bench directory
                mcp_bench_dir = Path(__file__).parent
                task_file_path = mcp_bench_dir / tasks_file_str
            
            logger.info(f"Loading tasks from {task_file_path}")
            
            if not task_file_path.exists():
                raise FileNotFoundError(f"Tasks file not found: {task_file_path}")
            
            with open(task_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different task file formats
            if 'server_tasks' in data:
                tasks = []
                for server_group in data['server_tasks']:
                    server_name = server_group.get('server_name', '')
                    # Extract servers list from server group (relevant servers for this task)
                    servers_list = server_group.get('servers', [])
                    if 'task' in server_group:
                        tasks.append({
                            'server_name': server_name,
                            'task': server_group['task'],
                            'servers': servers_list  # Store relevant servers
                        })
                    elif 'tasks' in server_group:
                        for task in server_group.get('tasks', []):
                            tasks.append({
                                'server_name': server_name,
                                'task': task,
                                'servers': servers_list  # Store relevant servers
                            })
            elif 'tasks' in data:
                tasks = data['tasks']
            else:
                tasks = data
            
            # Filter by server if specified
            if self.server_filter:
                original_count = len(tasks)
                filtered_tasks = []
                for task in tasks:
                    server_name = task.get('server_name', '')
                    if any(filter_name.lower() in server_name.lower() for filter_name in self.server_filter):
                        filtered_tasks.append(task)
                tasks = filtered_tasks
                logger.info(f"Filtered to {len(tasks)} tasks matching servers: {self.server_filter} (from {original_count} total)")
            
            # Apply task limit
            if self.task_limit:
                tasks = tasks[:self.task_limit]
                logger.info(f"Limited to {self.task_limit} tasks")
            
            logger.info(f"Loaded {len(tasks)} tasks")
            return tasks
            
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
            raise
    
    def group_tasks_by_server(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group tasks by server name."""
        grouped = defaultdict(list)
        for task in tasks:
            server_name = task.get('server_name', 'unknown')
            # Handle multi-server names (e.g., "Server1+Server2")
            if '+' in server_name:
                # For multi-server tasks, use the first server as the key
                primary_server = server_name.split('+')[0].strip()
                grouped[primary_server].append(task)
            else:
                grouped[server_name].append(task)
        
        logger.info(f"Grouped {len(tasks)} tasks into {len(grouped)} server groups")
        for server, server_tasks in grouped.items():
            logger.info(f"  {server}: {len(server_tasks)} tasks")
        
        return dict(grouped)
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names, optionally filtered."""
        try:
            model_configs = LLMFactory.get_model_configs()
            model_names = list(model_configs.keys())
            
            # Exclude gpt-5-nano and other gpt-5+ models
            excluded_models = ["gpt-5-nano"]
            original_count = len(model_names)
            model_names = [m for m in model_names if not any(excluded.lower() in m.lower() for excluded in excluded_models)]
            if len(model_names) < original_count:
                logger.info(f"Excluded {original_count - len(model_names)} model(s): {excluded_models}")
            
            # Default to 4o, 4.1, and 4.1-mini if no model filter is specified
            if not self.model_filter:
                # Filter to only 4o, 4.1, and 4.1-mini
                default_models = ["gpt-4o", "gpt-4.1", "gpt-4.1-mini"]
                filtered_models = [m for m in model_names if m in default_models]
                if filtered_models:
                    model_names = filtered_models
                    logger.info(f"Defaulting to 4o, 4.1, and 4.1-mini: {model_names}")
                else:
                    logger.warning("4o, 4.1, or 4.1-mini not found in available models, using all available models")
            else:
                # Apply model filter if specified
                original_count = len(model_names)
                # Filter models (case-insensitive, partial match)
                filtered_models = []
                for model_name in model_names:
                    if any(filter_name.lower() in model_name.lower() for filter_name in self.model_filter):
                        filtered_models.append(model_name)
                model_names = filtered_models
                logger.info(f"Filtered to {len(model_names)} models matching filter: {self.model_filter} (from {original_count} total)")
            
            logger.info(f"Found {len(model_names)} available models: {model_names}")
            return model_names
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
            # Return default models if factory fails
            return ["gpt-4o", "gpt-4.1", "gpt-4.1-mini"]
    
    def _get_judge_provider(self) -> Optional[LLMProvider]:
        """Get or create judge provider for evaluation using gpt-4.1."""
        if self._judge_provider is not None:
            return self._judge_provider
        
        # Use OpenAI with gpt-4.1 for judge (as requested)
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            from openai import AsyncOpenAI
            openai_client = AsyncOpenAI(api_key=openai_key)
            self._judge_provider = LLMProvider(openai_client, "gpt-4.1", "openai_compatible")
            logger.info("Using gpt-4.1 as judge model")
            return self._judge_provider
        
        # Try Azure as fallback (if OpenAI not available)
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        if azure_endpoint and azure_key:
            from openai import AsyncAzureOpenAI
            azure_client = AsyncAzureOpenAI(
                azure_endpoint=azure_endpoint,
                api_key=azure_key,
                api_version=config_loader.get_azure_api_version()
            )
            # Try to use gpt-4.1 from Azure if available, otherwise fallback to o4-mini
            self._judge_provider = LLMProvider(azure_client, "gpt-4.1", "azure")
            logger.info("Using gpt-4.1 (Azure) as judge model")
            return self._judge_provider
        
        logger.warning("No judge provider credentials available. Evaluation will be skipped.")
        return None
    
    async def _prepare_server_configs(
        self,
        server_name: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare server configurations for a task.
        
        Only connects to relevant servers (from task's 'servers' field) and
        explicitly excludes distraction servers to save time.
        """
        # Get servers info (same as benchmark runner)
        servers_info = self.local_config_loader.local_commands
        
        # Always load commands_config (needed for _prepare_server_configs, especially for resident servers)
        if self.benchmark_runner.commands_config is None:
            self.benchmark_runner.commands_config = await self.benchmark_runner.load_commands_config()
            # If load failed, set to empty dict to avoid None errors
            if self.benchmark_runner.commands_config is None:
                self.benchmark_runner.commands_config = {}
        
        # Extract relevant servers from task_data (if available)
        # task_data might be the full task info dict with 'servers' field, or just the task dict
        relevant_servers = None
        if isinstance(task_data, dict):
            # Check if 'servers' is at the top level (from task info)
            relevant_servers = task_data.get('servers')
            # If not found, check if task_data has a 'task' key with the actual task
            if relevant_servers is None and 'task' in task_data:
                # The 'servers' field should be at the task_info level, not inside 'task'
                # But let's also check the task itself
                task = task_data.get('task', {})
                if isinstance(task, dict):
                    # The 'servers' field is typically at the server group level, not in individual tasks
                    # So we should have gotten it from task_data.get('servers') above
                    pass
        
        # Extract distraction servers from task data
        distraction_servers = []
        if isinstance(task_data, dict):
            # Check if distraction_servers is in the task itself
            task = task_data.get('task', {})
            if isinstance(task, dict):
                distraction_servers = task.get('distraction_servers', [])
            # Also check top level (in case task_data is the task dict directly)
            if not distraction_servers:
                distraction_servers = task_data.get('distraction_servers', [])
        
        # If we have a list of relevant servers, use only those
        # Otherwise, fall back to parsing server_name (for backward compatibility)
        if relevant_servers and isinstance(relevant_servers, list):
            logger.info(f"Using relevant servers from task: {relevant_servers}")
            logger.info(f"Excluding distraction servers: {distraction_servers}")
            
            # Build server configs only for relevant servers
            server_configs = []
            required_server_names = []
            
            for srv_name in relevant_servers:
                # Skip if it's a distraction server
                if srv_name in distraction_servers:
                    logger.warning(f"Skipping {srv_name} as it's in distraction_servers list")
                    continue
                
                srv_config = self.benchmark_runner.map_server_name_to_config(srv_name, servers_info)
                if srv_config:
                    server_configs.append(srv_config)
                    required_server_names.append(srv_name)
                else:
                    logger.warning(f"Server configuration not found for {srv_name}")
            
            if not server_configs:
                return {
                    'status': 'failed',
                    'error': f'No valid server configurations found for relevant servers: {relevant_servers}'
                }
            
            logger.info(f"Connecting to {len(server_configs)} relevant server(s): {required_server_names}")
            logger.info(f"Excluded {len(distraction_servers)} distraction server(s)")
            
            return {
                'status': 'success',
                'all_server_configs': server_configs,
                'required_server_names': required_server_names
            }
        else:
            # Fall back to original behavior (parse server_name)
            # But still exclude distraction servers
            logger.info(f"No explicit 'servers' field found, using server_name: {server_name}")
            logger.info(f"Excluding distraction servers: {distraction_servers}")
            
            # Prepare server configs using benchmark runner method
            server_config_result = await self.benchmark_runner._prepare_server_configs(
                server_name,
                servers_info,
                task_data
            )
            
            # Filter out distraction servers from the result
            if server_config_result.get('status') == 'success':
                all_server_configs = server_config_result.get('all_server_configs', [])
                filtered_configs = []
                filtered_server_names = []
                
                for config in all_server_configs:
                    config_name = config.get('name', '')
                    # Skip distraction servers
                    if config_name in distraction_servers:
                        logger.info(f"Filtering out distraction server: {config_name}")
                        continue
                    filtered_configs.append(config)
                    if config_name not in filtered_server_names:
                        filtered_server_names.append(config_name)
                
                logger.info(f"After filtering: connecting to {len(filtered_configs)} server(s): {filtered_server_names}")
                
                return {
                    'status': 'success',
                    'all_server_configs': filtered_configs,
                    'required_server_names': server_config_result.get('required_server_names', filtered_server_names)
                }
            
            return server_config_result
    
    async def _execute_with_traditional_agent(
        self,
        task_info: Dict[str, Any],
        model_name: str,
        server_manager: Any
    ) -> Dict[str, Any]:
        """Execute task using traditional agent (TaskExecutor)."""
        import time
        start_time = time.time()
        
        try:
            # Get model config and create LLM provider
            model_configs = LLMFactory.get_model_configs()
            if model_name not in model_configs:
                raise ValueError(f"Model {model_name} not found in available models")
            
            model_config = model_configs[model_name]
            llm_provider = await LLMFactory.create_llm_provider(model_config)
            if not llm_provider:
                raise ValueError(f"Failed to create LLM provider for model: {model_name}")
            
            # Create executor with same config as benchmark runner
            # Use config value for concurrent_summarization (same as benchmark runner)
            concurrent_summarization = config_loader.is_concurrent_summarization_enabled()
            executor = TaskExecutor(
                llm_provider,
                server_manager,
                concurrent_summarization=concurrent_summarization
            )
            
            # Get task query - same way as benchmark runner
            # Task structure: task_info has 'task' key containing task_data dict
            task_data = task_info.get('task', {})
            if isinstance(task_data, str):
                # If task is a string, use it directly
                task_query = task_data
            else:
                # Extract from task_data dict (same as benchmark runner)
                # Use fuzzy description if enabled, otherwise use detailed description
                if self.use_fuzzy_descriptions:
                    task_query = task_data.get('fuzzy_description', task_data.get('task_description', ''))
                else:
                    task_query = task_data.get('task_description', '')
            
            if not task_query:
                raise ValueError("No task query found in task info")
            
            # Execute task with timeout (same as benchmark runner)
            timeout_seconds = config_loader.get_task_timeout()
            try:
                result = await asyncio.wait_for(
                    executor.execute(task_query),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.warning(f"Task execution timed out after {timeout_seconds} seconds")
                raise ValueError(f"Task execution timed out after {timeout_seconds} seconds")
            
            execution_time = time.time() - start_time
            
            # Format result for evaluation
            formatted_result = {
                'solution': result.get('solution', ''),
                'execution_results': result.get('execution_results', []),
                'total_rounds': len(result.get('execution_results', [])),
                'available_tools': server_manager.all_tools,
                'planning_json_compliance': result.get('planning_json_compliance', 1.0),
                'accumulated_information': result.get('accumulated_information', ''),
                'total_output_tokens': result.get('total_output_tokens', 0),
                'total_prompt_tokens': result.get('total_prompt_tokens', 0),
                'total_tokens': result.get('total_tokens', 0)
            }
            
            return {
                'task_id': task_info.get('task_id', 'unknown'),
                'server_name': task_info.get('server_name', 'unknown'),
                'model_name': model_name,
                'status': 'completed',
                'result': formatted_result,
                'execution_time': execution_time,
                'agent_execution_time': execution_time,
                'task_execution_start_time': start_time
            }
            
        except Exception as e:
            logger.error(f"Error executing with traditional agent: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'task_id': task_info.get('task_id', 'unknown'),
                'server_name': task_info.get('server_name', 'unknown'),
                'model_name': model_name,
                'status': 'failed',
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def _execute_with_code_execution_agent(
        self,
        task_info: Dict[str, Any],
        model_name: str,
        server_manager: Any
    ) -> Dict[str, Any]:
        """Execute task using code execution agent (CodeExecutionTaskExecutor)."""
        import time
        start_time = time.time()
        
        try:
            # Get OpenAI API key
            openai_api_key = os.getenv("OPENAI_API_KEY")
            if not openai_api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            
            # Clean model name (remove _code_execution suffix if present)
            clean_model_name = model_name.replace("_code_execution", "") if model_name else "gpt-4o-mini"
            
            # Get mcp_servers directory path (relative to mcp-bench directory)
            mcp_servers_dir = str(self.mcp_bench_dir / "mcp_servers")
            
            # Create code execution executor with dynamic tool discovery
            code_executor = CodeExecutionTaskExecutor(
                server_manager=server_manager,
                openai_api_key=openai_api_key,
                model=clean_model_name,
                max_turns=7,
                mcp_servers_dir=mcp_servers_dir
            )
            
            # Get task query - same way as benchmark runner
            # Task structure: task_info has 'task' key containing task_data dict
            task_data = task_info.get('task', {})
            if isinstance(task_data, str):
                # If task is a string, use it directly
                task_query = task_data
            else:
                # Extract from task_data dict (same as benchmark runner)
                # Use fuzzy description if enabled, otherwise use detailed description
                if self.use_fuzzy_descriptions:
                    task_query = task_data.get('fuzzy_description', task_data.get('task_description', ''))
                else:
                    task_query = task_data.get('task_description', '')
            
            if not task_query:
                raise ValueError("No task query found in task info")
            
            # Execute task
            code_exec_result = await code_executor.execute(task_query)
            
            execution_time = time.time() - start_time
            
            # Extract tool calls from code executions for evaluation
            execution_results = []
            for code_exec in code_exec_result.get('code_executions', []):
                exec_info = code_exec.get('execution', {})
                if exec_info.get('success'):
                    execution_results.append({
                        'tool': 'code_execution',
                        'parameters': {'code': code_exec.get('code', '')[:200]},
                        'result': exec_info.get('output', ''),
                        'success': True,
                        'round_num': code_exec.get('turn', 1)
                    })
            
            # Format result for evaluation
            formatted_result = {
                'solution': code_exec_result.get('solution', ''),
                'execution_results': execution_results,
                'total_rounds': code_exec_result.get('total_turns', 0),
                'available_tools': server_manager.all_tools,
                'planning_json_compliance': 1.0,
                'accumulated_information': code_exec_result.get('solution', ''),
                'total_output_tokens': code_exec_result.get('total_output_tokens', 0),
                'total_prompt_tokens': code_exec_result.get('total_prompt_tokens', 0),
                'total_tokens': code_exec_result.get('total_tokens', 0)
            }
            
            return {
                'task_id': task_info.get('task_id', 'unknown'),
                'server_name': task_info.get('server_name', 'unknown'),
                'model_name': model_name,
                'status': 'completed',
                'result': formatted_result,
                'execution_time': execution_time,
                'agent_execution_time': execution_time,
                'task_execution_start_time': start_time,
                'total_turns': code_exec_result.get('total_turns', 0),
                'total_tokens': code_exec_result.get('total_tokens', 0),
                'code_executions': code_exec_result.get('code_executions', []),
                'tool_calls': code_exec_result.get('tool_calls', [])
            }
            
        except Exception as e:
            logger.error(f"Error executing with code execution agent: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'task_id': task_info.get('task_id', 'unknown'),
                'server_name': task_info.get('server_name', 'unknown'),
                'model_name': model_name,
                'status': 'failed',
                'error': str(e),
                'execution_time': time.time() - start_time
            }
    
    async def _evaluate_task_result(
        self,
        task_info: Dict[str, Any],
        execution_result: Dict[str, Any],
        model_name: str,
        server_name: str
    ) -> Dict[str, Any]:
        """Evaluate task result using judge."""
        try:
            judge_provider = self._get_judge_provider()
            if not judge_provider:
                logger.warning("No judge provider available - skipping evaluation")
                return execution_result
            
            # Create evaluator with judge stability enabled (2 runs for averaging)
            # Judge stability uses randomized prompts and averages results for more reliable scores
            enable_judge_stability = config_loader.is_judge_stability_enabled()
            evaluator = TaskEvaluator(judge_provider, enable_judge_stability=enable_judge_stability)
            
            # Get result data
            result_data = execution_result.get('result', {})
            
            # Extract task string - ensure it's a string, not a dict or other type
            task_str = task_info.get('query') or task_info.get('task') or task_info.get('description') or ''
            
            # Handle different types
            if isinstance(task_str, dict):
                # If it's a dict, try to extract a string value
                task_str = task_str.get('query') or task_str.get('task') or task_str.get('description') or ''
            elif task_str is None:
                task_str = ''
            
            # Ensure it's a string
            if not isinstance(task_str, str):
                task_str = str(task_str) if task_str else ''
            
            # If still empty, try to get from task_data if available
            if not task_str and 'task_data' in task_info:
                task_data = task_info.get('task_data', {})
                if isinstance(task_data, dict):
                    task_str = task_data.get('query') or task_data.get('task') or task_data.get('description') or ''
                    if not isinstance(task_str, str):
                        task_str = str(task_str) if task_str else ''
            
            # Final fallback
            if not task_str:
                task_str = 'Task evaluation'
            
            # Evaluate using the correct method signature
            evaluation = await evaluator.evaluate(
                task=task_str,
                execution_results=result_data.get('execution_results', []),
                final_solution=result_data.get('solution', ''),
                total_rounds=result_data.get('total_rounds', 0),
                available_tools=result_data.get('available_tools', {}),
                planning_json_compliance=result_data.get('planning_json_compliance', 1.0),
                accumulated_information=result_data.get('accumulated_information', '')
            )
            
            # Add evaluation to result
            execution_result['evaluation'] = evaluation
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error evaluating task result: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return execution_result
    
    async def run_task_with_agent(
        self,
        task_info: Dict[str, Any],
        model_name: str,
        agent_type: str,
        server_manager: Any
    ) -> Dict[str, Any]:
        """
        Run a single task with a specific agent and model.
        
        Args:
            task_info: Task information
            model_name: Model name to use
            agent_type: 'traditional' or 'code_execution'
            server_manager: Connected server manager
            
        Returns:
            Execution result dictionary with evaluation
        """
        try:
            # Execute with appropriate agent
            if agent_type == 'traditional':
                execution_result = await self._execute_with_traditional_agent(
                    task_info, model_name, server_manager
                )
            elif agent_type == 'code_execution':
                execution_result = await self._execute_with_code_execution_agent(
                    task_info, model_name, server_manager
                )
            else:
                raise ValueError(f"Unknown agent type: {agent_type}")
            
            # Evaluate result
            if execution_result.get('status') == 'completed':
                final_result = await self._evaluate_task_result(
                    task_info,
                    execution_result,
                    model_name,
                    task_info.get('server_name', 'unknown')
                )
            else:
                final_result = execution_result
            
            # Add model and agent info
            final_result['model_name'] = model_name
            final_result['agent_type'] = agent_type
            
            return final_result
            
        except Exception as e:
            logger.error(f"Error running task with {agent_type} agent and model {model_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                'task_id': task_info.get('task_id', 'unknown'),
                'server_name': task_info.get('server_name', 'unknown'),
                'model_name': model_name,
                'agent_type': agent_type,
                'status': 'failed',
                'error': str(e),
                'execution_time': 0
            }
    
    async def run_server_group(
        self,
        server_name: str,
        server_tasks: List[Dict[str, Any]],
        models: List[str]
    ) -> None:
        """
        Run all tasks for a server group with all models and agents.
        Connects to server once and runs all combinations before disconnecting.
        
        Args:
            server_name: Server name
            server_tasks: List of tasks for this server
            models: List of model names to test
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing server group: {server_name}")
        logger.info(f"  Tasks: {len(server_tasks)}")
        logger.info(f"  Models: {len(models)}")
        logger.info(f"  Agents: 2 (traditional, code_execution)")
        logger.info(f"  Total combinations: {len(server_tasks) * len(models) * 2}")
        logger.info(f"{'='*80}\n")
        
        # Prepare server configs for first task (assuming all tasks use same server)
        if not server_tasks:
            logger.warning(f"No tasks for server {server_name}")
            return
        
        first_task = server_tasks[0]
        # Pass the full task info (which includes 'servers' field if available)
        server_config_result = await self._prepare_server_configs(server_name, first_task)
        
        if server_config_result.get('status') == 'failed':
            logger.error(f"Failed to prepare server configs: {server_config_result.get('error')}")
            return
        
        all_server_configs = server_config_result.get('all_server_configs', [])
        
        # Connect to servers once for this group
        try:
            async with ConnectionManager(all_server_configs, filter_problematic_tools=self.filter_problematic_tools) as conn_mgr:
                if not conn_mgr.all_tools:
                    logger.error(f"No tools discovered from server {server_name}")
                    return
                
                # Run all combinations for this server group
                combination_count = 0
                total_combinations = len(server_tasks) * len(models) * 2
                
                for task_idx, task_info in enumerate(server_tasks, 1):
                    for model_idx, model_name in enumerate(models, 1):
                        for agent_idx, agent_type in enumerate(['traditional', 'code_execution'], 1):
                            combination_count += 1
                            
                            logger.info(f"\n{'-'*80}")
                            logger.info(f"Combination {combination_count}/{total_combinations}")
                            logger.info(f"  Task: {task_idx}/{len(server_tasks)}")
                            logger.info(f"  Model: {model_idx}/{len(models)} ({model_name})")
                            logger.info(f"  Agent: {agent_idx}/2 ({agent_type})")
                            logger.info(f"{'-'*80}")
                            
                            try:
                                # Run task
                                result = await self.run_task_with_agent(
                                    task_info,
                                    model_name,
                                    agent_type,
                                    conn_mgr.server_manager
                                )
                                
                                # Save result
                                self._save_result(result, task_info)
                                
                                # Update stats
                                if result.get('status') == 'completed':
                                    self.stats['completed_combinations'] += 1
                                else:
                                    self.stats['failed_combinations'] += 1
                                
                            except Exception as e:
                                logger.error(f"Error in combination {combination_count}: {e}")
                                import traceback
                                logger.error(traceback.format_exc())
                                
                                # Record error
                                error_result = {
                                    'task_id': task_info.get('task_id', 'unknown'),
                                    'server_name': server_name,
                                    'model_name': model_name,
                                    'agent_type': agent_type,
                                    'status': 'failed',
                                    'error': str(e),
                                    'execution_time': 0
                                }
                                self._save_result(error_result, task_info)
                                self.stats['failed_combinations'] += 1
                            
                            # Small delay between combinations
                            await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error connecting to server {server_name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _save_result(self, result: Dict[str, Any], task_info: Dict[str, Any]) -> None:
        """Save result to CSV and JSON."""
        try:
            task_id = result.get('task_id', task_info.get('task_id', 'unknown'))
            server_name = result.get('server_name', task_info.get('server_name', 'unknown'))
            model_name = result.get('model_name', 'unknown')
            agent_type = result.get('agent_type', 'unknown')
            
            # Extract task query
            task_query = task_info.get('query', task_info.get('task', task_info.get('description', '')))
            
            # Extract metrics
            execution_time = result.get('execution_time', 0) or result.get('agent_execution_time', 0)
            result_data = result.get('result', {})
            input_tokens = result_data.get('total_prompt_tokens', 0)
            output_tokens = result_data.get('total_output_tokens', 0)
            total_tokens = result_data.get('total_tokens', 0)
            answer = result_data.get('solution', '')
            num_turns = result_data.get('total_rounds', 0)
            evaluation = result.get('evaluation', {})
            
            # Extract code (for CE agent)
            code = None
            if agent_type == 'code_execution':
                code_executions = result.get('code_executions', [])
                if code_executions:
                    last_execution = code_executions[-1]
                    code = last_execution.get('code', '')
            
            # Extract tools used
            tools_used = result_data.get('execution_results', [])
            
            # Map agent type
            agent_type_short = 'MCP' if agent_type == 'traditional' else 'CE'
            
            # Save to CSV tracker
            self.csv_tracker.add_task_result(
                task_id=task_id,
                server=server_name,
                model=model_name,
                agent_type=agent_type_short,
                agent_execution_time=execution_time,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                query=task_query,
                answer=answer,
                code=code,
                num_turns=num_turns,
                tools_used=tools_used,
                evaluation=evaluation
            )
            
            # Add to results list
            self.all_results.append(result)
            
        except Exception as e:
            logger.error(f"Error saving result: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.errors.append({
                'error': str(e),
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
    
    async def run(self) -> Dict[str, Any]:
        """Run the global evaluation."""
        start_time = time.time()
        
        logger.info("="*80)
        logger.info("GLOBAL EVALUATION RUNNER")
        logger.info("="*80)
        logger.info(f"Tasks file: {self.tasks_file}")
        logger.info(f"Task limit: {self.task_limit or 'all'}")
        logger.info(f"Server filter: {self.server_filter or 'all servers'}")
        logger.info(f"Model filter: {self.model_filter or 'all available models'}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("="*80)
        logger.info("")
        
        try:
            # Load tasks
            tasks = await self.load_tasks()
            self.stats['total_tasks'] = len(tasks)
            
            if not tasks:
                logger.warning("No tasks to run!")
                return self._build_summary(start_time)
            
            # Get available models
            models = self.get_available_models()
            
            if not models:
                logger.warning("No models available!")
                return self._build_summary(start_time)
            
            # Group tasks by server
            server_groups = self.group_tasks_by_server(tasks)
            
            # Calculate total combinations
            total_combinations = len(tasks) * len(models) * 2
            self.stats['total_combinations'] = total_combinations
            logger.info(f"\nTotal combinations to run: {total_combinations}")
            logger.info(f"  Tasks: {len(tasks)}")
            logger.info(f"  Models: {len(models)}")
            logger.info(f"  Agents: 2")
            logger.info("")
            
            # Run each server group
            for server_idx, (server_name, server_tasks) in enumerate(server_groups.items(), 1):
                try:
                    logger.info(f"\n{'#'*80}")
                    logger.info(f"Server Group {server_idx}/{len(server_groups)}: {server_name}")
                    logger.info(f"{'#'*80}")
                    
                    await self.run_server_group(server_name, server_tasks, models)
                    
                    # Update completed tasks count
                    for task in server_tasks:
                        if any(r.get('task_id') == task.get('task_id') for r in self.all_results):
                            self.stats['completed_tasks'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing server group {server_name}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    self.errors.append({
                        'error': str(e),
                        'server_name': server_name,
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
            
            # Build summary
            summary = self._build_summary(start_time)
            
            # Save summary
            summary_file = self.output_dir / f"global_evaluation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info(f"\nSummary saved to: {summary_file}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Fatal error in global runner: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._build_summary(start_time)
    
    def _build_summary(self, start_time: float) -> Dict[str, Any]:
        """Build evaluation summary."""
        elapsed_time = time.time() - start_time
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_time_seconds': elapsed_time,
            'statistics': self.stats.copy(),
            'errors': self.errors,
            'output_files': {
                'csv': str(self.csv_tracker.csv_path),
                'json': str(self.csv_tracker.json_path)
            }
        }
        
        # Calculate success rates
        if self.stats['total_combinations'] > 0:
            summary['success_rate'] = self.stats['completed_combinations'] / self.stats['total_combinations']
        else:
            summary['success_rate'] = 0.0
        
        logger.info("\n" + "="*80)
        logger.info("EVALUATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Total tasks: {self.stats['total_tasks']}")
        logger.info(f"Total combinations: {self.stats['total_combinations']}")
        logger.info(f"Completed: {self.stats['completed_combinations']}")
        logger.info(f"Failed: {self.stats['failed_combinations']}")
        logger.info(f"Success rate: {summary['success_rate']:.2%}")
        logger.info(f"Elapsed time: {elapsed_time:.2f}s")
        logger.info(f"CSV file: {self.csv_tracker.csv_path}")
        logger.info(f"JSON file: {self.csv_tracker.json_path}")
        logger.info("="*80)
        
        return summary


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Global runner for comprehensive evaluation across tasks, models, and agents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --tasks-file tasks/tasks.json
  %(prog)s --tasks-file tasks/tasks.json --task-limit 5
  %(prog)s --tasks-file tasks/tasks.json --servers Wikipedia "National Parks"
  %(prog)s --tasks-file tasks/tasks.json --models gpt-4o gpt-4o-mini
  %(prog)s --tasks-file tasks/tasks.json --task-limit 10 --servers Wikipedia --models gpt-4o
        '''
    )
    
    parser.add_argument(
        '--tasks-file',
        required=True,
        metavar='FILE',
        help='Path to tasks JSON file (mandatory)'
    )
    
    parser.add_argument(
        '--task-limit',
        type=int,
        default=None,
        help='Limit number of tasks to run (default: all)'
    )
    
    parser.add_argument(
        '--servers',
        nargs='+',
        metavar='SERVER',
        help='Filter tasks by server name(s). Example: --servers Wikipedia "National Parks"'
    )
    
    parser.add_argument(
        '--models',
        nargs='+',
        metavar='MODEL',
        help='Filter models to use. Example: --models gpt-4o gpt-4o-mini. If not specified, uses all available models.'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./results',
        metavar='DIR',
        help='Output directory for results (default: ./results)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create runner
    runner = GlobalRunner(
        tasks_file=args.tasks_file,
        task_limit=args.task_limit,
        server_filter=args.servers,
        model_filter=args.models,
        output_dir=args.output_dir
    )
    
    # Run evaluation
    try:
        summary = await runner.run()
        logger.info("\n✅ Global evaluation completed!")
        return 0
    except KeyboardInterrupt:
        logger.info("\n⚠️  Evaluation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
