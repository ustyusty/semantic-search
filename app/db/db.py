import os
import asyncpg
from dotenv import load_dotenv
import logging

from app.decorators.log import log_exceptions

load_dotenv()
logger = logging.getLogger(__name__)


class DataBase:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None
    
    @log_exceptions()
    async def create_pool(self):
        """Создание пулла соединения с бд"""
        self.pool = await asyncpg.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT")),
        )
        logger.info("Успешное подключение к базе данных")
        
    @log_exceptions("Ошибка SQL в fetch")
    async def fetchall(self, SQLquery: str, *args):
        """Принимает `str` запрос, args\n
        Возвращает  `(asyncpg.Record)`"""

        if not self.pool:
            logger.error("pool does not exist")
            return
        conn: asyncpg.Connection
        async with self.pool.acquire() as conn:
            result = await conn.fetch(SQLquery, *args)
            logger.debug(f"Fetch Query: {SQLquery} | Args: {args} | Result: {result}")
            return result
    
    @log_exceptions("Ошибка SQL в execute")
    async def execute(self, SQLquery: str, *args):
        """Принимает `str` запрос, args\n
        Возвращает `str`"""
        if not self.pool:
            logger.error("pool does not exist")
            return
        
        conn: asyncpg.Connection
        async with self.pool.acquire() as conn:
            result = await conn.execute(SQLquery, *args)
            logger.debug(f"Execute Query: {SQLquery} | Args: {args} | Result: {result}")
            return result
        
    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Соединение с БД закрыто")