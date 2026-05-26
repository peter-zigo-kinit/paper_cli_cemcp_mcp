"""
OpenAI Agent for discovering tools from real MCP servers and generating code
Uses official MCP protocol to discover and interact with MCP servers
"""
import json
from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
from openai import OpenAI

from app.app_logging.logger import setup_logger
from app.prompts import CODE_AGENT_PROMPT, SUMMARIZATION_PROMPT, JUDGE_AGENT_PROMPT
from .verdicts import pre_execution_verdict_enums, post_execution_verdict_enums
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_MAX_TOKENS,
    OPENAI_TEMPERATURE
)


# Setup logger
logger = setup_logger(__name__)

class Agent(ABC):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.client = OpenAI(api_key=api_key or OPENAI_API_KEY)
        self.model = model or OPENAI_MODEL
        self.max_tokens = OPENAI_MAX_TOKENS
    
    
    def llm_call(self, messages: List[Dict[str, str]]) -> Dict[str, str]:
        """
        Call OpenAI API with JSON mode to ensure structured response

        Args:
            messages: List of messages to send to the LLM
        
        Returns:
            Dictionary with:
                - status: "exploring" or "complete"
                - code: Generated Python code
                - reasoning: Explanation of status choice
                - token_usage: Token usage information

        Raises:
            Exception: If there is an error calling the LLM
        """
        try:
            response = self.client.chat.completions.create(
                                                    model=self.model,
                                                    messages=messages,
                                                    response_format={"type": "json_object"},
                                                    max_tokens=self.max_tokens,
                                                    temperature=OPENAI_TEMPERATURE
                                                )

            raw_result = response.choices[0].message.content
            
            result = json.loads(raw_result)
            result["token_usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            return result

        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise e


class OpenAICodeAgent(Agent):
    """Agent that discovers MCP tools from real MCP servers and generates Python code using OpenAI"""

    async def generate_code_with_history(
        self, 
        messages: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Generate code with conversation history and status indicator.
        
        Uses progressive discovery approach where agent explores tools
        and data structures across multiple turns. Returns structured
        JSON response with status to determine if more turns are needed.
        
        Args:
            messages: Conversation history with role and content
                Example: [
                    {"role": "user", "content": "query"},
                    {"role": "assistant", "content": "code1"},
                    {"role": "user", "content": "result1"},
                    ...
                ]
        
        Returns:
            Dictionary with:
                - status: "exploring" "execution" or "complete"
                - code: Generated Python code
                - reasoning: Explanation of status choice
        
        Raises:
            ValueError: If LLM response is invalid JSON or missing fields
            llm_call Exceptions errors
        """
        # Build messages array with system prompt and conversation history
        openai_messages = [{"role": "system", "content": CODE_AGENT_PROMPT}] # The CODE_AGENT_PROMPT used while Maintenance a messeges list
        openai_messages.extend(messages)
        logger.info(f"\n\nOpenAI Code Messages:\n\n{json.dumps(openai_messages, indent=2)}\n")
        

        # Read openAI docs Response and try to bind and provide the tools def's for the agent.
        # Call OpenAI API with JSON mode to ensure structured response
        result = None
        try:
            result = self.llm_call(openai_messages)
        except Exception as e:
            raise e
        
        # Validate required fields are present
        if "status" not in result or "code" not in result:
            raise ValueError(f"Invalid LLM response format: {result}")
        
        # Validate status value
        if result["status"] not in ["exploring", "execution", "complete"]:
            raise ValueError(f"Invalid status value: {result['status']}")
        
        return result


class OpenAIJudge(Agent):
    """Agent that judges the code and the execution results"""
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(api_key, model)
        # Agent use enum for verdicts if status is False.
        self.pre_execution_verdict_enums = pre_execution_verdict_enums
        self.post_execution_verdict_enums = post_execution_verdict_enums

    async def judge_code_and_execution_results(
        self,
        messages: List[Dict[str, str]], # Format by the orchestrator.
        mode: str = "pre_execution" # "pre_execution" or "post_execution"
    ) -> Dict[str, Any]:
        """
        Judge the code and the execution results
        """
        verdict_enums = self.pre_execution_verdict_enums if mode == "pre_execution" else self.post_execution_verdict_enums
        openai_judge_messages = [ { "role": "system", "content": JUDGE_AGENT_PROMPT } ]
        openai_judge_messages.extend(messages)
        logger.info(f"\n\nOpenAI Judge Messages:\n\n{json.dumps(openai_judge_messages, indent=2)}\n")

        judge_result = None
        try:
            judge_result = self.llm_call(openai_judge_messages)
        except Exception as e:
            raise e
        
        # Validate required fields are present
        if "status" not in judge_result or "reasoning" not in judge_result or "verdict" not in judge_result:
            raise ValueError(f"Invalid LLM response format: {judge_result}")       
        
        if judge_result['status'] not in [True, False]:
            raise ValueError(f"Invalid status value: {judge_result['status']}")
        
        if judge_result['verdict'] not in verdict_enums:
            raise ValueError(f"Invalid verdict value: {judge_result['verdict']}")
        
        # Format real boolean value
        return judge_result

