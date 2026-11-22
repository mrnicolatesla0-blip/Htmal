from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .provider import ProviderNotConfigured, fetch_quotes

app = FastAPI(title="Bharat Market Data API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "provider": "not_configured"}


@app.get("/api/market/quotes")
def quotes(symbols: str = Query("RELIANCE,TCS,INFY,HDFCBANK,SBIN")):
    requested = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not requested or len(requested) > 50:
        raise HTTPException(status_code=400, detail="Supply between 1 and 50 symbols.")
    try:
        result = fetch_quotes(requested)
    except ProviderNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Market-data provider request failed.")
    if not isinstance(result, dict) or not isinstance(result.get("quotes"), list):
        raise HTTPException(status_code=502, detail="Provider returned an invalid quote payload.")
    return {
        "source": "configured_market_data_provider",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "quotes": result["quotes"],
    }


@app.get("/")
def home():
    from fastapi.responses import FileResponse
    from pathlib import Path
    return FileResponse(Path(__file__).parent.parent / "frontend" / "index.html")
