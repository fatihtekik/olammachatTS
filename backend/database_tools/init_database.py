"""
Инициализация базы данных SportAI
Создает все таблицы согласно текущим моделям
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию backend в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database.db import engine
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet,
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats,
    PlayerRatingHistory, Holiday, TriggerConfiguration
)
from sqlmodel import SQLModel, Session, select
from datetime import datetime

def init_database():
    """Создание всех таблиц в базе данных"""
    print("🔧 Инициализация базы данных SportAI...")
    
    try:
        # Создание всех таблиц
        SQLModel.metadata.create_all(bind=engine)
        print("✅ Все таблицы успешно созданы!")
        
        # Проверка созданных таблиц
        print("\n📊 Созданные таблицы:")
        tables = [
            "User", "ChatSession", "ChatMessage",
            "Player", "PlayerStats", "League", "Match", "MatchSet",
            "MatchCriticalMoment", "PlayerTrigger", "PlayerPeriodStats",
            "PlayerRatingHistory", "Holiday", "TriggerConfiguration"
        ]
        for table in tables:
            print(f"   ✓ {table}")
        
        # Создание дефолтных конфигураций триггеров
        init_default_trigger_configs()
        
        print("\n✨ База данных готова к использованию!")
        print(f"📁 Файл БД: {backend_dir / 'ollamachat.db'}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании БД: {e}")
        raise

def init_default_trigger_configs():
    """Создание дефолтных конфигураций для триггеров"""
    print("\n⚙️  Создание конфигураций триггеров...")
    
    default_configs = [
        {
            "trigger_name": "losing_streaks",
            "is_enabled": True,
            "threshold_value": 3.0,
            "period_days": 30,
            "description": "Серия из 3+ поражений подряд"
        },
        {
            "trigger_name": "lead_collapse",
            "is_enabled": True,
            "threshold_value": 2.0,
            "period_days": 30,
            "description": "Потеря преимущества 2:0 в сетах"
        },
        {
            "trigger_name": "comeback_inability",
            "is_enabled": True,
            "threshold_value": 2.0,
            "period_days": 30,
            "description": "Неспособность отыграться с 0:2"
        },
        {
            "trigger_name": "losers_50_percent",
            "is_enabled": True,
            "threshold_value": 50.0,
            "period_days": 30,
            "description": "50%+ поражений за период"
        },
        {
            "trigger_name": "top_performers",
            "is_enabled": True,
            "threshold_value": 70.0,
            "period_days": 30,
            "description": "Высокая результативность (70%+ побед)"
        },
        {
            "trigger_name": "psychological_breakdown",
            "is_enabled": True,
            "threshold_value": 1.0,
            "period_days": 30,
            "description": "Психологический срыв в матче"
        },
        {
            "trigger_name": "pressure_situations",
            "is_enabled": True,
            "threshold_value": 1.0,
            "period_days": 30,
            "description": "Поведение в критических ситуациях"
        }
    ]
    
    with Session(engine) as session:
        # Проверяем, не созданы ли уже конфигурации
        existing = session.exec(select(TriggerConfiguration)).first()
        if existing:
            print("   ⚠️  Конфигурации уже существуют, пропуск...")
            return
        
        for config_data in default_configs:
            config = TriggerConfiguration(
                **config_data,
                updated_at=datetime.now()
            )
            session.add(config)
        
        session.commit()
        print(f"   ✓ Создано {len(default_configs)} конфигураций триггеров")

if __name__ == "__main__":
    init_database()
