# тут все ручки (endpoint-ы) нашего API: добавить документ, поиск, загрузка pdf
import asyncio
import io
import logging

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from pypdf import PdfReader

from app.core.auth import require_admin
from app.core.embedder import embed

# ограничение на размер загружаемого pdf
MAX_PDF_SIZE = 15 * 1024 * 1024  # 15 MB

# параметры чанкирования PDF: модель режет вход до ~128 токенов,
# поэтому большие документы разбиваем на куски по словам с перекрытием
CHUNK_WORDS = 120
CHUNK_OVERLAP = 20


def chunk_text(text: str, size: int = CHUNK_WORDS, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), step)]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["search"])


# модельки pydantic - они проверяют что приходит от пользователя и что мы отдаём
class AddDocumentIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    block: str | None = None


class AddDocumentOut(BaseModel):
    id: int


class SearchHit(BaseModel):
    id: int
    title: str
    snippet: str
    block: str | None = None
    score: float


# ручка для добавления нового документа (только для админа)
@router.post("/documents", response_model=AddDocumentOut, status_code=201, dependencies=[Depends(require_admin)])
async def add_document(payload: AddDocumentIn, request: Request):
    """Добавляет новый документ в базу данных.

    :param payload: Данные документа (заголовок, содержание, блок).
    :param request: Объект запроса FastAPI.
    :return: ID добавленного документа."""
    # считаем эмбеддинг (вектор) по тексту и кладём всё в базу
    repo = request.app.state.repo
    vec = list(await asyncio.to_thread(embed, f"{payload.title}\n{payload.content}"))
    doc_id = await repo.add(payload.title, payload.content, vec, payload.block)
    await request.app.state.refresh_index()
    return AddDocumentOut(id=doc_id)


# ручка поиска - основная фишка проекта, ищет похожие доки по смыслу
@router.get("/search", response_model=list[SearchHit])
async def search(q: str, k: int = 3, request: Request = None):
    """Выполняет семантический поиск документов по запросу.

    :param q: Поисковый запрос.
    :param k: Количество результатов (от 1 до 20).
    :param request: Объект запроса FastAPI.
    :return: Список найденных документов с оценками."""
    # проверяем что запрос не пустой
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")
    # сколько результатов вернуть (от 1 до 20)
    k = max(1, min(k, 20))

    index = request.app.state.index
    if not index["ids"]:
        return []

    # превращаем запрос в вектор (в отдельном потоке чтобы не блокировать event loop)
    # и считаем близость со всеми документами через матричное умножение
    query_vec = np.asarray(await asyncio.to_thread(embed, q), dtype=np.float32)
    matrix = index["matrix"]
    scores = matrix @ query_vec
    # берём топ-k самых похожих (argpartition быстрее full sort при большом N)
    if k >= len(scores):
        top = np.argsort(-scores)
    else:
        part = np.argpartition(-scores, k)[:k]
        top = part[np.argsort(-scores[part])]

    hits: list[SearchHit] = []
    for idx in top:
        i = int(idx)
        content = index["contents"][i]
        snippet = content
        hits.append(SearchHit(
            id=index["ids"][i],
            title=index["titles"][i],
            snippet=snippet,
            block=index["blocks"][i],
            score=float(scores[i]),
        ))
    return hits


# ручка загрузки pdf файла - из него вытащим текст и сохраним как документ
@router.post("/documents/upload", response_model=AddDocumentOut, status_code=201, dependencies=[Depends(require_admin)])
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    block: str | None = Form(None),
):
    """Загружает PDF-файл, извлекает текст и сохраняет как документ.

    :param request: Объект запроса FastAPI.
    :param file: Загружаемый PDF-файл.
    :param title: Заголовок документа (опционально).
    :param block: Блок документа (опционально).
    :return: ID добавленного документа."""
    # проверяем что это именно пдф-ка
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Ожидается PDF-файл")

    # читаем файл целиком и проверяем размер
    data = await file.read()
    if len(data) > MAX_PDF_SIZE:
        raise HTTPException(status_code=413, detail="Файл слишком большой (>15 МБ)")

    # пробуем вытащить текст со всех страниц пдфки
    try:
        reader = PdfReader(io.BytesIO(data))
        content = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
    except Exception as e:
        logger.warning("Ошибка парсинга PDF %s: %s", file.filename, e)
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать PDF: {e}")

    # если текста не нашлось (например это скан картинками) - ругаемся
    if not content:
        raise HTTPException(status_code=422, detail="PDF не содержит извлекаемого текста (возможно, скан без OCR)")

    # если заголовок не передали - берём имя файла без расширения
    doc_title = (title or "").strip() or file.filename.rsplit(".", 1)[0]

    # режем PDF на чанки и сохраняем каждый отдельной записью со своим эмбеддингом —
    # иначе модель видит только первые ~100 слов всего документа
    chunks = chunk_text(content)
    repo = request.app.state.repo
    last_id = None
    total = len(chunks)
    # считаем эмбеддинги пачкой в отдельном потоке — сильно быстрее, чем по одному
    from app.core.embedder import embed_batch
    titles = [f"{doc_title} (ч. {n}/{total})" if total > 1 else doc_title for n in range(1, total + 1)]
    payloads = [f"{t}\n{c}" for t, c in zip(titles, chunks)]
    vecs = await asyncio.to_thread(embed_batch, payloads)
    for chunk_title, chunk, vec in zip(titles, chunks, vecs):
        last_id = await repo.add(chunk_title, chunk, list(vec), block)

    await request.app.state.refresh_index()
    return AddDocumentOut(id=last_id)


# простая ручка - вернуть сколько всего документов в базе
@router.get("/documents/count")
async def documents_count(request: Request):
    """Возвращает количество документов в базе данных.
    
    :param request: Объект запроса FastAPI.
    :return: Словарь с количеством документов."""
    return {"count": await request.app.state.repo.count()}
