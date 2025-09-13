from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from interface.api.v1.router import api_router
from interface.dependencies.container import container
from infrastructure.config.settings import settings


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Intelligent Document Search API v2.0")
    
    # Create storage directories
    settings.create_directories()
    
    # Test connections
    try:
        redis_client = container.get_redis_client()
        if not await redis_client.ping():
            logger.warning("Redis connection failed - sessions will not persist")
        else:
            logger.info("Redis connection successful")
    except Exception as e:
        logger.warning(f"Redis connection error: {e}")
    
    try:
        chroma_client = container.get_chroma_client()
        count = await chroma_client.count()
        logger.info(f"ChromaDB connection successful - {count} embeddings loaded")
    except Exception as e:
        logger.error(f"ChromaDB connection error: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await container.close_connections()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent Document Search API with RAG and conversational AI",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include API router
app.include_router(api_router, prefix=settings.api_prefix)


# Root endpoints
@app.get("/")
async def root():
    return {
        "message": "Intelligent Document Search API",
        "version": settings.app_version,
        "status": "running",
        "docs_url": "/docs",
        "api_prefix": settings.api_prefix
    }


@app.get("/health")
async def health_check():
    try:
        # Test Redis connection
        redis_client = container.get_redis_client()
        redis_healthy = await redis_client.ping()
        
        # Test ChromaDB connection
        chroma_client = container.get_chroma_client()
        embedding_count = await chroma_client.count()
        
        return {
            "status": "healthy",
            "version": settings.app_version,
            "services": {
                "redis": "healthy" if redis_healthy else "unhealthy",
                "chromadb": "healthy",
                "embedding_count": embedding_count
            },
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


@app.get("/info")
async def app_info():
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.debug else "production",
        "features": {
            "chat": True,
            "document_search": True,
            "session_management": True,
            "rate_limiting": True,
            "contextual_retrieval": settings.use_contextual_retrieval
        },
        "limits": {
            "max_messages_per_session": settings.max_messages_per_session,
            "max_daily_messages": settings.max_daily_messages,
            "chunk_size": settings.chunk_size,
            "default_search_results": settings.default_search_results
        }
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred" if not settings.debug else str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "interface.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
