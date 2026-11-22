import os
import httpx
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


TWELVE_DATA_URL = "https://api.twelvedata.com"

def _twelve_data_key():
    key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="USA market data is not configured. Add TWELVE_DATA_API_KEY to Render environment variables.")
    return key

@app.get("/api/us/search")
async def us_search(q: str = Query(..., min_length=1, max_length=80)):
    key = _twelve_data_key()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{TWELVE_DATA_URL}/symbol_search", params={"symbol": q.strip(), "apikey": key, "outputsize": 20})
        data = response.json()
        if response.status_code >= 400 or data.get("status") == "error":
            raise HTTPException(status_code=502, detail=data.get("message", "US symbol search failed."))
        matches = [item for item in data.get("data", []) if item.get("country") in ("United States", "USA", "US")]
        return {"market": "USA", "provider": "Twelve Data", "count": len(matches), "results": matches}
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach the US market-data provider.")

@app.get("/api/us/quote")
async def us_quote(symbol: str = Query(..., min_length=1, max_length=30)):
    key = _twelve_data_key()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(f"{TWELVE_DATA_URL}/quote", params={"symbol": symbol.strip().upper(), "apikey": key})
        data = response.json()
        if response.status_code >= 400 or data.get("status") == "error" or data.get("code"):
            raise HTTPException(status_code=502, detail=data.get("message", "US quote unavailable."))
        return {"market": "USA", "provider": "Twelve Data", "quote": data}
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach the US market-data provider.")
