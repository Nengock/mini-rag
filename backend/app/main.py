from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
import logging
import os
import psutil
import torch
import gc
from app.utils.error_handling import (
    APIError,
    PDFProcessingError,
    api_error_handler,
    pdf_processing_error_handler,
    validation_exception_handler,
    general_exception_handler
)
from app.utils.security import SecurityMiddleware, APIKeyMiddleware
from app.utils.rate_limit import rate_limit_middleware
from app.utils.monitoring import system_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Environment variables
MODEL_DEVICE = os.getenv("MODEL_DEVICE", "cpu")
TORCH_THREADS = int(os.getenv("TORCH_THREADS", "4"))
MAX_UPLOAD_SIZE = int(os.getenv("MAX_UPLOAD_SIZE", "10485760"))  # 10MB default

# Configure torch threads
torch.set_num_threads(TORCH_THREADS)

app = FastAPI(
    title="PDF-RAG API",
    description="API for PDF document processing and question answering",
    version="1.0.0"
)

# Add security middleware first
app.add_middleware(SecurityMiddleware, 
    rate_limit_requests=int(os.getenv("RATE_LIMIT", "60")),
    allowed_hosts=os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
)

# Add API key middleware if API_KEY is configured
if os.getenv("API_KEY"):
    app.add_middleware(APIKeyMiddleware)

# Register exception handlers
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(PDFProcessingError, pdf_processing_error_handler)
app.add_exception_handler(Exception, general_exception_handler)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost,http://localhost:80").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    metrics = system_monitor.start_request(
        path=request.url.path,
        method=request.method
    )
    
    try:
        response = await call_next(request)
        system_monitor.end_request(metrics, status_code=response.status_code)
        return response
    except Exception as e:
        system_monitor.end_request(metrics, status_code=500, error=str(e))
        raise

def get_memory_usage():
    """Get current memory usage statistics"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    stats = {
        "rss": memory_info.rss / (1024 * 1024),  # RSS in MB
        "vms": memory_info.vms / (1024 * 1024),  # VMS in MB
        "percent": process.memory_percent(),
        "cpu_percent": process.cpu_percent(),
    }
    
    # Add GPU stats if available
    if torch.cuda.is_available():
        stats.update({
            "gpu_memory_allocated": torch.cuda.memory_allocated() / (1024 * 1024),  # MB
            "gpu_memory_reserved": torch.cuda.memory_reserved() / (1024 * 1024),  # MB
            "gpu_max_memory": torch.cuda.max_memory_allocated() / (1024 * 1024),  # MB
        })
        
    return stats

@app.middleware("http")
async def check_file_size(request: Request, call_next):
    if request.url.path == "/api/documents/upload":
        try:
            content_length = int(request.headers.get("content-length", "0"))
            if content_length > MAX_UPLOAD_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "detail": f"File too large. Maximum size allowed is {MAX_UPLOAD_SIZE/1024/1024:.1f}MB"
                    }
                )
        except ValueError:
            pass
    return await call_next(request)

@app.get("/api/health")
async def health_check():
    # Run garbage collection
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return {
        "status": "healthy",
        "config": {
            "model_device": MODEL_DEVICE,
            "torch_threads": TORCH_THREADS,
            "max_upload_size": MAX_UPLOAD_SIZE
        },
        "memory": get_memory_usage(),
        "system": {
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "memory_total": psutil.virtual_memory().total / (1024 * 1024),  # MB
            "memory_available": psutil.virtual_memory().available / (1024 * 1024),  # MB
            "gpu_available": torch.cuda.is_available(),
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        }
    }

# Include API routes
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)