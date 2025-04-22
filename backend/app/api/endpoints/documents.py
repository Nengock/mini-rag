from fastapi import APIRouter, UploadFile, HTTPException, BackgroundTasks
from app.core.pdf_processor import PDFProcessor
from app.models.document import DocumentResponse
from typing import List
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
pdf_processor = PDFProcessor()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        document_id = await pdf_processor.save_document(file)
        background_tasks.add_task(pdf_processor.process_document, document_id)
        
        return DocumentResponse(
            document_id=document_id,
            filename=file.filename,
            status="processing"
        )
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{document_id}")
async def get_document_status(document_id: str):
    try:
        status = await pdf_processor.get_document_status(document_id)
        if not status:
            raise HTTPException(status_code=404, detail="Document not found")
        return status
    except Exception as e:
        logger.error(f"Status check error for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    try:
        success = await pdf_processor.delete_document(document_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document")
        return {"message": "Document deleted successfully"}
    except Exception as e:
        logger.error(f"Delete error for {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))