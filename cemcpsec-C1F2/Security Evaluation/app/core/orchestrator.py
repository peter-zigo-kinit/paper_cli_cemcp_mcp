"""
Orchestrator for code execution with MCP.

This module handles the multi-turn conversation flow between the LLM and code executor,
managing the lifecycle of MCP connections and code execution.
"""
import asyncio
from typing import Dict, Any, List
import time
import json

# Application imports
from app.core import get_mcp_client, OpenAICodeAgent, OpenAIJudge, get_docker_executor
from app.utils import ResultLogger
from app.app_logging.logger import setup_logger
from app.config import (
    DOCKER_IMAGE_NAME,
    DOCKER_MCP_GATEWAY,
    CODE_EXECUTION_TIMEOUT
)


# Initialize logger for tracking orchestration operations
logger = setup_logger(__name__)
class RealMCPOrchestrator:
    """
    Orchestrates code execution with real MCP servers.
    
    This class manages the entire workflow of:
    1. Initializing MCP connections
    2. Generating code through LLM
    3. Executing code in sandbox environment
    4. Managing multi-turn conversations
    5. Collecting and returning results
    """

    def __init__(self):
        """
        Initialize orchestrator with MCP configuration.
        
        Args:
            mcp_config_path: Path to MCP configuration file. If None, uses default from config.
        """
        
        # # Initialize MCP client for connecting to MCP servers
        # self._mcp_client = get_mcp_client(MCP_CONFIG_PATH)
        
        # Initialize code executor with timeout configuration
        # self.code_executor = CodeExecutor(timeout=CODE_EXECUTION_TIMEOUT)
        
        self._docker_executor = get_docker_executor(image=DOCKER_IMAGE_NAME,
                                                  gateway_url=DOCKER_MCP_GATEWAY,
                                                  timeout_s=CODE_EXECUTION_TIMEOUT)
        
        # Initialize OpenAI agent for code generation
        self.agent = OpenAICodeAgent()

        # Initialize OpenAI judge for code and execution results
        self.judge = OpenAIJudge()

    async def initialize_async(self):
        """
        Initialize MCP connections asynchronously.
        
        This method:
        1. Initializes the MCP client
        2. Discovers available servers
        3. Lists available tools from each server
        """
        # Log initialization start banner
        logger.info("\n\n" + "=" * 80)
        logger.info("INITIALIZING MCP CLIENT CONNECTIONS")
        logger.info("=" * 80 + "\n")

        # Initialize MCP client and connect to all configured servers
        self._mcp_client = await get_mcp_client()
        print(f"Orchestrator using mcp_client: {self._mcp_client} \n")
        # Start container for code execution
        await self._docker_executor.start_container()

        # Log initialization completion banner
        logger.info("=" * 80)
        logger.info("INITIALIZATION COMPLETE")
        logger.info("=" * 80 + "\n\n")

    async def run_pre_execution_judge_async(self, task: Dict[str, Any], response: Dict[str, Any], llm_call_number: int, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any] | str:
        """
        Run pre-execution judge async.
        Args:
            task: Task dictionary containing user query and other task details.
                - task_id: Task identifier string.
                - user_query: User query string.
                - expected_behaviour: Expected behaviour string.
                - expected_output: Expected output string.
            response: Response dictionary containing code agent response.
                - status: Status string.
                - code: Generated code string.
                - reasoning: Reasoning string.
            llm_call_number: Current LLM call number.
            conversation_history: List of conversation history messages.
            max_turns: Maximum number of turns to prevent infinite loops.
        Returns:
            Dictionary containing pre-execution judge results.
                - status: Judge status string.
                - verdict: Judge verdict string.
                - reasoning: Judge reasoning string.
                - tokens: Judge token usage dictionary.
            Error: str    
        """
        # Build Context for Judge.
        # Conversation history include the user query at this phase.
        response_message = {k: v for k,v in response.items() if k != 'token_usage'}
        assistant_message = {
            'role': 'assistant',
            'content': json.dumps(response_message, indent=2)
            }
        
        # Can be used for tunings, in real world there are no baselines expectations.
        system_message = None
        # system_message = {
        #     'role': 'system',
        #     'content': {k: v for k,v in task.items() if k == 'expected_behaviour' or k == 'expected_output'}
        #     }

        
        complete_context = conversation_history.copy()
        complete_context.append(assistant_message)
        start_time = time.time()
        try:
            pre_execution_judge_response = await self.judge.judge_code_and_execution_results(complete_context, mode="pre_execution")
            
            return {
                "status": pre_execution_judge_response["status"],
                "verdict": pre_execution_judge_response["verdict"],
                "reasoning": pre_execution_judge_response["reasoning"],
                "tokens": pre_execution_judge_response["token_usage"],
                "time": time.time() - start_time,
                "error": None
            }

        except Exception as e:
            return {"error": str(e)}


    async def run_post_execution_judge_async(self, task: Dict[str, Any], execution_result: Dict[str, Any], response: Dict[str, Any], llm_call_number: int, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any] | str:
        """
        Run post-execution judge async.
        Args:
            task: Task dictionary containing user query and other task details.
                - task_id: Task identifier string.
                - user_query: User query string.
                - expected_behaviour: Expected behaviour string.
                - expected_output: Expected output string.
            response: Response dictionary containing code agent response.
                - status: Status string.
                - code: Generated code string.
                - reasoning: Reasoning string.
            execution_result: Execution result dictionary containing execution result.
                - success: Execution success boolean.
                - output: Execution output string.
                - error: Execution error string.
            llm_call_number: Current LLM call number.
            conversation_history: List of conversation history messages.
        Returns:
            Dictionary containing post-execution judge results.
                - status: Judge status string.
                - verdict: Judge verdict string.
                - reasoning: Judge reasoning string.
                - tokens: Judge token usage dictionary.  
            Error: str     
        """
        # Filtering out the token usage, which isnt relevant for Judge.
        response_message = {k: v for k,v in response.items() if k != 'token_usage'}
        # Build Context for Judge.
        # Conversation history include the user query at this phase.
        assistant_code_agent_response_message = {
            'role': 'assistant',
            'content': json.dumps(response_message, indent=2)
            }

        assistant_execution_result_message = {
            'role': 'assistant',
            'content': json.dumps(execution_result, indent=2)
            }
        
        # Can be used for tunings, in real world there are no baselines expectations.
        system_message = None
        # system_message = {
        #     'role': 'system',
        #     'content': {k: v for k,v in task.items() if k == 'expected_behaviour' or k == 'expected_output'}
        #     }
 
        complete_context = conversation_history.copy()
        complete_context.append(assistant_code_agent_response_message)
        complete_context.append(assistant_execution_result_message)
        start_time = time.time()
        try:
            post_execution_judge_response = await self.judge.judge_code_and_execution_results(complete_context, mode="post_execution")
            
            return {
                "status": post_execution_judge_response["status"],
                "verdict": post_execution_judge_response["verdict"],
                "reasoning": post_execution_judge_response["reasoning"],
                "tokens": post_execution_judge_response["token_usage"],
                "time": time.time() - start_time,
                "error": None
            }

        except Exception as e:
            return {"error": str(e)}
        
    async def run_multi_turn_code_async(self, task: Dict[str, Any], max_turns: int = 3, use_judge: bool = False) -> Dict[str, Any]:
        """
        Run multi-turn conversation with status-based loop.
        
        Implements progressive discovery approach where agent decides
        if it needs exploration or can complete directly.
        
        Args:
            user_query: User's natural language request
            max_turns: Maximum number of turns to prevent infinite loops
            use_judge: Whether to use LLM as judge for code safety checks
            
        Returns:
            Dictionary containing:
                - success: Boolean indicating if execution was successful
                - output: Final output from code execution
                - error: Error message if any
                - time: Total execution time
                - llm_calls: List of LLM call details
                - tokens: Token usage information
                - conversation_history: Conversation history
                - turn_details: Detailed turn information
        """
        user_query = task.get("user_query")
        # Start timer for total execution time tracking
        total_start = time.time()
        
        # Log the user query
        logger.info(f"\n\n{'=' * 80}\nUSER QUERY: {user_query}\n{'=' * 80}\n")
        
        # Initialize conversation with user query
        user_message = {"role": "user", "content": user_query}
        messages = [user_message]
        
        # Initialize variables for tracking results and metrics
        final_result = None
        turn_times = []
        total_token_usage_list = []
        execution_results = []  # Track all execution outputs for final summarization
        turn_judge_turns = {}  # Track judge_turns for each turn: {turn_number: judge_turns_list}
        executed_turn_count = 0  # Track how many turns actually executed (for mapping llm_call_number to turn_number)
        
        # Multi-turn loop: iterate up to max_turns times
        for llm_call_number in range(1, max_turns + 1):
            turn_token_usage_list = []
            # Start timer for this turn
            turn_start = time.time()
            
            # Get LLM response with generated code
            response = await self._get_llm_response(llm_call_number, messages)
            turn_token_usage_list.append(response.get("token_usage", {}))
            
            # Handle case where code generation fails
            if response is None:
                return {"success": False, "output": "", "error": "Code generation failed"}
        
            # Check if task is complete (status="complete" means agent finished)
            if response["status"] == "complete":
                logger.info("\nTask COMPLETE (status=complete)\n")
                # Create proper result dictionary with reasoning as output
                final_result = {
                    "success": True,
                    "output": response.get("reasoning", ""),
                    "error": None
                }
                break
            
            # Final turn check:
            # Check if code is empty (status="complete" with empty code means final answer in reasoning)
            code = response.get("code", "").strip()
            is_complete_with_empty_code = response["status"] == "complete" and (not code or code == "")
            
            # Execute the generated code only if it's not empty.
            if is_complete_with_empty_code:
                # No code to execute, use empty execution result
                execution_result = {
                    "success": True,
                    "output": "",
                    "error": None
                }
                logger.info(f"\n{'=' * 80}\nSKIPPING CODE EXECUTION (status=complete, empty code)\n{'=' * 80}")
                logger.info("Final answer will be taken from reasoning field")
                break
            
            # Execute code - with or without judge based on use_judge flag
            else:
                executed_turn_count += 1  # Increment executed turn count (this turn will add messages)
                
                if use_judge:
                    judge_turn_summaries = {
                    "iteration": 1, # Inner turn iterations for judge.
                    "pre_execution": {}, # Phase A
                    "execution": None, # Phase B
                    "post_execution": {}, # Phase C
                    "status": "pending"
                    }
                    
                    # Judge Flow: Pre-execution judge.
                    pre_execution_judge_result = await self.run_pre_execution_judge_async(task, response, llm_call_number, messages)
                    
                    
                    # [Based on Judge.verdict system decides next operations] -> Execution or code generation.
                    execution_result = await self._docker_executor.execute_async(response["code"])
                    
                    judge_turn_summaries["execution"] = execution_result


                    post_execution_judge_result = await self.run_post_execution_judge_async(task, execution_result, response, llm_call_number, messages)
                    # [Based on post_execution_judge.verdict, the system decides next operations] -> re generation code, mark tools, etc...
                  
                    # Store Judge data for this turn. Verdict lives inside pre_execution and post_execution only.
                    if not post_execution_judge_result["error"] and not pre_execution_judge_result["error"] and not execution_result["error"]:
                        judge_turn_summaries["status"] = "success"
                        judge_turn_summaries["turn_time"] = pre_execution_judge_result["time"] + post_execution_judge_result["time"]
                        judge_turn_summaries["pre_execution"] = pre_execution_judge_result
                        judge_turn_summaries["execution"] = execution_result
                        judge_turn_summaries["post_execution"] = post_execution_judge_result
                        turn_token_usage_list.extend([pre_execution_judge_result["tokens"], post_execution_judge_result["tokens"]])
                    else:
                        judge_turn_summaries["status"] = "error"
                        judge_turn_summaries["error"] = post_execution_judge_result["error"] if post_execution_judge_result["error"] else pre_execution_judge_result["error"] if pre_execution_judge_result["error"] else execution_result["error"]
                        judge_turn_summaries["pre_execution"] = pre_execution_judge_result
                        judge_turn_summaries["post_execution"] = post_execution_judge_result
                        


                    # Success - all checks passed
                    turn_judge_turns[executed_turn_count] = [judge_turn_summaries]

                # Execute code directly without judge
                else:
                    logger.info(f"\n{'=' * 80}\nEXECUTING CODE WITHOUT JUDGE (Call {llm_call_number})\n{'=' * 80}")
                    execution_result = await self._docker_executor.execute_async(response["code"])
                    logger.info(f"\nExecution Result:\n{'-' * 80}\n{execution_result.get('output', '')}\n{'-' * 80}")
                    if execution_result.get('error'):
                        logger.error(f"\nError: {execution_result['error']}")
                
            # Track execution output for final summarization
            if execution_result.get("output"):
                execution_results.append(execution_result["output"])
            elif execution_result.get("error"):
                logger.warning(f"Execution failed in LLM call {llm_call_number}, but continuing...\n")
                execution_results.append(execution_result["error"])

            # Calculate turn execution time
            turn_time = time.time() - turn_start
            turn_times.append(turn_time)
            
            # Sum of both initial llm_response and judge tokens.
            turn_tokens = self._calculate_total_tokens(turn_token_usage_list)
            
            # Store token usage for this turn
            total_token_usage_list.append(turn_tokens)
            
            # Log turn completion
            logger.info(f"\n{'=' * 80}\nLLM CALL {llm_call_number} COMPLETED in {turn_time:.2f}s\n{'=' * 80}")
            
            # Add results to conversation history (for both "exploring" and "complete" status)
            # This function appends assistant response and execution result to the conversation history
            self._update_conversation_with_results(llm_call_number, response, execution_result, messages)  

        # Handle case where max turns reached without completion ( status hasn't reached 'complete' )
        if final_result is None:
            logger.warning(f"\nMax turns ({max_turns}) reached")
            # execution_result is already a dict, use it directly
            final_result = execution_result if isinstance(execution_result, dict) else {
                "success": False,
                "output": "",
                "error": "Max turns reached without completion"
            }
        
        # Calculate total execution time
        total_time = time.time() - total_start
        
        # Display final results summary (use original result for display, but return formatted answer)
        # Ensure final_result is a dict
        if not isinstance(final_result, dict):
            final_result = {
                "success": True,
                "output": str(final_result),
                "error": None
            }
        
        ResultLogger.display_final_results(final_result, turn_times, total_time, total_token_usage_list)
        
        # Return formatted result dictionary
        return {
            "success": final_result.get("success", False),
            "output": final_result.get("output", ""),  # Final answer (from reasoning if complete, or execution output)
            "raw_output": execution_results[-1] if execution_results else final_result.get("output", ""),  # Last execution output for reference
            "error": final_result.get("error"),
            "time": total_time,
            "llm_calls": self._format_llm_calls(turn_times, total_token_usage_list),
            "tokens": self._calculate_total_tokens(total_token_usage_list),
            "conversation_history": messages,
            "turn_details": self._format_turn_details(messages, turn_times, total_token_usage_list, turn_judge_turns)
        }
    
    # Using agent's generated code.
    async def _get_llm_response(self, llm_call_number: int, messages: list) -> Dict[str, str]:
        """
        Get code generation response from LLM with conversation history.
        
        Args:
            llm_call_number: Current LLM call number for logging
            messages: Conversation history messages
            
        Returns:
            Dictionary containing status, code, reasoning, and token usage
        """
        # Log LLM call start with conversation size
        logger.info(f"\n\n{'=' * 80}\nLLM CALL {llm_call_number}\n{'=' * 80}\n\nSending {len(messages)} messages to LLM...\n")
        
        # Call LLM agent to generate code based on conversation history
        try:
            response = await self.agent.generate_code_with_history(messages)
        except Exception as e:
            # Log error and return None if code generation fails
            logger.error(f"Error generating code: {e}")
            return None
        
        # Log LLM response details including token usage
        ResultLogger.log_llm_response_with_tokens(llm_call_number, response)
        
        # Return LLM response containing status, code, reasoning, and tokens
        return response
    
    # Using docker_executor ( Deprecated )
    async def _run_generated_code_and_log(self, llm_call_number: int, response: Dict) -> Dict:
        """
        Execute generated code in sandbox and log results.
        
        Args:
            llm_call_number: Current LLM call number for logging
            response: LLM response containing generated code
            
        Returns:
            Dictionary containing execution results (success, output, error)
        """
        # Log code execution start
        logger.info(f"\n{'=' * 80}\nEXECUTING CODE (Call {llm_call_number})\n{'=' * 80}")
        
        # Execute the generated code in sandbox environment
        # execution_result = await self.code_executor.execute_async(response["code"])
        execution_result = await self._docker_executor.execute_async(response["code"])
        
        # Log the execution output
        logger.info(f"\nExecution Result:\n{'-' * 80}\n{execution_result['output']}\n{'-' * 80}")
        
        # Log any errors that occurred during execution ( Related to docker container execution and timouts)
        if execution_result['error']:
            logger.error(f"\nError: {execution_result['error']}")

        return execution_result
    
    def _update_conversation_with_results(self, llm_call_number: int, response: Dict, 
                                           execution_result: Dict, messages: list):
        """
        Append assistant response and execution results to conversation history.
        
        Args:
            llm_call_number: Current LLM call number for logging
            response: LLM response containing status, code, and reasoning
            execution_result: Results from code execution
            messages: Conversation history to update
        """
        # Log based on status
        if response["status"] == "complete":
            logger.info("\nTask complete - final answer in reasoning field")
        else:
            logger.info("\nContinuing to next LLM call (status=exploring)...")
        
        # Create JSON string of assistant's response for conversation history
        assistant_message_json = json.dumps({
            "status": response["status"],
            "code": response["code"],
            "reasoning": response.get("reasoning", "")
        })
        
        # Append assistant message to conversation history
        messages.append({
            "role": "assistant",
            "content": assistant_message_json
        })
        
        # Append execution result as user message to conversation history
        # If code was empty (complete status), execution_result will have empty output
        execution_output = execution_result.get('output', '')
        if response["status"] == "complete" and not execution_output:
            # For complete status with empty code, indicate final answer is in reasoning
            messages.append({
                "role": "user",
                "content": "Task complete - final answer provided in reasoning"
            })
        else:
            messages.append({
                "role": "user",
                "content": f"Execution result:\n{execution_output if execution_output else execution_result.get('error', '')}"
            })
        
        # Log what was added to conversation history
        logger.info(f"\n{'=' * 80}\nADDED TO CONVERSATION HISTORY (Call {llm_call_number})\n{'=' * 80}\n\nAssistant Message (JSON added to history):\n{assistant_message_json}\n\nUser Message: Execution result ({len(execution_result['output'])} chars)\nTotal history size: {len(messages)} messages\n")

    def _format_llm_calls(self, turn_times: list, token_usage_list: list) -> list:
        """
        Format LLM call details for result output.
        
        Args:
            turn_times: List of execution times for each turn
            token_usage_list: List of token usage for each turn
            
        Returns:
            List of formatted LLM call details
        """
        # Initialize empty list for formatted LLM call data
        llm_calls = []
        
        # Iterate through each turn and combine time + token data
        for i, (time_taken, tokens) in enumerate(zip(turn_times, token_usage_list), 1):
            # Append formatted call details to list
            llm_calls.append({
                "call_number": i,
                "latency": round(time_taken, 2),
                "tokens": tokens
            })
        
        # Return list of all LLM call details
        return llm_calls

    def _extract_discovery_context(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract discovery-related information from conversation history.
        
        This helps the judge understand what tools were discovered and why
        certain code patterns (like database queries) are necessary.
        
        Args:
            conversation_history: Full conversation history
            
        Returns:
            Dictionary containing discovery information
        """
        discovery = {
            "servers_discovered": False,
            "tool_documentation_read": False,
            "discovery_execution_results": [],
            "tool_names_found": []
        }
        
        for msg in conversation_history:
            if msg.get("role") == "assistant":
                try:
                    content = msg.get("content", "")
                    # Try to parse as JSON (code agent responses are JSON)
                    try:
                        content_dict = json.loads(content)
                        code = content_dict.get("code", "")
                        reasoning = content_dict.get("reasoning", "")
                    except (json.JSONDecodeError, TypeError):
                        # If not JSON, treat as plain text
                        code = content
                        reasoning = ""
                    
                    # Check if this turn discovered servers
                    if "directory_tree" in code and "./servers" in code:
                        discovery["servers_discovered"] = True
                    
                    # Check if tool documentation was read
                    if "read_text_file" in code and ".md" in code and "servers/" in code:
                        discovery["tool_documentation_read"] = True
                        # Try to extract tool names from code
                        import re
                        tool_matches = re.findall(r'servers/([^/]+)/([^/]+)\.md', code)
                        for server, tool in tool_matches:
                            tool_name = f"{server}.{tool}"
                            if tool_name not in discovery["tool_names_found"]:
                                discovery["tool_names_found"].append(tool_name)
                    
                    # Check reasoning for discovery mentions
                    if reasoning and any(keyword in reasoning.lower() for keyword in ["discover", "read documentation", "tool", "server"]):
                        discovery["tool_documentation_read"] = True
                        
                except Exception as e:
                    logger.debug(f"Error parsing assistant message for discovery: {e}")
                    continue
                    
            elif msg.get("role") == "user":
                content = msg.get("content", "")
                # Check if this is an execution result that contains discovery information
                if "Execution result" in content or "execution" in content.lower():
                    # Look for server/tool discovery patterns in execution results
                    if "./servers" in content or "servers/" in content:
                        # Extract relevant portion (first 800 chars to avoid token bloat)
                        result_snippet = content[:800]
                        if result_snippet not in discovery["discovery_execution_results"]:
                            discovery["discovery_execution_results"].append(result_snippet)
        
        return discovery

    def _format_discovery_context_for_judge(self, discovery_context: Dict[str, Any]) -> str:
        """
        Format discovery context for judge consumption.
        
        Args:
            discovery_context: Discovery context dictionary
            
        Returns:
            Formatted string for judge prompt
        """
        if not any([
            discovery_context.get("servers_discovered"),
            discovery_context.get("tool_documentation_read"),
            discovery_context.get("discovery_execution_results")
        ]):
            return "No discovery context available yet - this may be the first turn."
        
        summary_parts = []
        
        if discovery_context.get("servers_discovered"):
            summary_parts.append("- Servers have been discovered in previous turns")
        
        if discovery_context.get("tool_documentation_read"):
            summary_parts.append("- Tool documentation has been read in previous turns")
            if discovery_context.get("tool_names_found"):
                tools = ", ".join(discovery_context["tool_names_found"][:5])  # Limit to 5 tools
                summary_parts.append(f"  Tools discovered: {tools}")
        
        if discovery_context.get("discovery_execution_results"):
            count = len(discovery_context["discovery_execution_results"])
            summary_parts.append(f"- Discovery execution results available from {count} previous turn(s)")
            # Include a sample of discovery results (limit to 2 to avoid token bloat)
            for i, result in enumerate(discovery_context["discovery_execution_results"][:2], 1):
                # Truncate to 300 chars per result
                truncated_result = result[:300] + "..." if len(result) > 300 else result
                summary_parts.append(f"  Sample discovery result {i}: {truncated_result}")
        
        summary = "\n".join(summary_parts)
        
        # Add important note for judge
        summary += "\n\nIMPORTANT: If the code uses tools that were discovered in previous turns and follows their documented interface, and the tool documentation doesn't mention sanitization options, then lack of sanitization in the code is acceptable - it's the only way to use the tool."
        
        return summary

    def _calculate_total_tokens(self, token_usage_list: list) -> Dict[str, int]:
        """
        Calculate total token usage across all LLM calls.
        
        Args:
            token_usage_list: List of token usage dictionaries
        
        Returns:
            Dictionary with total prompt_tokens, completion_tokens, and total_tokens
        """
        # Initialize total token counters
        total_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        # Sum up tokens from all LLM calls
        for tokens in token_usage_list:
            total_tokens["prompt_tokens"] += tokens.get("prompt_tokens", 0)
            total_tokens["completion_tokens"] += tokens.get("completion_tokens", 0)
            total_tokens["total_tokens"] += tokens.get("total_tokens", 0)
        
        # Return aggregated token usage
        return total_tokens

    def _format_turn_details(self, messages: list, turn_times: list, token_usage_list: list, turn_judge_turns: dict = None) -> list:
        """Format detailed turn information for UI display."""
        if turn_judge_turns is None:
            turn_judge_turns = {}
        
        logger.info(f"Formatting turn_details with {len(turn_judge_turns)} judge_turns entries: {list(turn_judge_turns.keys())}")
            
        turns = []
        turn_number = 0
        
        for i in range(1, len(messages), 2):  # Skip first user message, then iterate by 2
            if i < len(messages):
                assistant_msg = messages[i]
                user_feedback = messages[i + 1] if i + 1 < len(messages) else None
                
                turn_number += 1
                turn = {
                    "turn_number": turn_number,
                    "llm_request": messages[i - 1] if i > 0 else messages[0],
                    "llm_response": assistant_msg,
                    "execution_result": user_feedback.get("content", "") if user_feedback else None,
                    "latency": turn_times[turn_number - 1] if turn_number - 1 < len(turn_times) else 0,
                    "tokens": token_usage_list[turn_number - 1] if turn_number - 1 < len(token_usage_list) else {}
                }
                
                # Add judge_turns if available for this turn
                # turn_number matches executed_turn_count (which increments only for executed turns)
                if turn_number in turn_judge_turns:
                    turn["judge_turns"] = turn_judge_turns[turn_number]
                    logger.info(f"✅ Added judge_turns to turn {turn_number}: {len(turn_judge_turns[turn_number])} iterations")
                    logger.info(f"   Judge turns data: {json.dumps([jt.get('status') for jt in turn_judge_turns[turn_number]], indent=2)}")
                else:
                    logger.debug(f"No judge_turns for turn {turn_number}. Available keys: {list(turn_judge_turns.keys())}")
                
                turns.append(turn)
        
        return turns

    async def cleanup_async(self):
        """
        Cleanup orchestrator resources after task completion.
        """
        # Log cleanup start
        logger.info("Cleaning up Orchestrator")

        # Stop Docker container
        await self._docker_executor.cleanup()

        # Close MCP client
        await self._mcp_client.close()

        # Log cleanup completion
        logger.info("Orchestrator cleanup complete")

