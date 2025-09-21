from fastapi import APIRouter

from interface.api.v1.endpoints import admin, chat, documents, queue

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(chat.router)
api_router.include_router(admin.router)
api_router.include_router(documents.router)
api_router.include_router(queue.router)

# Add more routers here as needed
# api_router.include_router(sessions.router)
