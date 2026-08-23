

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    
    username: str = Field(min_length=3, max_length=100, examples=["john_doe"])
    email: EmailStr = Field(examples=["john@example.com"])


class UserResponse(BaseModel):
    
    id: str
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
