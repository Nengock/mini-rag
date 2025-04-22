from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional, Dict, Any

class Query(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    document_id: str
    context_window: Optional[int] = Field(4096, ge=512, le=8192)

    @validator('question')
    def validate_question(cls, v):
        if not v.strip():
            raise ValueError("Question cannot be empty")
        return v.strip()

class QueryResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any] = Field(default_factory=dict)