import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.main import app


def make_pdf(num_pages: int = 1, width: float = 200, height: float = 200) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=width, height=height)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture()
def single_page_pdf() -> bytes:
    return make_pdf(1)


@pytest.fixture()
def three_page_pdf() -> bytes:
    return make_pdf(3)


@pytest.fixture()
def client(isolated_db) -> TestClient:
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_merge_pdfs(client: TestClient, single_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/merge",
        files=[
            ("files", ("a.pdf", single_page_pdf, "application/pdf")),
            ("files", ("b.pdf", single_page_pdf, "application/pdf")),
        ],
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) == 2


def test_merge_requires_two_files(client: TestClient, single_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/merge",
        files=[("files", ("a.pdf", single_page_pdf, "application/pdf"))],
    )
    assert response.status_code == 400
    assert "two" in response.json()["detail"].lower()


def test_split_single_range_returns_pdf(client: TestClient, three_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/split",
        params={"pages": "1-2"},
        files={"file": ("doc.pdf", three_page_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) == 2


def test_split_all_returns_zip(client: TestClient, three_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/split",
        params={"pages": "all"},
        files={"file": ("doc.pdf", three_page_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.content[:2] == b"PK"


def test_split_invalid_pages(client: TestClient, single_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/split",
        params={"pages": "5"},
        files={"file": ("doc.pdf", single_page_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "out of bounds" in response.json()["detail"].lower()


def test_compress_pdf(client: TestClient, single_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/compress",
        files={"file": ("doc.pdf", single_page_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) == 1


def test_watermark_pdf(client: TestClient, single_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/watermark",
        params={"text": "CONFIDENTIAL", "position": "center"},
        files={"file": ("doc.pdf", single_page_pdf, "application/pdf")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) == 1


def test_watermark_requires_text(client: TestClient, single_page_pdf: bytes):
    response = client.post(
        "/v1/pdf/watermark",
        params={"text": "   "},
        files={"file": ("doc.pdf", single_page_pdf, "application/pdf")},
    )
    assert response.status_code == 400
    assert "text" in response.json()["detail"].lower()


def test_corrupt_pdf_rejected(client: TestClient):
    response = client.post(
        "/v1/pdf/compress",
        files={"file": ("bad.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower() or "corrupt" in response.json()["detail"].lower()


def test_file_size_limit(client: TestClient, single_page_pdf: bytes, monkeypatch):
    monkeypatch.setattr("app.config.settings.max_pdf_bytes", 10)
    response = client.post(
        "/v1/pdf/compress",
        files={"file": ("doc.pdf", single_page_pdf, "application/pdf")},
    )
    assert response.status_code == 413
    assert "maximum size" in response.json()["detail"].lower()


def test_non_pdf_extension_rejected(client: TestClient):
    response = client.post(
        "/v1/pdf/compress",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "pdf" in response.json()["detail"].lower()
