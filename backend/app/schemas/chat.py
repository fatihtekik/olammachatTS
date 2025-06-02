from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class MessageBase(BaseModel):
    """Базовая схема сообщения в чате"""
    role: str  # 'user' или 'assistant'
    content: str
    timestamp: Optional[datetime] = None
    error: Optional[bool] = False
    attachments: Optional[List[Dict[str, Any]]] = None

class MessageCreate(MessageBase):
    """Схема для создания сообщения"""
    pass

class MessageResponse(MessageBase):
    """Схема ответа с сообщением"""
    id: str
    session_id: str

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    """Базовая схема сессии чата"""
    title: str
    model: str

class ChatSessionCreate(ChatSessionBase):
    """Схема для создания сессии чата"""
    messages: Optional[List[MessageCreate]] = None

class MessagesUpdate(BaseModel):
    """Схема для массового обновления сообщений"""
    messages: List[MessageCreate]

class ChatSessionUpdate(BaseModel):
    """Схема для обновления сессии чата"""
    title: Optional[str] = None
    model: Optional[str] = None

class ChatSessionResponse(ChatSessionBase):
    """Схема ответа с сессией чата"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True
