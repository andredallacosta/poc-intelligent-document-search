from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.core.config import settings
from api.core.redis import redis_client
from api.routers import sessions, documents, chat

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_client.connect()
    yield
    await redis_client.disconnect()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(documents.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {
        "message": "POC Intelligent Document Search API", 
        "version": settings.version,
        "environment": settings.environment
    }

@app.get("/health")
async def health_check():
    try:
        redis_status = "ok" if redis_client.redis and await redis_client.redis.ping() else "error"
    except:
        redis_status = "error"
    
    return {
        "status": "ok",
        "redis": redis_status,
        "version": settings.version
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
