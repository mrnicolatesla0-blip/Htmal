"""Bounded, offline Bitcoin SHA-256d research benchmark.

This module hashes the authentic Bitcoin Genesis Block header repeatedly for
one second. It does not vary the nonce, search for a valid block, connect to
a node/pool, or submit work to the Bitcoin network.
"""
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Bitcoin Research"])

GENESIS_HEADER_HEX = (
    "01000000"
    + "00" * 32
    + "3ba3edfd7a7b12b27ac72c3e67768f617fc81bc3888a51323a9fb8aa4b1e5e4a"
    + "29ab5f49"
    + "ffff001d"
    + "1dac2b7c"
)
GENESIS_HEADER = bytes.fromhex(GENESIS_HEADER_HEX)
EXPECTED_GENESIS_HASH = (
    "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"
)


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


@router.get("/bitcoin-research")
def bitcoin_research_page():
    page = Path(__file__).parent.parent / "frontend" / "bitcoin_research.html"
    return FileResponse(page)


@router.post("/api/research/sha256d-benchmark")
def sha256d_benchmark():
    # Validate the reference header before starting the timed experiment.
    reference_hash = sha256d(GENESIS_HEADER)[::-1].hex()
    verified = reference_hash == EXPECTED_GENESIS_HASH
    if not verified:
        return {
            "status": "error",
            "verification": "FAIL",
            "message": "Genesis reference hash did not match.",
        }

    count = 0
    started = time.perf_counter()
    deadline = started + 1.0
    last_digest = b""
    while time.perf_counter() < deadline:
        last_digest = sha256d(GENESIS_HEADER)
        count += 1
    elapsed = time.perf_counter() - started

    return {
        "experiment": "sha256d-fixed-header-throughput",
        "status": "completed",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "reference": {
            "name": "Bitcoin Genesis Block header",
            "header_bytes": len(GENESIS_HEADER),
            "header_hex": GENESIS_HEADER_HEX,
            "expected_hash": EXPECTED_GENESIS_HASH,
            "calculated_hash": reference_hash,
            "verified": verified,
        },
        "measurement": {
            "duration_seconds": round(elapsed, 6),
            "hash_calculations": count,
            "hashes_per_second": round(count / elapsed, 2) if elapsed else 0,
            "last_digest_display_order": last_digest[::-1].hex(),
        },
        "scope": {
            "nonce_search": False,
            "bitcoin_node_connected": False,
            "pool_connected": False,
            "network_submissions": 0,
            "description": "Offline repeated hashing of one fixed, verified 80-byte header. This is a throughput benchmark, not Bitcoin mining.",
        },
    }
