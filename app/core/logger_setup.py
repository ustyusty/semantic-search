# настраиваем красивый цветной логгер чтобы в консоли было удобно читать
from dotenv import load_dotenv
import os
import logging
from colorlog import ColoredFormatter
from functools import wraps

load_dotenv()
def setup():
    """Настраивает логгер с цветным выводом и уровнем логирования из переменной окружения LOG_LEVEL."""
    log_level_str = os.getenv("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper())

    formatter = ColoredFormatter(
        "%(log_color)s%(asctime)s - [%(name)s:%(lineno)d] - %(levelname)s - %(message)s",
        datefmt=None,
        reset=True,
        log_colors={
            'DEBUG':    'cyan',      # Голубой для отладки
            'INFO':     'green',     # Зеленый для обычной инфы
            'WARNING':  'yellow',    # Желтый для предупреждений
            'ERROR':    'red',       # Красный для ошибок
            'CRITICAL': 'red,bg_white', # Красный на белом для критических ошибок
        },
        secondary_log_colors={},
        style='%'
    )

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[stream]
    )
