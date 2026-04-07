import logging
from fastapi import FastAPI

from app.core.logger_setup import setup

setup() # logger
logger = logging.getLogger(__name__)

app = FastAPI()
@app.get("/")
async def root():
    return {"message": "Hello World"}

