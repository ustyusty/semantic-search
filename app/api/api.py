# тут все ручки (endpoint-ы) нашего API: добавить документ, поиск, загрузка pdf
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
    # считаем эмбеддинг (вектор) по тексту и кладём всё в базу
    repo = request.app.state.repo
    vec = embed(f"{payload.title}\n{payload.content}")
    doc_id = await repo.add(payload.title, payload.content, vec, payload.block)
    await request.app.state.refresh_index()
    return AddDocumentOut(id=doc_id)


# ручка поиска - основная фишка проекта, ищет похожие доки по смыслу
@router.get("/search", response_model=list[SearchHit])
async def search(q: str, k: int = 3, request: Request = None):
    # проверяем что запрос не пустой
    q = q.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")
    # сколько результатов вернуть (от 1 до 20)
    k = max(1, min(k, 20))

    index = request.app.state.index
    if not index["ids"]:
        return []

    # превращаем запрос в вектор и считаем близость со всеми документами через матричное умножение
    query_vec = np.asarray(embed(q), dtype=np.float32)
    matrix = index["matrix"]
    scores = matrix @ query_vec
    # берём топ-k самых похожих (сортируем по убыванию)
    top = np.argsort(-scores)[:k]

    hits: list[SearchHit] = []
    for idx in top:
        i = int(idx)
        content = index["contents"][i]
        snippet = content[:300] + ("…" if len(content) > 300 else "")
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
    repo = request.app.state.repo
    vec = embed(f"{doc_title}\n{content}")
    doc_id = await repo.add(doc_title, content, vec, block)
    await request.app.state.refresh_index()
    return AddDocumentOut(id=doc_id)


# простая ручка - вернуть сколько всего документов в базе
@router.get("/documents/count")
async def documents_count(request: Request):
    return {"count": await request.app.state.repo.count()}
