"""
Result Logger Utility for logging LLM responses, token usage, and final results
"""
from typing import Dict, List, Any
import json
import os
from datetime import datetime
from app.app_logging.logger import setup_logger


# Setup logger
logger = setup_logger(__name__)


class ResultLogger:
    """Handles all logging for LLM responses, token usage, and final results"""
    
    @staticmethod
    def log_llm_response_with_tokens(llm_call_number: int, response: Dict):
        """
        Log LLM response including status, reasoning, code, and token usage.
        
        Args:
            llm_call_number: Sequential number of the LLM call
            response: Response dictionary from LLM containing status, code, reasoning, and token_usage
        """
        # Build response JSON for logging
        response_json = json.dumps({
            "status": response["status"],
            "code": response["code"],
            "reasoning": response.get("reasoning", "")
        }, indent=2)
        
        # Extract token usage information
        token_usage = response.get("token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)
        
        # Log complete LLM response with token usage
        logger.info(f"{'=' * 80}\nLLM RESPONSE (Call {llm_call_number})\n{'=' * 80}\nJSON Response:\n{response_json}\n\nStatus: {response['status']}\nReasoning: {response.get('reasoning', '')}\n\n{'=' * 80}\nTOKEN USAGE (Call {llm_call_number})\n{'=' * 80}\nInput Tokens: {prompt_tokens}\nOutput Tokens: {completion_tokens}\nTotal Tokens: {total_tokens}\n{'=' * 80}\n\nGenerated Code:\n{'-' * 80}\n{response['code']}\n{'-' * 80}")
    
    @staticmethod
    def calculate_and_log_token_usage(token_usage_list: List[Dict]):
        """
        Calculate and log token usage statistics for all LLM calls.
        
        Args:
            token_usage_list: List of token usage dictionaries from all LLM calls
        """
        if not token_usage_list:
            return
        
        # Calculate total token usage across all LLM calls
        total_prompt_tokens = sum(usage.get("prompt_tokens", 0) for usage in token_usage_list)
        total_completion_tokens = sum(usage.get("completion_tokens", 0) for usage in token_usage_list)
        total_tokens_consumed = sum(usage.get("total_tokens", 0) for usage in token_usage_list)
        
        # Build per-call token usage summary
        token_lines = []
        for i, usage in enumerate(token_usage_list, 1):
            prompt = usage.get("prompt_tokens", 0)
            completion = usage.get("completion_tokens", 0)
            total = usage.get("total_tokens", 0)
            token_lines.append(f"LLM Call {i}: Input={prompt}, Output={completion}, Total={total}")
        token_summary = "\n".join(token_lines)
        
        # Log complete token usage report
        logger.info(f"\n{'=' * 80}\nTOKEN USAGE SUMMARY\n{'=' * 80}\n{token_summary}\n\n{'-' * 80}\nTOTAL TOKENS CONSUMED\n{'-' * 80}\nTotal Input Tokens: {total_prompt_tokens}\nTotal Output Tokens: {total_completion_tokens}\nTotal Tokens: {total_tokens_consumed}\n{'=' * 80}\n")
    
    @staticmethod
    def display_final_results(final_result: Dict, turn_times: List[float], 
                              total_time: float, token_usage_list: List[Dict]):
        """
        Display final results and performance summary with token usage.
        
        Args:
            final_result: Dictionary containing execution results (success, output, error)
            turn_times: List of execution times for each LLM call
            total_time: Total execution time for all calls
            token_usage_list: List of token usage dictionaries from all LLM calls
        """
        status = 'SUCCESS' if final_result['success'] else 'FAILED'
        
        # Log final results
        logger.info(f"\n\n{'=' * 80}\nFINAL RESULTS\n{'=' * 80}\n\nStatus: {status}\n\nOutput:\n{'-' * 80}\n{final_result['output']}\n{'-' * 80}\n")
        
        # Log errors if any
        if final_result['error']:
            logger.error(f"Error Details:\n{'-' * 80}\n{final_result['error']}\n{'-' * 80}\n")
        
        # Build performance summary with latency
        perf_lines = [f"LLM Call {i}: {t:.2f}s (latency)" for i, t in enumerate(turn_times, 1)]
        perf_summary = "\n".join(perf_lines)
        
        logger.info(f"\n{'=' * 80}\nPERFORMANCE SUMMARY\n{'=' * 80}\n{perf_summary}\n\nTotal Time: {total_time:.2f}s\nTotal LLM Calls: {len(turn_times)}\n{'=' * 80}\n")
        
        # Display token usage summary
        ResultLogger.calculate_and_log_token_usage(token_usage_list)
    
    @staticmethod
    def save_benchmark_results(query: str, final_result: Dict, turn_times: List[float], 
                               total_time: float, token_usage_list: List[Dict]) -> None:
        """
        Save benchmark results to JSON file maintaining all query history.
        
        Args:
            query: User query that was benchmarked
            final_result: Dictionary containing execution results (success, output, error)
            turn_times: List of execution times for each LLM call
            total_time: Total execution time for all calls
            token_usage_list: List of token usage dictionaries from all LLM calls
        """
        results_file = "Code_MCP_Benchmark_Results.json"
        
        # Calculate total tokens
        total_prompt_tokens = sum(usage.get("prompt_tokens", 0) for usage in token_usage_list)
        total_completion_tokens = sum(usage.get("completion_tokens", 0) for usage in token_usage_list)
        total_tokens_consumed = sum(usage.get("total_tokens", 0) for usage in token_usage_list)
        
        # Build LLM calls details with latency
        llm_calls_details = []
        for i, usage in enumerate(token_usage_list, 1):
            call_detail = {
                "call_number": i,
                "latency": round(turn_times[i-1], 2) if i <= len(turn_times) else 0,
                "tokens": {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                }
            }
            llm_calls_details.append(call_detail)
        
        # Build result dictionary
        result = {
            "success": final_result['success'],
            "final_output": final_result['output'],
            "error": final_result.get('error', ''),
            "time": round(total_time, 2),
            "llm_calls": llm_calls_details,
            "total_tokens": {
                "prompt_tokens": total_prompt_tokens,
                "completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens_consumed
            }
        }
        
        # Load existing results or create new list
        if os.path.exists(results_file):
            with open(results_file, "r") as f:
                try:
                    all_results = json.load(f)
                    # Convert old format to list if needed
                    if not isinstance(all_results, list):
                        all_results = [all_results]
                except json.JSONDecodeError:
                    all_results = []
        else:
            all_results = []
        
        # Add new result with metadata
        result_with_metadata = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "result": result
        }
        
        all_results.append(result_with_metadata)
        
        # Save all results
        with open(results_file, "w") as f:
            json.dump(all_results, f, indent=2)
        
        logger.info(f"\nBenchmark results saved to {results_file} (Total runs: {len(all_results)})")

