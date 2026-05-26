import os, requests
from mcp.types import CallToolResult
MCP_GATEWAY = os.environ["MCP_GATEWAY"] if "MCP_GATEWAY" in os.environ else "http://host.docker.internal:8080" # e.g. http://host.docker.internal:8080

def mcp_call_http(name: str, args: dict) -> dict:
    # Call the MCP gateway server to execute the tool
    r = requests.post(f"{MCP_GATEWAY}/mcp/call", json={"name": name, "args": args, "timeout_s": 30}, timeout=35)
    # Raise an exception if the request failed
    r.raise_for_status()
    
    # Unpacking CallToolResult from serialized response
    tool_response = CallToolResult(**r.json())
    
    # Check for errors and raise exception if present
    if tool_response.isError:
        # Extract error message from content (TextContent) or structuredContent
        error_msg = None
        if tool_response.content:
            # Try to get text from content blocks
            for block in tool_response.content:
                if hasattr(block, 'text') and block.text:
                    error_msg = block.text
                    break
        # Fallback to structuredContent if content didn't have text
        if not error_msg and tool_response.structuredContent:
            error_msg = tool_response.structuredContent.get('error', 'Unknown error')
        # Final fallback
        if not error_msg:
            error_msg = 'Tool execution failed'
        raise RuntimeError(error_msg) # This will be caught by the executor and logged as an error
    
    # Return structuredContent for successful calls
    return tool_response.structuredContent
