import os, requests
import sys
import asyncio
import json
from typing import Any, Optional
from pydantic import BaseModel
import uvicorn

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.mcp_client import get_mcp_client
from costume_mcp_servers import reset_shared_db


async def test_mcp_client():
    """
    Test MCP client initialization and list tools.
    """
    mcp_client = await get_mcp_client()
    await mcp_client.initialize()
    tools = await mcp_client.list_tools("filesystem")
    print(f"list_tools:\n\n {tools} \n\n")
    result = await mcp_client.call_tool(
        server_name="filesystem",
        tool_name="list_directory",
        arguments={"path": "./"}
    )
    print(f"list_directory:\n\n {result} \n\n")

async def test_ce_benchmark_init_cleanup():
    """
    Test code execution benchmark initialization and cleanup.
    """
    from app.benchmarks import CodeExecutionBenchmark
    
    benchmark = CodeExecutionBenchmark()
    
    try:
        # All in one event loop context
        await benchmark.initialize_async()
        result = await benchmark.run_benchmark_async("Your query here")
        print(result)
    finally:
        # Cleanup in the SAME event loop
        await benchmark.cleanup_async()

async def test_tmcp_benchmark_init_cleanup():
    """
    Test traditional MCP benchmark initialization and cleanup.
    """
    from app.benchmarks import TraditionalMCPBenchmark
    
    benchmark = TraditionalMCPBenchmark()
    
    try:
        # All in one event loop context
        await benchmark.initialize_async()
        result = await benchmark.run_benchmark_async("Your query here")
        print(result)
    finally:
        # Cleanup in the SAME event loop
        await benchmark.cleanup_async()

async def test_query_db_with_pydantic():
    """
    Test calling query_db tool with Pydantic object argument.
    
    When a tool expects a Pydantic object, the argument structure must match
    the function parameter name. For query_db(request: QueryRequest), you need:
    {"request": {"query": "...", "inverse": false}}
    """
    
    mcp_client = await get_mcp_client()
    
    # CORRECT: When tool expects Pydantic object, wrap it in parameter name
    # The function signature is: query_db(request: QueryRequest)
    # So arguments must be: {"request": {"query": "...", "inverse": false}}
    result = await mcp_client.call_tool(
        server_name="db_server",
        tool_name="query_db",
        arguments={
            "request": {
                "query": "SELECT * FROM users",
                "inverse": False  # Optional, defaults to False
            }
        }
    )
    print(result)
    
def extract_text(result: Any) -> Optional[str]:
    content = getattr(result, "content", None)
    if not content:
        return None
    texts = [getattr(c, "text", "") for c in content if getattr(c, "text", None)]
    return "\n".join(texts) if texts else None



async def test_add_user_record_and_grant_access_with_pydantic():
    """
    Test calling add_user_record tool with Pydantic object argument.
    """
    
    mcp_client = await get_mcp_client()
    result = await mcp_client.call_tool(
        server_name="db_server",
        tool_name="add_user_record",
        arguments={
            "user": {
                "name": "Alma",
                "role": "Co-Founder",
                "pass_key": "P678371",
            }
        }
    )
    result = result
    print(f"add_user_record result type: {type(result)} \n\n result: \n\n{result} \n\n")
    
    user = result.structuredContent.get("user")
    print(f"user:\n\n {user} \n\n")

    result_grant_access = await mcp_client.call_tool(
        server_name="db_server",
        tool_name="grant_door_access",
        arguments={
            "user": user,
            "door": {
                "code": "A",
                "description": "Main Office"
            }
        }
    )
    print(f"grant_door_access results:\n\n {result_grant_access} \n\n")



if __name__ == "__main__":
    reset_shared_db()
    # asyncio.run(test_query_db_with_pydantic())
    asyncio.run(test_add_user_record_and_grant_access_with_pydantic())
    # test_mcp_call_http()


# Checking tools_bridge.py 
# on terminal run: 
# curl -X GET "http://localhost:8080/health"

# curl -X GET "http://localhost:8080/tools/available"

# curl -X POST "http://localhost:8080/tools/list_directory" \
#   -H "Content-Type: application/json" \
#   -d '{"path": "."}'

# curl -X POST "http://localhost:8080/tools/inspect_csv" \
#   -H "Content-Type: application/json" \
#   -d '{"path": "./data/file.csv"}'

# curl -X POST "http://localhost:8080/tools/read_file" \
#   -H "Content-Type: application/json" \
#   -d '{"path": "./README.md"}'

# # curl -X POST "http://localhost:8080/tools/write_file" \
#   -H "Content-Type: application/json" \
#   -d '{"path": "./output.txt", "content": "Hello World"}'


# Using the tool_bridge from docker with interactive terminal: 
# - Make sure the tool_bridge is running: uv run tools_bridge.py
# Start the conteiner: docker run -it python:3.8 "bash"
# then hit the server using curl with the url 'http://host.docker.internal:8080/tools/list_directory'




# To do:
# - Have to unify the dynamic tools description for both traditional (up front) and the generated servers files description for code exec.
# - remove old irrelevant files from the project, once everything is tied and work properly. (checked)
# - make a single env's for docker image name and gateway route. (checked)
# - make sure everything is documented.
# - create the entire workflow scheme diagram.
