# тут класс для работы с PostgreSQL через asyncpg (асинхронно)
import os
import asyncpg
from dotenv import load_dotenv
import logging

from app.decorators.log import log_exceptions

# грузим переменные окружения из .env
load_dotenv()
logger = logging.getLogger(__name__)


# класс-обёртка над соединением с БД
class DataBase:
    def __init__(self):
        # пул это набор соединений, чтобы не пересоздавать каждый раз
        self.pool: asyncpg.Pool | None = None
    
    @log_exceptions()
    async def create_pool(self):
        """Создаёт пул соединений с базой данных PostgreSQL."""
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
        """Выполняет SQL-запрос и возвращает все результаты.

        :param SQLquery: SQL-запрос.
        :param args: Параметры запроса.
        :return: Список записей asyncpg.Record."""
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
        """Выполняет SQL-запрос без возврата результатов.
        
        :param SQLquery: SQL-запрос.
        :param args: Параметры запроса.
        :return: Строка с результатом выполнения."""
        if not self.pool:
            logger.error("pool does not exist")
            return
        
        conn: asyncpg.Connection
        async with self.pool.acquire() as conn:
            result = await conn.execute(SQLquery, *args)
            logger.debug(f"Execute Query: {SQLquery} | Args: {args} | Result: {result}")
            return result
        
    # закрываем соединение когда приложение выключается
    async def close(self):
        """Закрывает пул соединений с базой данных."""
        if self.pool:
            await self.pool.close()
            logger.info("Соединение с БД закрыто")