"""
Проверка структуры и статистики базы данных SportAI
Показывает информацию о всех таблицах и их содержимом
"""
import sys
import os
from pathlib import Path

# Устанавливаем кодировку UTF-8 для вывода
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    sys.stdout.reconfigure(encoding='utf-8')

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
from sqlalchemy import inspect, text
import os

def check_database_file():
    """Проверка существования файла БД"""
    db_path = backend_dir / "ollamachat.db"
    
    print("📁 Файл базы данных:")
    if db_path.exists():
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"   ✓ {db_path}")
        print(f"   📊 Размер: {size_mb:.2f} MB")
        return True
    else:
        print(f"   ❌ Файл не найден: {db_path}")
        print("   💡 Используйте 'python database_tools/init_database.py' для создания БД")
        return False

def check_tables():
    """Проверка существования всех таблиц"""
    print("\n📋 Таблицы в базе данных:")
    
    try:
        with SessionLocal() as session:
            inspector = inspect(session.bind)
            existing_tables = inspector.get_table_names()
            
            expected_tables = [
                "user", "chatsession", "chatmessage",
                "player", "playerstats", "league", "match", "matchset",
                "matchcriticalmoment", "playertrigger", "playerperiodstats",
                "playerratinghistory", "holiday", "triggerconfiguration"
            ]
            
            for table in expected_tables:
                if table in existing_tables:
                    print(f"   ✓ {table}")
                else:
                    print(f"   ❌ {table} (отсутствует)")
            
            # Дополнительные таблицы
            extra_tables = set(existing_tables) - set(expected_tables)
            if extra_tables:
                print("\n   ℹ️  Дополнительные таблицы:")
                for table in extra_tables:
                    print(f"      • {table}")
                    
    except Exception as e:
        print(f"   ❌ Ошибка при проверке таблиц: {e}")

def get_table_stats():
    """Статистика по количеству записей в таблицах"""
    print("\n📊 Статистика данных:")
    
    try:
        with SessionLocal() as session:
            stats = {
                "Пользователи": session.query(User).count(),
                "Сессии чата": session.query(ChatSession).count(),
                "Сообщения чата": session.query(ChatMessage).count(),
                "Игроки": session.query(Player).count(),
                "Статистика игроков": session.query(PlayerStats).count(),
                "Лиги": session.query(League).count(),
                "Матчи": session.query(Match).count(),
                "Сеты": session.query(MatchSet).count(),
                "Критические моменты": session.query(MatchCriticalMoment).count(),
                "Триггеры": session.query(PlayerTrigger).count(),
                "Статистика по периодам": session.query(PlayerPeriodStats).count(),
                "История рейтингов": session.query(PlayerRatingHistory).count(),
                "Праздники": session.query(Holiday).count(),
                "Конфигурации триггеров": session.query(TriggerConfiguration).count(),
            }
            
            max_label_len = max(len(label) for label in stats.keys())
            for label, count in stats.items():
                print(f"   {label:<{max_label_len}} : {count:>6}")
                
            # Дополнительная статистика
            print("\n📈 Дополнительная информация:")
            
            # Активные триггеры
            active_triggers = session.query(PlayerTrigger).filter(
                PlayerTrigger.is_active == True
            ).count()
            print(f"   Активные триггеры: {active_triggers}")
            
            # Средний рейтинг игроков
            from sqlalchemy import func
            avg_rating = session.query(func.avg(Player.current_rating)).scalar()
            if avg_rating:
                print(f"   Средний рейтинг игроков: {avg_rating:.2f}")
            
            # Последний загруженный матч
            last_match = session.query(Match).order_by(
                Match.created_at.desc()
            ).first()
            if last_match:
                print(f"   Последний матч: {last_match.date} ({last_match.created_at})")
            
    except Exception as e:
        print(f"   ❌ Ошибка при получении статистики: {e}")

def check_integrity():
    """Проверка целостности данных"""
    print("\n🔍 Проверка целостности данных:")
    
    try:
        with SessionLocal() as session:
            issues = []
            
            # 1. Игроки без статистики
            players_without_stats = session.query(Player).outerjoin(
                PlayerStats
            ).filter(PlayerStats.id == None).count()
            
            if players_without_stats > 0:
                issues.append(f"⚠️  {players_without_stats} игроков без статистики")
            
            # 2. Матчи без победителя
            matches_without_winner = session.query(Match).filter(
                Match.winner_id == None
            ).count()
            
            if matches_without_winner > 0:
                issues.append(f"⚠️  {matches_without_winner} матчей без победителя")
            
            # 3. Матчи с некорректным счётом
            matches_with_bad_score = session.query(Match).filter(
                (Match.sets_player1 == None) | (Match.sets_player2 == None)
            ).count()
            
            if matches_with_bad_score > 0:
                issues.append(f"⚠️  {matches_with_bad_score} матчей с некорректным счётом")
            
            # 4. Дублирующиеся SL-ID
            duplicate_sl_ids = session.execute(text("""
                SELECT match_sl_id, COUNT(*) as cnt
                FROM match
                WHERE match_sl_id IS NOT NULL
                GROUP BY match_sl_id
                HAVING COUNT(*) > 1
            """)).fetchall()
            
            if duplicate_sl_ids:
                issues.append(f"⚠️  {len(duplicate_sl_ids)} дублирующихся SL-ID")
            
            if issues:
                for issue in issues:
                    print(f"   {issue}")
            else:
                print("   ✅ Проблем не обнаружено")
                
    except Exception as e:
        print(f"   ❌ Ошибка при проверке целостности: {e}")

def main():
    """Главная функция проверки БД"""
    print("="*60)
    print("🔧 ПРОВЕРКА БАЗЫ ДАННЫХ SPORTAI")
    print("="*60)
    
    if not check_database_file():
        return
    
    check_tables()
    get_table_stats()
    check_integrity()
    
    print("\n" + "="*60)
    print("✨ Проверка завершена")
    print("="*60)

if __name__ == "__main__":
    main()
