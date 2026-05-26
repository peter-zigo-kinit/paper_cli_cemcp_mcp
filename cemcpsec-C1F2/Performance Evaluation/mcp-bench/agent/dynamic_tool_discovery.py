"""
Dynamic Tool Discovery Module for Code Execution Agent.

This module scans the mcp_servers directory to discover tool definitions
dynamically based on task requirements, without requiring pre-connection
to MCP servers.
"""

import ast
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import importlib.util

logger = logging.getLogger(__name__)


class DynamicToolDiscovery:
    """Discovers MCP tools by scanning server source files."""
    
    def __init__(self, mcp_servers_dir: Optional[str] = None):
        """
        Initialize dynamic tool discovery.
        
        Args:
            mcp_servers_dir: Path to mcp_servers directory. If None, tries to find it automatically.
        """
        if mcp_servers_dir is None:
            # Try to find mcp_servers directory relative to current file or project root
            current_file = Path(__file__).resolve()
            # Go up from agent/ to mcp-bench/ to mcp_servers/
            possible_paths = [
                current_file.parent.parent / "mcp_servers",  # mcp-bench/mcp_servers
                Path("mcp_servers"),  # Current working directory
                Path("mcp-bench/mcp_servers"),  # From project root
            ]
            for path in possible_paths:
                if path.exists():
                    mcp_servers_dir = str(path)
                    break
            else:
                raise ValueError("Could not find mcp_servers directory. Please specify mcp_servers_dir parameter.")
        
        self.mcp_servers_dir = Path(mcp_servers_dir).resolve()
        if not self.mcp_servers_dir.exists():
            raise ValueError(f"MCP servers directory not found: {mcp_servers_dir}")
        
        # Cache for discovered tools per server
        self._tool_cache: Dict[str, Dict[str, Any]] = {}
        
        # Server name mappings (directory name -> server name)
        self._server_name_mapping = self._build_server_name_mapping()
    
    def _build_server_name_mapping(self) -> Dict[str, str]:
        """Build mapping from directory names to server names."""
        # Common mappings based on directory structure
        mapping = {
            "wikipedia-mcp": "Wikipedia",
            "mcp-server-nationalparks": "National Parks",
            "unit-converter-mcp": "Unit Converter",
            "weather_mcp": "Weather Data",
            "math-mcp": "Math MCP",
            "time-mcp": "Time MCP",
            "huggingface-mcp-server": "Hugging Face",
            "metmuseum-mcp": "Metropolitan Museum",
            "mcp-google-map": "Google Maps",
            "openapi-mcp-server": "OpenAPI Explorer",
            "biomcp": "BioMCP",
            "bibliomantic-mcp-server": "Bibliomantic",
            "context7-mcp": "Context7",
            "dexpaprika-mcp": "DEX Paprika",
            "fruityvice-mcp": "FruityVice",
            "game-trends-mcp": "Game Trends",
            "hugeicons-mcp-server": "Huge Icons",
            "mcp-nixos": "NixOS",
            "mcp-osint-server": "OSINT Intelligence",
            "mcp-reddit": "Reddit",
            "nasa-mcp": "NASA Data",
            "okx-mcp": "OKX Exchange",
            "paper-search-mcp": "Paper Search",
            "scientific_computation_mcp": "Scientific Computing",
            "car-price-mcp-main": "Car Price Evaluator",
            "call-for-papers-mcp": "Call for Papers",
            "medcalc": "Medical Calculator",
            "movie-recommender-mcp": "Movie Recommender",
        }
        return mapping
    
    def discover_tools_for_task(self, task: str, server_manager: Any = None) -> Dict[str, Any]:
        """
        Discover tools dynamically based on task requirements.
        
        Args:
            task: Task description to analyze for relevant servers
            server_manager: Optional server manager for connection info
            
        Returns:
            Dictionary of discovered tools in format: {"ServerName:tool_name": {...}}
        """
        logger.info(f"Discovering tools dynamically for task: {task[:100]}...")
        
        # Analyze task to find relevant servers
        relevant_servers = self._identify_relevant_servers(task)
        logger.info(f"Identified {len(relevant_servers)} relevant servers: {relevant_servers}")
        
        # Discover tools from relevant servers
        all_tools = {}
        for server_dir in relevant_servers:
            server_name = self._server_name_mapping.get(server_dir, server_dir.replace("-", " ").title())
            tools = self._discover_server_tools(server_dir, server_name)
            all_tools.update(tools)
        
        logger.info(f"Discovered {len(all_tools)} tools from {len(relevant_servers)} servers")
        return all_tools
    
    def _identify_relevant_servers(self, task: str) -> List[str]:
        """
        Analyze task to identify which servers might be relevant.
        
        Args:
            task: Task description
            
        Returns:
            List of server directory names
        """
        task_lower = task.lower()
        relevant_servers = []
        
        # Keyword-based server matching
        server_keywords = {
            "wikipedia-mcp": ["wikipedia", "wiki", "article", "encyclopedia"],
            "mcp-server-nationalparks": ["national park", "park", "campground", "visitor center"],
            "unit-converter-mcp": ["convert", "unit", "temperature", "length", "weight", "volume"],
            "weather_mcp": ["weather", "forecast", "temperature", "rain", "snow", "climate"],
            "math-mcp": ["math", "calculate", "statistics", "arithmetic", "equation"],
            "time-mcp": ["time", "timezone", "date", "clock", "calendar"],
            "huggingface-mcp-server": ["hugging face", "model", "ai model", "transformer"],
            "metmuseum-mcp": ["museum", "art", "metropolitan", "artwork", "collection"],
            "mcp-google-map": ["map", "location", "geocode", "directions", "place", "address"],
            "openapi-mcp-server": ["api", "openapi", "endpoint", "rest api"],
            "biomcp": ["biology", "gene", "protein", "disease", "biomedical"],
            "nasa-mcp": ["nasa", "space", "astronomy", "planet", "satellite"],
            "mcp-reddit": ["reddit", "subreddit", "post", "comment"],
            "paper-search-mcp": ["paper", "research", "publication", "academic"],
            "scientific_computation_mcp": ["scientific", "computation", "numerical", "simulation"],
        }
        
        for server_dir, keywords in server_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                relevant_servers.append(server_dir)
        
        # If no servers found, include common ones as fallback
        if not relevant_servers:
            logger.info("No specific servers identified, using common servers as fallback")
            relevant_servers = ["wikipedia-mcp", "unit-converter-mcp", "math-mcp"]
        
        return relevant_servers
    
    def _discover_server_tools(self, server_dir: str, server_name: str) -> Dict[str, Any]:
        """
        Discover tools from a specific server directory.
        
        Args:
            server_dir: Server directory name
            server_name: Display name for the server
            
        Returns:
            Dictionary of tools in format: {"ServerName:tool_name": {...}}
        """
        # Check cache first
        cache_key = f"{server_dir}:{server_name}"
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]
        
        server_path = self.mcp_servers_dir / server_dir
        if not server_path.exists():
            logger.warning(f"Server directory not found: {server_path}")
            return {}
        
        tools = {}
        
        # Try Python servers first (FastMCP)
        python_tools = self._discover_python_tools(server_path, server_name)
        tools.update(python_tools)
        
        # Try TypeScript/JavaScript servers
        if not python_tools:
            ts_tools = self._discover_typescript_tools(server_path, server_name)
            tools.update(ts_tools)
        
        # Cache results
        self._tool_cache[cache_key] = tools
        
        return tools
    
    def _discover_python_tools(self, server_path: Path, server_name: str) -> Dict[str, Any]:
        """Discover tools from Python server files (FastMCP pattern)."""
        tools = {}
        
        # Find Python server files
        python_files = list(server_path.rglob("server.py")) + \
                      list(server_path.rglob("*_server.py")) + \
                      list(server_path.rglob("*.py"))
        
        for py_file in python_files:
            # Skip test files and __pycache__
            if "test" in str(py_file) or "__pycache__" in str(py_file):
                continue
            
            try:
                file_tools = self._parse_python_tools(py_file, server_name)
                tools.update(file_tools)
            except Exception as e:
                logger.debug(f"Error parsing {py_file}: {e}")
                continue
        
        return tools
    
    def _parse_python_tools(self, py_file: Path, server_name: str) -> Dict[str, Any]:
        """Parse Python file for FastMCP tool definitions."""
        tools = {}
        
        try:
            content = py_file.read_text(encoding='utf-8')
        except Exception as e:
            logger.debug(f"Error reading {py_file}: {e}")
            return tools
        
        # Pattern 1: @server.tool() or @app.tool() decorator
        # Look for function definitions with @server.tool() or @app.tool()
        tool_pattern = r'@(?:server|app)\.tool\(\)\s*\n\s*def\s+(\w+)\s*\([^)]*\)\s*->[^:]*:\s*"""(.*?)"""'
        matches = re.finditer(tool_pattern, content, re.DOTALL | re.MULTILINE)
        
        for match in matches:
            tool_name = match.group(1)
            description = match.group(2).strip()
            
            # Try to extract parameters from function signature
            func_match = re.search(rf'def\s+{tool_name}\s*\(([^)]*)\)', content)
            input_schema = self._infer_python_schema(func_match.group(1) if func_match else "", description)
            
            tool_key = f"{server_name}:{tool_name}"
            tools[tool_key] = {
                "name": tool_name,
                "server": server_name,
                "description": description,
                "input_schema": input_schema
            }
        
        # Pattern 2: FastMCP with types.Tool definitions
        # Look for types.Tool(...) definitions
        tool_def_pattern = r'types\.Tool\s*\(\s*name\s*=\s*["\'](\w+)["\']\s*,\s*description\s*=\s*["\']([^"\']+)["\']'
        matches = re.finditer(tool_def_pattern, content, re.DOTALL)
        
        for match in matches:
            tool_name = match.group(1)
            description = match.group(2).strip()
            
            # Try to find inputSchema
            schema_match = re.search(
                rf'name\s*=\s*["\']{tool_name}["\'][^)]*inputSchema\s*=\s*(\{{[^}}]+\}})', 
                content, 
                re.DOTALL
            )
            input_schema = {}
            if schema_match:
                try:
                    input_schema = json.loads(schema_match.group(1))
                except:
                    pass
            
            tool_key = f"{server_name}:{tool_name}"
            tools[tool_key] = {
                "name": tool_name,
                "server": server_name,
                "description": description,
                "input_schema": input_schema
            }
        
        return tools
    
    def _infer_python_schema(self, params_str: str, description: str) -> Dict[str, Any]:
        """Infer JSON schema from Python function parameters."""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        if not params_str:
            return schema
        
        # Parse parameters
        params = [p.strip() for p in params_str.split(',') if p.strip()]
        
        for param in params:
            # Skip self/cls
            if param in ['self', 'cls']:
                continue
            
            # Parse parameter (handle type hints and defaults)
            # Examples: "query: str", "limit: int = 10", "value: float"
            param_match = re.match(r'(\w+)(?::\s*(\w+))?(?:\s*=\s*[^,]+)?', param)
            if param_match:
                param_name = param_match.group(1)
                param_type = param_match.group(2) if param_match.group(2) else "string"
                
                # Map Python types to JSON schema types
                type_mapping = {
                    "str": "string",
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "object"
                }
                json_type = type_mapping.get(param_type.lower(), "string")
                
                schema["properties"][param_name] = {
                    "type": json_type,
                    "description": f"Parameter {param_name}"
                }
                
                # If no default value, mark as required
                if '=' not in param:
                    schema["required"].append(param_name)
        
        return schema
    
    def _discover_typescript_tools(self, server_path: Path, server_name: str) -> Dict[str, Any]:
        """Discover tools from TypeScript/JavaScript server files."""
        tools = {}
        
        # Find TypeScript/JavaScript server files
        ts_files = list(server_path.rglob("server.ts")) + \
                   list(server_path.rglob("index.ts")) + \
                   list(server_path.rglob("*.ts"))
        
        js_files = list(server_path.rglob("server.js")) + \
                   list(server_path.rglob("index.js")) + \
                   list(server_path.rglob("*.js"))
        
        for ts_file in ts_files + js_files:
            # Skip test files and node_modules
            if "test" in str(ts_file) or "node_modules" in str(ts_file):
                continue
            
            try:
                file_tools = self._parse_typescript_tools(ts_file, server_name)
                tools.update(file_tools)
            except Exception as e:
                logger.debug(f"Error parsing {ts_file}: {e}")
                continue
        
        return tools
    
    def _parse_typescript_tools(self, ts_file: Path, server_name: str) -> Dict[str, Any]:
        """Parse TypeScript/JavaScript file for MCP SDK tool definitions."""
        tools = {}
        
        try:
            content = ts_file.read_text(encoding='utf-8')
        except Exception as e:
            logger.debug(f"Error reading {ts_file}: {e}")
            return tools
        
        # Pattern: tools array in setRequestHandler(ListToolsRequestSchema, ...)
        # Look for: tools: [{ name: "...", description: "...", inputSchema: {...} }]
        tools_array_pattern = r'tools\s*:\s*\[(.*?)\]'
        tools_match = re.search(tools_array_pattern, content, re.DOTALL)
        
        if tools_match:
            tools_str = tools_match.group(1)
            
            # Extract individual tool definitions
            # Pattern: { name: "...", description: "...", inputSchema: {...} }
            tool_pattern = r'\{\s*name\s*:\s*["\'](\w+)["\']\s*,\s*description\s*:\s*["\']([^"\']+)["\']'
            tool_matches = re.finditer(tool_pattern, tools_str, re.DOTALL)
            
            for tool_match in tool_matches:
                tool_name = tool_match.group(1)
                description = tool_match.group(2).strip()
                
                # Try to find inputSchema for this tool
                # Look for inputSchema after the tool name
                schema_start = tool_match.end()
                schema_match = re.search(
                    r'inputSchema\s*:\s*(\{[^}]+\})',
                    tools_str[schema_start:schema_start+500],
                    re.DOTALL
                )
                input_schema = {}
                if schema_match:
                    try:
                        # Try to parse as JSON (may need cleaning)
                        schema_str = schema_match.group(1)
                        # Replace single quotes with double quotes for JSON
                        schema_str = schema_str.replace("'", '"')
                        input_schema = json.loads(schema_str)
                    except:
                        pass
                
                tool_key = f"{server_name}:{tool_name}"
                tools[tool_key] = {
                    "name": tool_name,
                    "server": server_name,
                    "description": description,
                    "input_schema": input_schema
                }
        
        return tools
    
    def get_all_available_servers(self) -> List[str]:
        """Get list of all available server directories."""
        if not self.mcp_servers_dir.exists():
            return []
        
        servers = []
        for item in self.mcp_servers_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                servers.append(item.name)
        
        return sorted(servers)
    
    def discover_all_tools(self) -> Dict[str, Any]:
        """
        Discover all tools from all available servers.
        
        Returns:
            Dictionary of all discovered tools
        """
        all_tools = {}
        servers = self.get_all_available_servers()
        
        for server_dir in servers:
            server_name = self._server_name_mapping.get(server_dir, server_dir.replace("-", " ").title())
            tools = self._discover_server_tools(server_dir, server_name)
            all_tools.update(tools)
        
        return all_tools

