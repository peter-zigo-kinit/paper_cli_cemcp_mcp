"""
Result Adapter for converting agent results to mcp-bench format.

This module handles the conversion between:
- AI_Code_Execution_with_MCP agent results
- mcp-bench expected result format with execution_results, solution, etc.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ResultAdapter:
    """Adapter for converting agent results to mcp-bench format."""
    
    def __init__(self, available_tools: Optional[Dict[str, Any]] = None):
        """
        Initialize the result adapter.
        
        Args:
            available_tools: Dictionary of available tools (for including in results)
        """
        self.available_tools = available_tools or {}
    
    def convert_traditional_mcp_result(self, agent_result: Dict[str, Any], 
                                      task_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert TraditionalMCPBenchmark result to mcp-bench format.
        
        Args:
            agent_result: Result from TraditionalMCPBenchmark.run_benchmark_async():
                {
                    'success': bool,
                    'output': str,
                    'time': float,
                    'llm_calls': List[Dict],
                    'tokens': Dict[str, int]
                }
            task_metadata: Task metadata from TaskAdapter
        
        Returns:
            Result in mcp-bench format:
                {
                    'solution': str,
                    'total_rounds': int,
                    'execution_results': List[Dict],
                    'accumulated_information': str,
                    'total_output_tokens': int,
                    'total_prompt_tokens': int,
                    'total_tokens': int
                }
        """
        # Extract solution from output
        solution = agent_result.get('output', '')
        
        # Calculate total rounds from LLM call count
        llm_calls = agent_result.get('llm_calls', [])
        total_rounds = len(llm_calls)
        
        # Create execution_results from LLM calls
        # Note: Traditional MCP doesn't expose individual tool calls directly,
        # so we create a simplified structure based on LLM calls
        execution_results = self._create_execution_results_from_llm_calls(llm_calls)
        
        # Create accumulated_information from execution history
        accumulated_information = self._create_accumulated_info_from_llm_calls(
            llm_calls, agent_result.get('time', 0)
        )
        
        # Extract token usage - try top-level first, then aggregate from llm_calls
        tokens = agent_result.get('tokens', {})
        
        # Check if tokens are at top level (with different key names)
        if tokens:
            # Map orchestrator format (prompt_tokens, completion_tokens) to expected format
            total_prompt_tokens = tokens.get('prompt_tokens', tokens.get('input', 0))
            total_output_tokens = tokens.get('completion_tokens', tokens.get('output', 0))
            total_tokens = tokens.get('total_tokens', tokens.get('total', 0))
        else:
            # Aggregate from llm_calls if top-level tokens are missing
            total_prompt_tokens = 0
            total_output_tokens = 0
            total_tokens = 0
            
            for llm_call in llm_calls:
                call_tokens = llm_call.get('tokens', {})
                if call_tokens:
                    # Handle both formats
                    total_prompt_tokens += call_tokens.get('prompt_tokens', call_tokens.get('input', 0))
                    total_output_tokens += call_tokens.get('completion_tokens', call_tokens.get('output', 0))
                    total_tokens += call_tokens.get('total_tokens', call_tokens.get('total', 0))
        
        return {
            'solution': solution,
            'total_rounds': total_rounds,
            'execution_results': execution_results,
            'accumulated_information': accumulated_information,
            'total_output_tokens': total_output_tokens,
            'total_prompt_tokens': total_prompt_tokens,
            'total_tokens': total_tokens
        }
    
    def convert_code_execution_result(self, agent_result: Dict[str, Any],
                                     task_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert CodeExecutionBenchmark result to mcp-bench format.
        
        Args:
            agent_result: Result from CodeExecutionBenchmark.run_benchmark_async():
                {
                    'success': bool,
                    'output': str,
                    'error': str (optional),
                    'time': float,
                    'llm_calls': List[Dict],
                    'tokens': Dict[str, int]
                }
            task_metadata: Task metadata from TaskAdapter
        
        Returns:
            Result in mcp-bench format
        """
        # Extract solution from output
        solution = agent_result.get('output', '')
        if not solution and agent_result.get('error'):
            solution = f"Error: {agent_result.get('error', 'Unknown error')}"
        
        # Calculate total rounds from LLM call count
        llm_calls = agent_result.get('llm_calls', [])
        total_rounds = len(llm_calls)
        
        # Create execution_results from LLM calls and code execution
        # Code execution generates Python code that calls MCP tools,
        # but we don't have direct access to individual tool calls
        execution_results = self._create_execution_results_from_code_execution(
            llm_calls, agent_result
        )
        
        # Create accumulated_information from execution history
        accumulated_information = self._create_accumulated_info_from_code_execution(
            llm_calls, agent_result
        )
        
        # Extract token usage - try top-level first, then aggregate from llm_calls
        tokens = agent_result.get('tokens', {})
        
        # Check if tokens are at top level (with different key names)
        if tokens:
            # Map orchestrator format (prompt_tokens, completion_tokens) to expected format
            total_prompt_tokens = tokens.get('prompt_tokens', tokens.get('input', 0))
            total_output_tokens = tokens.get('completion_tokens', tokens.get('output', 0))
            total_tokens = tokens.get('total_tokens', tokens.get('total', 0))
        else:
            # Aggregate from llm_calls if top-level tokens are missing
            total_prompt_tokens = 0
            total_output_tokens = 0
            total_tokens = 0
            
            for llm_call in llm_calls:
                call_tokens = llm_call.get('tokens', {})
                if call_tokens:
                    # Handle both formats
                    total_prompt_tokens += call_tokens.get('prompt_tokens', call_tokens.get('input', 0))
                    total_output_tokens += call_tokens.get('completion_tokens', call_tokens.get('output', 0))
                    total_tokens += call_tokens.get('total_tokens', call_tokens.get('total', 0))
        
        return {
            'solution': solution,
            'total_rounds': total_rounds,
            'execution_results': execution_results,
            'accumulated_information': accumulated_information,
            'total_output_tokens': total_output_tokens,
            'total_prompt_tokens': total_prompt_tokens,
            'total_tokens': total_tokens
        }
    
    def _create_execution_results_from_llm_calls(self, llm_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create execution_results structure from LLM calls.
        
        Since Traditional MCP doesn't expose individual tool calls,
        we create a simplified structure where each LLM call represents a round.
        """
        execution_results = []
        
        for i, llm_call in enumerate(llm_calls, 1):
            # Create a simplified execution result for each LLM call
            # In Traditional MCP, the LLM decides which tools to call,
            # but we don't have direct access to those calls
            execution_results.append({
                'round_num': i,
                'tool': 'llm_decision',
                'server': 'traditional_mcp',
                'parameters': {},
                'success': True,
                'result': f"LLM call {i} completed",
                'latency': llm_call.get('latency', 0),
                'tokens': llm_call.get('tokens', {})
            })
        
        return execution_results
    
    def _create_execution_results_from_code_execution(self, 
                                                     llm_calls: List[Dict[str, Any]],
                                                     agent_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create execution_results structure from code execution.
        
        Code execution generates Python code that calls MCP tools,
        but we don't have direct access to individual tool calls.
        We create a structure based on LLM calls (code generation rounds).
        """
        execution_results = []
        
        for i, llm_call in enumerate(llm_calls, 1):
            # Each LLM call generates code that may call multiple MCP tools
            # We represent this as a code execution round
            execution_results.append({
                'round_num': i,
                'tool': 'code_execution',
                'server': 'code_execution_mcp',
                'parameters': {},
                'success': True,
                'result': f"Code execution round {i} completed",
                'latency': llm_call.get('latency', 0),
                'tokens': llm_call.get('tokens', {})
            })
        
        return execution_results
    
    def _create_accumulated_info_from_llm_calls(self, llm_calls: List[Dict[str, Any]], 
                                                total_time: float) -> str:
        """
        Create accumulated_information from LLM call history.
        """
        info_parts = []
        info_parts.append(f"Traditional MCP Execution Summary")
        info_parts.append(f"Total execution time: {total_time:.2f}s")
        info_parts.append(f"Total LLM calls: {len(llm_calls)}")
        info_parts.append("")
        
        for i, llm_call in enumerate(llm_calls, 1):
            info_parts.append(f"--- Round {i} ---")
            info_parts.append(f"Latency: {llm_call.get('latency', 0):.2f}s")
            tokens = llm_call.get('tokens', {})
            if tokens:
                info_parts.append(f"Tokens: {tokens.get('total_tokens', 0)} "
                                f"(prompt: {tokens.get('prompt_tokens', 0)}, "
                                f"completion: {tokens.get('completion_tokens', 0)})")
            info_parts.append("")
        
        return "\n".join(info_parts)
    
    def _create_accumulated_info_from_code_execution(self, 
                                                    llm_calls: List[Dict[str, Any]],
                                                    agent_result: Dict[str, Any]) -> str:
        """
        Create accumulated_information from code execution history.
        """
        info_parts = []
        info_parts.append(f"Code Execution MCP Summary")
        info_parts.append(f"Total execution time: {agent_result.get('time', 0):.2f}s")
        info_parts.append(f"Total LLM calls: {len(llm_calls)}")
        
        if agent_result.get('error'):
            info_parts.append(f"Error: {agent_result.get('error')}")
        
        info_parts.append("")
        
        for i, llm_call in enumerate(llm_calls, 1):
            info_parts.append(f"--- Round {i} ---")
            info_parts.append(f"Latency: {llm_call.get('latency', 0):.2f}s")
            tokens = llm_call.get('tokens', {})
            if tokens:
                info_parts.append(f"Tokens: {tokens.get('total_tokens', 0)} "
                                f"(prompt: {tokens.get('prompt_tokens', 0)}, "
                                f"completion: {tokens.get('completion_tokens', 0)})")
            info_parts.append("")
        
        return "\n".join(info_parts)
    
    def add_available_tools(self, tools: Dict[str, Any]) -> None:
        """
        Update available tools for inclusion in results.
        
        Args:
            tools: Dictionary of available tools
        """
        self.available_tools = tools
    
    def get_available_tools(self) -> Dict[str, Any]:
        """
        Get available tools for inclusion in results.
        
        Returns:
            Dictionary of available tools
        """
        return self.available_tools

