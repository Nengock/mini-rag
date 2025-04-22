from fastapi import APIRouter, HTTPException
from app.core.rag_engine import RAGEngine
from app.models.query import Query, QueryResponse
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
rag_engine = RAGEngine()

@router.post("/ask", response_model=QueryResponse)
async def ask_question(query: Query):
    try:
        if not query.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
            
        if len(query.question) > 500:
            raise HTTPException(status_code=400, detail="Question is too long (max 500 characters)")
            
        logger.info(f"Processing question for document {query.document_id}: {query.question[:100]}...")
        
        response = await rag_engine.process_query(
            question=query.question,
            document_id=query.document_id,
            context_window=query.context_window
        )
        
        logger.info(f"Generated response for document {query.document_id} with {response.metadata.get('chunks_used', 0)} chunks")
        return response
        
    except FileNotFoundError as e:
        logger.error(f"Document not found error: {str(e)}")
        raise HTTPException(status_code=404, detail="Document not found or not processed yet")
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again."
        )