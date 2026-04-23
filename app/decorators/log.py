# декоратор чтобы автоматом ловить исключения и писать их в лог
from functools import wraps
import logging
logger = logging.getLogger(__name__)

# декоратор с параметром (поэтому тут три уровня вложенности функций)
def log_exceptions(custom_msg:str = ""):
    """Декоратор для логирования исключений в асинхронных функциях.
    
    :param custom_msg: Пользовательское сообщение перед ошибкой."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            
            except Exception as e:

                logger.exception("%s | Function: %s | Args: %s | Kwargs: %s | Error: %s",
                    custom_msg,
                    func.__name__,
                    args,
                    kwargs,
                    str(e))
                raise
            
        return wrapper
    return decorator