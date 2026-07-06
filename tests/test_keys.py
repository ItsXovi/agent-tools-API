import io
import sqlite3
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.config import settings
from app.services.keys import TIER_LIMITS


def make_pdf(num_pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_invalid_api_key_rejected(client: TestClient, require_auth):
    client.headers["X-API-Key"] = "atk_invalid_key"
    response = client.post(
        "/v1/pdf/compress",
        files={"file": ("doc.pdf", make_pdf(), "application/pdf")},
    )
    assert response.status_code == 401


def test_missing_api_key_rejected(client: TestClient, require_auth):
    response = client.post(
        "/v1/pdf/compress",
        files={"file": ("doc.pdf", make_pdf(), "application/pdf")},
    )
    assert response.status_code == 401


def test_valid_api_key_accepted(authed_client: TestClient):
    response = authed_client.post(
        "/v1/pdf/compress",
        files={"file": ("doc.pdf", make_pdf(), "application/pdf")},
    )
    assert response.status_code == 200


def test_usage_increment_and_headers(authed_client: TestClient):
    response = authed_client.post(
        "/v1/pdf/compress",
        files={"file": ("doc.pdf", make_pdf(), "application/pdf")},
    )
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == str(TIER_LIMITS["free"])
    assert response.headers["X-RateLimit-Remaining"] == str(TIER_LIMITS["free"] - 1)
    assert "X-RateLimit-Reset" in response.headers

    usage = authed_client.get("/v1/usage").json()
    assert usage["conversions_used"] == 1
    assert usage["limit"] == TIER_LIMITS["free"]
    assert usage["tier"] == "free"


def test_429_when_over_limit(client: TestClient, require_auth, api_key: str, isolated_db: str):
    conn = sqlite3.connect(isolated_db)
    row = conn.execute("SELECT id FROM api_keys LIMIT 1").fetchone()
    assert row is not None
    key_id = row[0]
    period = datetime.now(UTC).strftime("%Y-%m")
    conn.execute(
        "INSERT INTO usage (key_id, period, conversions) VALUES (?, ?, ?)",
        (key_id, period, TIER_LIMITS["free"]),
    )
    conn.commit()
    conn.close()

    client.headers["X-API-Key"] = api_key
    response = client.post(
        "/v1/pdf/compress",
        files={"file": ("doc.pdf", make_pdf(), "application/pdf")},
    )
    assert response.status_code == 429
    assert response.headers["X-RateLimit-Remaining"] == "0"


def test_get_usage(authed_client: TestClient):
    response = authed_client.get("/v1/usage")
    assert response.status_code == 200
    data = response.json()
    assert data["conversions_used"] == 0
    assert data["limit"] == TIER_LIMITS["free"]
    assert data["reset_at"]
    assert data["label"] == "test"


def test_create_key_endpoint(client: TestClient, require_auth):
    response = client.post(
        "/v1/keys",
        headers={"X-Admin-Secret": settings.admin_secret},
        json={"label": "ci-key", "tier": "indie"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["api_key"].startswith("atk_")
    assert data["tier"] == "indie"
    assert data["limit"] == TIER_LIMITS["indie"]

    compress = client.post(
        "/v1/pdf/compress",
        headers={"X-API-Key": data["api_key"]},
        files={"file": ("doc.pdf", make_pdf(), "application/pdf")},
    )
    assert compress.status_code == 200
