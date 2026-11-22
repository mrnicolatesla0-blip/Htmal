# Bharat Market Data

A read-only Indian market-data explorer connected to the **official NSE-hosted MCP data service**. It does not buy or sell shares and does not connect to a broker.

## Data endpoints

- Current NSE market tools: `https://mcp.nseindia.in/cmmkt/mcp`
- Historical end-of-day tools: `https://mcp.nseindia.in/bhavcopy/cm/mcp`

The backend discovers the tool catalogue from NSE at runtime, displays each tool's description and input schema, and forwards read-only requests to the selected NSE tool. NSE documents these public endpoints as requiring no API key.

## Freshness and coverage

NSE describes intraday data as approximately 1–3 minutes delayed, with no tick-by-tick/order-book feed. The historical service provides end-of-day data. This integration is NSE-only; it does not include all BSE products or every market segment.

## Usage restrictions

NSE states that this MCP data is for informational use and is not for commercial exploitation, real-time trading, investment advice, or commercial deployment. Do not redistribute it or build a commercial product on it without obtaining the required permissions. Read the [official NSE MCP page](https://www.nseindia.in/nse-mcp) and linked terms.

## Run locally

1. Use Python 3.10+.
2. Install dependencies: `pip install -r requirements.txt`.
3. Start the backend: `uvicorn backend.main:app --reload`.
4. Open `http://127.0.0.1:8000`.

The browser communicates with FastAPI; the backend connects to NSE. Do not expose the backend publicly without rate limits, caching, security controls, and a review of NSE's terms.

## API routes

- `GET /api/health`
- `GET /api/nse/tools?server=live`
- `GET /api/nse/tools?server=history`
- `POST /api/nse/call`

No fabricated/sample prices are used. Provider errors are shown instead of invented values.
