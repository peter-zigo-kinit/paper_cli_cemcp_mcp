import os, sys
from typing import Any, Dict, Optional, List
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from mcp.types import CallToolResult, TextContent
# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core import get_mcp_client


class CallReq(BaseModel):
    name: str                 # "<server>.<tool>"
    args: Dict[str, Any] = {}
    timeout_s: int = 30

class CallResp(BaseModel):
    ok: bool
    result: Optional[Any] = None
    content_text: Optional[str] = None
    error: Optional[str] = None

def extract_text(result: Any) -> Optional[str]:
    content = getattr(result, "content", None)
    if not content:
        return None
    texts = [getattr(c, "text", "") for c in content if getattr(c, "text", None)]
    return "\n".join(texts) if texts else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _mcp_client
    print("Starting MCP gateway server")
    _mcp_client = await get_mcp_client()
    print(f"MCP gateway server using mcp_client: {_mcp_client} \n")
    yield

app = FastAPI(title="MCP Gateway", version="1.0.0", lifespan=lifespan)

@app.get("/mcp/tools")
async def tools():
    out: List[Dict[str, Any]] = []
    for server in _mcp_client.get_available_servers():
        if not _mcp_client.is_server_connected(server):
            print(f"Server {server} is not connected")
            continue
        tools = await _mcp_client.list_tools(server)
        for t in tools:
            # tool objects vary; use getattr safely
            name = getattr(t, "name", None) or (t.get("name") if isinstance(t, dict) else None)
            desc = getattr(t, "description", None) or (t.get("description") if isinstance(t, dict) else None)
            schema = getattr(t, "inputSchema", None) or (t.get("inputSchema") if isinstance(t, dict) else None)
            out.append({
                "name": f"{server}.{name}",
                "description": desc or "",
                "inputSchema": schema or {},
            })
    return {"tools": out}


@app.post("/mcp/call", response_model=CallToolResult)
async def call_tool(req: CallReq) -> CallToolResult:
    if "." not in req.name:
        raise HTTPException(status_code=400, detail="name must be '<server>.<tool>'")

    server, tool = req.name.split(".", 1)

    async def _call():
        return await _mcp_client.call_tool(server_name=server, tool_name=tool, arguments=req.args)

    try:
        result = await asyncio.wait_for(_call(), timeout=req.timeout_s)
        return result
        
    except asyncio.TimeoutError:
        return CallToolResult(isError=True, 
                              content=[TextContent(type="text", text=f"timeout after {req.timeout_s}s")],
                              structuredContent={'error': f"timeout after {req.timeout_s}s"})

    except Exception as e:
        return CallToolResult(isError=True, 
                              content=[TextContent(type="text", text=str(e))],
                              structuredContent={'error': str(e)})
