"""
Core MCP functionality - client, executor, and agent
"""
# Import verdict_enums first so it's in namespace before agent loads (agent -> prompts -> agent_prompt imports app.core)
from .verdicts import pre_execution_verdict_enums, post_execution_verdict_enums
from .mcp_client import MCPClient, get_mcp_client
from .agent import OpenAICodeAgent, OpenAIJudge
from .docker_executor import get_docker_executor



__all__ = [
    'pre_execution_verdict_enums',
    'post_execution_verdict_enums',
    'MCPClient',
    'get_mcp_client',
    'OpenAICodeAgent',
    'OpenAIJudge',
    'get_docker_executor',
]

