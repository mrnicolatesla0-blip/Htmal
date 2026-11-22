# Bharat Market Data

A market-data dashboard for Indian listed equities. This is a data/education project, not a broker and not investment advice.

## What is real, and what is not
- The application does **not** generate sample prices or pretend that demo values are live.
- It requests quotes from a market-data provider configured by the operator.
- Live NSE/BSE data requires a provider subscription and the relevant exchange data-display permissions. The provider's API format must be connected in `backend/provider.py`.
- Until a provider is configured, the API deliberately returns HTTP 503 rather than fabricated market prices.

## Run locally
1. Create a Python virtual environment.
2. Install `requirements.txt`.
3. Copy `.env.example` to `.env` and configure the provider only after an authorised data subscription is in place.
4. Run: `uvicorn backend.main:app --reload`
5. Open `http://127.0.0.1:8000`.

Never commit API keys, passwords, broker credentials, or `.env` files.

## Provider adapter contract
Implement `fetch_quotes(symbols)` in `backend/provider.py` for the selected licensed provider. Return:
```json
{
  "quotes": [
    {
      "symbol": "RELIANCE",
      "exchange": "NSE",
      "ltp": 0,
      "change": 0,
      "change_percent": 0,
      "volume": 0,
      "timestamp": "2026-01-01T09:15:00+05:30"
    }
  ]
}
```
Replace the zeroes with actual provider values; never use these example numbers as market data.

## Scope
This first version is read-only: quotes and watchlist display only. It does not place orders, hold funds, or connect to a trading account. Any future regulated functionality needs qualified adult oversight and appropriate legal/compliance review.
