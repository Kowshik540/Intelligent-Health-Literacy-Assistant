

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    
    id: str
    filename: str
    file_type: str
    file_size: Optional[int] = None
    chunk_count: int
    status: str
    description: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    
    message: str
    document: DocumentResponse


class DocumentListResponse(BaseModel):
    
    total: int
    documents: list[DocumentResponse]
