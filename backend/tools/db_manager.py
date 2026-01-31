"""
Универсальный менеджер базы данных.
Позволяет просматривать статистику, очищать данные, создавать/удалять БД.
"""
import os
import sys
from pathlib import Path

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import SQLModel, Session, select
from app.database.db import SQLALCHEMY_DATABASE_URL, engine

# Импортируем модели
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet,
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats,
    PlayerRatingHistory, Holiday, TriggerConfiguration,
    ScenarioStats, MatchScenario
)

DB_PATH = Path(__file__).parent.parent / "ollamachat.db"


def print_header(title: str):
    """Красивый заголовок"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def get_db_stats() -> dict | None:
    """
    Получает статистику записей в БД.
    
    Returns:
        dict: Словарь с количеством записей по таблицам или None если БД не существует
    """
    if not DB_PATH.exists():
        return None
    
    with Session(engine) as session:
        try:
            return {
                'users': len(session.exec(select(User)).all()),
                'chat_sessions': len(session.exec(select(ChatSession)).all()),
                'chat_messages': len(session.exec(select(ChatMessage)).all()),
                'players': len(session.exec(select(Player)).all()),
                'player_stats': len(session.exec(select(PlayerStats)).all()),
                'leagues': len(session.exec(select(League)).all()),
                'matches': len(session.exec(select(Match)).all()),
                'match_sets': len(session.exec(select(MatchSet)).all()),
                'critical_moments': len(session.exec(select(MatchCriticalMoment)).all()),
                'player_triggers': len(session.exec(select(PlayerTrigger)).all()),
                'period_stats': len(session.exec(select(PlayerPeriodStats)).all()),
                'rating_history': len(session.exec(select(PlayerRatingHistory)).all()),
                'holidays': len(session.exec(select(Holiday)).all()),
                'trigger_configs': len(session.exec(select(TriggerConfiguration)).all()),
                'scenario_stats': len(session.exec(select(ScenarioStats)).all()),
                'match_scenarios': len(session.exec(select(MatchScenario)).all())
            }
        except Exception as e:
            print(f"⚠️ Ошибка получения статистики: {e}")
            return None


def show_stats():
    """Выводит статистику БД в консоль"""
    print_header("СТАТИСТИКА БАЗЫ ДАННЫХ")
    
    if not DB_PATH.exists():
        print("❌ База данных не существует!")
        print(f"   Путь: {DB_PATH.absolute()}")
        return
    
    # Информация о файле
    size_kb = DB_PATH.stat().st_size / 1024
    print(f"\n📁 Файл БД: {DB_PATH.name}")
    print(f"📍 Путь: {DB_PATH.absolute()}")
    print(f"📊 Размер: {size_kb:.2f} KB")
    
    stats = get_db_stats()
    
    if not stats:
        print("\n⚠️ Не удалось получить статистику")
        return
    
    print("\n👥 ПОЛЬЗОВАТЕЛИ И ЧАТЫ:")
    print(f"  └─ Пользователей: {stats['users']}")
    print(f"  └─ Сессий чатов: {stats['chat_sessions']}")
    print(f"  └─ Сообщений: {stats['chat_messages']}")
    
    print("\n🎾 ИГРОКИ:")
    print(f"  └─ Игроков: {stats['players']}")
    print(f"  └─ Статистик игроков: {stats['player_stats']}")
    print(f"  └─ Лиг: {stats['leagues']}")
    
    print("\n🏓 МАТЧИ:")
    print(f"  └─ Матчей: {stats['matches']}")
    print(f"  └─ Сетов: {stats['match_sets']}")
    print(f"  └─ Критических моментов: {stats['critical_moments']}")
    
    print("\n⚡ ТРИГГЕРЫ И АНАЛИТИКА:")
    print(f"  └─ Триггеров игроков: {stats['player_triggers']}")
    print(f"  └─ Статистика по периодам: {stats['period_stats']}")
    print(f"  └─ История рейтингов: {stats['rating_history']}")
    print(f"  └─ Статистика сценариев: {stats['scenario_stats']}")
    print(f"  └─ Связей матч-сценарий: {stats['match_scenarios']}")
    
    print("\n⚙️ КОНФИГУРАЦИЯ:")
    print(f"  └─ Праздников: {stats['holidays']}")
    print(f"  └─ Настроек триггеров: {stats['trigger_configs']}")
    
    total = sum(stats.values())
    print(f"\n📊 ВСЕГО записей: {total}")


def delete_database() -> bool:
    """
    Полное удаление файла БД.
    
    Returns:
        bool: True если успешно
    """
    print_header("УДАЛЕНИЕ БАЗЫ ДАННЫХ")
    
    if not DB_PATH.exists():
        print("ℹ️ База данных не существует (нечего удалять)")
        return True
    
    print(f"📍 Путь к БД: {DB_PATH.absolute()}")
    print("\n⚠️ ВНИМАНИЕ: Файл БД будет БЕЗВОЗВРАТНО удалён!")
    
    confirm = input("\n❓ Продолжить удаление? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', 'да', 'д']:
        print("❌ Операция отменена")
        return False
    
    try:
        os.remove(DB_PATH)
        print("✅ База данных успешно удалена!")
        return True
    except Exception as e:
        print(f"❌ Ошибка при удалении: {e}")
        return False


def create_database() -> bool:
    """
    Создание новой БД с нуля.
    
    Returns:
        bool: True если успешно
    """
    print_header("СОЗДАНИЕ НОВОЙ БАЗЫ ДАННЫХ")
    
    if DB_PATH.exists():
        print(f"⚠️ База данных уже существует: {DB_PATH}")
        confirm = input("Удалить существующую и создать новую? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'да', 'д']:
            print("❌ Операция отменена")
            return False
        os.remove(DB_PATH)
        print("✅ Старая база удалена")
    
    print("\n📋 Создание таблиц на основе моделей...")
    SQLModel.metadata.create_all(engine)
    
    print("✅ База данных создана!")
    print(f"📍 Путь: {DB_PATH.absolute()}")
    return True


def clear_matches_only() -> bool:
    """
    Очистка только матчей и связанных данных (игроки сохраняются).
    
    Returns:
        bool: True если успешно
    """
    print_header("ОЧИСТКА МАТЧЕЙ (игроки сохраняются)")
    
    if not DB_PATH.exists():
        print("❌ База данных не существует!")
        return False
    
    with Session(engine) as session:
        matches = len(session.exec(select(Match)).all())
        sets = len(session.exec(select(MatchSet)).all())
        triggers = len(session.exec(select(PlayerTrigger)).all())
        moments = len(session.exec(select(MatchCriticalMoment)).all())
        match_scenarios = len(session.exec(select(MatchScenario)).all())
        
        print(f"\n📊 Будет удалено:")
        print(f"  └─ Матчей: {matches}")
        print(f"  └─ Сетов: {sets}")
        print(f"  └─ Триггеров: {triggers}")
        print(f"  └─ Критических моментов: {moments}")
        print(f"  └─ Связей матч-сценарий: {match_scenarios}")
        
        if matches == 0:
            print("\n✅ Матчей в БД нет!")
            return True
        
        confirm = input("\n❓ Продолжить очистку? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'да', 'д']:
            print("❌ Операция отменена")
            return False
        
        # Удаляем в правильном порядке (от зависимых к независимым)
        print("\n🗑️ Удаление данных...")
        
        # 1. Триггеры
        for trigger in session.exec(select(PlayerTrigger)).all():
            session.delete(trigger)
        print("   ✅ Триггеры удалены")
        
        # 2. Связи матч-сценарий
        for ms in session.exec(select(MatchScenario)).all():
            session.delete(ms)
        print("   ✅ Связи матч-сценарий удалены")
        
        # 3. Критические моменты
        for moment in session.exec(select(MatchCriticalMoment)).all():
            session.delete(moment)
        print("   ✅ Критические моменты удалены")
        
        # 4. Сеты
        for match_set in session.exec(select(MatchSet)).all():
            session.delete(match_set)
        print("   ✅ Сеты удалены")
        
        # 5. Матчи
        for match in session.exec(select(Match)).all():
            session.delete(match)
        print("   ✅ Матчи удалены")
        
        session.commit()
        
    print("\n✅ Очистка матчей завершена! Игроки сохранены.")
    return True


def clear_all_data() -> bool:
    """
    Полная очистка всех данных (таблицы остаются).
    
    Returns:
        bool: True если успешно
    """
    print_header("ПОЛНАЯ ОЧИСТКА ВСЕХ ДАННЫХ")
    
    if not DB_PATH.exists():
        print("❌ База данных не существует!")
        return False
    
    stats = get_db_stats()
    if not stats:
        print("⚠️ Не удалось получить статистику")
        return False
    
    total = sum(stats.values())
    
    print(f"\n📊 Будет удалено {total} записей из всех таблиц")
    print("⚠️ Структура таблиц сохранится, но все данные будут удалены!")
    
    confirm = input("\n❓ Продолжить полную очистку? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', 'да', 'д']:
        print("❌ Операция отменена")
        return False
    
    print("\n🗑️ Удаление данных...")
    
    with Session(engine) as session:
        # Удаляем в правильном порядке (от зависимых к независимым)
        
        # Чаты
        for msg in session.exec(select(ChatMessage)).all():
            session.delete(msg)
        for sess in session.exec(select(ChatSession)).all():
            session.delete(sess)
        print("   ✅ Чаты удалены")
        
        # Триггеры и аналитика
        for trigger in session.exec(select(PlayerTrigger)).all():
            session.delete(trigger)
        print("   ✅ Триггеры удалены")
        
        # Связи матч-сценарий
        for ms in session.exec(select(MatchScenario)).all():
            session.delete(ms)
        print("   ✅ Связи матч-сценарий удалены")
        
        # Критические моменты
        for moment in session.exec(select(MatchCriticalMoment)).all():
            session.delete(moment)
        print("   ✅ Критические моменты удалены")
        
        # Сеты
        for match_set in session.exec(select(MatchSet)).all():
            session.delete(match_set)
        print("   ✅ Сеты удалены")
        
        # Матчи
        for match in session.exec(select(Match)).all():
            session.delete(match)
        print("   ✅ Матчи удалены")
        
        # Статистика сценариев
        for ss in session.exec(select(ScenarioStats)).all():
            session.delete(ss)
        print("   ✅ Статистика сценариев удалена")
        
        # Статистика игроков
        for ps in session.exec(select(PlayerStats)).all():
            session.delete(ps)
        for pp in session.exec(select(PlayerPeriodStats)).all():
            session.delete(pp)
        for ph in session.exec(select(PlayerRatingHistory)).all():
            session.delete(ph)
        print("   ✅ Статистика игроков удалена")
        
        # Игроки
        for player in session.exec(select(Player)).all():
            session.delete(player)
        print("   ✅ Игроки удалены")
        
        # Лиги
        for league in session.exec(select(League)).all():
            session.delete(league)
        print("   ✅ Лиги удалены")
        
        # Конфигурация
        for holiday in session.exec(select(Holiday)).all():
            session.delete(holiday)
        for config in session.exec(select(TriggerConfiguration)).all():
            session.delete(config)
        print("   ✅ Конфигурация удалена")
        
        # Пользователи
        for user in session.exec(select(User)).all():
            session.delete(user)
        print("   ✅ Пользователи удалены")
        
        session.commit()
    
    print("\n✅ Все данные успешно удалены!")
    return True


def add_column_if_missing():
    """Добавляет недостающие колонки в таблицы (миграция)"""
    print_header("ПРОВЕРКА И ДОБАВЛЕНИЕ КОЛОНОК")
    
    if not DB_PATH.exists():
        print("❌ База данных не существует!")
        return False
    
    import sqlite3
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверяем колонку is_pair в playertrigger
    cursor.execute("PRAGMA table_info(playertrigger)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'is_pair' not in columns:
        print("⚠️ Колонка 'is_pair' отсутствует в playertrigger")
        print("📋 Добавление колонки...")
        cursor.execute("ALTER TABLE playertrigger ADD COLUMN is_pair BOOLEAN DEFAULT 1")
        conn.commit()
        print("✅ Колонка 'is_pair' добавлена!")
    else:
        print("✅ Колонка 'is_pair' уже существует")
    
    conn.close()
    return True


def main_menu():
    """Интерактивное меню"""
    while True:
        print_header("УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ")
        print("\n1. 📊 Показать статистику БД")
        print("2. 🆕 Создать новую БД (с удалением старой)")
        print("3. 🏓 Очистить только матчи (игроки остаются)")
        print("4. 🗑️ Очистить все данные (таблицы остаются)")
        print("5. 💥 Полное удаление БД")
        print("6. 🔧 Добавить недостающие колонки (миграция)")
        print("0. 🚪 Выход")
        
        choice = input("\n➡️ Выберите действие (0-6): ").strip()
        
        if choice == '0':
            print("\n👋 До свидания!")
            break
        elif choice == '1':
            show_stats()
        elif choice == '2':
            create_database()
        elif choice == '3':
            clear_matches_only()
        elif choice == '4':
            clear_all_data()
        elif choice == '5':
            delete_database()
        elif choice == '6':
            add_column_if_missing()
        else:
            print("❌ Неверный выбор!")
        
        input("\n⏎ Нажмите Enter для продолжения...")


def main():
    """Точка входа CLI"""
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        actions = {
            'stats': show_stats,
            'create': create_database,
            'clear-matches': clear_matches_only,
            'clear-all': clear_all_data,
            'delete': delete_database,
            'migrate': add_column_if_missing
        }
        
        if action in actions:
            actions[action]()
        else:
            print(f"❌ Неизвестная команда: {action}")
            print("\n📋 Доступные команды:")
            print("  python -m tools.db_manager stats         - показать статистику")
            print("  python -m tools.db_manager create        - создать новую БД")
            print("  python -m tools.db_manager clear-matches - очистить матчи")
            print("  python -m tools.db_manager clear-all     - очистить все данные")
            print("  python -m tools.db_manager delete        - удалить БД")
            print("  python -m tools.db_manager migrate       - добавить колонки")
    else:
        main_menu()


if __name__ == "__main__":
    main()
