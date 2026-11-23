"""Bitcoin research endpoints: offline hashing and read-only public-chain verification."""
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
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
ESPLORA_API = "https://blockstream.info/api"


def sha256d(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def decode_compact_target(bits: int) -> int:
    """Decode Bitcoin's compact nBits target representation."""
    exponent = bits >> 24
    mantissa = bits & 0x007FFFFF
    if bits & 0x00800000 or mantissa == 0:
        raise ValueError("Invalid compact proof-of-work target")
    if exponent <= 3:
        return mantissa >> (8 * (3 - exponent))
    return mantissa << (8 * (exponent - 3))


@router.get("/bitcoin-research")
def bitcoin_research_page():
    page = Path(__file__).parent.parent / "frontend" / "bitcoin_research.html"
    return FileResponse(page)


@router.post("/api/research/sha256d-benchmark")
def sha256d_benchmark():
    """Bounded offline benchmark of the authentic Bitcoin Genesis header."""
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


@router.get("/api/research/bitcoin/network-tip")
async def bitcoin_network_tip():
    """Fetch the current public Bitcoin mainnet tip and verify its header locally.

    This is read-only: it does not connect to a peer-to-peer node, broadcast
    transactions, submit mining shares, or perform nonce search.
    """
    timeout = httpx.Timeout(15.0, connect=8.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            height_response = await client.get(f"{ESPLORA_API}/blocks/tip/height")
            height_response.raise_for_status()
            height_text = height_response.text.strip()
            if not height_text.isdigit():
                raise ValueError("Block explorer returned an invalid tip height")
            height = int(height_text)

            hash_response = await client.get(f"{ESPLORA_API}/blocks/tip/hash")
            hash_response.raise_for_status()
            tip_hash = hash_response.text.strip().lower()
            if len(tip_hash) != 64 or any(c not in "0123456789abcdef" for c in tip_hash):
                raise ValueError("Block explorer returned an invalid tip hash")

            block_response = await client.get(f"{ESPLORA_API}/block/{tip_hash}")
            block_response.raise_for_status()
            block = block_response.json()

            header_response = await client.get(f"{ESPLORA_API}/block/{tip_hash}/header")
            header_response.raise_for_status()
            header_hex = header_response.text.strip()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Public Bitcoin data provider returned HTTP {exc.response.status_code}.",
        )
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not retrieve or parse public Bitcoin block data: {type(exc).__name__}.",
        )

    try:
        header = bytes.fromhex(header_hex)
        if len(header) != 80:
            raise ValueError("Bitcoin block header must be exactly 80 bytes")

        calculated_hash = sha256d(header)[::-1].hex()
        hash_matches = calculated_hash == tip_hash
        header_bits = int.from_bytes(header[72:76], "little")
        api_bits = int(block["bits"])
        if header_bits != api_bits:
            raise ValueError("Block metadata nBits does not match the raw header")
        target = decode_compact_target(header_bits)
        hash_integer = int.from_bytes(sha256d(header), "little")
        meets_target = hash_integer <= target
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not independently verify returned block header: {str(exc)}",
        )

    return {
        "status": "verified" if hash_matches and meets_target else "verification_failed",
        "network": "Bitcoin mainnet",
        "provider": "Blockstream Esplora public API",
        "source_base_url": ESPLORA_API,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "block": {
            "height": height,
            "hash": tip_hash,
            "calculated_hash": calculated_hash,
            "previous_block_hash": block.get("previousblockhash"),
            "timestamp_unix": block.get("timestamp"),
            "transaction_count": block.get("tx_count"),
            "bits": f"{header_bits:08x}",
            "nonce": int.from_bytes(header[76:80], "little"),
            "header_bytes": len(header),
            "header_hex": header_hex,
        },
        "verification": {
            "header_hash_matches_api": hash_matches,
            "proof_of_work_meets_encoded_target": meets_target,
            "target_hex": f"{target:064x}",
            "method": "SHA-256d of the 80-byte header; digest interpreted as a little-endian Bitcoin proof-of-work integer.",
        },
        "scope": {
            "read_only_public_api": True,
            "bitcoin_p2p_node_connected": False,
            "nonce_search": False,
            "mining_pool_connected": False,
            "network_submissions": 0,
        },
    }



