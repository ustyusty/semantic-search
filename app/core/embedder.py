# тут работа с нейросеткой которая превращает текст в вектор (эмбеддинг)
import logging
from functools import lru_cache
from typing import Iterable

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# название модельки, она мультиязычная - понимает и русский тоже
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# загружаем модель только один раз (lru_cache запоминает результат)
@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    logger.info("Загрузка модели эмбеддингов: %s", MODEL_NAME)
    return SentenceTransformer(MODEL_NAME)


# превратить один текст в вектор (нормализуем чтобы длина была 1)
def embed(text: str) -> list[float]:
    vec = get_model().encode(text, normalize_embeddings=True)
    return vec.astype(np.float32).tolist()


# то же самое но сразу для пачки текстов - так быстрее
def embed_batch(texts: Iterable[str]) -> list[list[float]]:
    vecs = get_model().encode(list(texts), normalize_embeddings=True, batch_size=16)
    return [v.astype(np.float32).tolist() for v in vecs]


# косинусная близость двух векторов - показывает насколько они похожи
def cosine(a: list[float], b: list[float]) -> float:
    na, nb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    return float(np.dot(na, nb))
