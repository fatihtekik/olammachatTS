from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from pydantic import field_validator
import uuid
from passlib.context import CryptContext

if TYPE_CHECKING:
    from app.models.chat import ChatSession

# Создаем контекст для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserBase(SQLModel):
    """Базовая модель пользователя"""
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)
    is_admin: bool = Field(default=False)
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class User(UserBase, table=True):
    """Модель пользователя в базе данных"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    hashed_password: str
    
    # Связь с сессиями чата
    chat_sessions: List["ChatSession"] = Relationship(back_populates="user")
    
    # Метод для верификации пароля
    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)
    
    # Метод для хеширования пароля
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
