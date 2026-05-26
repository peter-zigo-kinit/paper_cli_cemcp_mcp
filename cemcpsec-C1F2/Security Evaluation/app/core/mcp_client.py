"""
Real MCP Client implementation using official MCP SDK
"""
import asyncio
import json
import os
from typing import Any, Dict, List
from contextlib import AsyncExitStack
import threading

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.app_logging.logger import setup_logger
from app.config import MCP_CONFIG_PATH
from costume_mcp_servers import get_handler_server

# Setup logger
logger = setup_logger(__name__)


class MCPClient:
    _mcp_client_instance = None
    _lock = None
    _thread_lock = threading.Lock()
    _init_done = False

    """Client for interacting with real MCP servers using official protocol"""
    def __init__(self, config_path: str = "mcp_config.json"):
        # Load MCP server configurations from file
        self.config_path = config_path
        self.server_configs = self._load_config()
        
        # Store active sessions
        self.sessions = {}
        # Create stack to hold all async resources - Add MCP server process to stack, Add JSON-RPC session to stack 
        self.exit_stack = AsyncExitStack()
        
        # Track if client is initialized
        self.initialized = False
        
        # Store generated tool catalog
        self._catalog = ""
    
    @classmethod
    async def get_mcp_client(cls, config_path: str = MCP_CONFIG_PATH):
        """Get or create the global MCP client instance"""
        
        if cls._mcp_client_instance is None:
            with cls._thread_lock:
                if cls._mcp_client_instance is None:
                    cls._mcp_client_instance = cls(config_path)

        if not cls._init_done:
            with cls._thread_lock:
                if not cls._init_done:
                    await cls._mcp_client_instance.initialize()
                    cls._init_done = True

        return cls._mcp_client_instance

    def _load_config(self) -> Dict[str, Any]:
        """Load MCP server configurations from JSON file"""
        if not os.path.exists(self.config_path):
            return {}
        
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        return config.get("mcpServers", {})

    @staticmethod
    def _get_attr(obj: Any, key: str, default=None):
        """Helper to get attribute from dict or object."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    @staticmethod
    def _schema_to_example(schema: Dict[str, Any] | None) -> str:
        """
        Convert a JSON schema to an example JSON string with placeholder values.
        """
        if not isinstance(schema, dict):
            return "{}"

        props = schema.get("properties", {}) or {}
        if not props:
            return "{}"

        example = {}
        for k, v in props.items():
            t = (v or {}).get("type")
            if t == "string":
                example[k] = "<string>"
            elif t == "integer":
                example[k] = 0
            elif t == "number":
                example[k] = 0.0
            elif t == "boolean":
                example[k] = False
            elif t == "array":
                example[k] = []
            elif t == "object":
                example[k] = {}
            else:
                example[k] = "<value>"

        return str(example).replace("'", '"')

    async def initialize(self):
        """Initialize connections to all configured MCP servers and generate tool documentation"""
        
        if self.initialized:
            logger.debug("MCP Client already initialized, skipping")
            return
        logger.info("Initializing MCP Client connections...")
        # Connect to each configured server and creates communication channels
        for server_name, config in self.server_configs.items():
            await self._connect_server(server_name, config)
        
        # Generate tool descriptions and catalog
        await self._generate_tool_catalog()
        
        self.initialized = True
        logger.info(f"MCP Client initialization complete. Connected servers: {list(self.sessions.keys())}")

    async def _connect_server(self, server_name: str, config: Dict[str, Any]):
        """Connect to a single MCP server"""
        try:
            # Extract server parameters
            command = config.get("command")
            args = config.get("args", [])
            
            # Step 1: Create server parameters
            # Packages the server launch configuration into an MCP SDK object.
            # Launch the MCP server by running this command.
            server_params = StdioServerParameters(
                command=command,
                args=args,
            )
            
            # Step 2: Launch the MCP server process
            # Create stdio client and session
            stdio = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            # read: to read response from MCP server & write: write commands to MCP Server
            read, write = stdio   # Get input/output pipes
            
            # Step 3: Create JSON-RPC session for communication
            # Creates a session object that manages the JSON-RPC protocol communication with the server.
            # This session obj can send tool call request,receive tool response
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            # Initialize the session
            await session.initialize()
            
            # Store session
            self.sessions[server_name] = session
            
            logger.info(f"Connected to MCP server: {server_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {str(e)}")

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """List all tools available on a specific MCP server"""
        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' is not connected")
        
        #store sessions
        session = self.sessions[server_name]
        
        try:
            # Call list_tools on the MCP server
            tools_result = await session.list_tools()
            return tools_result.tools
        except Exception as e:
            logger.error(f"Error listing tools from {server_name}: {type(e).__name__}: {str(e)}")
            # Return empty list instead of failing completely
            return []

    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """Call a tool on a connected MCP server using real protocol"""
        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' is not connected")
        
        session = self.sessions[server_name]
        
        logger.info(f"Calling {server_name}.{tool_name} with arguments: {arguments}")
        
        # Call the tool using MCP protocol
        result = await session.call_tool(tool_name, arguments)
        
        return result

    async def _generate_tool_catalog(self):
        """
        Generate tool documentation files and build catalog.
        
        Creates:
        - Documentation files under: servers/<server_name>/<tool_name>.md
        - Index file for each server: servers/<server_name>/index.md
        - Stores catalog string in self._catalog
        """
        logger.info("Generating MCP tool descriptions and catalog")
        
        # Resolve servers directory relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        servers_root = os.path.abspath(os.path.join(current_dir, "..", "..", "servers"))
        os.makedirs(servers_root, exist_ok=True)

        # Build catalog lines
        catalog_lines: List[str] = []
        catalog_lines.append("## MCP TOOL CATALOG")
        catalog_lines.append("Use the tool `mcp_call(name, args)` to call any MCP tool.")
        catalog_lines.append('`name` must be "<server>.<tool>" and `args` must be a JSON object.\n')

        for server in self.get_available_servers():
            if not self.is_server_connected(server):
                continue

            tools = await self.list_tools(server)
            if not tools:
                continue

            # Create servers/<server_name>/ directory
            server_dir = os.path.join(servers_root, server)
            os.makedirs(server_dir, exist_ok=True)

            index_lines = [
                f"# MCP Tools — {server}",
                "",
                "Read a tool file before calling it.",
                "",
            ]

            # Add server section to catalog
            catalog_lines.append(f"### Server: {server}")

            for t in tools:
                # Skip tools with "Deprecated" in the title
                tool_title = self._get_attr(t, "title", "")
                if tool_title and "Deprecated" in tool_title:
                    continue
                
                tool_name = self._get_attr(t, "name")
                description = self._get_attr(t, "description", "") or ""
                input_schema = self._get_attr(t, "inputSchema", {}) or {}

                # Generate individual tool file
                tool_file = f"{tool_name}.md"
                tool_path = os.path.join(server_dir, tool_file)
                example_args = self._schema_to_example(input_schema)

                content = [
                    f"# {server}.{tool_name}",
                    "",
                    description if description else "_No description provided._",
                    "",
                    "## Input Schema",
                    "```json",
                    str(json.dumps(input_schema, indent=2)) if input_schema else "{}",
                    "```",
                    "",
                    "## Example Usage",
                    "```python",
                    f'mcp_call_http(name="{server}.{tool_name}", args={example_args})',
                    "```",
                    "",
                ]

                with open(tool_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(content))

                index_lines.append(f"- `{tool_file}`")

                # Add tool to catalog
                fq = f"{server}.{tool_name}"
                if description:
                    catalog_lines.append(f"- **{fq}** — {description}")
                else:
                    catalog_lines.append(f"- **{fq}**")
                catalog_lines.append(f'  - Example: `mcp_call(name="{fq}", args={example_args})`')

            # Write server-specific index.md
            index_path = os.path.join(server_dir, "index.md")
            with open(index_path, "w", encoding="utf-8") as f:
                if server == "db_server":
                    handler_server = get_handler_server()
                    index_lines.append(handler_server.server_guide)
                f.write("\n".join(index_lines))

            # Add blank line between servers in catalog
            catalog_lines.append("")

        # Store catalog in private field
        self._catalog = "\n".join(catalog_lines)
        logger.info("MCP tool descriptions and catalog generated successfully")

    def get_catalog(self) -> str:
        """
        Get the generated tool catalog.
        
        Returns:
            str: Markdown-formatted catalog of all MCP tools.
        """
        return self._catalog
        

    def get_available_servers(self) -> List[str]:
        """Get list of all configured server names"""
        return list(self.server_configs.keys())

    def is_server_connected(self, server_name: str) -> bool:
        """Check if a server is connected and session is valid"""
        if server_name not in self.sessions:
            return False
        
        # Additional check: ensure session is not closed
        session = self.sessions[server_name]
        try:
            # Check if the session's write stream is still open
            return hasattr(session, '_write_stream') and session._write_stream is not None
        except:
            # If any error checking session state, assume it's not connected
            return False

    async def close(self):
        """Close all MCP server connections"""
        if not self.initialized:
            return
        await self.exit_stack.aclose()
        self.sessions.clear()
        self.initialized = False
        logger.info("All MCP connections closed")



async def get_mcp_client(config_path: str = MCP_CONFIG_PATH) -> MCPClient:
    """Get or create the global MCP client instance"""
    return await MCPClient.get_mcp_client(config_path)
    
