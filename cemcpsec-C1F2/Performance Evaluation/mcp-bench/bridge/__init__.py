"""
Bridge module for connecting AI_Code_Execution_with_MCP agents to mcp-bench.

This module provides adapters and runners to execute mcp-bench tasks using
the Traditional MCP and Code Execution MCP agents from AI_Code_Execution_with_MCP.
"""

from .task_adapter import TaskAdapter
from .result_adapter import ResultAdapter
from .mcp_config_adapter import MCPConfigAdapter
from .runner import BridgeRunner

__all__ = [
    'TaskAdapter',
    'ResultAdapter',
    'MCPConfigAdapter',
    'BridgeRunner',
]

