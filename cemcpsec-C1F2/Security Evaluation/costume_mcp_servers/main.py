# threat_demo_server.py - Main entry point
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from costume_mcp_servers.server_factory import get_handler_server

global handler_server
handler_server = get_handler_server()
print(f"handler_server: {handler_server.name}")
mcp = handler_server.mcp


if __name__ == "__main__":
    mcp.run()