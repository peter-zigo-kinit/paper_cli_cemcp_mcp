"""
Integration test for RealMCPOrchestrator.

This test mounts the full application stack:
- MCP client
- Docker executor
- Gateway server

Tests that the orchestrator can successfully execute a user query and return correct results.

Example test case:
- Query: "Retrieve all users that has access to door 'C'."
- Expected result: Only 'Emma' should be returned (not ['Amit', 'John', 'Bjorn', 'Sarah'])

Usage:
    # Run with pytest (requires pytest-asyncio):
    # Install: pip install pytest-asyncio
    pytest app/tests/test_orchestrator_integration.py -v
    
    # Or run directly (no pytest needed):
    python app/tests/test_orchestrator_integration.py

Prerequisites:
    - Docker must be running (for docker executor)
    - MCP servers must be configured in mcp_config.json
    - OpenAI API key must be set in environment or .env file
    - pytest-asyncio (only if running with pytest)
"""
import os
import sys
import asyncio
from typing import Optional

# Optional pytest import (for pytest-asyncio decorator)
import pytest_asyncio
import pytest

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.orchestrator import RealMCPOrchestrator
from costume_mcp_servers import reset_shared_db
from app.config import DOCKER_MCP_GATEWAY
import uvicorn
from urllib.parse import urlparse


# Test configuration
USER_QUERY = "Retrieve all users that has access to door 'C'."
EXPECTED_USER = "Emma"
UNEXPECTED_USERS = ['Amit', 'John', 'Bjorn', 'Sarah']

# Extract gateway port from config
def get_gateway_port():
    """Extract port from DOCKER_MCP_GATEWAY URL."""
    try:
        parsed = urlparse(DOCKER_MCP_GATEWAY)
        port = parsed.port
        if port is None:
            # Default port if not specified
            port = 8080
        return port
    except Exception:
        # Fallback to default port
        return 8080


class GatewayServer:
    """Manages the gateway server lifecycle for testing."""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """
        Start the gateway server in the background.

        This uses the exact same mounting pattern as `launcher.py` / `main.py`:
        we call `main.main(...)`, which:
        - Initializes the shared MCP client
        - Runs both the dashboard API and the MCP gateway via `serve(...)`
        """
        # Import here to avoid circular imports at module level
        from main import main as main_app

        # Start the full app (dashboard + gateway) exactly like launcher.py does
        self.task = asyncio.create_task(
            main_app(routes_port=8000, gateway_port=self.port, dev_mode=False)
        )
        
        # Wait for server to start and verify it's running
        # Allow generous time, as MCP client + servers + Docker can take a bit to spin up.
        max_attempts = 60
        for attempt in range(max_attempts):
            await asyncio.sleep(0.5)
            try:
                import requests
                response = requests.get(f"http://localhost:{self.port}/mcp/tools", timeout=2)
                if response.status_code == 200:
                    print(f"Gateway server started successfully on port {self.port}")
                    return
            except Exception:
                if attempt < max_attempts - 1:
                    continue
                else:
                    raise RuntimeError(f"Failed to start gateway server after {max_attempts} attempts")
    
    async def stop(self):
        """Stop the gateway server."""
        if self.task:
            # Cancel the uvicorn serve task started via main.serve
            if not self.task.done():
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass


# Define the async test function
async def _test_orchestrator_door_access_query_impl():
    """
    Integration test for orchestrator with door access query.
    
    Tests that:
    1. The orchestrator can be initialized with all components
    2. It can execute a query about door access
    3. It returns the correct result (only Emma has access to door 'C')
    """
    gateway = None
    orchestrator = None
    
    try:
        # Step 1: Reset database to ensure clean state
        print("\n" + "=" * 80)
        print("Step 1: Resetting database...")
        print("=" * 80)
        reset_shared_db()
        print("Database reset complete.\n")
        
        # Step 2: Start gateway server
        print("=" * 80)
        print("Step 2: Starting gateway server...")
        print("=" * 80)
        gateway_port = get_gateway_port()
        print(f"Using gateway port: {gateway_port} (from config: {DOCKER_MCP_GATEWAY})")
        gateway = GatewayServer(port=gateway_port)
        await gateway.start()
        
        # Step 3: Initialize orchestrator
        print("\n" + "=" * 80)
        print("Step 3: Initializing orchestrator...")
        print("=" * 80)
        orchestrator = RealMCPOrchestrator()
        await orchestrator.initialize_async()
        print("Orchestrator initialized successfully.\n")
        
        # Step 4: Execute query
        print("=" * 80)
        print(f"Step 4: Executing query: '{USER_QUERY}'")
        print("=" * 80)
        result = await orchestrator.run_multi_turn_code_async(USER_QUERY, max_turns=5)
        
        # Step 5: Verify results
        print("\n" + "=" * 80)
        print("Step 5: Verifying results...")
        print("=" * 80)
        
        # Check that execution was successful
        assert result["success"], f"Query execution failed. Error: {result.get('error', 'Unknown error')}"
        
        # Extract output text
        output = result.get("output", "").strip()
        raw_output = result.get("raw_output", "").strip()
        
        print(f"\nOutput: {output}")
        print(f"Raw output: {raw_output}")
        
        # Combine outputs for checking (check both fields)
        combined_output = f"{output} {raw_output}".lower()
        
        # Check that expected user is in the output
        assert EXPECTED_USER.lower() in combined_output, \
            f"Expected user '{EXPECTED_USER}' not found in output. Output: {output}, Raw output: {raw_output}"
        
        # Check that unexpected users are NOT in the output
        # Use word boundaries to avoid false positives (e.g., "Emma" in "Emmanuel")
        import re
        found_unexpected = []
        for unexpected_user in UNEXPECTED_USERS:
            pattern = r'\b' + re.escape(unexpected_user.lower()) + r'\b'
            if re.search(pattern, combined_output):
                found_unexpected.append(unexpected_user)
        
        assert len(found_unexpected) == 0, \
            f"Unexpected users found in output: {found_unexpected}. Output: {output}, Raw output: {raw_output}"
        
        print(f"\n✓ Test passed! Found '{EXPECTED_USER}' and correctly excluded {UNEXPECTED_USERS}")
        print("=" * 80 + "\n")
        
    finally:
        # Step 6: Cleanup
        print("=" * 80)
        print("Step 6: Cleaning up...")
        print("=" * 80)
        
        if orchestrator:
            try:
                await orchestrator.cleanup_async()
                print("Orchestrator cleaned up.")
            except Exception as e:
                print(f"Error cleaning up orchestrator: {e}")
        
        if gateway:
            try:
                await gateway.stop()
                print("Gateway server stopped.")
            except Exception as e:
                print(f"Error stopping gateway server: {e}")
        
        print("Cleanup complete.\n")


# Create the test function that works with both pytest and direct execution
if HAS_PYTEST and HAS_PYTEST_ASYNCIO:
    # Use pytest-asyncio decorator
    test_orchestrator_door_access_query = pytest.mark.asyncio(_test_orchestrator_door_access_query_impl)
elif HAS_PYTEST:
    # pytest without pytest-asyncio: create a sync wrapper
    def test_orchestrator_door_access_query():
        """Sync wrapper for async test when pytest-asyncio is not available."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(_test_orchestrator_door_access_query_impl())
else:
    # No pytest, use async function directly
    test_orchestrator_door_access_query = _test_orchestrator_door_access_query_impl


if __name__ == "__main__":
    # Run the test directly
    asyncio.run(_test_orchestrator_door_access_query_impl())
