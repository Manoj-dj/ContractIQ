from fastapi import APIRouter, HTTPException
from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.rag_service import RAGService
from app.core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

rag_service = RAGService()

@router.post("/", response_model=ChatResponse)
async def chat_with_contract(request: ChatRequest):
    """
    Chat with contract using RAG-based QA system
    
    - Maintains conversational context across turns
    - Retrieves relevant contract sections and extracted clauses
    - Generates contextual answers using Gemini 2.0 Flash
    - Stores conversation history for session continuity
    """
    logger.info(f"Chat request: session={request.session_id}, doc={request.doc_id}")
    
    try:
        # Validate query length
        if len(request.query.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Query is too short. Please provide a more detailed question."
            )
        
        # Answer query using RAG
        result = rag_service.answer_query(
            session_id=request.session_id,
            doc_id=request.doc_id,
            user_query=request.query
        )
        
        # Prepare response
        response = ChatResponse(
            session_id=request.session_id,
            doc_id=request.doc_id,
            query=request.query,
            reformulated_query=result.get("reformulated_query"),
            answer=result["answer"],
            sources=[
                {
                    "text": source["text"][:200] + "..." if len(source["text"]) > 200 else source["text"],
                    "type": source["type"],
                    "clause_type": source.get("clause_type"),
                    "risk_level": source.get("risk_level")
                }
                for source in result.get("sources", [])
            ],
            timestamp=datetime.now()
        )
        
        logger.info(f"Chat response generated for session {request.session_id}")
        
        return response
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Chat failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, limit: int = 10):
    """
    Retrieve conversation history for a session
    
    Args:
        session_id: Session identifier
        limit: Maximum number of turns to retrieve
    
    Returns:
        List of conversation turns
    """
    logger.info(f"Retrieving chat history for session: {session_id}")
    
    try:
        from app.core.database import sqlite_db
        
        history = sqlite_db.get_conversation_history(session_id, limit)
        
        logger.info(f"Retrieved {len(history)} conversation turns")
        
        return {
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    
    except Exception as e:
        logger.error(f"Failed to retrieve chat history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear conversation history for a session
    
    Args:
        session_id: Session identifier to clear
    
    Returns:
        Success message
    """
    logger.info(f"Clearing session: {session_id}")
    
    try:
        from app.core.database import sqlite_db
        
        conn = sqlite_db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"Cleared {deleted_count} conversation turns for session {session_id}")
        
        return {
            "message": f"Session cleared successfully",
            "session_id": session_id,
            "deleted_turns": deleted_count
        }
    
    except Exception as e:
        logger.error(f"Failed to clear session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}")
