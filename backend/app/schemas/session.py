from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class MessageBase(BaseModel):
    role: str
    content: str
    data: Optional[Any] = None

class Message(MessageBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    title: str

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatRequest(BaseModel):
    query: str

class ChatSession(ChatSessionBase):
    id: int
    user_id: int
    created_at: datetime
    messages: List[Message] = []
    
    class Config:
        from_attributes = True
