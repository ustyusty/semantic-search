from .db import DataBase


class DocumentRepo:
    def __init__(self, db: DataBase):
        self.db = db

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

    async def all(self) -> list[dict]:
        rows = await self.db.fetchall(
            "SELECT id, title, content, block, embedding FROM documents ORDER BY id"
        )
        return [dict(r) for r in rows or []]

    async def count(self) -> int:
        rows = await self.db.fetchall("SELECT COUNT(*) AS n FROM documents")
        return int(rows[0]["n"]) if rows else 0

    async def clear(self):
        await self.db.execute("TRUNCATE documents RESTART IDENTITY")
