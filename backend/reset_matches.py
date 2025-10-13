"""
Скрипт для очистки матчей из базы данных.
Удаляет все матчи, но сохраняет игроков.
"""

import sys
import os

# Добавляем путь к backend в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.db import SQLALCHEMY_DATABASE_URL, engine, SessionLocal
from app.models.match import Match, MatchSet, PlayerTrigger

def reset_matches():
    """Удаляет все матчи из базы данных"""
    
    print("🔄 Начинаем очистку матчей...")
    
    try:
        # Используем существующую конфигурацию базы данных
        database_url = SQLALCHEMY_DATABASE_URL
        print(f"📊 Подключение к базе данных: {database_url}")
        
        # Используем существующую сессию
        db = SessionLocal()
        
        # Подсчитываем количество записей до удаления
        matches_count = db.query(Match).count()
        match_sets_count = db.query(MatchSet).count()
        triggers_count = db.query(PlayerTrigger).count()
        
        print(f"\n📈 Текущее состояние базы данных:")
        print(f"  - Матчей: {matches_count}")
        print(f"  - Сетов: {match_sets_count}")
        print(f"  - Триггеров: {triggers_count}")
        
        if matches_count == 0 and match_sets_count == 0 and triggers_count == 0:
            print("\n✅ База данных уже пуста!")
            db.close()
            return
        
        # Запрашиваем подтверждение
        print("\n⚠️  ВНИМАНИЕ! Это действие удалит ВСЕ матчи, сеты и триггеры!")
        print("⚠️  Игроки и их рейтинги будут сохранены.")
        response = input("\n❓ Продолжить? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y', 'да', 'д']:
            print("\n❌ Операция отменена пользователем.")
            db.close()
            return
        
        print("\n🗑️  Начинаем удаление...")
        
        # Удаляем в правильном порядке (из-за foreign keys)
        
        # 1. Удаляем триггеры
        print("  1️⃣  Удаление триггеров...")
        deleted_triggers = db.query(PlayerTrigger).delete()
        db.commit()
        print(f"     ✅ Удалено триггеров: {deleted_triggers}")
        
        # 2. Удаляем сеты
        print("  2️⃣  Удаление сетов...")
        deleted_sets = db.query(MatchSet).delete()
        db.commit()
        print(f"     ✅ Удалено сетов: {deleted_sets}")
        
        # 3. Удаляем матчи
        print("  3️⃣  Удаление матчей...")
        deleted_matches = db.query(Match).delete()
        db.commit()
        print(f"     ✅ Удалено матчей: {deleted_matches}")
        
        # Проверяем результат
        remaining_matches = db.query(Match).count()
        remaining_sets = db.query(MatchSet).count()
        remaining_triggers = db.query(PlayerTrigger).count()
        
        print(f"\n📊 Результат:")
        print(f"  - Удалено матчей: {deleted_matches}")
        print(f"  - Удалено сетов: {deleted_sets}")
        print(f"  - Удалено триггеров: {deleted_triggers}")
        print(f"\n  - Осталось матчей: {remaining_matches}")
        print(f"  - Осталось сетов: {remaining_sets}")
        print(f"  - Осталось триггеров: {remaining_triggers}")
        
        if remaining_matches == 0 and remaining_sets == 0 and remaining_triggers == 0:
            print("\n✅ Все матчи успешно удалены!")
            print("ℹ️  Игроки сохранены и готовы к новой загрузке данных.")
        else:
            print("\n⚠️  Внимание! Не все записи были удалены.")
        
        db.close()
        print("\n✅ Соединение с базой данных закрыто.")
        
    except Exception as e:
        print(f"\n❌ Ошибка при очистке базы данных: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def reset_matches_keep_recent(days: int = 7):
    """
    Удаляет старые матчи, оставляя только матчи за последние N дней
    
    Args:
        days: Количество дней для сохранения
    """
    
    print(f"🔄 Начинаем очистку старых матчей (старше {days} дней)...")
    
    try:
        from datetime import datetime, timedelta
        
        # Используем существующую конфигурацию базы данных
        database_url = SQLALCHEMY_DATABASE_URL
        print(f"📊 Подключение к базе данных: {database_url}")
        
        # Используем существующую сессию
        db = SessionLocal()
        
        # Вычисляем дату отсечки
        cutoff_date = datetime.now() - timedelta(days=days)
        print(f"📅 Дата отсечки: {cutoff_date.strftime('%Y-%m-%d')}")
        
        # Подсчитываем количество записей
        total_matches = db.query(Match).count()
        old_matches = db.query(Match).filter(Match.date < cutoff_date.date()).count()
        recent_matches = total_matches - old_matches
        
        print(f"\n📈 Статистика:")
        print(f"  - Всего матчей: {total_matches}")
        print(f"  - Старых матчей (будет удалено): {old_matches}")
        print(f"  - Недавних матчей (будет сохранено): {recent_matches}")
        
        if old_matches == 0:
            print("\n✅ Нет старых матчей для удаления!")
            db.close()
            return
        
        # Запрашиваем подтверждение
        print(f"\n⚠️  ВНИМАНИЕ! Будут удалены все матчи старше {days} дней!")
        response = input("\n❓ Продолжить? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y', 'да', 'д']:
            print("\n❌ Операция отменена пользователем.")
            db.close()
            return
        
        print("\n🗑️  Начинаем удаление старых записей...")
        
        # Получаем ID старых матчей
        old_match_ids = [m.id for m in db.query(Match.id).filter(Match.date < cutoff_date.date()).all()]
        
        # 1. Удаляем триггеры для старых матчей
        print("  1️⃣  Удаление триггеров для старых матчей...")
        deleted_triggers = db.query(PlayerTrigger).filter(
            PlayerTrigger.period_start < cutoff_date.date()
        ).delete(synchronize_session=False)
        db.commit()
        print(f"     ✅ Удалено триггеров: {deleted_triggers}")
        
        # 2. Удаляем сеты для старых матчей
        print("  2️⃣  Удаление сетов для старых матчей...")
        deleted_sets = db.query(MatchSet).filter(
            MatchSet.match_id.in_(old_match_ids)
        ).delete(synchronize_session=False)
        db.commit()
        print(f"     ✅ Удалено сетов: {deleted_sets}")
        
        # 3. Удаляем старые матчи
        print("  3️⃣  Удаление старых матчей...")
        deleted_matches = db.query(Match).filter(
            Match.date < cutoff_date.date()
        ).delete(synchronize_session=False)
        db.commit()
        print(f"     ✅ Удалено матчей: {deleted_matches}")
        
        # Проверяем результат
        remaining_matches = db.query(Match).count()
        
        print(f"\n📊 Результат:")
        print(f"  - Удалено матчей: {deleted_matches}")
        print(f"  - Удалено сетов: {deleted_sets}")
        print(f"  - Удалено триггеров: {deleted_triggers}")
        print(f"  - Осталось матчей: {remaining_matches}")
        
        print("\n✅ Старые матчи успешно удалены!")
        
        db.close()
        print("\n✅ Соединение с базой данных закрыто.")
        
    except Exception as e:
        print(f"\n❌ Ошибка при очистке базы данных: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("=" * 60)
    print("🎾 Скрипт очистки матчей из базы данных")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
            print(f"\nРежим: Удаление матчей старше {days} дней")
            reset_matches_keep_recent(days)
        except ValueError:
            print("\n❌ Ошибка: Укажите количество дней числом")
            print("Использование: python reset_matches.py [дни]")
            print("Пример: python reset_matches.py 30  # Удалить матчи старше 30 дней")
            sys.exit(1)
    else:
        print("\nРежим: Полная очистка всех матчей")
        reset_matches()
    
    print("\n" + "=" * 60)
