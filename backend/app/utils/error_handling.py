from fastapi import Request, status
from fastapi.responses import JSONResponse
from typing import Union, Dict, Any
import logging
from app.core.pdf_processor import PDFProcessingError, PDFCorruptedError, EmptyDocumentError

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base API error class"""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Union[Dict[str, Any], None] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class RateLimitError(APIError):
    """Raised when rate limit is exceeded"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS)

class ValidationError(APIError):
    """Raised for validation errors"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)

async def api_error_handler(request: Request, exc: APIError):
    """Handle API errors"""
    error_response = {
        "error": exc.message,
        "status_code": exc.status_code,
    }
    if exc.details:
        error_response["details"] = exc.details
    
    # Log error with context
    logger.error(
        f"API Error: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "details": exc.details
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

async def pdf_processing_error_handler(request: Request, exc: PDFProcessingError):
    """Handle PDF processing errors"""
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, PDFCorruptedError):
        message = "Invalid or corrupted PDF file"
    elif isinstance(exc, EmptyDocumentError):
        message = "PDF document contains no extractable text"
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Error processing PDF document"
    
    logger.error(
        f"PDF Processing Error: {str(exc)}",
        extra={
            "error_type": exc.__class__.__name__,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "error": message,
            "details": str(exc)
        }
    )

async def validation_exception_handler(request: Request, exc: Exception):
    """Handle validation errors"""
    logger.warning(
        f"Validation Error: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": str(exc)
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle any unhandled exceptions"""
    logger.error(
        f"Unhandled Exception: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if str(exc) else "An unexpected error occurred"
        }
    )