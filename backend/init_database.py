"""
Универсальный скрипт инициализации базы данных
Создаёт все таблицы на основе моделей SQLModel
"""
import os
import sys
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import SQLModel, create_engine, Session
from app.database.db import SQLALCHEMY_DATABASE_URL, engine

# Импортируем все модели для создания таблиц
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet, 
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats, 
    PlayerRatingHistory, Holiday, TriggerConfiguration,
    ScenarioStats, MatchScenario
)

DB_PATH = "./ollamachat.db"


def print_header(title: str):
    """Красивый заголовок"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_existing_db() -> bool:
    """Проверяет наличие существующей БД"""
    return os.path.exists(DB_PATH)


def delete_existing_db():
    """Удаляет существующую БД"""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"✅ Старая база данных удалена: {DB_PATH}")
            return True
        except Exception as e:
            print(f"❌ Ошибка при удалении БД: {e}")
            return False
    return True


def create_all_tables():
    """Создаёт все таблицы в БД"""
    print("\n📋 Создание таблиц...")
    
    try:
        # Создаём все таблицы на основе метаданных SQLModel
        SQLModel.metadata.create_all(engine)
        
        print("\n✅ Созданы следующие таблицы:")
        print("   👤 Пользователи:")
        print("      └─ users")
        print("   💬 Чаты:")
        print("      ├─ chat_sessions")
        print("      └─ chat_messages")
        print("   🎾 Спортивные данные:")
        print("      ├─ players (игроки)")
        print("      ├─ player_stats (статистика игроков)")
        print("      ├─ leagues (лиги)")
        print("      ├─ matches (матчи)")
        print("      ├─ match_sets (сеты)")
        print("      ├─ match_critical_moments (критические моменты)")
        print("      ├─ player_triggers (триггеры)")
        print("      ├─ player_period_stats (статистика по периодам)")
        print("      ├─ player_rating_history (история рейтингов)")
        print("      ├─ scenario_stats (статистика сценариев)")
        print("      └─ match_scenarios (связи матч-сценарий)")
        print("   ⚙️ Конфигурация:")
        print("      ├─ holidays (праздники)")
        print("      └─ trigger_configurations (настройки триггеров)")
        
        return True
    except Exception as e:
        print(f"\n❌ Ошибка при создании таблиц: {e}")
        return False


def verify_database():
    """Проверяет корректность созданной БД"""
    print("\n🔍 Проверка базы данных...")
    
    try:
        with Session(engine) as session:
            # Проверяем возможность работы с каждой таблицей
            session.exec("SELECT COUNT(*) FROM users").one()
            session.exec("SELECT COUNT(*) FROM chat_sessions").one()
            session.exec("SELECT COUNT(*) FROM chat_messages").one()
            session.exec("SELECT COUNT(*) FROM players").one()
            session.exec("SELECT COUNT(*) FROM player_stats").one()
            session.exec("SELECT COUNT(*) FROM leagues").one()
            session.exec("SELECT COUNT(*) FROM matches").one()
            session.exec("SELECT COUNT(*) FROM match_sets").one()
            session.exec("SELECT COUNT(*) FROM match_critical_moments").one()
            session.exec("SELECT COUNT(*) FROM player_triggers").one()
            session.exec("SELECT COUNT(*) FROM player_period_stats").one()
            session.exec("SELECT COUNT(*) FROM player_rating_history").one()
            session.exec("SELECT COUNT(*) FROM holidays").one()
            session.exec("SELECT COUNT(*) FROM trigger_configurations").one()
            session.exec("SELECT COUNT(*) FROM scenario_stats").one()
            session.exec("SELECT COUNT(*) FROM match_scenarios").one()
            
        print("✅ Все таблицы успешно созданы и доступны!")
        return True
    except Exception as e:
        print(f"❌ Ошибка при проверке БД: {e}")
        return False


def init_database(force: bool = False):
    """
    Основная функция инициализации БД
    
    Args:
        force: Принудительное пересоздание БД без подтверждения
    """
    print_header("ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    
    # Проверяем существующую БД
    db_exists = check_existing_db()
    
    if db_exists:
        print(f"\n⚠️ База данных уже существует: {os.path.abspath(DB_PATH)}")
        
        if not force:
            confirm = input("\n❓ Удалить существующую и создать новую? (yes/no): ").strip().lower()
            if confirm not in ['yes', 'y', 'да']:
                print("❌ Операция отменена")
                return False
        
        if not delete_existing_db():
            return False
    
    # Создаём таблицы
    if not create_all_tables():
        return False
    
    # Проверяем корректность
    if not verify_database():
        return False
    
    print_header("УСПЕШНО ЗАВЕРШЕНО")
    print(f"\n✨ База данных готова к использованию!")
    print(f"📍 Путь: {os.path.abspath(DB_PATH)}")
    print(f"\n💡 Для управления БД используйте: python manage_db.py")
    
    return True


def main():
    """Точка входа"""
    if len(sys.argv) > 1:
        # Режим командной строки
        if sys.argv[1] == '--force' or sys.argv[1] == '-f':
            init_database(force=True)
        else:
            print("Использование:")
            print("  python init_database.py           - интерактивный режим")
            print("  python init_database.py --force   - пересоздать без подтверждения")
    else:
        # Интерактивный режим
        init_database(force=False)


if __name__ == "__main__":
    main()
