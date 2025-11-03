"""
Тестовый скрипт для проверки создания всех таблиц
"""
import sys
from pathlib import Path
import sqlite3

# Добавляем корневую директорию backend в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def check_test_db(db_name="test_init.db"):
    """Проверка таблиц в тестовой БД"""
    test_db_path = backend_dir / db_name
    
    if not test_db_path.exists():
        print(f"❌ Тестовая БД не найдена: {db_name}")
        return
    
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        "chatsession",
        "chatmessage", 
        "holiday",
        "league",
        "match",
        "matchcriticalmoment",
        "matchset",
        "player",
        "playerperiodstats",
        "playerratinghistory",
        "playerstats",
        "playertrigger",
        "triggerconfiguration",
        "user"
    ]
    
    print("="*60)
    print("🧪 ПРОВЕРКА ТЕСТОВОЙ БД")
    print("="*60)
    print(f"\n📁 Файл: {test_db_path}")
    print(f"📊 Всего таблиц: {len(tables)}")
    print("\n📋 Созданные таблицы:")
    
    for table in tables:
        status = "✅" if table in expected_tables else "⚠️"
        print(f"   {status} {table}")
    
    print("\n🔍 Ожидаемые таблицы:")
    for table in expected_tables:
        if table not in tables:
            print(f"   ❌ {table} - ОТСУТСТВУЕТ")
    
    missing = set(expected_tables) - set(tables)
    extra = set(tables) - set(expected_tables)
    
    if missing:
        print(f"\n❌ Отсутствуют таблицы: {', '.join(missing)}")
    if extra:
        print(f"\n⚠️  Дополнительные таблицы: {', '.join(extra)}")
    
    if not missing and not extra:
        print("\n✅ Все таблицы созданы корректно!")
    
    conn.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    check_test_db()
