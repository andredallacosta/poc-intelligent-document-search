from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
import logging

from api.services.rag_service import rag_service
from api.models.chat import DocumentSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

@router.get("/search")
async def search_documents(
    q: str = Query(..., description="Search query", min_length=1),
    limit: int = Query(5, description="Number of results", ge=1, le=20),
    source: Optional[str] = Query(None, description="Filter by document source")
):
    try:
        filters = {}
        if source:
            filters["source"] = source
        
        results = await rag_service.search_documents(
            query=q,
            n_results=limit,
            filters=filters if filters else None
        )
        
        formatted_results = []
        for result in results:
            doc_source = DocumentSource(
                source=result["source"],
                page=result.get("page"),
                chunk_index=result.get("chunk_index"),
                similarity=result["similarity"],
                text_preview=result["preview"]
            )
            formatted_results.append(doc_source)
        
        return {
            "query": q,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Error in document search: {e}")
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

@router.get("/sources")
async def list_document_sources():
    try:
        # Get sources from a test search
        test_results = await rag_service.search_documents("documento", n_results=50)
        
        sources = set()
        for result in test_results:
            source = result.get("source")
            if source and source != "Unknown":
                sources.add(source)
        
        return {
            "sources": sorted(list(sources)),
            "total_sources": len(sources)
        }
        
    except Exception as e:
        logger.error(f"Error listing sources: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing sources: {str(e)}")
