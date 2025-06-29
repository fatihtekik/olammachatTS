#!/usr/bin/env python3
"""
Скрипт для проверки таблиц в базе данных SQLite
"""
import sqlite3
import os

def check_database_tables():
    """Проверяет и выводит все таблицы в базе данных"""
    db_path = 'ollamachat.db'
    
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена!")
        return
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        print("=== ТАБЛИЦЫ В БАЗЕ ДАННЫХ ===")
        if tables:
            for table in tables:
                table_name = table[0]
                print(f"\n📋 Таблица: {table_name}")
                
                # Получаем структуру таблицы
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                print("   Столбцы:")
                for col in columns:
                    col_id, col_name, col_type, not_null, default_val, pk = col
                    pk_str = " (PRIMARY KEY)" if pk else ""
                    not_null_str = " NOT NULL" if not_null else ""
                    default_str = f" DEFAULT {default_val}" if default_val is not None else ""
                    print(f"   - {col_name}: {col_type}{not_null_str}{default_str}{pk_str}")
                
                # Получаем количество записей
                cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                count = cursor.fetchone()[0]
                print(f"   📊 Количество записей: {count}")
        else:
            print("❌ Таблицы не найдены!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")

if __name__ == "__main__":
    check_database_tables()
