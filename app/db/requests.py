from .db import DataBase
class Repo:
    def __init__(self, db:DataBase):
        self.db = db

    async def add_new_user(self, telegram_id: int, username:str):
        is_new_user = await self.db.fetchall(
            """
            INSERT INTO users (user_id)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING user_id
            """,
            telegram_id, username)
        return is_new_user