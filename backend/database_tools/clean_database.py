"""
Полная очистка базы данных SportAI
ВНИМАНИЕ: Удаляет ВСЕ данные из всех таблиц!
"""
import sys
import os
from pathlib import Path

# Добавляем корневую директорию backend в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.database.db import SessionLocal
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet,
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats,
    PlayerRatingHistory, Holiday, TriggerConfiguration
)

def confirm_action():
    """Запрос подтверждения от пользователя"""
    print("⚠️  ВНИМАНИЕ! Эта операция удалит ВСЕ данные из базы данных!")
    print("   - Все матчи и сеты")
    print("   - Всех игроков и их статистику")
    print("   - Все триггеры и анализы")
    print("   - Историю чатов")
    print("   - Все пользователи")
    print("")
    response = input("Вы уверены? Введите 'YES' для подтверждения: ")
    return response == "YES"

def clean_database():
    """Удаление всех данных из всех таблиц"""
    if not confirm_action():
        print("❌ Операция отменена пользователем")
        return
    
    print("\n🗑️  Очистка базы данных...")
    
    try:
        with SessionLocal() as session:
            # Порядок удаления важен из-за foreign key constraints
            
            # 1. Удаляем чат данные
            print("   🗑️  Удаление сообщений чата...")
            session.query(ChatMessage).delete()
            session.commit()
            
            print("   🗑️  Удаление сессий чата...")
            session.query(ChatSession).delete()
            session.commit()
            
            print("   🗑️  Удаление пользователей...")
            session.query(User).delete()
            session.commit()
            
            # 2. Удаляем триггеры и статистику игроков
            print("   🗑️  Удаление триггеров игроков...")
            session.query(PlayerTrigger).delete()
            session.commit()
            
            print("   🗑️  Удаление критических моментов...")
            session.query(MatchCriticalMoment).delete()
            session.commit()
            
            print("   🗑️  Удаление сетов матчей...")
            session.query(MatchSet).delete()
            session.commit()
            
            # 3. Удаляем матчи
            print("   🗑️  Удаление матчей...")
            session.query(Match).delete()
            session.commit()
            
            # 4. Удаляем историю рейтингов
            print("   🗑️  Удаление истории рейтингов...")
            session.query(PlayerRatingHistory).delete()
            session.commit()
            
            # 5. Удаляем статистику по периодам
            print("   🗑️  Удаление статистики по периодам...")
            session.query(PlayerPeriodStats).delete()
            session.commit()
            
            # 6. Удаляем статистику игроков
            print("   🗑️  Удаление статистики игроков...")
            session.query(PlayerStats).delete()
            session.commit()
            
            # 7. Удаляем игроков
            print("   🗑️  Удаление игроков...")
            session.query(Player).delete()
            session.commit()
            
            # 8. Удаляем лиги
            print("   🗑️  Удаление лиг...")
            session.query(League).delete()
            session.commit()
            
            # 9. Удаляем праздники
            print("   🗑️  Удаление праздников...")
            session.query(Holiday).delete()
            session.commit()
            
            # 10. Удаляем конфигурации триггеров
            print("   🗑️  Удаление конфигураций триггеров...")
            session.query(TriggerConfiguration).delete()
            session.commit()
            
        print("\n✅ База данных полностью очищена!")
        print("💡 Используйте 'python database_tools/init_database.py' для пересоздания таблиц")
        
    except Exception as e:
        print(f"❌ Ошибка при очистке БД: {e}")
        raise

if __name__ == "__main__":
    clean_database()
