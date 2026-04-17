"""Загрузка документов из Orion-tecnologics-docs/*.json в БД с эмбеддингами.

Запуск:
    python -m scripts.seed              # добавляет новые
    python -m scripts.seed --reset      # очищает таблицу перед загрузкой
"""
import argparse
import asyncio
import json
import logging
from pathlib import Path

from app.core.embedder import embed_batch
from app.core.logger_setup import setup
from app.db.db import DataBase
from app.db.requests import DocumentRepo

DOCS_DIR = Path(__file__).resolve().parent.parent / "Orion-tecnologics-docs"
SKIP_FILES = {"doc-list.json"}

setup()
logger = logging.getLogger(__name__)


def load_documents() -> list[dict]:
    items: list[dict] = []
    for file in sorted(DOCS_DIR.glob("*.json")):
        if file.name in SKIP_FILES:
            continue
        data = json.loads(file.read_text(encoding="utf-8"))
        block = data.get("document_block") or data.get("block_name")
        for d in data.get("documents", []):
            items.append({
                "title": d["title"],
                "content": d["content"],
                "block": block,
            })
    return items


async def main(reset: bool):
    db = DataBase()
    await db.create_pool()
    repo = DocumentRepo(db)
    try:
        if reset:
            await repo.clear()
            logger.info("Таблица documents очищена")

        docs = load_documents()
        logger.info("Найдено документов: %d", len(docs))
        if not docs:
            return

        texts = [f"{d['title']}\n{d['content']}" for d in docs]
        vectors = embed_batch(texts)

        for d, vec in zip(docs, vectors):
            doc_id = await repo.add(d["title"], d["content"], vec, d["block"])
            logger.info("+ %d: %s", doc_id, d["title"])
    finally:
        await db.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="очистить таблицу перед загрузкой")
    args = ap.parse_args()
    asyncio.run(main(args.reset))
