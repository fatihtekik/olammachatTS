from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать не менее 8 символов')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        # Простая валидация email
        if '@' not in v:
            raise ValueError('Некорректный email адрес')
        return v

class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    """Схема для ответа с данными пользователя"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
