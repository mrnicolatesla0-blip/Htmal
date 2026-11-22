from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .nse_client import NSE_SERVERS, call_nse_tool, list_nse_tools

app = FastAPI(title="Bharat Market Data API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ToolCall(BaseModel):
    server: str = Field(pattern="^(live|history)$")
    name: str = Field(min_length=1, max_length=120)
    arguments: dict = Field(default_factory=dict)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "provider": "official_nse_mcp",
        "coverage": "NSE cash-market tools; see tool catalogue",
        "trading": False,
    }


@app.get("/api/nse/tools")
async def nse_tools(server: str = Query("live", pattern="^(live|history)$")):
    try:
        tools = await list_nse_tools(server)
        return {"server": server, "count": len(tools), "tools": tools}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NSE tool discovery failed: {type(exc).__name__}")


@app.post("/api/nse/call")
async def nse_call(request: ToolCall):
    try:
        result = await call_nse_tool(request.server, request.name, request.arguments)
        return {"server": request.server, "tool": request.name, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NSE request failed: {type(exc).__name__}")


@app.get("/")
def home():
    from fastapi.responses import FileResponse
    from pathlib import Path
    return FileResponse(Path(__file__).parent.parent / "frontend" / "index.html")
