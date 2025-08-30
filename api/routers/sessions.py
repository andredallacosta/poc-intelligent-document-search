from fastapi import APIRouter, HTTPException
from typing import Optional

from api.services.session_service import session_service
from api.models.session import SessionData
from api.models.chat import SessionHistoryResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionData)
async def create_session(session_id: Optional[str] = None):
    try:
        session = await session_service.create_session(session_id)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating session: {str(e)}")

@router.get("/{session_id}", response_model=SessionData)
async def get_session(session_id: str):
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str):
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionHistoryResponse(
        session_id=session.session_id,
        messages=[msg.model_dump() for msg in session.messages],
        total_messages=len(session.messages),
        created_at=session.created_at,
        last_activity=session.last_activity,
        total_tokens_used=session.total_tokens_used
    )

@router.delete("/{session_id}")
async def delete_session(session_id: str):
    success = await session_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted successfully"}
