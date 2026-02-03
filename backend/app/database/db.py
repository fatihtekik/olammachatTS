from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, create_engine, Session
import logging
from pathlib import Path

# Импортируем все модели для создания таблиц
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet, 
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats, 
    PlayerRatingHistory, Holiday, TriggerConfiguration,
    ScenarioStats, MatchScenario
)

# Определяем абсолютный путь к БД в папке backend
BACKEND_DIR = Path(__file__).parent.parent.parent  # backend/
DB_PATH = BACKEND_DIR / "ollamachat.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Создание движка SQLAlchemy
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для инициализации моделей БД
def init_db():
    try:
        # Создаем таблицы
        SQLModel.metadata.create_all(bind=engine)
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Error initializing database: {e}")
