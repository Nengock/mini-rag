import PyPDF2
from pathlib import Path
import uuid
import asyncio
from typing import List, Dict
import spacy
import logging
from datetime import datetime
import os
from app.core.vector_store import VectorStore
from app.models.document import DocumentChunk

logger = logging.getLogger(__name__)

# Load configuration from environment variables
MAX_PAGES = int(os.getenv("MAX_PAGES", "1000"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

class PDFProcessingError(Exception):
    """Base exception for PDF processing errors"""
    pass

class PDFExtractionError(PDFProcessingError):
    """Raised when text extraction from PDF fails"""
    pass

class PDFCorruptedError(PDFProcessingError):
    """Raised when PDF file is corrupted"""
    pass

class EmptyDocumentError(PDFProcessingError):
    """Raised when no text content could be extracted"""
    pass

class PDFProcessor:
    def __init__(self):
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
        self.nlp = spacy.load("en_core_web_sm")
        self.vector_store = VectorStore()
        self.processing_status = {}
        self.document_metadata = {}
        self.chunk_size = CHUNK_SIZE
        self.chunk_overlap = CHUNK_OVERLAP

    async def _update_processing_progress(self, document_id: str, message: str, progress: float):
        """Update processing status with progress information"""
        self.processing_status[document_id] = f"processing: {message} ({progress:.0%})"
        if document_id in self.document_metadata:
            self.document_metadata[document_id]["processing_progress"] = progress

    async def save_document(self, file) -> str:
        document_id = str(uuid.uuid4())
        file_path = self.upload_dir / f"{document_id}.pdf"
        
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            # Initialize metadata
            self.document_metadata[document_id] = {
                "filename": file.filename,
                "processed_at": datetime.utcnow().isoformat(),
                "file_size": len(content),
                "chunk_count": 0,
                "total_pages": 0,
                "configuration": {
                    "chunk_size": self.chunk_size,
                    "chunk_overlap": self.chunk_overlap,
                    "max_pages": MAX_PAGES
                }
            }
            
            # Validate PDF is readable and extract metadata
            try:
                with open(file_path, "rb") as f:
                    try:
                        reader = PyPDF2.PdfReader(f)
                        total_pages = len(reader.pages)
                        
                        # Check if PDF is empty
                        if total_pages == 0:
                            raise PDFCorruptedError("PDF file contains no pages")
                        
                        # Check if PDF is too large
                        if total_pages > MAX_PAGES:
                            raise PDFCorruptedError(f"PDF file too large (max {MAX_PAGES} pages)")
                            
                        # Try to extract text from first page to validate content
                        first_page_text = reader.pages[0].extract_text().strip()
                        if not first_page_text:
                            raise PDFCorruptedError("First page contains no extractable text")
                        
                        # Get PDF metadata if available
                        pdf_info = reader.metadata
                        if pdf_info:
                            self.document_metadata[document_id]["pdf_metadata"] = {
                                "title": pdf_info.get("/Title", ""),
                                "author": pdf_info.get("/Author", ""),
                                "subject": pdf_info.get("/Subject", ""),
                                "creator": pdf_info.get("/Creator", ""),
                                "creation_date": pdf_info.get("/CreationDate", ""),
                            }
                        
                        # Update page count
                        self.document_metadata[document_id]["total_pages"] = total_pages
                        
                    except Exception as e:
                        raise PDFCorruptedError(f"Invalid or corrupted PDF file: {str(e)}")
                        
            except Exception as e:
                raise PDFCorruptedError(f"Failed to validate PDF: {str(e)}")
            
            self.processing_status[document_id] = "uploaded"
            logger.info(f"Document {document_id} saved and validated successfully")
            return document_id
            
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            if document_id in self.document_metadata:
                del self.document_metadata[document_id]
            if isinstance(e, PDFProcessingError):
                raise
            raise PDFProcessingError(f"Failed to save document: {str(e)}")

    async def process_document(self, document_id: str):
        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                await self._process_document_internal(document_id)
                return
            except Exception as e:
                retry_count += 1
                error_msg = f"Error processing document (attempt {retry_count}/{MAX_RETRIES}): {str(e)}"
                logger.error(error_msg)
                if retry_count >= MAX_RETRIES:
                    self.processing_status[document_id] = f"error: {str(e)}"
                    if document_id in self.document_metadata:
                        self.document_metadata[document_id]["error"] = str(e)
                    await self.delete_document(document_id)
                    raise PDFProcessingError(error_msg)
                await asyncio.sleep(1)  # Wait before retrying

    async def _process_document_internal(self, document_id: str):
        try:
            await self._update_processing_progress(document_id, "Starting processing", 0.0)
            logger.info(f"Starting processing of document {document_id}")
            
            file_path = self.upload_dir / f"{document_id}.pdf"
            if not file_path.exists():
                raise FileNotFoundError(f"PDF file not found for document {document_id}")
            
            # Extract text from PDF
            await self._update_processing_progress(document_id, "Extracting text", 0.2)
            chunks = await self._extract_text(file_path)
            
            if not chunks:
                raise EmptyDocumentError("No text content could be extracted from the PDF")
            
            # Update metadata before indexing
            self.document_metadata[document_id].update({
                "chunk_count": len(chunks),
                "average_chunk_length": sum(len(c.text) for c in chunks) / len(chunks)
            })
            
            # Process and store chunks with progress tracking
            await self.vector_store.add_chunks(
                document_id, 
                chunks,
                progress_callback=lambda msg, prog: self._update_processing_progress(
                    document_id,
                    msg,
                    0.3 + prog * 0.7  # Scale progress to remaining 70%
                )
            )
            
            # Update final metadata
            self.document_metadata[document_id].update({
                "completed_at": datetime.utcnow().isoformat(),
                "processing_progress": 1.0
            })
            
            self.processing_status[document_id] = "completed"
            logger.info(f"Document {document_id} processed successfully with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error in _process_document_internal: {str(e)}")
            raise

    async def delete_document(self, document_id: str) -> bool:
        """Delete document files and associated data"""
        try:
            # Delete PDF file
            file_path = self.upload_dir / f"{document_id}.pdf"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted PDF file for document {document_id}")
            
            # Delete vector store data
            await self.vector_store.delete_document(document_id)
            logger.info(f"Deleted vector store data for document {document_id}")
            
            # Clear metadata and status
            self.document_metadata.pop(document_id, None)
            self.processing_status.pop(document_id, None)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False

    def _create_chunks_from_text(self, text: str, page_num: int) -> List[DocumentChunk]:
        chunks = []
        doc = self.nlp(text)
        
        current_chunk = []
        current_length = 0
        chunk_id = 0
        
        for para in doc.sents:
            para_text = para.text.strip()
            if not para_text:
                continue
                
            # If adding this paragraph would exceed chunk size, save current chunk
            if current_length + len(para_text) > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append(DocumentChunk(
                    chunk_id=f"{page_num}-{chunk_id}",
                    text=chunk_text,
                    page_number=page_num,
                    metadata={
                        "position": chunk_id,
                        "length": len(chunk_text),
                        "page": page_num
                    }
                ))
                chunk_id += 1
                
                # Keep last paragraph for overlap
                overlap_size = 0
                overlap_chunk = []
                for text in reversed(current_chunk):
                    if overlap_size + len(text) > self.chunk_overlap:
                        break
                    overlap_chunk.insert(0, text)
                    overlap_size += len(text)
                
                current_chunk = overlap_chunk
                current_length = overlap_size
            
            current_chunk.append(para_text)
            current_length += len(para_text)
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append(DocumentChunk(
                chunk_id=f"{page_num}-{chunk_id}",
                text=chunk_text,
                page_number=page_num,
                metadata={
                    "position": chunk_id,
                    "length": len(chunk_text),
                    "page": page_num
                }
            ))
        
        return chunks

    async def _extract_text(self, file_path: Path) -> List[DocumentChunk]:
        chunks = []
        try:
            with open(file_path, "rb") as file:
                try:
                    reader = PyPDF2.PdfReader(file)
                except Exception as e:
                    raise PDFCorruptedError(f"Failed to read PDF file: {str(e)}")
                
                total_pages = len(reader.pages)
                logger.info(f"Processing PDF with {total_pages} pages")
                
                for page_num in range(total_pages):
                    try:
                        text = reader.pages[page_num].extract_text()
                        if text.strip():  # Only process non-empty pages
                            page_chunks = self._create_chunks_from_text(text, page_num)
                            chunks.extend(page_chunks)
                            logger.debug(f"Processed page {page_num + 1}/{total_pages} with {len(page_chunks)} chunks")
                    except Exception as e:
                        logger.warning(f"Error processing page {page_num}: {str(e)}")
                        continue
                        
        except PDFProcessingError:
            raise
        except Exception as e:
            raise PDFExtractionError(f"Error processing PDF: {str(e)}")
            
        if not chunks:
            raise EmptyDocumentError("No text content could be extracted from the PDF")
            
        logger.info(f"Successfully extracted {len(chunks)} chunks from PDF")
        return chunks

    async def get_document_status(self, document_id: str) -> Dict:
        """Get the current status of document processing"""
        if document_id not in self.processing_status:
            return None
            
        return {
            "document_id": document_id,
            "status": self.processing_status[document_id],
            "metadata": self.document_metadata.get(document_id, {})
        }