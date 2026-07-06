from __future__ import annotations

import hashlib
import secrets
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from app.config import settings

Tier = Literal["free", "indie", "team"]

TIER_LIMITS: dict[Tier, int] = {
    "free": 50,
    "indie": 2000,
    "team": 10000,
}

METERED_PATHS = frozenset(
    {
        "/v1/pdf/merge",
        "/v1/pdf/split",
        "/v1/pdf/compress",
        "/v1/pdf/watermark",
    }
)


@dataclass(frozen=True)
class ApiKeyRecord:
    id: str
    label: str | None
    tier: Tier
    limit: int
    conversions_used: int
    reset_at: datetime


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _current_period() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _reset_at() -> datetime:
    now = datetime.now(UTC)
    if now.month == 12:
        return datetime(now.year + 1, 1, 1, tzinfo=UTC)
    return datetime(now.year, now.month + 1, 1, tzinfo=UTC)


def _connect() -> sqlite3.Connection:
    path = Path(settings.database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY,
                key_hash TEXT NOT NULL UNIQUE,
                label TEXT,
                tier TEXT NOT NULL DEFAULT 'free',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS usage (
                key_id TEXT NOT NULL,
                period TEXT NOT NULL,
                conversions INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (key_id, period),
                FOREIGN KEY (key_id) REFERENCES api_keys(id)
            );
            """
        )


def create_api_key(*, label: str | None = None, tier: Tier = "free") -> tuple[str, ApiKeyRecord]:
    if tier not in TIER_LIMITS:
        raise ValueError(f"Invalid tier: {tier}")

    raw_key = f"atk_{secrets.token_urlsafe(32)}"
    key_id = secrets.token_hex(8)
    now = datetime.now(UTC).isoformat()

    with _connect() as conn:
        conn.execute(
            "INSERT INTO api_keys (id, key_hash, label, tier, created_at) VALUES (?, ?, ?, ?, ?)",
            (key_id, _hash_key(raw_key), label, tier, now),
        )

    record = get_key_by_id(key_id)
    assert record is not None
    return raw_key, record


def get_key_by_raw(raw_key: str) -> ApiKeyRecord | None:
    key_hash = _hash_key(raw_key)
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, label, tier FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        ).fetchone()
    if row is None:
        return None
    return _build_record(row["id"], row["label"], row["tier"])


def get_key_by_id(key_id: str) -> ApiKeyRecord | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, label, tier FROM api_keys WHERE id = ?",
            (key_id,),
        ).fetchone()
    if row is None:
        return None
    return _build_record(row["id"], row["label"], row["tier"])


def _build_record(key_id: str, label: str | None, tier: str) -> ApiKeyRecord:
    tier_typed: Tier = tier if tier in TIER_LIMITS else "free"
    period = _current_period()
    with _connect() as conn:
        row = conn.execute(
            "SELECT conversions FROM usage WHERE key_id = ? AND period = ?",
            (key_id, period),
        ).fetchone()
    used = int(row["conversions"]) if row else 0
    return ApiKeyRecord(
        id=key_id,
        label=label,
        tier=tier_typed,
        limit=TIER_LIMITS[tier_typed],
        conversions_used=used,
        reset_at=_reset_at(),
    )


def increment_usage(key_id: str) -> ApiKeyRecord:
    period = _current_period()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO usage (key_id, period, conversions)
            VALUES (?, ?, 1)
            ON CONFLICT(key_id, period) DO UPDATE SET conversions = conversions + 1
            """,
            (key_id, period),
        )
    record = get_key_by_id(key_id)
    assert record is not None
    return record
