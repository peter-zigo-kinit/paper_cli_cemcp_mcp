"""
Utility to read MCP server code files to help code execution agent understand available tools.

This module reads server source code from mcp_servers directory to provide additional
context to the code execution agent about what tools are available and how they work.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def find_server_code_files(server_name: str, mcp_servers_dir: str) -> List[Path]:
    """
    Find source code files for a given server.
    
    Args:
        server_name: Name of the server (as it appears in commands.json)
        mcp_servers_dir: Path to mcp_servers directory
        
    Returns:
        List of Path objects to relevant source code files
    """
    server_dir = Path(mcp_servers_dir)
    code_files = []
    
    # Common patterns for server directories
    # Server names might match directory names with variations
    possible_dirs = []
    
    # Try exact match first
    exact_match = server_dir / server_name.lower().replace(" ", "-")
    if exact_match.exists() and exact_match.is_dir():
        possible_dirs.append(exact_match)
    
    # Try to find directories that might contain the server
    for item in server_dir.iterdir():
        if item.is_dir():
            dir_name_lower = item.name.lower()
            server_name_lower = server_name.lower().replace(" ", "-")
            # Check if directory name contains server name or vice versa
            if (server_name_lower in dir_name_lower or 
                dir_name_lower in server_name_lower or
                dir_name_lower.replace("-", "_") in server_name_lower.replace(" ", "_")):
                possible_dirs.append(item)
    
    # Look for Python/TypeScript source files in found directories
    for dir_path in possible_dirs:
        # Look for Python files (*.py) that might contain tool definitions
        for py_file in dir_path.rglob("*.py"):
            # Skip __pycache__ and test files
            if "__pycache__" not in str(py_file) and "test" not in py_file.name.lower():
                # Prefer files with common server/tool naming patterns
                if any(pattern in py_file.name.lower() for pattern in ["server", "tool", "main", "index", "__init__"]):
                    code_files.append(py_file)
        
        # Look for TypeScript/JavaScript files (*.ts, *.js)
        for ts_file in dir_path.rglob("*.ts"):
            if "node_modules" not in str(ts_file) and "test" not in ts_file.name.lower():
                if any(pattern in ts_file.name.lower() for pattern in ["server", "tool", "index", "main"]):
                    code_files.append(ts_file)
        
        # Limit to first few relevant files to avoid overwhelming the prompt
        if len(code_files) >= 3:
            break
    
    return code_files[:5]  # Limit to 5 files


def read_server_code_snippet(file_path: Path, max_lines: int = 200) -> str:
    """
    Read a snippet of server code from a file.
    
    Args:
        file_path: Path to the code file
        max_lines: Maximum number of lines to read
        
    Returns:
        Code snippet as string
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # If file is small, return all
        if len(lines) <= max_lines:
            return ''.join(lines)
        
        # Otherwise, try to find tool definitions and return relevant sections
        # Look for common patterns like @server.tool(), @tool(), def tool_, etc.
        relevant_sections = []
        in_tool_definition = False
        tool_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line contains tool definition markers
            if any(marker in line.lower() for marker in ['@server.tool', '@tool', 'def ', 'function ', 'tool(']):
                # Start collecting tool definition
                in_tool_definition = True
                # Include a few lines before for context
                start = max(0, i - 3)
                tool_lines = lines[start:i+1]
            
            if in_tool_definition:
                tool_lines.append(line)
                # Stop after collecting a reasonable amount
                if len(tool_lines) > 50:
                    relevant_sections.extend(tool_lines)
                    tool_lines = []
                    in_tool_definition = False
        
        # Add any remaining tool lines
        if tool_lines:
            relevant_sections.extend(tool_lines)
        
        # If we found relevant sections, return them
        if relevant_sections:
            return ''.join(relevant_sections[:max_lines])
        
        # Otherwise, return first and last portions of file
        first_half = ''.join(lines[:max_lines//2])
        last_half = ''.join(lines[-max_lines//2:])
        return f"{first_half}\n... (file truncated) ...\n{last_half}"
        
    except Exception as e:
        logger.warning(f"Could not read code file {file_path}: {e}")
        return ""


def get_server_code_context(server_name: str, mcp_servers_dir: str) -> str:
    """
    Get code context for a server to help the code execution agent understand tools.
    
    Args:
        server_name: Name of the server
        mcp_servers_dir: Path to mcp_servers directory
        
    Returns:
        Formatted string with server code snippets
    """
    code_files = find_server_code_files(server_name, mcp_servers_dir)
    
    if not code_files:
        return ""
    
    context_parts = [f"## Server Code Context for '{server_name}'\n"]
    context_parts.append(f"Found {len(code_files)} relevant source file(s):\n")
    
    for i, file_path in enumerate(code_files, 1):
        relative_path = file_path.relative_to(Path(mcp_servers_dir))
        context_parts.append(f"\n### File {i}: {relative_path}\n")
        context_parts.append("```python" if file_path.suffix == '.py' else "```typescript")
        context_parts.append("\n")
        
        code_snippet = read_server_code_snippet(file_path)
        context_parts.append(code_snippet)
        
        context_parts.append("\n```\n")
    
    context_parts.append("\nNote: This code shows how tools are implemented in the server. ")
    context_parts.append("Use the tool names and parameters as defined in the connected MCP server.\n")
    
    return ''.join(context_parts)

