from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import json
import time
import uuid
import logging

from api.services.rag_service import rag_service
from api.services.llm_service import llm_service
from api.services.session_service import session_service
from api.models.chat import ChatRequest, ChatResponse, DocumentSource, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    start_time = time.time()
    
    try:
        # Get or create session
        session_id = request.session_id or str(uuid.uuid4())
        session = await session_service.get_session(session_id)
        
        if not session:
            session = await session_service.create_session(session_id)
            logger.info(f"Created new session {session_id}")
        
        # Check rate limiting
        if not await session_service.check_rate_limit(session_id):
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Maximum requests per day reached."
            )
        
        # Search relevant documents
        logger.info(f"Searching documents for: '{request.message[:50]}...'")
        search_results = await rag_service.search_documents(
            query=request.message,
            n_results=5
        )
        
        # Get conversation history for LLM context
        conversation_history = session.get_context_for_llm(max_tokens=3000)
        
        # Generate response using LLM
        logger.info("Generating LLM response")
        llm_result = await llm_service.generate_response(
            user_message=request.message,
            search_results=search_results,
            conversation_history=conversation_history
        )
        
        # Format sources for response
        sources = []
        for result in search_results:
            source = DocumentSource(
                source=result["source"],
                page=result.get("page"),
                chunk_index=result.get("chunk_index"),
                similarity=result["similarity"],
                text_preview=result["preview"]
            )
            sources.append(source)
        
        # Save conversation to session
        await session_service.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            tokens_used=llm_result["tokens_used"] // 2  # Rough estimate for input
        )
        
        await session_service.add_message(
            session_id=session_id,
            role="assistant",
            content=llm_result["response"],
            tokens_used=llm_result["tokens_used"] // 2  # Rough estimate for output
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        response = ChatResponse(
            response=llm_result["response"],
            session_id=session_id,
            sources=sources,
            tokens_used=llm_result["tokens_used"],
            response_time_ms=response_time
        )
        
        logger.info(f"Chat response completed in {response_time}ms")

        with open("../../results.txt", "a") as f:
            f.write(response.model_dump_json())

        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/sessions/{session_id}/messages")
async def get_session_messages(session_id: str):
    try:
        session = await session_service.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "messages": [msg.model_dump() for msg in session.messages],
            "total_messages": len(session.messages),
            "total_tokens_used": session.total_tokens_used,
            "created_at": session.created_at,
            "last_activity": session.last_activity
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

