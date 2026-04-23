# тут работа с нейросеткой которая превращает текст в вектор (эмбеддинг)
import logging
from functools import lru_cache
from typing import Iterable

import os
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

torch.set_num_threads(max(1, os.cpu_count() or 1))
torch.set_grad_enabled(False)


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Загружает и возвращает модель для создания эмбеддингов.

    :return: Экземпляр модели SentenceTransformer."""
    logger.info("Загрузка модели эмбеддингов: %s", MODEL_NAME)
    m = SentenceTransformer(MODEL_NAME)
    m.eval()
    return m


# превратить один текст в вектор (нормализуем чтобы длина была 1)
@lru_cache(maxsize=4096)
def embed(text: str) -> tuple[float, ...]:
    """Преобразует текст в вектор эмбеддинга.

    :param text: Входной текст.
    :return: Вектор эмбеддинга в виде кортежа чисел с плавающей запятой.
        """
    with torch.inference_mode():
        vec = get_model().encode(text, normalize_embeddings=True, show_progress_bar=False)
    return tuple(vec.astype(np.float32).tolist())


def embed_batch(texts: Iterable[str]) -> list[list[float]]:
    """Преобразует пачку текстов в векторы эмбеддингов.

    :param texts: Итерабельный объект с входными текстами.
    :return: Список векторов эмбеддингов, каждый в виде списка чисел с плавающей запятой."""
    with torch.inference_mode():
        vecs = get_model().encode(list(texts), normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return [v.astype(np.float32).tolist() for v in vecs]


# косинусная близость двух векторов - показывает насколько они похожи
def cosine(a: list[float], b: list[float]) -> float:
    """Вычисляет косинусную близость между двумя векторами.
    
    :param a: Первый вектор.
    :param b: Второй вектор.
    :return: Значение косинусной близости в виде числа с плавающей запятой."""
    na, nb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    return float(np.dot(na, nb))
