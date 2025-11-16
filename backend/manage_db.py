"""
Универсальный скрипт управления базой данных.
Позволяет сбрасывать, пересоздавать и очищать БД.
"""
import os
import sys
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import SQLModel, create_engine, Session, select
from app.database.db import SQLALCHEMY_DATABASE_URL, engine
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.match import (
    Player, PlayerStats, League, Match, MatchSet, 
    MatchCriticalMoment, PlayerTrigger, PlayerPeriodStats, 
    PlayerRatingHistory, Holiday, TriggerConfiguration,
    ScenarioStats, MatchScenario
)

DB_PATH = "./ollamachat.db"

def print_header(title):
    """Красивый заголовок"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def get_db_stats():
    """Получает статистику БД"""
    if not os.path.exists(DB_PATH):
        return None
    
    with Session(engine) as session:
        return {
            'users': session.exec(select(User)).all().__len__(),
            'chat_sessions': session.exec(select(ChatSession)).all().__len__(),
            'chat_messages': session.exec(select(ChatMessage)).all().__len__(),
            'players': session.exec(select(Player)).all().__len__(),
            'player_stats': session.exec(select(PlayerStats)).all().__len__(),
            'leagues': session.exec(select(League)).all().__len__(),
            'matches': session.exec(select(Match)).all().__len__(),
            'match_sets': session.exec(select(MatchSet)).all().__len__(),
            'critical_moments': session.exec(select(MatchCriticalMoment)).all().__len__(),
            'player_triggers': session.exec(select(PlayerTrigger)).all().__len__(),
            'period_stats': session.exec(select(PlayerPeriodStats)).all().__len__(),
            'rating_history': session.exec(select(PlayerRatingHistory)).all().__len__(),
            'holidays': session.exec(select(Holiday)).all().__len__(),
            'trigger_configs': session.exec(select(TriggerConfiguration)).all().__len__(),
            'scenario_stats': session.exec(select(ScenarioStats)).all().__len__(),
            'match_scenarios': session.exec(select(MatchScenario)).all().__len__()
        }

def show_stats():
    """Показывает статистику БД"""
    print_header("СТАТИСТИКА БАЗЫ ДАННЫХ")
    
    if not os.path.exists(DB_PATH):
        print("❌ База данных не существует!")
        return
    
    stats = get_db_stats()
    
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

def delete_database():
    """Полное удаление БД"""
    print_header("ПОЛНОЕ УДАЛЕНИЕ БАЗЫ ДАННЫХ")
    
    if not os.path.exists(DB_PATH):
        print("ℹ️ База данных не существует (нечего удалять)")
        return True
    
    print(f"📍 Путь к БД: {os.path.abspath(DB_PATH)}")
    print("\n⚠️ ВНИМАНИЕ: Все данные будут БЕЗВОЗВРАТНО удалены!")
    
    confirm = input("\n❓ Продолжить удаление? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', 'да']:
        print("❌ Операция отменена")
        return False
    
    try:
        os.remove(DB_PATH)
        print("✅ База данных успешно удалена!")
        return True
    except Exception as e:
        print(f"❌ Ошибка при удалении: {e}")
        return False

def create_database():
    """Создание новой БД"""
    print_header("СОЗДАНИЕ НОВОЙ БАЗЫ ДАННЫХ")
    
    if os.path.exists(DB_PATH):
        print(f"⚠️ База данных уже существует: {DB_PATH}")
        confirm = input("Удалить существующую и создать новую? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'да']:
            print("❌ Операция отменена")
            return False
        os.remove(DB_PATH)
        print("✅ Старая база удалена")
    
    print("\n📋 Создание таблиц...")
    SQLModel.metadata.create_all(engine)
    
    print("✅ База данных создана!")
    print(f"📍 Путь: {os.path.abspath(DB_PATH)}")
    return True

def clear_matches_only():
    """Очистка только матчей (игроки остаются)"""
    print_header("ОЧИСТКА МАТЧЕЙ (игроки сохраняются)")
    
    if not os.path.exists(DB_PATH):
        print("❌ База данных не существует!")
        return False
    
    with Session(engine) as session:
        matches = session.exec(select(Match)).all().__len__()
        sets = session.exec(select(MatchSet)).all().__len__()
        triggers = session.exec(select(PlayerTrigger)).all().__len__()
        match_scenarios = session.exec(select(MatchScenario)).all().__len__()
        
        print(f"\n📊 Будет удалено:")
        print(f"  └─ Матчей: {matches}")
        print(f"  └─ Сетов: {sets}")
        print(f"  └─ Триггеров: {triggers}")
        print(f"  └─ Связей матч-сценарий: {match_scenarios}")
        
        if matches == 0:
            print("\n✅ Матчей в БД нет!")
            return True
        
        confirm = input("\n❓ Продолжить очистку? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'да']:
            print("❌ Операция отменена")
            return False
        
        # Удаляем триггеры
        for trigger in session.exec(select(PlayerTrigger)).all():
            session.delete(trigger)
        
        # Удаляем связи матч-сценарий ПЕРЕД удалением матчей
        for match_scenario in session.exec(select(MatchScenario)).all():
            session.delete(match_scenario)
        
        # Удаляем сеты
        for match_set in session.exec(select(MatchSet)).all():
            session.delete(match_set)
        
        # Удаляем критические моменты
        for moment in session.exec(select(MatchCriticalMoment)).all():
            session.delete(moment)
        
        # Удаляем матчи
        for match in session.exec(select(Match)).all():
            session.delete(match)
        
        session.commit()
        print("✅ Матчи успешно удалены!")
        return True

def clear_all_data():
    """Очистка всех данных (но таблицы остаются)"""
    print_header("ПОЛНАЯ ОЧИСТКА ВСЕХ ДАННЫХ")
    
    if not os.path.exists(DB_PATH):
        print("❌ База данных не существует!")
        return False
    
    stats = get_db_stats()
    total = sum(stats.values())
    
    print(f"\n📊 Будет удалено {total} записей из всех таблиц")
    print("⚠️ Структура таблиц сохранится, но все данные будут удалены!")
    
    confirm = input("\n❓ Продолжить полную очистку? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', 'да']:
        print("❌ Операция отменена")
        return False
    
    with Session(engine) as session:
        # Удаляем в правильном порядке (от зависимых к независимым)
        for msg in session.exec(select(ChatMessage)).all():
            session.delete(msg)
        for sess in session.exec(select(ChatSession)).all():
            session.delete(sess)
        for trigger in session.exec(select(PlayerTrigger)).all():
            session.delete(trigger)
        for moment in session.exec(select(MatchCriticalMoment)).all():
            session.delete(moment)
        # Удаляем сценарии ПЕРЕД удалением матчей
        for match_scenario in session.exec(select(MatchScenario)).all():
            session.delete(match_scenario)
        for match_set in session.exec(select(MatchSet)).all():
            session.delete(match_set)
        for match in session.exec(select(Match)).all():
            session.delete(match)
        # Удаляем статистику сценариев ПЕРЕД удалением игроков
        for scenario_stat in session.exec(select(ScenarioStats)).all():
            session.delete(scenario_stat)
        for stats in session.exec(select(PlayerStats)).all():
            session.delete(stats)
        for period in session.exec(select(PlayerPeriodStats)).all():
            session.delete(period)
        for history in session.exec(select(PlayerRatingHistory)).all():
            session.delete(history)
        for player in session.exec(select(Player)).all():
            session.delete(player)
        for league in session.exec(select(League)).all():
            session.delete(league)
        for holiday in session.exec(select(Holiday)).all():
            session.delete(holiday)
        for config in session.exec(select(TriggerConfiguration)).all():
            session.delete(config)
        for user in session.exec(select(User)).all():
            session.delete(user)
        
        session.commit()
    
    print("✅ Все данные успешно удалены!")
    return True

def main_menu():
    """Главное меню"""
    while True:
        print_header("УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ")
        print("\n1. 📊 Показать статистику БД")
        print("2. 🆕 Создать новую БД (с удалением старой)")
        print("3. 🏓 Очистить только матчи (игроки остаются)")
        print("4. 🗑️ Очистить все данные (таблицы остаются)")
        print("5. 💥 Полное удаление БД")
        print("0. 🚪 Выход")
        
        choice = input("\n➡️ Выберите действие (0-5): ").strip()
        
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
        else:
            print("❌ Неверный выбор!")
        
        input("\n⏎ Нажмите Enter для продолжения...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Командная строка
        action = sys.argv[1].lower()
        if action == 'stats':
            show_stats()
        elif action == 'create':
            create_database()
        elif action == 'clear-matches':
            clear_matches_only()
        elif action == 'clear-all':
            clear_all_data()
        elif action == 'delete':
            delete_database()
        else:
            print(f"Неизвестная команда: {action}")
            print("\nДоступные команды:")
            print("  python manage_db.py stats         - показать статистику")
            print("  python manage_db.py create        - создать новую БД")
            print("  python manage_db.py clear-matches - очистить матчи")
            print("  python manage_db.py clear-all     - очистить все данные")
            print("  python manage_db.py delete        - удалить БД")
    else:
        # Интерактивное меню
        main_menu()
