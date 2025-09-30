from fastapi import APIRouter

from interface.api.v1.endpoints import admin, chat, documents, queue

api_router = APIRouter()

api_router.include_router(chat.router)
api_router.include_router(admin.router)
api_router.include_router(documents.router)
api_router.include_router(queue.router)
