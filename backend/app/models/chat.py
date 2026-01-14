from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel, Relationship, JSON
import uuid

class ChatSessionBase(SQLModel):
    """Базовая модель сессии чата"""
    title: str
    model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ChatMessage(SQLModel, table=True):
    """Модель сообщения чата"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(foreign_key="chatsession.id")
    role: str  # 'user' или 'assistant'
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[bool] = Field(default=False)
    attachments: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON)
    
    session: "ChatSession" = Relationship(back_populates="messages")

class ChatSession(ChatSessionBase, table=True):
    """Модель сессии чата в базе данных"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user.id")
    
    # Связи с другими моделями
    user: "User" = Relationship(back_populates="chat_sessions")
    messages: List[ChatMessage] = Relationship(back_populates="session")
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование сессии в словарь для отправки на фронтенд"""
        return {
            "id": self.id,
            "title": self.title,
            "model": self.model,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "error": msg.error,
                    "attachments": msg.attachments or []
                }
                for msg in self.messages
            ]
        }
