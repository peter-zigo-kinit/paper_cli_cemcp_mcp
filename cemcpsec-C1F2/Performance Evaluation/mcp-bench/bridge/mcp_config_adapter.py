"""
MCP Config Adapter for converting between mcp-bench and AI_Code_Execution_with_MCP config formats.

This module handles the conversion between:
- mcp-bench format: commands.json with cmd, env, cwd, transport, port, endpoint
- AI_Code_Execution_with_MCP format: mcp_config.json with command, args
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MCPConfigAdapter:
    """Adapter for converting MCP server configurations between formats."""
    
    def __init__(self, commands_json_path: str = "mcp_servers/commands.json", 
                 api_key_path: str = "mcp_servers/api_key"):
        """
        Initialize the MCP config adapter.
        
        Args:
            commands_json_path: Path to mcp-bench commands.json file
            api_key_path: Path to API key file
        """
        self.commands_json_path = Path(commands_json_path)
        self.api_key_path = Path(api_key_path)
        self.api_keys: Dict[str, str] = {}
        self._load_api_keys()
    
    def _load_api_keys(self) -> None:
        """Load API keys from api_key file."""
        if not self.api_key_path.exists():
            logger.warning(f"API key file not found at {self.api_key_path}")
            return
        
        try:
            with open(self.api_key_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        self.api_keys[key.strip()] = value.strip()
            logger.info(f"Loaded {len(self.api_keys)} API keys")
        except Exception as e:
            logger.warning(f"Error loading API keys: {e}")
    
    def convert_to_aicode_format(self, server_name: str, server_config: Dict[str, Any], 
                                 base_path: str = "mcp_servers") -> Optional[Dict[str, Any]]:
        """
        Convert mcp-bench server config to AI_Code_Execution_with_MCP format.
        
        Args:
            server_name: Name of the server
            server_config: Server configuration from commands.json:
                {
                    'cmd': str,  # e.g., "python server.py"
                    'env': List[str],  # e.g., ["API_KEY"]
                    'cwd': str,  # e.g., "../server-name"
                    'transport': str (optional),  # "http" or stdio
                    'port': int (optional),
                    'endpoint': str (optional)
                }
            base_path: Base path for resolving relative cwd paths
        
        Returns:
            Configuration in AI_Code_Execution_with_MCP format:
                {
                    'command': str,
                    'args': List[str]
                }
            Returns None if conversion fails or transport is HTTP (not supported by AI_Code_Execution_with_MCP)
        """
        # Check if this is an HTTP server (not supported by AI_Code_Execution_with_MCP's stdio client)
        if server_config.get('transport') == 'http':
            logger.warning(f"Server {server_name} uses HTTP transport, which is not supported by AI_Code_Execution_with_MCP")
            return None
        
        # Parse command string into command and args
        cmd = server_config.get('cmd', '')
        if not cmd:
            logger.warning(f"Server {server_name} has no command")
            return None
        
        # Split command into parts
        cmd_parts = cmd.split()
        if not cmd_parts:
            logger.warning(f"Server {server_name} has empty command")
            return None
        
        command = cmd_parts[0]
        args = cmd_parts[1:] if len(cmd_parts) > 1 else []
        
        # Verify the command exists (for common commands like python, node)
        import shutil
        if command in ['python', 'python3', 'node', 'nodejs']:
            command_path = shutil.which(command)
            if not command_path:
                logger.warning(f"Command '{command}' not found in PATH for server {server_name}")
                logger.warning(f"  This will likely cause connection failure")
            else:
                logger.debug(f"Found command '{command}' at: {command_path}")
        
        # Handle working directory - resolve to absolute path
        cwd = server_config.get('cwd', '')
        resolved_cwd = None
        if cwd:
            # If cwd is relative, resolve it relative to base_path (which is mcp_servers directory)
            if cwd.startswith('../'):
                # For paths like "../wikipedia-mcp", resolve relative to base_path's parent
                # base_path is typically "mcp-bench/mcp_servers", so "../wikipedia-mcp" 
                # should resolve to "mcp-bench/wikipedia-mcp"
                base_path_parent = os.path.dirname(base_path)
                cwd_relative = cwd[3:]  # Remove leading ../
                resolved_cwd = os.path.abspath(os.path.join(base_path_parent, cwd_relative))
            elif cwd.startswith('./'):
                # For paths like "./subdir", resolve relative to base_path
                cwd_relative = cwd[2:]  # Remove leading ./
                resolved_cwd = os.path.abspath(os.path.join(base_path, cwd_relative))
            else:
                # Absolute path or relative to base_path
                if os.path.isabs(cwd):
                    resolved_cwd = cwd
                else:
                    resolved_cwd = os.path.abspath(os.path.join(base_path, cwd))
            
            # Verify the directory exists
            if not os.path.exists(resolved_cwd):
                logger.warning(f"Working directory {resolved_cwd} does not exist for server {server_name}")
                logger.warning(f"  Original cwd: {cwd}, base_path: {base_path}")
                
                # Try fallback: check if server exists in mcp_servers directory
                # Some servers might be in mcp_servers/server-name instead of ../server-name
                if cwd.startswith('../'):
                    # Extract just the directory name (e.g., "wikipedia-mcp" from "../wikipedia-mcp")
                    # But handle nested paths like "../call-for-papers-mcp/call-for-papers-mcp-main"
                    server_dir_name = cwd_relative
                    # Try in base_path (mcp_servers/server-name)
                    fallback_cwd = os.path.abspath(os.path.join(base_path, server_dir_name))
                    if os.path.exists(fallback_cwd):
                        logger.info(f"Found server in mcp_servers directory: {fallback_cwd}")
                        resolved_cwd = fallback_cwd
                    else:
                        # Try splitting the path and checking each part
                        # For "../call-for-papers-mcp/call-for-papers-mcp-main", try:
                        # 1. mcp_servers/call-for-papers-mcp/call-for-papers-mcp-main
                        path_parts = server_dir_name.split(os.sep)
                        if len(path_parts) > 1:
                            # Try building path from base_path
                            nested_fallback = os.path.abspath(os.path.join(base_path, *path_parts))
                            if os.path.exists(nested_fallback):
                                logger.info(f"Found server in nested mcp_servers directory: {nested_fallback}")
                                resolved_cwd = nested_fallback
                            else:
                                logger.warning(f"Server directory not found in any expected location")
                                resolved_cwd = None
                        else:
                            logger.warning(f"Server directory not found in any expected location")
                            resolved_cwd = None
                else:
                    resolved_cwd = None
            else:
                logger.info(f"Resolved working directory for {server_name}: {resolved_cwd}")
        
        # Handle environment variables
        env_vars = server_config.get('env', [])
        env_dict = {}
        for env_var in env_vars:
            if env_var in self.api_keys:
                env_dict[env_var] = self.api_keys[env_var]
        
        # Note: AI_Code_Execution_with_MCP's MCPClient doesn't support env vars in config
        # The environment will need to be set before running, or we need to modify the approach
        # For now, we'll return the config and note that env vars need to be handled separately
        
        return {
            'command': command,
            'args': args,
            # Store resolved paths and env for MCP client
            'cwd': resolved_cwd,  # Absolute path to working directory
            'env': env_dict,  # Environment variables dict
            '_original_cwd': cwd,  # Keep original for reference
            '_server_name': server_name
        }
    
    def create_mcp_config_json(self, server_configs: Dict[str, Dict[str, Any]], 
                              output_path: str = "mcp_config.json") -> str:
        """
        Create mcp_config.json file from server configurations.
        
        Args:
            server_configs: Dictionary mapping server names to their configs
                (in AI_Code_Execution_with_MCP format)
            output_path: Path where to write the config file
        
        Returns:
            Path to the created config file
        """
        # Filter out None configs (failed conversions)
        valid_configs = {name: config for name, config in server_configs.items() 
                        if config is not None}
        
        # Include env and cwd if they exist (for MCP client to use)
        cleaned_configs = {}
        for name, config in valid_configs.items():
            cleaned_config = {
                'command': config['command'],
                'args': config['args']
            }
            # Include environment variables if present
            if 'env' in config and config['env']:
                cleaned_config['env'] = config['env']
            # Include working directory if present (absolute path)
            if 'cwd' in config and config['cwd']:
                cleaned_config['cwd'] = config['cwd']
            cleaned_configs[name] = cleaned_config
        
        mcp_config = {
            'mcpServers': cleaned_configs
        }
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        logger.info(f"Created mcp_config.json at {output_path} with {len(cleaned_configs)} servers")
        return output_path
    
    def convert_servers_for_task(self, server_names: List[str], 
                                 commands_config: Dict[str, Any],
                                 base_path: str = "mcp_servers") -> Dict[str, Any]:
        """
        Convert multiple servers for a task to AI_Code_Execution_with_MCP format.
        
        Args:
            server_names: List of server names required for the task
            commands_config: Full commands.json configuration
            base_path: Base path for resolving relative paths
        
        Returns:
            Dictionary mapping server names to their converted configs
        """
        converted_configs = {}
        
        for server_name in server_names:
            if server_name not in commands_config:
                logger.warning(f"Server {server_name} not found in commands config")
                continue
            
            server_config = commands_config[server_name]
            converted = self.convert_to_aicode_format(server_name, server_config, base_path)
            
            if converted:
                converted_configs[server_name] = converted
            else:
                logger.warning(f"Failed to convert server {server_name}")
        
        return converted_configs

