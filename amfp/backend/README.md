# AMFP Cloud Backend

A small FastAPI service that accepts wireless measurement metadata and returns mathematical features plus robust baseline anomaly flags.

## Safety and technical scope

- This API processes measurements supplied by a client. It does not tune a radio, receive RF, or decode cellular traffic.
- An ordinary Android application can read only measurements exposed by Android and the phone manufacturer.
- Cellular metadata availability varies by Android version, modem, carrier, permissions, and location state.
- Never submit call contents, messages, subscriber identifiers, SIM identifiers, or other private communications.
- An anomaly is a statistical difference from a supplied baseline, not proof of an intrusion.

## Run locally

Python 3.10 or newer is recommended.

```bash
cd amfp/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export AMFP_API_KEY="replace-this-with-a-long-random-secret"
uvicorn app:app --host 127.0.0.1 --port 8000
```

On Windows PowerShell, set the key with:

```powershell
$env:AMFP_API_KEY="replace-this-with-a-long-random-secret"
uvicorn app:app --host 127.0.0.1 --port 8000
```

Health check: `GET /health`

Interactive API docs: `http://127.0.0.1:8000/docs`

## Example request

Send `POST /v1/analyze` with header `X-AMFP-API-Key`.

```json
{
  "current": {
    "signal_dbm": -91,
    "rsrp_dbm": -112,
    "rsrq_db": -14,
    "sinr_db": 3
  },
  "baseline": [
    {"signal_dbm": -75, "rsrp_dbm": -95, "rsrq_db": -9, "sinr_db": 18},
    {"signal_dbm": -76, "rsrp_dbm": -96, "rsrq_db": -10, "sinr_db": 17},
    {"signal_dbm": -74, "rsrp_dbm": -94, "rsrq_db": -9, "sinr_db": 19},
    {"signal_dbm": -75, "rsrp_dbm": -95, "rsrq_db": -10, "sinr_db": 18},
    {"signal_dbm": -77, "rsrp_dbm": -97, "rsrq_db": -11, "sinr_db": 16}
  ]
}
```

Example using curl:

```bash
curl -X POST http://127.0.0.1:8000/v1/analyze \
  -H "Content-Type: application/json" \
  -H "X-AMFP-API-Key: $AMFP_API_KEY" \
  -d '{"current":{"signal_dbm":-91,"rsrp_dbm":-112,"rsrq_db":-14,"sinr_db":3},"baseline":[{"signal_dbm":-75,"rsrp_dbm":-95,"rsrq_db":-9,"sinr_db":18},{"signal_dbm":-76,"rsrp_dbm":-96,"rsrq_db":-10,"sinr_db":17},{"signal_dbm":-74,"rsrp_dbm":-94,"rsrq_db":-9,"sinr_db":19},{"signal_dbm":-75,"rsrp_dbm":-95,"rsrq_db":-10,"sinr_db":18},{"signal_dbm":-77,"rsrp_dbm":-97,"rsrq_db":-11,"sinr_db":16}]}'
```

## Deploy with Docker

```bash
docker build -t amfp-api .
docker run --rm -p 8000:8000 -e AMFP_API_KEY="your-long-random-secret" amfp-api
```

For public hosting, use a reputable hosting provider, HTTPS, a strong secret stored in the provider's environment settings, request limits, and access logs that avoid collecting personal identifiers. Do not commit API keys to GitHub.

## Anomaly method

For each available metric, the API compares the current value against the median of the supplied baseline. It calculates median absolute deviation (MAD) and uses a conservative threshold. At least five baseline values are required. Missing metrics remain unavailable rather than being invented.

The initial API analyzes signal strength (dBm), RSRP (dBm), RSRQ (dB), and SINR (dB). Optional frequency and bandwidth fields are used only when actually supplied by a measurement source.
