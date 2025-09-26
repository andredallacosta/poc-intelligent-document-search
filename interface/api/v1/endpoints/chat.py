import logging

from fastapi import APIRouter, HTTPException

from application.dto.chat_dto import ChatRequestDTO
from domain.exceptions.chat_exceptions import (
    ChatError,
    InvalidMessageError,
    RateLimitExceededError,
    SessionNotFoundError,
)
from interface.schemas.chat import ChatRequest, ChatResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/ask",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Chat with documents",
    description="Send a message and get an AI response based on indexed documents",
)
async def ask_question(
    request: ChatRequest,
):
    try:
        logger.info(f"Processing chat request: '{request.message[:50]}...'")

        # Import dependencies from container
        from interface.dependencies.container import create_chat_use_case

        # Create use case with proper dependencies
        chat_use_case = await create_chat_use_case()

        # Convert Pydantic model to DTO
        chat_request_dto = ChatRequestDTO(
            message=request.message,
            session_id=request.session_id,
            metadata=request.metadata,
        )

        # Execute use case
        response_dto = await chat_use_case.execute(chat_request_dto)

        # Convert DTO to Pydantic response
        return ChatResponse(
            response=response_dto.response,
            session_id=response_dto.session_id,
            sources=[
                {
                    "document_id": source.document_id,
                    "chunk_id": source.chunk_id,
                    "source": source.source,
                    "page": source.page,
                    "similarity_score": source.similarity_score,
                    "excerpt": source.excerpt,
                }
                for source in response_dto.sources
            ],
            metadata=response_dto.metadata,
            processing_time=response_dto.processing_time,
            token_usage=response_dto.token_usage,
        )

    except InvalidMessageError as e:
        logger.warning(f"Invalid message: {e}")
        raise HTTPException(
            status_code=400, detail={"error": "Invalid message", "detail": str(e)}
        )

    except RateLimitExceededError as e:
        logger.warning(f"Rate limit exceeded: {e}")
        raise HTTPException(
            status_code=429, detail={"error": "Rate limit exceeded", "detail": str(e)}
        )

    except SessionNotFoundError as e:
        logger.error(f"Session not found: {e}")
        raise HTTPException(
            status_code=404, detail={"error": "Session not found", "detail": str(e)}
        )

    except ChatError as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "Chat processing failed", "detail": str(e)},
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "detail": "An unexpected error occurred",
            },
        )


@router.get(
    "/health",
    summary="Health check",
    description="Check if the chat service is healthy",
)
async def health_check():
    return {"status": "healthy", "service": "chat"}


@router.get(
    "/models", summary="Available models", description="Get list of available AI models"
)
async def get_available_models():
    return {
        "models": [
            {
                "id": "gpt-4o-mini",
                "name": "GPT-4o Mini",
                "description": "Fast and cost-effective model",
                "max_tokens": 4096,
            }
        ]
    }
