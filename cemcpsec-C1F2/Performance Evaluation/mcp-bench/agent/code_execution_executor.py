"""
Code Execution Task Executor Module.

This module provides a code execution agent that generates Python code to interact with
MCP servers. Unlike the traditional executor that calls tools directly, this executor
generates Python code that makes MCP calls programmatically using exec().

Classes:
    CodeExecutionTaskExecutor: Executor that generates and executes Python code
"""

import asyncio
import logging
import json
import traceback
from typing import List, Dict, Any, Optional
from pathlib import Path

from openai import AsyncOpenAI
from mcp_modules.server_manager_persistent import PersistentMultiServerManager as MultiServerManager
from agent.dynamic_tool_discovery import DynamicToolDiscovery

logger = logging.getLogger(__name__)


class CodeExecutionTaskExecutor:
    """
    Executor that generates and executes Python code to interact with MCP servers.
    
    This executor:
    1. Uses OpenAI to generate Python code
    2. Code makes MCP calls through server_manager
    3. Executes code using exec() in a controlled environment
    4. Returns execution results
    
    Attributes:
        server_manager: Manager for MCP server connections
        all_tools: Dictionary of all available tools from servers
        openai_client: OpenAI client for code generation
        model: OpenAI model name (e.g., "gpt-4.1-mini")
        max_turns: Maximum number of code generation/execution turns
    """

    def __init__(
        self,
        server_manager: MultiServerManager,
        openai_api_key: str,
        model: str = "gpt-4.1-mini",
        max_turns: int = 3,
        mcp_servers_dir: str = "mcp_servers"
    ) -> None:
        """
        Initialize code execution executor.
        
        Args:
            server_manager: MCP server manager with connected servers (used for execution, not discovery)
            openai_api_key: OpenAI API key
            model: OpenAI model name
            max_turns: Maximum number of code generation/execution turns
            mcp_servers_dir: Path to mcp_servers directory for dynamic tool discovery
        """
        self.server_manager = server_manager
        self.model = model
        self.max_turns = max_turns
        
        # Initialize dynamic tool discovery
        self.tool_discovery = DynamicToolDiscovery(mcp_servers_dir=mcp_servers_dir)
        
        # Tools will be discovered dynamically per task
        self.all_tools: Dict[str, Any] = {}
        
        # Initialize OpenAI client
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        
        # Execution history for multi-turn conversations
        self.execution_history: List[Dict[str, str]] = []
        
        # Tool calls tracking for this execution
        self.tool_calls: List[Dict[str, Any]] = []
        
        # Token usage tracking
        self.total_output_tokens = 0
        self.total_prompt_tokens = 0
        self.total_tokens = 0

    async def execute(self, task: str) -> Dict[str, Any]:
        """
        Execute a task by generating and running Python code.
        
        Args:
            task: Natural language description of the task
            
        Returns:
            Dictionary containing:
                - solution: Final answer
                - code_executions: List of code execution attempts
                - total_turns: Number of execution turns
                - total_output_tokens: Total output tokens used
                - total_prompt_tokens: Total prompt tokens used
                - total_tokens: Total tokens used
        """
        # Don't log the full task description - it's too verbose
        logger.info("Starting code execution for task")
        
        # Reset execution history and tool calls for new task
        self.execution_history = []
        self.tool_calls = []
        code_executions = []
        
        # Discover tools dynamically based on task
        logger.info("Discovering tools dynamically for this task...")
        self.all_tools = self.tool_discovery.discover_tools_for_task(task, self.server_manager)
        logger.info(f"Discovered {len(self.all_tools)} tools for task")
        
        # Build tools context for code generation
        tools_context = self._build_tools_context()
        
        for turn in range(1, self.max_turns + 1):
            logger.info(f"--- Code Generation Turn {turn}/{self.max_turns} ---")
            
            # Generate code using OpenAI
            code_result = await self._generate_code(task, tools_context, turn)
            
            if not code_result.get('success'):
                logger.error(f"Code generation failed on turn {turn}: {code_result.get('error')}")
                code_executions.append(code_result)
                break
            
            generated_code = code_result.get('code', '')
            reasoning = code_result.get('reasoning', '')
            
            logger.info(f"Generated code (turn {turn}):\n{generated_code}")
            logger.info(f"Reasoning: {reasoning}")
            
            # Post-process code to inject search fallbacks if missing
            generated_code = self._inject_search_fallbacks(generated_code)
            
            # Execute the generated code
            execution_result = await self._execute_code(generated_code, turn)
            
            # Log execution output
            if execution_result.get('output'):
                logger.info(f"Code execution output (turn {turn}):\n{execution_result.get('output')}")
            if execution_result.get('final_answer'):
                logger.info(f"Final answer (turn {turn}):\n{execution_result.get('final_answer')}")
            if execution_result.get('error'):
                logger.error(f"Code execution error (turn {turn}): {execution_result.get('error')}")
            code_executions.append({
                'turn': turn,
                'code': generated_code,
                'reasoning': reasoning,
                'execution': execution_result
            })
            
            # Check if task is complete
            if execution_result.get('complete', False):
                logger.info(f"Task marked as complete after turn {turn}")
                break
            
            # Add to execution history for next turn
            if turn < self.max_turns:
                # Build a more informative history entry
                history_entry = f"Generated code (turn {turn}):\n```python\n{generated_code}\n```\n"
                history_entry += f"Reasoning: {reasoning}\n"
                
                self.execution_history.append({
                    "role": "assistant",
                    "content": history_entry
                })
                
                # Build execution feedback
                execution_output = execution_result.get('output', '')
                final_answer = execution_result.get('final_answer', '')
                error = execution_result.get('error')
                
                feedback = f"Execution result (turn {turn}):\n"
                if execution_output:
                    feedback += f"Output:\n{execution_output}\n\n"
                if final_answer:
                    feedback += f"Final answer from code:\n{final_answer}\n\n"
                if error:
                    feedback += f"❌ ERROR: {error}\n\n"
                
                # Add guidance based on what happened
                if error:
                    feedback += "❌ CODE ERROR DETECTED. Your goal is to answer the query - fix the code:\n"
                    feedback += "- Read the error message carefully and fix the syntax/logic error\n"
                    feedback += "- Verify tool names match exactly (case-sensitive)\n"
                    feedback += "- Check tool parameters match the expected format\n"
                    feedback += "- Ensure all try/except blocks are properly structured\n"
                    feedback += "- Make sure extract_result_data() is used for all tool results\n"
                    feedback += "- Remember: Your PRIMARY GOAL is to answer the query - fix errors and try again\n"
                elif not final_answer or len(final_answer.strip()) < 50:
                    feedback += "❌ NO ANSWER PRODUCED. Your PRIMARY GOAL is to answer the query - fix this:\n"
                    feedback += "- Check if tools returned data (use extract_result_data() and check for None/empty)\n"
                    feedback += "- Try different tool parameters or alternative tools\n"
                    feedback += "- **CRITICAL**: Your code MUST synthesize results into a clear answer\n"
                    feedback += "- **CRITICAL**: Do NOT return raw JSON/data - write a reasoned response\n"
                    feedback += "- **CRITICAL**: Your reasoned_answer must directly answer what was asked\n"
                    feedback += "- Re-read the query to ensure you understand what's needed\n"
                elif not execution_result.get('complete', False):
                    feedback += "⚠️ ANSWER INCOMPLETE. Use remaining turns to fully answer the query:\n"
                    feedback += "- **FOCUS**: Does your answer fully address EVERY aspect of the query?\n"
                    feedback += "- Gather missing information if needed\n"
                    feedback += "- **IMPROVE REASONING**: Make your answer clearer and more complete\n"
                    feedback += "- Ensure your reasoned_answer directly answers what was asked\n"
                    feedback += "- Only set task_complete=True when 100% confident the answer is complete\n"
                    feedback += "- **Remember**: Completeness is more important than speed\n"
                else:
                    feedback += "✓ Answer provided. However, use remaining turns if needed to:\n"
                    feedback += "- Verify the answer fully addresses ALL aspects of the query\n"
                    feedback += "- Improve clarity and completeness\n"
                    feedback += "- Strengthen reasoning if needed\n"
                
                feedback += f"\n**REMAINING TURNS: {self.max_turns - turn}**\n"
                feedback += "**YOUR GOAL**: Answer the query completely and accurately.\n"
                feedback += "Use remaining turns to: (1) fix code errors, (2) gather missing info, (3) improve reasoning, (4) ensure completeness.\n"
                feedback += "**CRITICAL**: Only set task_complete=True when you are CERTAIN your answer fully answers the query."
                
                self.execution_history.append({
                    "role": "user",
                    "content": feedback
                })
        
        # Generate final answer if we have execution results
        final_solution = await self._generate_final_answer(task, code_executions)
        
        logger.info("Code execution completed.")
        logger.info(f"Final solution:\n{final_solution}")
        logger.info(f"Total turns: {len(code_executions)}")
        logger.info(f"Total tokens: {self.total_tokens} (prompt: {self.total_prompt_tokens}, output: {self.total_output_tokens})")
        logger.info(f"Total tool calls: {len(self.tool_calls)}")
        
        return {
            "solution": final_solution,
            "code_executions": code_executions,
            "total_turns": len(code_executions),
            "tool_calls": self.tool_calls,  # Include tracked tool calls
            "total_output_tokens": self.total_output_tokens,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_tokens": self.total_tokens
        }

    def _build_tools_context(self) -> str:
        """Build context string describing available MCP tools.
        
        Uses the same format as the regular MCP agent for consistency.
        """
        from mcp_modules.connector import MCPConnector
        
        # Use the same formatting as the regular MCP agent
        return MCPConnector.format_tools_for_prompt(self.all_tools)

    async def _generate_code(
        self,
        task: str,
        tools_context: str,
        turn: int
    ) -> Dict[str, Any]:
        """Generate Python code using OpenAI."""
        try:
            # Build system prompt
            system_prompt = r"""You are an expert Python programmer and problem solver. Your PRIMARY GOAL is to answer the user's query completely and accurately by generating Python code that interacts with MCP servers.

🎯 YOUR MISSION: ANSWER THE QUERY

Everything you do must be focused on answering the user's query. Every line of code, every tool call, every reasoning step must serve this purpose.

CORE PRINCIPLES:

**1. UNDERSTAND THE QUERY FIRST**
Before writing ANY code, you MUST:
- Read the query carefully and identify EXACTLY what is being asked
- Determine what information is needed to answer it completely
- Plan what tools you need and how to use them
- Know what a complete answer looks like

**2. USE TURNS WISELY**
You have up to 7 turns. Use them strategically:

TURN 1 (Most Important):
- Gather ALL necessary information in one comprehensive attempt
- Call ALL relevant tools needed to answer the query
- Provide a complete, well-reasoned answer
- Only set task_complete=True if you are 100% confident the answer fully addresses the query


**CRITICAL**: Only set task_complete=True when your answer FULLY addresses the query. If uncertain, use remaining turns.

**3. REASONING IS MANDATORY**
After gathering data, you MUST:
- Analyze the data in the context of the original query
- Synthesize information into a clear, coherent answer
- Explain how the information answers the query
- NEVER return raw JSON, lists, or unprocessed data
- Your reasoned_answer must be a well-written response that directly answers what was asked

**4. WRITE CORRECT, ROBUST CODE**
- Use try/except blocks around EVERY tool call
- Always check if results are None or empty before using them
- Use extract_result_data() for ALL tool results
- Handle errors gracefully - don't let one failure stop everything
- If searches return empty, try alternative queries (see pattern below)

**5. FOCUS ON COMPLETENESS**
Your answer is complete only when:
- It directly addresses every aspect of the user's query
- All necessary information has been gathered and synthesized
- The reasoning is clear and complete
- You are confident it fully answers what was asked

TECHNICAL REQUIREMENTS:

1. Code MUST be a complete async Python function named `main()`
2. Use: `await server_manager.call_tool("ServerName:tool_name", {"param": "value"})`
3. ALWAYS use `extract_result_data()` for result extraction (provided below)
4. ALWAYS wrap tool calls in try/except blocks
5. ALWAYS check for None/empty results before using them
6. Return: `(task_complete: bool, reasoned_answer: str)`
7. reasoned_answer MUST be a non-empty string - never None or empty
8. DO NOT call main() or use await at top level - just define the function

REQUIRED HELPER FUNCTION (Copy this into your code):


CRITICAL REMINDERS:
- Your PRIMARY GOAL is to answer the query - everything else is secondary
- reasoned_answer MUST be a well-written response, not raw data
- Use try/except for ALL tool calls
- Check for None/empty results before using them
- Only set task_complete=True when confident the answer is complete
- Use remaining turns if the answer is incomplete
- DO NOT call main() or use await at top level
"""

            # Build user prompt
            history_context = ""
            if self.execution_history:
                history_context = "\n\nPREVIOUS EXECUTION HISTORY:\n"
                for msg in self.execution_history[-4:]:  # Last 2 exchanges
                    history_context += f"{msg['role']}: {msg['content']}\n\n"
            
            user_prompt = f"""QUERY TO ANSWER: {task}

{tools_context}

{history_context}

**YOUR PRIMARY GOAL: Answer the query above completely and accurately.**

**STEP-BY-STEP INSTRUCTIONS:**

1. **UNDERSTAND THE QUERY** (Do this first - don't skip!)
   - What exactly is the user asking?
   - What information do you need to answer it?
   - What would a complete answer look like?

2. **SELECT AND USE TOOLS**
   - Review available tools and pick the right ones
   - Use correct tool names and parameters
   - Wrap EVERY tool call in try/except
   - Use extract_result_data() for ALL results
   - Check for None/empty before using results
   - If searches return empty, try alternative queries

3. **REASON AND SYNTHESIZE** (This is MANDATORY - don't skip!)
   - Analyze the data you gathered
   - Explain how it answers the query
   - Write a clear, well-reasoned response
   - DO NOT return raw JSON, lists, or unprocessed data
   - Your reasoned_answer must directly answer what was asked

4. **ASSESS COMPLETENESS**
   - Does your answer fully address the query?
   - Are all aspects covered?
   - Only set task_complete=True if you're 100% confident
   - If uncertain, set task_complete=False and use remaining turns

5. **TURN USAGE** (Current turn: {turn})
   - Turn 1: Try to complete everything - gather all info, provide complete answer
   - Turn 2+: Fix errors, fill gaps, improve reasoning if Turn 1 was incomplete
   - Use all available turns if needed to ensure completeness

**CODE REQUIREMENTS:**
- Must be valid Python code
- Must define async def main() function
- Must use try/except for all tool calls
- Must use extract_result_data() for all results
- Must check for None/empty results
- Must return (task_complete: bool, reasoned_answer: str)
- reasoned_answer must be a non-empty string

Generate Python code to answer the query. Return a JSON object with:
{{
    "reasoning": "Explain: (1) what the query is asking, (2) which tools you'll use and why, (3) how you'll synthesize results to answer the query",
    "code": "Complete Python code (properly escaped for JSON - escape quotes as \\", backslashes as \\\\, newlines as \\n)",
    "expect_complete": true/false
}}

**CRITICAL**: 
- Focus on answering the query - that's your only goal
- Write correct, error-free code
- Provide clear reasoning, not raw data
- Use turns wisely to ensure completeness"""

            # Call OpenAI
            # Some models (like gpt-5-nano) require max_completion_tokens instead of max_tokens
            # Try max_completion_tokens first, fall back to max_tokens if that fails
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                    max_completion_tokens=8000  # Try max_completion_tokens first for newer models
                )
            except Exception as token_error:
                # Fall back to max_tokens for older models
                if "max_completion_tokens" in str(token_error) or "max_tokens" in str(token_error):
                    response = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                        max_tokens=8000  # Fallback for older models
                    )
                else:
                    raise
            
            # Extract response
            response_content = response.choices[0].message.content
            usage = response.usage
            if usage:
                self.total_output_tokens += usage.completion_tokens
                self.total_prompt_tokens += usage.prompt_tokens
                self.total_tokens += usage.total_tokens
            
            # Parse JSON response
            try:
                result = json.loads(response_content)
                code = result.get('code', '').strip()
                
                # Remove markdown code fences if present
                if code.startswith('```python'):
                    code = code[9:]
                elif code.startswith('```'):
                    code = code[3:]
                if code.endswith('```'):
                    code = code[:-3]
                code = code.strip()
                
                return {
                    'success': True,
                    'code': code,
                    'reasoning': result.get('reasoning', ''),
                    'expect_complete': result.get('expect_complete', False)
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Error position: {getattr(e, 'pos', 'unknown')}")
                logger.debug(f"Raw response (first 1000 chars):\n{response_content[:1000]}")
                logger.debug(f"Raw response (last 500 chars):\n{response_content[-500:]}")
                
                # Try to extract code manually using regex as fallback
                # This handles cases where JSON is malformed or truncated
                try:
                    import re
                    
                    # Try multiple patterns to extract code field
                    # Pattern 1: "code":"..." (may be truncated)
                    code_patterns = [
                        r'"code"\s*:\s*"((?:[^"\\]|\\.)*)"',  # Standard pattern
                        r'"code"\s*:\s*"((?:[^"\\]|\\.)*)',   # Truncated (no closing quote)
                        r'"code"\s*:\s*"(.+?)(?:"\s*,|\s*})', # Greedy match
                        r'"code"\s*:\s*"(.+)',                 # Everything until end (truncated)
                    ]
                    
                    code = None
                    for pattern in code_patterns:
                        code_match = re.search(pattern, response_content, re.DOTALL)
                        if code_match:
                            code = code_match.group(1)
                            # Try to unescape, but handle errors gracefully
                            try:
                                code = code.encode().decode('unicode_escape')
                            except:
                                pass  # Keep original if unescaping fails
                            break
                    
                    if code:
                        code = code.strip()
                        
                        # Remove markdown code fences if present
                        if code.startswith('```python'):
                            code = code[9:]
                        elif code.startswith('```'):
                            code = code[3:]
                        if code.endswith('```'):
                            code = code[:-3]
                        code = code.strip()
                        
                        # Extract reasoning if available
                        reasoning = ""
                        reasoning_patterns = [
                            r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)"',
                            r'"reasoning"\s*:\s*"((?:[^"\\]|\\.)*)',
                            r'"reasoning"\s*:\s*"(.+?)(?:"\s*,|\s*})',
                        ]
                        for pattern in reasoning_patterns:
                            reasoning_match = re.search(pattern, response_content, re.DOTALL)
                            if reasoning_match:
                                try:
                                    reasoning = reasoning_match.group(1).encode().decode('unicode_escape')
                                except:
                                    reasoning = reasoning_match.group(1)
                                break
                        
                        # Extract expect_complete if available
                        expect_complete = False
                        expect_match = re.search(r'"expect_complete"\s*:\s*(true|false)', response_content, re.IGNORECASE)
                        if expect_match:
                            expect_complete = expect_match.group(1).lower() == 'true'
                        
                        logger.warning(f"Successfully extracted code from malformed/truncated JSON using regex fallback (code length: {len(code)})")
                        return {
                            'success': True,
                            'code': code,
                            'reasoning': reasoning,
                            'expect_complete': expect_complete
                        }
                except Exception as fix_error:
                    logger.error(f"Failed to extract code using regex fallback: {fix_error}")
                    logger.debug(traceback.format_exc())
                
                return {
                    'success': False,
                    'error': f"Invalid JSON response: {e}",
                    'raw_response': response_content[:2000]  # Show more context for debugging
                }
                
        except Exception as e:
            logger.error(f"Error generating code: {e}")
            import traceback as tb
            logger.error(tb.format_exc())
            return {
                'success': False,
                'error': str(e)
            }

    def _inject_search_fallbacks(self, code: str) -> str:
        """
        Post-process generated code to inject fallback logic for empty search results.
        This ensures searches try multiple query variations and fallback to direct lookups.
        """
        import re
        
        # Check if code already has fallback logic
        has_loop = re.search(r'for\s+\w+\s+in\s+.*(?:query|search|fallback)', code, re.IGNORECASE)
        has_multiple_searches = len(re.findall(r'search_wikipedia', code)) > 1
        has_fallback_check = re.search(r'if.*len\(.*results.*\)\s*==\s*0|if.*\.get\(.*results.*\[\]\)\s*==\s*\[\]', code, re.IGNORECASE)
        
        if has_loop or (has_multiple_searches and has_fallback_check):
            # Code already has fallback logic
            return code
        
        # Find the pattern: search_result = await ... search_wikipedia ... then search_data = extract_result_data
        # Then look for where results/frameworks are extracted
        pattern = r'(search_result\s*=\s*await\s+server_manager\.call_tool\(["\']Wikipedia:search_wikipedia["\'],\s*\{[^}]*"query"\s*:\s*"([^"]+)"[^}]*\}\))\s*\n\s*(search_data\s*=\s*extract_result_data\(search_result\))'
        
        match = re.search(pattern, code, re.MULTILINE)
        if not match:
            return code  # Pattern not found, return as-is
        
        original_query = match.group(2)
        search_call = match.group(1)
        extract_line = match.group(3)
        
        # Find where frameworks/results are extracted from search_data
        # Look for the next occurrence of 'frameworks' or 'results' assignment after search_data
        code_after_extract = code[match.end():]
        results_pattern = r'(\s+if\s+isinstance\(search_data.*?)\s+(\s+frameworks\s*=\s*\[|results\s*=\s*.*\.get\(["\']results)'
        results_match = re.search(results_pattern, code_after_extract, re.DOTALL)
        
        if not results_match:
            # Try simpler pattern - just find where frameworks gets assigned
            results_pattern = r'(\s+if\s+isinstance\(search_data[^\n]*)\s+(\s+frameworks\s*=)'
            results_match = re.search(results_pattern, code_after_extract, re.MULTILINE)
        
        if not results_match:
            return code  # Can't find where to inject
        
        # Find the insertion point (right after the frameworks/results assignment block starts)
        insert_offset = match.end() + results_match.end(1) if results_match else match.end()
        insert_line_num = code[:insert_offset].count('\n')
        code_lines = code.split('\n')
        
        # Get indentation from the line before insertion
        if insert_line_num < len(code_lines):
            prev_line = code_lines[insert_line_num - 1] if insert_line_num > 0 else ''
            indent_match = re.match(r'^(\s*)', prev_line)
            indent = indent_match.group(1) if indent_match else '        '
            
            # Generate fallback code with proper indentation
            fallback_code = f'''{indent}# INJECTED FALLBACK: Handle empty search results
{indent}if isinstance(search_data, dict) and 'results' in search_data:
{indent}    results_list = search_data.get('results', [])
{indent}    if len(results_list) == 0:
{indent}        print(f"⚠️ Search returned empty results for '{original_query}', trying fallback queries...")
{indent}        # Try alternative query variations
{indent}        fallback_queries = [
{indent}            "global {original_query}",
{indent}            "{original_query.replace('negotiation frameworks', 'agreements').replace('climate change negotiation frameworks', 'international climate agreements')}",
{indent}            "international climate agreements",
{indent}        ]
{indent}        
{indent}        for fallback_query in fallback_queries:
{indent}            try:
{indent}                fallback_result = await server_manager.call_tool("Wikipedia:search_wikipedia", {{"query": fallback_query, "limit": 5}})
{indent}                fallback_data = extract_result_data(fallback_result)
{indent}                if isinstance(fallback_data, dict) and 'results' in fallback_data:
{indent}                    fallback_results = fallback_data.get('results', [])
{indent}                    if len(fallback_results) > 0:
{indent}                        print(f"✓ Found {{len(fallback_results)}} results with fallback query: {{fallback_query}}")
{indent}                        search_data = fallback_data  # Use successful fallback
{indent}                        break
{indent}            except Exception as e:
{indent}                print(f"Fallback query '{{fallback_query}}' failed: {{e}}")
{indent}                continue
{indent}        
{indent}        # If still empty, try direct article lookups for known entities
{indent}        if isinstance(search_data, dict) and len(search_data.get('results', [])) == 0:
{indent}            print("⚠️ All searches failed, trying direct article lookups...")
{indent}            known_entities = ["Paris Agreement", "Kyoto Protocol", "United Nations Framework Convention on Climate Change"]
{indent}            direct_results = []
{indent}            for entity in known_entities:
{indent}                try:
{indent}                    article_result = await server_manager.call_tool("Wikipedia:get_article", {{"title": entity}})
{indent}                    article_data = extract_result_data(article_result)
{indent}                    if isinstance(article_data, dict) and article_data.get('exists', True):
{indent}                        direct_results.append({{"title": entity}})
{indent}                        print(f"✓ Found entity via direct lookup: {{entity}}")
{indent}                except:
{indent}                    pass
{indent}            
{indent}            if len(direct_results) > 0:
{indent}                search_data = {{'results': direct_results}}
{indent}                print(f"✓ Using {{len(direct_results)}} entities from direct lookups")
'''
            
            # Insert the fallback code
            code_lines.insert(insert_line_num, fallback_code.rstrip())
            logger.info("✓ Injected search fallback logic into generated code")
            return '\n'.join(code_lines)
        
        return code
    
    async def _execute_code(self, code: str, turn: int) -> Dict[str, Any]:
        """Execute generated Python code in a controlled environment."""
        try:
            logger.info(f"Executing code (turn {turn})...")
            
            # Verify server_manager is properly initialized and connected
            if self.server_manager is None:
                logger.error("❌ server_manager is None! Cannot execute code.")
                return {
                    'success': False,
                    'error': 'Server manager is not initialized',
                    'output': '',
                    'complete': False
                }
            
            # Verify server_manager has sessions/tools
            if not hasattr(self.server_manager, 'all_tools') or not self.server_manager.all_tools:
                logger.error(f"❌ server_manager has no tools! Available tools: {len(self.server_manager.all_tools) if hasattr(self.server_manager, 'all_tools') else 0}")
                logger.error(f"Server manager type: {type(self.server_manager)}")
                logger.error(f"Server manager attributes: {dir(self.server_manager)}")
                return {
                    'success': False,
                    'error': 'Server manager has no available tools',
                    'output': '',
                    'complete': False
                }
            
            # Verify server_manager has active sessions
            if hasattr(self.server_manager, 'sessions'):
                active_sessions = len(self.server_manager.sessions) if self.server_manager.sessions else 0
                logger.info(f"✓ Server manager has {active_sessions} active session(s)")
                logger.info(f"✓ Server manager has {len(self.server_manager.all_tools)} available tool(s)")
                for server_name in self.server_manager.sessions.keys():
                    logger.debug(f"  - Active session: {server_name}")
                for tool_name in list(self.server_manager.all_tools.keys())[:5]:  # Log first 5 tools
                    logger.debug(f"  - Available tool: {tool_name}")
            else:
                logger.warning("⚠️ Server manager has no 'sessions' attribute")
            
            # Remove any top-level await statements (they cause syntax errors)
            # The code should only define functions, we'll call them ourselves
            cleaned_code = self._remove_top_level_await(code)
            
            # Create a namespace for code execution
            # IMPORTANT: Add json to namespace since generated code uses it
            import json as json_module
            exec_namespace = {
                'server_manager': self.server_manager,
                'asyncio': asyncio,
                'json': json_module,  # Add json module so extract_result_data can use it
                '__builtins__': __builtins__
            }
            
            # Verify server_manager is accessible in namespace
            if 'server_manager' not in exec_namespace or exec_namespace['server_manager'] is None:
                logger.error("❌ Failed to add server_manager to execution namespace!")
                return {
                    'success': False,
                    'error': 'Failed to initialize execution environment',
                    'output': '',
                    'complete': False
                }
            
            logger.info(f"✓ Execution namespace ready with server_manager (type: {type(exec_namespace['server_manager'])})")
            
            # Execute the code (it should define async def main())
            try:
                exec(cleaned_code, exec_namespace)
            except SyntaxError as syntax_error:
                # If there's still a syntax error, try to provide better error message
                return {
                    'success': False,
                    'error': f'Syntax error in generated code: {str(syntax_error)}',
                    'output': '',
                    'complete': False
                }
            
            # Get the main function and execute it
            if 'main' not in exec_namespace:
                return {
                    'success': False,
                    'error': 'Code did not define a main() function',
                    'output': '',
                    'complete': False
                }
            
            main_func = exec_namespace['main']
            if not asyncio.iscoroutinefunction(main_func):
                return {
                    'success': False,
                    'error': 'main() is not an async function',
                    'output': '',
                    'complete': False
                }
            
            # Capture stdout AND add tool call logging
            import io
            import sys
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()
            
            # Wrap server_manager.call_tool to add logging AND verify server_manager state
            original_call_tool = self.server_manager.call_tool
            
            async def logged_call_tool(tool_name, parameters, use_cache=True):
                """Wrapper to log tool calls and results"""
                # Get server name for the tool
                server_name = None
                tool_info = self.server_manager.all_tools.get(tool_name) if hasattr(self.server_manager, 'all_tools') else None
                if tool_info:
                    server_name = tool_info.get('server')
                
                # Track this tool call
                tool_call_info = {
                    'tool': tool_name,
                    'server': server_name,
                    'parameters': parameters.copy() if parameters else {},
                    'turn': turn
                }
                
                # Verify server_manager state before calling
                print(f"\n{'='*80}")
                print(f"TOOL CALL: {tool_name}")
                print(f"PARAMETERS: {json.dumps(parameters, indent=2)}")
                print(f"Server Manager ID: {id(self.server_manager)}")
                print(f"Server Manager type: {type(self.server_manager)}")
                if hasattr(self.server_manager, 'sessions'):
                    print(f"Active sessions: {list(self.server_manager.sessions.keys()) if self.server_manager.sessions else 'None'}")
                    session_count = len(self.server_manager.sessions) if self.server_manager.sessions else 0
                    print(f"Session count: {session_count}")
                    # Verify session for the tool's server
                    if tool_info:
                        if server_name and self.server_manager.sessions:
                            session = self.server_manager.sessions.get(server_name)
                            print(f"Session for {server_name}: {'EXISTS' if session else 'MISSING'}")
                            if session:
                                print(f"  Session type: {type(session)}")
                                print(f"  Session ID: {id(session)}")
                print(f"{'='*80}")
                try:
                    result = await original_call_tool(tool_name, parameters, use_cache)
                    
                    # Mark tool call as successful
                    tool_call_info['success'] = True
                    self.tool_calls.append(tool_call_info)
                    print(f"\n{'='*80}")
                    print(f"TOOL RESULT for {tool_name}:")
                    print(f"Type: {type(result)}")
                    if hasattr(result, '__dict__'):
                        print(f"Attributes: {list(result.__dict__.keys())}")
                        if hasattr(result, 'content') and result.content:
                            print(f"Content items count: {len(result.content)}")
                            for i, item in enumerate(result.content[:3]):  # First 3 items
                                if hasattr(item, 'text'):
                                    print(f"  Content[{i}].text (first 500 chars): {item.text[:500]}")
                                elif isinstance(item, dict):
                                    print(f"  Content[{i}] (dict): {str(item)[:500]}")
                                else:
                                    print(f"  Content[{i}]: {str(item)[:500]}")
                    elif isinstance(result, dict):
                        print(f"Dict keys: {list(result.keys())}")
                        print(f"Dict content (first 1000 chars): {json.dumps(result, indent=2)[:1000]}")
                    elif isinstance(result, str):
                        print(f"String length: {len(result)}")
                        print(f"String preview (first 500 chars): {result[:500]}")
                    else:
                        print(f"Result (first 500 chars): {str(result)[:500]}")
                    print(f"{'='*80}\n")
                    return result
                except Exception as e:
                    # Mark tool call as failed
                    tool_call_info['success'] = False
                    tool_call_info['error'] = str(e)
                    self.tool_calls.append(tool_call_info)
                    
                    print(f"\n{'='*80}")
                    print(f"TOOL CALL ERROR for {tool_name}: {type(e).__name__}: {e}")
                    import traceback
                    print(f"Traceback:\n{traceback.format_exc()}")
                    print(f"{'='*80}\n")
                    raise
            
            # Verify server_manager in namespace matches our self.server_manager
            namespace_sm = exec_namespace['server_manager']
            if id(namespace_sm) != id(self.server_manager):
                logger.error(f"❌ SERVER_MANAGER ID MISMATCH! Namespace: {id(namespace_sm)}, Self: {id(self.server_manager)}")
                logger.error("This means a different server_manager instance is in the namespace!")
            else:
                logger.info(f"✓ Server manager ID matches: {id(namespace_sm)}")
            
            # Replace server_manager.call_tool in the namespace with logged version
            exec_namespace['server_manager'].call_tool = logged_call_tool
            
            try:
                # Execute the async main function
                result = await main_func()
                
                # Get captured output
                output = captured_output.getvalue()
                
                # Handle result
                if isinstance(result, tuple) and len(result) == 2:
                    task_complete, final_answer = result
                elif isinstance(result, bool):
                    task_complete = result
                    final_answer = output
                else:
                    task_complete = True
                    final_answer = output if output else str(result)
                
                sys.stdout = old_stdout
                
                logger.info(f"Code execution completed. Output length: {len(output)} chars")
                logger.info(f"Task complete: {task_complete}")
                
                return {
                    'success': True,
                    'output': output,
                    'final_answer': final_answer,
                    'complete': task_complete
                }
                
            except Exception as exec_error:
                sys.stdout = old_stdout
                error_msg = str(exec_error)
                logger.error(f"Code execution error: {error_msg}")
                logger.error(traceback.format_exc())
                
                return {
                    'success': False,
                    'error': error_msg,
                    'output': captured_output.getvalue(),
                    'complete': False
                }
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing code: {error_msg}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': error_msg,
                'output': '',
                'complete': False
            }
    
    def _remove_top_level_await(self, code: str) -> str:
        """Remove top-level await statements and function calls that cause syntax errors."""
        lines = code.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.lstrip()
            # Skip empty lines
            if not stripped:
                cleaned_lines.append(line)
                continue
            
            # Check if line is indented (inside a function)
            is_indented = line.startswith((' ', '\t'))
            
            # If not indented, check if it's a top-level await or function call
            if not is_indented:
                # Keep function definitions
                if stripped.startswith(('async def', 'def ', 'import ', 'from ', '#')):
                    cleaned_lines.append(line)
                # Remove top-level await statements (any line with await that's not a function definition)
                elif 'await' in stripped:
                    logger.debug(f"Removing top-level await statement: {line}")
                    continue
                # Remove any other variable assignments at top level that might call async functions
                # (keep only function definitions, imports, and comments at top level)
                elif '=' in stripped and not stripped.startswith('#'):
                    # This might be calling a function, skip it to be safe
                    logger.debug(f"Removing potential top-level assignment: {line}")
                    continue
                else:
                    cleaned_lines.append(line)
            else:
                # Keep all indented lines (inside functions)
                cleaned_lines.append(line)
        
        cleaned_code = '\n'.join(cleaned_lines)
        return cleaned_code

    async def _generate_final_answer(
        self,
        task: str,
        code_executions: List[Dict[str, Any]]
    ) -> str:
        """Generate final answer by reasoning about execution results in the context of the task."""
        if not code_executions:
            return "No code was executed."
        
        # Collect all execution outputs and results
        all_outputs = []
        all_final_answers = []
        errors = []
        
        for exec_info in code_executions:
            exec_result = exec_info.get('execution', {})
            if exec_result.get('output'):
                all_outputs.append(exec_result['output'])
            if exec_result.get('final_answer'):
                all_final_answers.append(exec_result['final_answer'])
            if exec_result.get('error'):
                errors.append(exec_result['error'])
        
        # Get the last successful execution's final answer (which should already be reasoned)
        last_execution = None
        for exec_info in reversed(code_executions):
            exec_result = exec_info.get('execution', {})
            if exec_result.get('success') and exec_result.get('final_answer'):
                last_execution = exec_result
                break
        
        # If we have a final_answer that looks reasoned (not just raw JSON), use it
        if last_execution:
            final_answer = last_execution.get('final_answer', '')
            # Check if it's just raw JSON/data (starts with { or [ and is short)
            if final_answer and not (final_answer.strip().startswith('{') and len(final_answer) < 500):
                # This looks like a reasoned answer, use it
                return final_answer
        
        # If we have outputs but no reasoned answer, generate one using LLM
        if all_outputs:
            # Combine all outputs
            combined_output = "\n\n".join(all_outputs)
            
            # Use LLM to reason about the results in the context of the task
            try:
                reasoning_prompt = f"""You are an expert at synthesizing information to answer questions.

TASK/QUERY: {task}

EXECUTION RESULTS:
{combined_output}

Your task is to analyze the execution results and provide a well-reasoned answer that directly addresses the query. 

IMPORTANT:
- Do NOT just repeat the raw execution output
- Synthesize the information into a coherent answer
- If the results are incomplete or unclear, explain what was found and what might be missing
- If there were errors, acknowledge them and provide what information is available
- Make sure your answer directly addresses what the user asked for

Provide a clear, well-reasoned answer:"""

                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing execution results and synthesizing them into clear, well-reasoned answers that directly address user queries."},
                        {"role": "user", "content": reasoning_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                reasoned_answer = response.choices[0].message.content.strip()
                
                # Track tokens
                usage = response.usage
                if usage:
                    self.total_output_tokens += usage.completion_tokens
                    self.total_prompt_tokens += usage.prompt_tokens
                    self.total_tokens += usage.total_tokens
                
                return reasoned_answer
                
            except Exception as e:
                logger.warning(f"Failed to generate reasoned answer via LLM: {e}. Falling back to raw output.")
                # Fallback to raw output if reasoning fails
                return combined_output
        
        # If we have errors but no outputs
        if errors:
            return f"Task execution encountered errors: {'; '.join(errors)}. No results were generated."
        
        return "Task execution completed but no results were generated."

