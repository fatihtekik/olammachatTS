"""
Скрипт для создания новой базы данных с нуля.
Удаляет старую БД и создает все таблицы заново.
"""
import os
import sys
from sqlmodel import SQLModel, create_engine

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(__file__))

# Импортируем все модели для создания таблиц
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet, 
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats, 
    PlayerRatingHistory, Holiday, TriggerConfiguration
)

# Путь к базе данных
DB_PATH = "./ollamachat.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

def create_new_database():
    """Создает новую базу данных с нуля"""
    
    print("="*60)
    print("СОЗДАНИЕ НОВОЙ БАЗЫ ДАННЫХ")
    print("="*60)
    
    # Проверяем существование старой БД
    if os.path.exists(DB_PATH):
        print(f"\n⚠️  Найдена существующая база данных: {DB_PATH}")
        response = input("Удалить старую БД и создать новую? (yes/no): ")
        
        if response.lower() not in ['yes', 'y', 'да']:
            print("Операция отменена.")
            return
        
        # Удаляем старую БД
        os.remove(DB_PATH)
        print(f"✅ Старая база данных удалена.")
    
    # Создаем движок SQLAlchemy
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=False  # Установите True для отладки SQL запросов
    )
    
    print("\n📋 Создание таблиц...")
    
    # Создаем все таблицы
    SQLModel.metadata.create_all(engine)
    
    print("\n✅ База данных успешно создана!")
    print(f"📍 Путь: {os.path.abspath(DB_PATH)}")
    
    print("\n📊 Созданные таблицы:")
    tables = [
        "user - Пользователи системы",
        "chatsession - Сессии чатов",
        "chatmessage - Сообщения в чатах",
        "player - Игроки",
        "playerstats - Статистика игроков",
        "league - Лиги",
        "match - Матчи",
        "matchset - Сеты матчей",
        "matchcriticalmoment - Критические моменты матчей",
        "playertrigger - Триггеры игроков",
        "playerperiodstats - Статистика игроков по периодам",
        "playerratinghistory - История рейтингов игроков",
        "holiday - Праздники",
        "triggerconfiguration - Конфигурация триггеров"
    ]
    
    for table in tables:
        print(f"  ✓ {table}")
    
    print("\n" + "="*60)
    print("База данных готова к использованию!")
    print("="*60)

if __name__ == "__main__":
    create_new_database()
