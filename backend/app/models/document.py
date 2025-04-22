from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class DocumentChunk(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    chunk_id: str
    text: str = Field(..., min_length=1)
    page_number: int = Field(..., ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    document_id: str
    filename: str
    status: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=lambda: {
        "processed_at": datetime.utcnow().isoformat(),
        "chunk_count": 0,
        "total_pages": 0
    })

    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = {'uploaded', 'processing', 'completed', 'error'}
        if not any(v.startswith(status) for status in allowed_statuses):
            raise ValueError(f"Invalid status. Must be one of: {allowed_statuses}")
        return v

    @validator('filename')
    def validate_filename(cls, v):
        if not v.lower().endswith('.pdf'):
            raise ValueError("Only PDF files are supported")
        return v