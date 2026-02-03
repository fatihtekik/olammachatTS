"""
Полный сброс базы данных с использованием актуальных моделей.
Удаляет файл БД и создаёт заново все таблицы на основе SQLModel моделей.
"""
import os
import sys
from pathlib import Path

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel
from app.database.db import SQLALCHEMY_DATABASE_URL, engine, DB_PATH

# Импортируем ВСЕ модели для создания таблиц
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet,
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats,
    PlayerRatingHistory, Holiday, TriggerConfiguration,
    ScenarioStats, MatchScenario
)


def print_header(title: str):
    """Красивый заголовок"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def reset_database(force: bool = False):
    """
    Полный сброс базы данных.
    Удаляет файл БД и создаёт заново все таблицы.
    
    Args:
        force: Если True, пропускает подтверждение
        
    Returns:
        bool: True если успешно
    """
    print_header("ПОЛНЫЙ СБРОС БАЗЫ ДАННЫХ")
    
    print(f"📍 Путь к БД: {DB_PATH.absolute()}")
    
    # Проверяем существование БД
    if DB_PATH.exists():
        print(f"📊 Размер текущей БД: {DB_PATH.stat().st_size / 1024:.2f} KB")
    else:
        print("ℹ️ База данных не существует, будет создана новая")
    
    if not force:
        print("\n⚠️ ВНИМАНИЕ: Все данные будут БЕЗВОЗВРАТНО удалены!")
        confirm = input("❓ Продолжить сброс? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'да', 'д']:
            print("❌ Сброс отменён")
            return False
    
    try:
        # 1. Удаляем файл БД
        if DB_PATH.exists():
            print("\n🗑️  Удаление существующей базы данных...")
            os.remove(DB_PATH)
            print("   ✅ База данных удалена")
        
        # 2. Создаём все таблицы заново
        print("\n📋 Создание таблиц на основе моделей...")
        SQLModel.metadata.create_all(engine)
        
        # Выводим список созданных таблиц
        print("\n✅ Созданы следующие таблицы:")
        print("   👤 Пользователи:")
        print("      └─ users")
        print("   💬 Чаты:")
        print("      ├─ chat_sessions (чат-сессии)")
        print("      └─ chat_messages (сообщения)")
        print("   🎾 Игроки:")
        print("      ├─ player (игроки)")
        print("      ├─ playerstats (статистика игроков)")
        print("      ├─ playerperiodstats (статистика по периодам)")
        print("      └─ playerratinghistory (история рейтингов)")
        print("   🏓 Матчи:")
        print("      ├─ match (матчи)")
        print("      ├─ matchset (сеты)")
        print("      ├─ matchcriticalmoment (критические моменты)")
        print("      └─ matchscenario (связи матч-сценарий)")
        print("   ⚡ Аналитика:")
        print("      ├─ playertrigger (триггеры игроков)")
        print("      └─ scenariostats (статистика сценариев)")
        print("   🏆 Лиги:")
        print("      └─ league (лиги)")
        print("   ⚙️ Конфигурация:")
        print("      ├─ holiday (праздники)")
        print("      └─ triggerconfiguration (настройки триггеров)")
        
        print_header("СБРОС УСПЕШНО ЗАВЕРШЁН")
        print(f"\n✨ База данных готова к использованию!")
        print(f"📍 Путь: {DB_PATH.absolute()}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при сбросе базы данных: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Точка входа CLI"""
    force = '--force' in sys.argv or '-f' in sys.argv
    
    success = reset_database(force=force)
    
    if success:
        print("\n🎉 Сброс выполнен успешно!")
        sys.exit(0)
    else:
        print("\n💥 Ошибка при сбросе!")
        sys.exit(1)


if __name__ == "__main__":
    main()
