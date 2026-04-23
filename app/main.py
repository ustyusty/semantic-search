# главный файл приложения, тут запускается FastAPI сервер
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# подключаем все наши модули из папки app
from app.api.api import router as api_router
from app.core.auth import require_admin
from app.core.embedder import get_model
from app.core.logger_setup import setup
from app.db.db import DataBase
from app.db.requests import DocumentRepo

# запускаем настройку логгера
setup()
logger = logging.getLogger(__name__)

# тут пути к папкам со статикой и шаблонами
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"


# функция которая обновляет индекс документов (берёт всё из БД и складывает в память)
async def refresh_index(app: FastAPI):
    """Обновляет индекс документов в памяти приложения.

    :param app: Экземпляр FastAPI приложения."""
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


# lifespan - это штука которая выполняется при старте и остановке приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения: инициализация и закрытие ресурсов.

    :param app: Экземпляр FastAPI приложения."""
    db = DataBase()
    await db.create_pool()
    app.state.db = db
    app.state.repo = DocumentRepo(db)
    app.state.refresh_index = lambda: refresh_index(app)
    get_model()
    await refresh_index(app)
    yield
    await db.close()


# создаём само приложение FastAPI и подключаем роуты из api.py
app = FastAPI(title="Semantic Search", lifespan=lifespan)
app.include_router(api_router)


# страница админки, чтобы её открыть нужно ввести логин и пароль
@app.get("/admin", include_in_schema=False)
async def admin_page(_: str = Depends(require_admin)):
    """Возвращает страницу админки для авторизованных пользователей.
    
    :param _: Имя пользователя (не используется).
    :return: HTML-страница админки."""
    return FileResponse(TEMPLATES_DIR / "admin.html")


# если папка static есть то отдаём её по корню сайта (там лежит index.html)
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
