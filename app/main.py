import logging
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.api import router as api_router
from app.core.auth import require_admin
from app.core.embedder import get_model
from app.core.logger_setup import setup
from app.db.db import DataBase
from app.db.requests import DocumentRepo

setup()
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"


async def refresh_index(app: FastAPI):
    docs = await app.state.repo.all()
    if docs:
        matrix = np.asarray([d["embedding"] for d in docs], dtype=np.float32)
    else:
        matrix = np.zeros((0, 0), dtype=np.float32)
    app.state.index = {
        "ids": [d["id"] for d in docs],
        "titles": [d["title"] for d in docs],
        "contents": [d["content"] for d in docs],
        "blocks": [d.get("block") for d in docs],
        "matrix": matrix,
    }
    logger.info("Индекс обновлён: %d документов", len(docs))


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = DataBase()
    await db.create_pool()
    app.state.db = db
    app.state.repo = DocumentRepo(db)
    app.state.refresh_index = lambda: refresh_index(app)
    get_model()
    await refresh_index(app)
    yield
    await db.close()


app = FastAPI(title="Semantic Search", lifespan=lifespan)
app.include_router(api_router)


@app.get("/admin", include_in_schema=False)
async def admin_page(_: str = Depends(require_admin)):
    return FileResponse(TEMPLATES_DIR / "admin.html")


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
