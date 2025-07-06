import os
import secrets
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    🔧 ГЛАВНЫЙ ФАЙЛ НАСТРОЕК ПРИЛОЖЕНИЯ
    
    Здесь можно изменить все основные параметры:
    - Где находится Ollama (OLLAMA_API_URL) 
    - Какие сайты могут обращаться к API (CORS)
    - Где хранится база данных 
    - Настройки безопасности
    
    Для чайников: если что-то не работает, сначала проверьте эти настройки!
    """
    
    # 📱 Основные настройки приложения
    APP_NAME: str = "OllamaChat"  # Название вашего приложения
    API_V1_STR: str = "/api/v1"   # Префикс для всех API запросов
    SECRET_KEY: str = secrets.token_urlsafe(32)  # Секретный ключ для токенов (генерируется автоматически)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # Токены действуют 7 дней
    
    # 🌐 CORS настройки - разрешает фронтенду обращаться к бэкенду
    # Если фронтенд на другом порту не работает, добавьте его сюда!
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",   # React стандартный порт
        "http://localhost:8080",   # Альтернативный порт  
        "http://localhost:5173",   # Vite стандартный порт
        "http://localhost:5174",   # Vite альтернативный порт
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080", 
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:5174",
        "*"  # 🚨 ВНИМАНИЕ: разрешает доступ ВСЕМ (небезопасно для продакшена!)
    ]
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        # Магия для обработки CORS настроек из переменных окружения
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # 🗄️ База данных - здесь хранятся чаты, пользователи и пр.
    DATABASE_URL: str = "sqlite:///./ollamachat.db"  # SQLite файл в текущей папке
    
    # 🤖 ГЛАВНАЯ НАСТРОЙКА OLLAMA!
    # Если Ollama запущена на другом компьютере или порту - меняйте здесь!
    OLLAMA_API_URL: str = "http://localhost:11434"  # Стандартный адрес локальной Ollama
    
    class Config:
        case_sensitive = True  # Настройки чувствительны к регистру


# 🌟 Объект settings используется во всем приложении для получения настроек
settings = Settings() 

# 💡 ПОДСКАЗКИ ДЛЯ ЧАЙНИКОВ:
# 1. Не работает соединение с Ollama? Проверьте OLLAMA_API_URL
# 2. Фронтенд не может подключиться? Добавьте его URL в BACKEND_CORS_ORIGINS  
# 3. Хотите использовать PostgreSQL вместо SQLite? Измените DATABASE_URL
# 4. Для продакшена уберите "*" из CORS и добавьте только нужные домены!
