# тут все sql-запросы для работы с таблицей documents
from .db import DataBase


# паттерн "репозиторий" - все запросы к документам в одном месте
class DocumentRepo:
    def __init__(self, db: DataBase):
        self.db = db

    # добавить новый документ в БД и вернуть его id
    async def add(self, title: str, content: str, embedding: list[float], block: str | None = None) -> int:
        rows = await self.db.fetchall(
            """
            INSERT INTO documents (title, content, block, embedding)
            VALUES ($1, $2, $3, $4)
            RETURNING id
            """,
            title, content, block, embedding,
        )
        return int(rows[0]["id"])

    # вытащить все документы из БД (нужно для построения индекса в памяти)
    async def all(self) -> list[dict]:
        rows = await self.db.fetchall(
            "SELECT id, title, content, block, embedding FROM documents ORDER BY id"
        )
        return [dict(r) for r in rows or []]

    # посчитать сколько всего документов в таблице
    async def count(self) -> int:
        rows = await self.db.fetchall("SELECT COUNT(*) AS n FROM documents")
        return int(rows[0]["n"]) if rows else 0

    # удалить вообще все документы и сбросить счётчик id
    async def clear(self):
        await self.db.execute("TRUNCATE documents RESTART IDENTITY")
