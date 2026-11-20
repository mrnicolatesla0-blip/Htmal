"""AMFP measurement analysis API.

Accepts user-authorized measurement metadata and returns mathematical
features plus robust baseline anomaly flags. It does not receive RF samples.
"""
import os
import secrets
from statistics import median
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="AMFP Signal Analysis API",
    version="1.0.0",
    description="Mathematical analysis of supplied wireless measurement metadata.",
)


class Measurement(BaseModel):
    timestamp: Optional[str] = Field(default=None, max_length=64)
    signal_dbm: Optional[float] = Field(default=None, ge=-160, le=0)
    rsrp_dbm: Optional[float] = Field(default=None, ge=-160, le=0)
    rsrq_db: Optional[float] = Field(default=None, ge=-50, le=20)
    sinr_db: Optional[float] = Field(default=None, ge=-50, le=100)
    center_frequency_hz: Optional[float] = Field(default=None, gt=0, le=100_000_000_000)
    peak_frequency_hz: Optional[float] = Field(default=None, gt=0, le=100_000_000_000)
    bandwidth_hz: Optional[float] = Field(default=None, gt=0, le=10_000_000_000)
    sample_rate_hz: Optional[float] = Field(default=None, gt=0, le=10_000_000_000)


class AnalyzeRequest(BaseModel):
    current: Measurement
    baseline: list[Measurement] = Field(default_factory=list, max_length=200)


def require_api_key(x_amfp_api_key: Optional[str] = Header(default=None)):
    expected = os.getenv("AMFP_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Backend is not configured. Set AMFP_API_KEY before accepting analysis requests.",
        )
    if not x_amfp_api_key or not secrets.compare_digest(x_amfp_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def robust_limit(values: list[float]) -> tuple[float, float]:
    """Return median and a conservative MAD-based deviation threshold."""
    center = median(values)
    mad = median([abs(value - center) for value in values])
    # 1.4826 * MAD estimates standard deviation for normally distributed data.
    # A minimum threshold avoids flagging tiny measurement jitter.
    return center, max(3.0 * 1.4826 * mad, 3.0)


def analyze_metric(name: str, current_value: Optional[float],
                   baseline_values: list[Optional[float]]) -> dict:
    values = [v for v in baseline_values if v is not None]
    if current_value is None:
        return {"value": None, "status": "unavailable"}
    if len(values) < 5:
        return {
            "value": current_value,
            "status": "baseline_insufficient",
            "baseline_count": len(values),
        }

    center, threshold = robust_limit(values)
    deviation = abs(current_value - center)
    return {
        "value": current_value,
        "baseline_median": round(center, 3),
        "absolute_deviation": round(deviation, 3),
        "threshold": round(threshold, 3),
        "status": "unusual" if deviation > threshold else "normal",
        "baseline_count": len(values),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "AMFP", "version": "1.0.0"}


@app.post("/v1/analyze", dependencies=[Depends(require_api_key)])
def analyze(request: AnalyzeRequest):
    current = request.current
    baseline = request.baseline

    metrics = {
        "signal_dbm": analyze_metric(
            "signal_dbm", current.signal_dbm, [m.signal_dbm for m in baseline]
        ),
        "rsrp_dbm": analyze_metric(
            "rsrp_dbm", current.rsrp_dbm, [m.rsrp_dbm for m in baseline]
        ),
        "rsrq_db": analyze_metric(
            "rsrq_db", current.rsrq_db, [m.rsrq_db for m in baseline]
        ),
        "sinr_db": analyze_metric(
            "sinr_db", current.sinr_db, [m.sinr_db for m in baseline]
        ),
    }

    features = {}
    if current.center_frequency_hz is not None and current.peak_frequency_hz is not None:
        features["frequency_offset_hz"] = (
            current.peak_frequency_hz - current.center_frequency_hz
        )
    if current.bandwidth_hz is not None and current.sample_rate_hz is not None:
        features["bandwidth_ratio_ppm"] = (
            current.bandwidth_hz / current.sample_rate_hz * 1_000_000
        )

    unusual = [name for name, result in metrics.items()
               if result["status"] == "unusual"]

    return {
        "project": "AMFP",
        "features": features,
        "metrics": metrics,
        "anomaly": {
            "detected": bool(unusual),
            "unusual_metrics": unusual,
            "interpretation": (
                "Measurement differs from the supplied baseline; investigate context."
                if unusual else
                "No unusual change detected in metrics with sufficient baseline."
            ),
        },
        "disclaimer": (
            "An anomaly is not proof of an attack. Network handovers, mobility, "
            "buildings, interference, and device differences can change measurements."
        ),
    }