@router.get("/bitcoin-wallet-monitor")
def bitcoin_wallet_monitor_page():
    page = Path(__file__).parent.parent / "frontend" / "bitcoin_wallet_monitor.html"
    return FileResponse(page)


@router.get("/api/research/bitcoin/address/{address}")
async def bitcoin_address_monitor(address: str):
    """Read-only public address balance and recent transaction monitor.

    No private keys, wallet generation, signing, broadcasting, or spending.
    """
    address = address.strip()
    base58_ok = re.fullmatch(r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}", address) is not None
    bech32_ok = re.fullmatch(r"bc1[ac-hj-np-z02-9]{11,71}", address.lower()) is not None
    if not (base58_ok or bech32_ok):
        raise HTTPException(status_code=400, detail="Enter a syntactically valid Bitcoin mainnet address.")

    timeout = httpx.Timeout(15.0, connect=8.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            info_response = await client.get(f"{ESPLORA_API}/address/{address}")
            if info_response.status_code == 404:
                raise HTTPException(status_code=404, detail="Address was not found by the public explorer.")
            info_response.raise_for_status()
            info = info_response.json()

            tx_response = await client.get(f"{ESPLORA_API}/address/{address}/txs")
            tx_response.raise_for_status()
            transactions = tx_response.json()
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Public explorer returned HTTP {exc.response.status_code}.")
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail=f"Could not retrieve public address data: {type(exc).__name__}.")

    try:
        chain = info.get("chain_stats") or {}
        mempool = info.get("mempool_stats") or {}
        confirmed_received = int(chain.get("funded_txo_sum", 0))
        confirmed_spent = int(chain.get("spent_txo_sum", 0))
        pending_received = int(mempool.get("funded_txo_sum", 0))
        pending_spent = int(mempool.get("spent_txo_sum", 0))
        recent = []
        for tx in transactions[:25]:
            net_sats = 0
            for output in tx.get("vout", []):
                if output.get("scriptpubkey_address") == address:
                    net_sats += int(output.get("value", 0))
            for txin in tx.get("vin", []):
                prevout = txin.get("prevout") or {}
                if prevout.get("scriptpubkey_address") == address:
                    net_sats -= int(prevout.get("value", 0))
            status = tx.get("status") or {}
            recent.append({
                "txid": tx.get("txid"),
                "confirmed": bool(status.get("confirmed")),
                "block_time": status.get("block_time"),
                "net_sats": net_sats,
                "direction": "incoming" if net_sats > 0 else ("outgoing" if net_sats < 0 else "no net change"),
            })
    except (ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail=f"Public explorer returned unexpected address data: {type(exc).__name__}.")

    confirmed_balance = confirmed_received - confirmed_spent
    mempool_delta = pending_received - pending_spent
    total_balance = confirmed_balance + mempool_delta
    return {
        "status": "ok",
        "network": "Bitcoin mainnet",
        "provider": "Blockstream Esplora public API",
        "address": address,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "balance": {
            "confirmed_sats": confirmed_balance,
            "pending_delta_sats": mempool_delta,
            "total_including_pending_sats": total_balance,
            "confirmed_btc": confirmed_balance / 100_000_000,
            "total_including_pending_btc": total_balance / 100_000_000,
            "confirmed_received_sats": confirmed_received,
            "confirmed_spent_sats": confirmed_spent,
        },
        "transaction_count": {
            "confirmed": int(chain.get("tx_count", 0)),
            "mempool": int(mempool.get("tx_count", 0)),
        },
        "recent_transactions": recent,
        "scope": {
            "public_address_only": True,
            "private_key_requested": False,
            "private_key_stored": False,
            "transaction_signing": False,
            "transaction_broadcasting": False,
            "spending_enabled": False,
        },
    }
