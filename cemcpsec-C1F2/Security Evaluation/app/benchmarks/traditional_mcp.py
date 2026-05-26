"""
Traditional MCP Benchmark using LangChain v1 create_agent.

This module implements the traditional approach to MCP where tools are
directly exposed to the LLM through LangChain's agent framework.
"""
# Standard library imports
import time
from typing import Dict, Any


# LangChain imports for agent framework
from langchain.agents import create_agent

# Application imports
from app.app_logging.logger import setup_logger
from app.core import get_mcp_client
from app.config import OPENAI_MODEL

# Dynamic MCP tools
from app.dynamic_langchain.langchain_mcp_call_tool import mcp_call

# Initialize logger for tracking benchmark operations
logger = setup_logger(__name__)



class TraditionalMCPBenchmark:
    """
    Benchmark Traditional MCP using LangChain v1 create_agent.
    
    This class implements the traditional approach where:
    1. MCP tools are wrapped as LangChain tools
    2. LLM directly calls tools through agent framework
    3. Each tool call requires LLM invocation
    """
    
    def __init__(self):
        """
        Initialize Traditional MCP Benchmark.
        
        Sets up:
        - MCP client for filesystem operations
        - Token usage tracking
        - LLM call tracking
        """
        self.conversation_history = []
        
        # Initialize token usage tracking dictionary
        self.total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Initialize LLM call counters
        self.llm_calls = 0
        self.llm_calls_list = []

        # mcp_tools
        self.mcp_tools = [mcp_call]
        
    async def initialize_async(self):
        """
        Initialize MCP connections to filesystem server.
        
        This establishes the connection to the MCP server
        that provides file system tools.
        """
        # Initialize MCP client and connect to filesystem server
        self._mcp_client = await get_mcp_client()
        print(f"Traditional MCP Benchmark using mcp_client: {self._mcp_client} \n")
        self.mcp_tool_catalog = self._mcp_client.get_catalog()
       

        
    async def run_benchmark_async(self, query: str) -> Dict[str, Any]:
        """
        Run traditional MCP benchmark with timing and token tracking.
        
        Workflow:
        1. Create MCP tools for agent
        2. Initialize LangChain agent
        3. Execute query through agent
        4. Track token usage and timing
        5. Return formatted results
        
        Args:
            query: User query to process
            
        Returns:
            Dictionary with benchmark results:
                - success: Execution success status
                - output: Final output text
                - time: Total execution time
                - llm_calls: List of LLM call details
                - tokens: Token usage information
                - conversation_history: Conversation history
                - turn_details: Detailed turn information
        """
        # Reset token tracking for new benchmark run
        self.total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Reset LLM call counters for new benchmark run
        self.llm_calls = 0
        self.llm_calls_list = []
        
        # Start timing the benchmark execution
        start_time = time.time()
        
        # Log benchmark start with banner
        logger.info(f"\n{'=' * 80}\nTRADITIONAL MCP BENCHMARK (LangChain v1)\n{'=' * 80}\n")
        logger.info(f"Query: {query}\n")
        
        # Initialize LangChain agent with model, tools, and system prompt
        agent = create_agent(
            model=OPENAI_MODEL,
            tools=self.mcp_tools,
            system_prompt=self._get_system_prompt()
        )
        

        # Initialize conversation history with user query
        self.conversation_history = [
            {"role": "user", "content": query}
        ]

        try:
            # Invoke agent with user query
            result = await agent.ainvoke({
                "messages": [
                    {"role": "user", "content": query}
                ]
            })
            logger.info(f"result: \n {result}")
            # Initialize variables for output and call tracking
            output = ""
            call_count = 0
            
            # Process agent result messages
            if "messages" in result:
                # Iterate through all messages in result to build complete conversation history
                for msg in result["messages"]:
                    msg_type = getattr(msg, 'type', None) or getattr(msg, '__class__', {}).__name__.lower()
                    
                    # Extract content based on message type
                    content = None
                    role = None
                    
                    if hasattr(msg, 'content'):
                        # For AI and Human messages, get content directly
                        if msg_type in ["ai", "human"]:
                            content = msg.content
                            if isinstance(content, list):
                                # Content might be a list of content blocks
                                content = " ".join(str(c) for c in content)
                            role = "assistant" if msg_type == "ai" else "user"
                        elif msg_type == "tool":
                            # Tool messages contain tool calls or tool results
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                # Tool call request - format nicely
                                import json
                                tool_calls_formatted = []
                                for tc in msg.tool_calls:
                                    tool_name = tc.get('name', 'unknown')
                                    tool_args = tc.get('args', {})
                                    tool_calls_formatted.append(
                                        f"{tool_name}({json.dumps(tool_args)})"
                                    )
                                content = f"[Tool Call: {', '.join(tool_calls_formatted)}]"
                                role = "tool"
                            elif hasattr(msg, 'content') and msg.content:
                                # Tool result
                                tool_content = msg.content
                                if isinstance(tool_content, list):
                                    tool_content = " ".join(str(c) for c in tool_content)
                                content = f"[Tool Result: {tool_content}]"
                                role = "tool"
                            else:
                                # Empty tool message
                                content = "[Tool executed - no result]"
                                role = "tool"
                    
                    # Add all messages to conversation history (skip initial user message as it's already added)
                    if content is not None and role is not None:
                        # Only add if not duplicate of initial user message
                        is_duplicate_user = (role == "user" and 
                                           len(self.conversation_history) > 0 and 
                                           self.conversation_history[-1].get("role") == "user" and
                                           self.conversation_history[-1].get("content") == str(content))
                        
                        if not is_duplicate_user:
                            self.conversation_history.append({
                                "role": role,
                                "content": str(content)
                            })
                    
                    # Track AI messages for token usage and final output
                    if msg_type == "ai":
                        call_count += 1
                        # Update output with latest AI message (final answer)
                        if content:
                            output = str(content)
                        
                        # Check if message has token usage metadata
                        if hasattr(msg, 'response_metadata'):
                            token_usage = msg.response_metadata.get('token_usage', {})
                            
                            # Process token usage if available
                            if token_usage:
                                # Extract individual token counts
                                prompt_tokens = token_usage.get('prompt_tokens', 0)
                                completion_tokens = token_usage.get('completion_tokens', 0)
                                total_tokens = token_usage.get('total_tokens', 0)
                                
                                # Accumulate token counts
                                self.total_tokens["prompt_tokens"] += prompt_tokens
                                self.total_tokens["completion_tokens"] += completion_tokens
                                self.total_tokens["total_tokens"] += total_tokens
                                
                                # Append LLM call details to list
                                self.llm_calls_list.append({
                                    "call_number": call_count,
                                    "latency": 0,
                                    "tokens": {
                                        "prompt_tokens": prompt_tokens,
                                        "completion_tokens": completion_tokens,
                                        "total_tokens": total_tokens
                                    }
                                })
                                
                                # Log LLM call details
                                logger.info(f"\n{'=' * 80}\nLLM CALL {call_count}\n{'=' * 80}")
                                logger.info(f"\nTOKEN USAGE (Call {call_count})")
                                logger.info(f"{'=' * 80}")
                                logger.info(f"Input Tokens: {prompt_tokens}")
                                logger.info(f"Output Tokens: {completion_tokens}")
                                logger.info(f"Total Tokens: {total_tokens}")
                                logger.info(f"{'=' * 80}\n")
            
            # Store total LLM call count
            self.llm_calls = call_count
            
            # Calculate total execution time
            total_time = time.time() - start_time
            
            # Calculate average latency per LLM call
            if self.llm_calls > 0:
                avg_latency_per_call = total_time / self.llm_calls
                
                # Update latency for each call in the list
                for call_detail in self.llm_calls_list:
                    call_detail["latency"] = round(avg_latency_per_call, 2)
            



            # Log final results banner
            logger.info(f"\n{'=' * 80}\nFINAL RESULTS\n{'=' * 80}")
            logger.info(f"\nStatus: SUCCESS")
            logger.info(f"\nOutput:\n{'-' * 80}\n{output}\n{'-' * 80}\n")
            
            # Log performance summary
            logger.info(f"\n{'=' * 80}\nPERFORMANCE SUMMARY\n{'=' * 80}")
            logger.info(f"Total Time: {total_time:.2f}s")
            logger.info(f"Total LLM Calls: {self.llm_calls}")
            logger.info(f"{'=' * 80}\n")
            
            # Log token usage summary
            logger.info(f"\n{'=' * 80}\nTOKEN USAGE SUMMARY\n{'=' * 80}")
            logger.info(f"\n{'-' * 80}\nTOTAL TOKENS CONSUMED\n{'-' * 80}")
            logger.info(f"Total Input Tokens: {self.total_tokens['prompt_tokens']}")
            logger.info(f"Total Output Tokens: {self.total_tokens['completion_tokens']}")
            logger.info(f"Total Tokens: {self.total_tokens['total_tokens']}")
            logger.info(f"{'=' * 80}\n")
            
            # Return successful benchmark result
            return {
                "success": True,
                "output": output,
                "time": total_time,
                "llm_calls": self.llm_calls_list,
                "tokens": self.total_tokens,
                "conversation_history": self.conversation_history,
                "turn_details": self._format_turn_details()
                
            }
            
        except Exception as e:
            # Log error details
            logger.error(f"\nError: {str(e)}")
            
            # Calculate total time even on failure
            total_time = time.time() - start_time
            
            # Return failed benchmark result with error details
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "time": total_time,
                "llm_calls": self.llm_calls_list,
                "tokens": self.total_tokens,
                "conversation_history": self.conversation_history,
                "turn_details": self._format_turn_details()
            }

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for the LangChain agent.
        
        Returns:
            System prompt string with tool usage instructions
        """
        # Return comprehensive system prompt with tool usage guidelines
        return f"""You are a data analysis assistant.

                ## AVAILABLE TOOLS

                {self.mcp_tool_catalog}

                ## IMPORTANT RULES
                - When using tools, ALWAYS call mcp_call with BOTH fields:
                  - name="<server>.<tool>"
                  - args={...}.
                  - Never omit name.
                - For filesystem operations, prefer tools under the `filesystem.*` server.
                - If the user gives an exact path, use it directly.
            """

    def _format_turn_details(self) -> list:
        """Format turn details from conversation history.
        
        For Traditional MCP, the conversation includes user messages, AI messages, tool calls, and tool results.
        We group messages by LLM calls to create turn details where each AI message represents a turn.
        """
        turns = []
        
        if not self.conversation_history or not self.llm_calls_list:
            # No conversation history, return basic turn info
            for i, call_info in enumerate(self.llm_calls_list):
                turns.append({
                    "turn_number": i + 1,
                    "llm_request": {"role": "system", "content": "No detailed trace available"},
                    "llm_response": {"role": "assistant", "content": "No detailed trace available"},
                    "latency": call_info.get("latency", 0),
                    "tokens": call_info.get("tokens", {})
                })
            return turns
        
        # Find indices of all AI (assistant) messages - these mark the turns
        ai_indices = [i for i, msg in enumerate(self.conversation_history) if msg.get("role") == "assistant"]
        
        # Create a turn for each LLM call
        for turn_num, call_info in enumerate(self.llm_calls_list, 1):
            if turn_num - 1 < len(ai_indices):
                ai_idx = ai_indices[turn_num - 1]
                
                # Collect all messages leading up to this AI response (the "request")
                request_messages = []
                for i in range(ai_idx):
                    msg = self.conversation_history[i]
                    # Include user messages and tool results in the request context
                    if msg.get("role") in ["user", "tool"]:
                        request_messages.append(msg)
                
                # Get the AI response
                ai_response_msg = self.conversation_history[ai_idx]
                
                # Collect tool interactions after this AI response (before next turn)
                tool_interactions = []
                if turn_num < len(ai_indices):
                    # Get messages between this AI response and next AI response
                    for i in range(ai_idx + 1, ai_indices[turn_num]):
                        msg = self.conversation_history[i]
                        if msg.get("role") == "tool":
                            tool_interactions.append(msg.get("content", ""))
                else:
                    # Last turn - get all remaining messages
                    for i in range(ai_idx + 1, len(self.conversation_history)):
                        msg = self.conversation_history[i]
                        if msg.get("role") == "tool":
                            tool_interactions.append(msg.get("content", ""))
                
                # Build the request content from collected messages
                request_content_parts = []
                for msg in request_messages:
                    if msg.get("role") == "user":
                        request_content_parts.append(msg.get("content", ""))
                    elif msg.get("role") == "tool":
                        request_content_parts.append(msg.get("content", ""))
                
                turn = {
                    "turn_number": turn_num,
                    "llm_request": {
                        "role": "user",
                        "content": "\n\n".join(request_content_parts) if request_content_parts else "Processing query..."
                    },
                    "llm_response": {
                        "role": "assistant",
                        "content": ai_response_msg.get("content", "")
                    },
                    "tool_interactions": tool_interactions if tool_interactions else None,
                    "latency": call_info.get("latency", 0),
                    "tokens": call_info.get("tokens", {})
                }
            else:
                # Fallback if indices don't match
                turn = {
                    "turn_number": turn_num,
                    "llm_request": {"role": "user", "content": "Query processing..."},
                    "llm_response": {"role": "assistant", "content": "Processing..."},
                    "latency": call_info.get("latency", 0),
                    "tokens": call_info.get("tokens", {})
                }
            
            turns.append(turn)
        
        return turns

    async def cleanup_async(self):
        """
        Cleanup MCP connections.
        """
        await self._mcp_client.close()
