from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers.v1 import router as v1_router
from app.services.keys import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Self-serve PDF API: merge, split, compress, and watermark PDF files. "
        "Metered API keys with monthly usage limits."
    ),
    lifespan=lifespan,
)

app.include_router(v1_router)

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.app_version}


@app.get("/")
async def landing() -> FileResponse:
    index = DOCS_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return FileResponse(__file__)  # fallback; should not happen


if DOCS_DIR.exists():
    app.mount("/static", StaticFiles(directory=DOCS_DIR), name="static")
