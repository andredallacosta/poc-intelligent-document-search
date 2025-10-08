from fastapi import APIRouter

from interface.api.v1.endpoints import admin, auth, chat, documents, queue, tokens

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(admin.router)
api_router.include_router(documents.router)
api_router.include_router(queue.router)
api_router.include_router(tokens.router)
