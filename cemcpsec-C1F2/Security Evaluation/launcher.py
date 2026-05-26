"""
Application Launcher for MCP Benchmark Dashboard.

This module provides an interactive launcher for the unified MCP Benchmark Dashboard
which includes both single-task and multi-task modes in one FastAPI application.
"""
import sys
import asyncio
import uvicorn
import os
def server_selection():
    from dotenv import set_key, find_dotenv
    from costume_mcp_servers.server_factory import enum_servers
    """Select a server from the list of available MCP threat servers."""
    dotenv_path = find_dotenv()

    print("\nAvailable MCP servers:")
    for i, server in enumerate(enum_servers):
        print(f"  {i + 1}. {server['description']}")
    choice = input("Enter the number of the server you want to use: ").strip()

    if not choice.isdigit():
        print("\nInvalid choice. Please enter a valid number.")
        return server_selection()

    idx = int(choice)
    if idx not in range(1, len(enum_servers) + 1):
        print("\nInvalid choice. Please enter a valid number.")
        return server_selection()

    set_key(dotenv_path, "SERVER_CHOICE", enum_servers[idx - 1]["value"])
    print(f"SERVER_CHOICE: {enum_servers[idx - 1]['value']}")

def print_banner():
    """Print welcome banner."""
    print("=" * 80)
    print("MCP BENCHMARK SYSTEM")
    print("=" * 80)
    print()

def print_menu():
    """Print menu options."""
    print("Choose an option:")
    print()
    print("  1. 🚀 Start MCP Benchmark Dashboard")
    print("     - Unified web interface at: http://localhost:8000")
    print("     - Single Task Mode: Run individual queries")
    print("     - Multiple Tasks Mode: Run batch benchmarks")
    print("     - Real-time comparison charts and analytics")
    print("     - API documentation at: http://localhost:8000/docs")
    print("     - MCP Gateway at: http://localhost:8080")
    print()
    print("  2. 💻 Start MCP Benchmark Dashboard in Dev Mode (sandbox's interactive shell)")
    print("     - Unified web interface at: http://localhost:8000")
    print("     - API documentation at: http://localhost:8000/docs")
    print("     - MCP Gateway at: http://localhost:8080")
    print()
    print("  3. ❌ Exit")
    print()

def start_main_server():
    """
    Start the main FastAPI server (Dashboard).
    
    Configuration:
    - Host: 0.0.0.0 (accessible from network)
    - Port: 8000
    - Reload: False (disabled for multiprocessing)
    - Log level: info
    """
    uvicorn.run(
        app="app.api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )

def start_gateway_server():
    """
    Start the MCP Gateway server.
    
    Configuration:
    - Host: 0.0.0.0 (accessible from network)
    - Port: 8085
    - Reload: False (disabled for multiprocessing)
    - Log level: info
    """
    uvicorn.run(
        app="docker_code.mcp_gateway_server:app",
        host="localhost",
        port=8085,
        reload=False,
        log_level="info"
    )

async def serve(app, host, port):
    config = uvicorn.Config(app, host=host, port=port, loop = "asyncio", lifespan="on", log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def launch(routes_port=8000, gateway_port=8080, dev_mode: bool = False):
    from app.core import get_mcp_client
    global _mcp_client
    _mcp_client = await get_mcp_client()
    try:
        os.environ["DEV_MODE"] = str(dev_mode)
        await asyncio.gather(
            serve("app.api.routes:app", "0.0.0.0", routes_port),
            serve("docker_code.mcp_gateway_server:app", "localhost", gateway_port)
        )
    finally:
        await _mcp_client.close()

def start_dashboard(dev_mode: bool = False):
    """Start the unified FastAPI Dashboard (Main + Gateway with single/multiple task modes)."""
    print("\n" + "=" * 80)
    print("Starting MCP Benchmark Dashboard...")
    print("Dashboard: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("MCP Gateway: http://localhost:8080")
    print("Gateway Docs: http://localhost:8080/docs")
    print("\nFeatures:")
    print("  • Single Task Mode - Run individual queries")
    print("  • Multiple Tasks Mode - Run batch benchmarks")
    print("  • Real-time comparison charts")
    print("Press Ctrl+C to stop")
    print("=" * 80 + "\n")
    
    # Import and run the existing main.py logic (already uses shared MCP client)
    try:
        asyncio.run(launch(dev_mode=dev_mode))
    except KeyboardInterrupt:
        print("\n\nDashboard stopped")

def main():
    """Main launcher function."""
    # Set MCP server choice at launch.
    while True:
        print_banner()
        print_menu()
        
        try:
            choice = input("Enter your choice (1-2): ").strip()
            if choice == "1":
                server_selection() # Setting Threat server handler.
                start_dashboard()
                break
            
            elif choice == "2":
                server_selection()
                start_dashboard(dev_mode=True)
                break

            elif choice == "3":
                print("\nGoodbye! 👋\n")
                sys.exit(0)
                
            else:
                print("\n❌ Invalid choice. Please enter 1, 2 or 3.\n")
                input("Press Enter to continue...")
                print("\n" * 2)
        
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋\n")
            sys.exit(0)
        
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            input("Press Enter to continue...")

if __name__ == "__main__":
    main()

