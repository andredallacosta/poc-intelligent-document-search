import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from infrastructure.config.settings import settings
from interface.api.v1.router import api_router
from interface.dependencies.container import container

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
        # Initialize PostgreSQL connection
        from infrastructure.database.connection import db_connection

        db_connection.initialize()

        # Test connection with a simple query
        from sqlalchemy import text

        async for session in db_connection.get_session():
            result = await session.execute(text("SELECT 1"))
            if result.scalar() == 1:
                logger.info("PostgreSQL connection successful")
            break

        # PostgreSQL connection successful
        logger.info("PostgreSQL repositories initialized successfully")
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        logger.error("PostgreSQL connection failed - system will not function properly")

    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        from infrastructure.database.connection import db_connection

        await db_connection.close()
    except Exception as e:
        logger.warning(f"Error closing database connection: {e}")

    await container.close_connections()


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Intelligent Document Search API with RAG and conversational AI",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
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
        "api_prefix": settings.api_prefix,
    }


@app.get("/health")
async def health_check():
    try:
        # Test Redis connection
        redis_client = container.get_redis_client()
        redis_healthy = await redis_client.ping()

        # Test database connections
        postgres_healthy = False
        embedding_count = 0
        database_type = "unknown"

        # Try PostgreSQL first
        try:
            from sqlalchemy import text

            from infrastructure.database.connection import db_connection

            async for session in db_connection.get_session():
                result = await session.execute(text("SELECT 1"))
                postgres_healthy = result.scalar() == 1
                database_type = "postgresql"
                break

            # Count PostgreSQL embeddings if available
            if postgres_healthy:
                try:
                    # TODO: Implementar count no PostgresVectorRepository
                    embedding_count = 0  # Placeholder
                except:
                    pass

        except Exception as pg_error:
            logger.warning(f"PostgreSQL connection failed: {pg_error}")
            database_type = "none"

        # Determine overall system health
        system_healthy = redis_healthy and postgres_healthy

        return {
            "status": "healthy" if system_healthy else "degraded",
            "version": settings.app_version,
            "services": {
                "redis": "healthy" if redis_healthy else "unhealthy",
                "database": {
                    "type": database_type,
                    "postgres": "healthy" if postgres_healthy else "unhealthy",
                    "embedding_count": embedding_count,
                },
            },
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e), "timestamp": time.time()},
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
            "contextual_retrieval": settings.use_contextual_retrieval,
        },
        "limits": {
            "max_messages_per_session": settings.max_messages_per_session,
            "max_daily_messages": settings.max_daily_messages,
            "chunk_size": settings.chunk_size,
            "default_search_results": settings.default_search_results,
        },
    }


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": (
                "An unexpected error occurred" if not settings.debug else str(exc)
            ),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "interface.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
