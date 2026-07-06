from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.keys import create_api_key, init_db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch) -> Generator[str, None, None]:
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(settings, "database_path", str(db_path))
    init_db()
    yield str(db_path)


@pytest.fixture(autouse=True)
def auth_off_by_default(monkeypatch) -> None:
    """Keep legacy tests working even if REQUIRE_API_KEY is set in the shell."""
    monkeypatch.setattr(settings, "require_api_key", False)
    monkeypatch.setattr(settings, "admin_secret", "")


@pytest.fixture()
def require_auth(monkeypatch) -> None:
    monkeypatch.setattr(settings, "require_api_key", True)
    monkeypatch.setattr(settings, "admin_secret", "test-admin-secret")


@pytest.fixture()
def api_key(require_auth) -> str:
    raw_key, _ = create_api_key(label="test", tier="free")
    return raw_key


@pytest.fixture()
def client(isolated_db) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def authed_client(client: TestClient, api_key: str) -> TestClient:
    client.headers.update({"X-API-Key": api_key})
    return client
