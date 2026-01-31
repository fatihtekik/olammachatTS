"""
Миграции базы данных.
Добавление недостающих колонок и изменение схемы.
"""
import sys
import sqlite3
from pathlib import Path

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

DB_PATH = Path(__file__).parent.parent / "ollamachat.db"


def print_header(title: str):
    """Красивый заголовок"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def get_table_columns(cursor, table_name: str) -> list:
    """Получает список колонок таблицы"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]


def add_column(cursor, table: str, column: str, col_type: str, default=None) -> bool:
    """
    Добавляет колонку в таблицу если её нет.
    
    Returns:
        bool: True если колонка была добавлена
    """
    columns = get_table_columns(cursor, table)
    
    if column in columns:
        print(f"  ✓ {table}.{column} - уже существует")
        return False
    
    default_clause = f" DEFAULT {default}" if default is not None else ""
    sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"
    
    cursor.execute(sql)
    print(f"  + {table}.{column} - добавлена ({col_type})")
    return True


def migrate_playertrigger(cursor) -> int:
    """Миграция таблицы playertrigger"""
    print("\n📋 Таблица: playertrigger")
    
    changes = 0
    
    # is_pair - для H2H триггеров
    if add_column(cursor, "playertrigger", "is_pair", "BOOLEAN", 1):
        changes += 1
    
    return changes


def migrate_match(cursor) -> int:
    """Миграция таблицы match"""
    print("\n📋 Таблица: match")
    
    changes = 0
    columns = get_table_columns(cursor, "match")
    
    # Проверяем все колонки из модели
    expected_columns = {
        'serve_efficiency_p1': ('INTEGER', None),
        'receive_efficiency_p1': ('INTEGER', None),
        'serve_efficiency_p2': ('INTEGER', None),
        'receive_efficiency_p2': ('INTEGER', None),
        'match_duration_formatted': ('TEXT', None),
        'timeouts_p1': ('INTEGER', None),
        'timeouts_p2': ('INTEGER', None),
        'yellow_cards_p1': ('INTEGER', None),
        'yellow_cards_p2': ('INTEGER', None),
        'red_cards_p1': ('INTEGER', None),
        'red_cards_p2': ('INTEGER', None),
        'game_balance': ('INTEGER', None),
    }
    
    for col_name, (col_type, default) in expected_columns.items():
        if add_column(cursor, "match", col_name, col_type, default):
            changes += 1
    
    return changes


def migrate_matchset(cursor) -> int:
    """Миграция таблицы matchset"""
    print("\n📋 Таблица: matchset")
    
    changes = 0
    
    expected_columns = {
        'serve_efficiency_p1': ('INTEGER', None),
        'receive_efficiency_p1': ('INTEGER', None),
        'serve_efficiency_p2': ('INTEGER', None),
        'receive_efficiency_p2': ('INTEGER', None),
        'set_duration_formatted': ('TEXT', None),
        'set_balance': ('INTEGER', None),
    }
    
    for col_name, (col_type, default) in expected_columns.items():
        if add_column(cursor, "matchset", col_name, col_type, default):
            changes += 1
    
    return changes


def run_migrations(force: bool = False) -> bool:
    """
    Запуск всех миграций.
    
    Args:
        force: Если True, не запрашивает подтверждение
        
    Returns:
        bool: True если успешно
    """
    print_header("МИГРАЦИИ БАЗЫ ДАННЫХ")
    
    if not DB_PATH.exists():
        print("❌ База данных не существует!")
        print(f"   Путь: {DB_PATH.absolute()}")
        print("\n💡 Создайте БД командой: python -m tools.db_reset")
        return False
    
    print(f"📍 База данных: {DB_PATH.absolute()}")
    
    if not force:
        print("\n⚠️ Будут добавлены недостающие колонки в таблицы")
        confirm = input("❓ Продолжить? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y', 'да', 'д']:
            print("❌ Операция отменена")
            return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        total_changes = 0
        
        # Запускаем миграции для каждой таблицы
        total_changes += migrate_playertrigger(cursor)
        total_changes += migrate_match(cursor)
        total_changes += migrate_matchset(cursor)
        
        if total_changes > 0:
            conn.commit()
            print(f"\n✅ Миграции выполнены! Изменений: {total_changes}")
        else:
            print("\n✅ База данных актуальна, изменений не требуется")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка при миграции: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_schema():
    """Показывает текущую схему БД"""
    print_header("СХЕМА БАЗЫ ДАННЫХ")
    
    if not DB_PATH.exists():
        print("❌ База данных не существует!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем список таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\n📊 Всего таблиц: {len(tables)}")
    
    for table in tables:
        if table.startswith('sqlite_'):
            continue
            
        columns = get_table_columns(cursor, table)
        print(f"\n📋 {table} ({len(columns)} колонок):")
        for col in columns:
            print(f"    └─ {col}")
    
    conn.close()


def main():
    """Точка входа CLI"""
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == 'run':
            force = '--force' in sys.argv or '-f' in sys.argv
            run_migrations(force=force)
        elif action == 'schema':
            show_schema()
        else:
            print(f"❌ Неизвестная команда: {action}")
            print("\n📋 Доступные команды:")
            print("  python -m tools.migrate run          - запустить миграции")
            print("  python -m tools.migrate run --force  - без подтверждения")
            print("  python -m tools.migrate schema       - показать схему БД")
    else:
        run_migrations()


if __name__ == "__main__":
    main()
