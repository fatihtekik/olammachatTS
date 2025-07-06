#!/usr/bin/env python3
"""
Скрипт для полного сброса базы данных
"""
import os
import sys
from pathlib import Path
import sqlite3

def reset_database():
    """Сбрасывает базу данных и создает новую"""
    
    # Получаем путь к базе данных
    current_dir = Path(__file__).parent
    db_path = current_dir / "ollamachat.db"
    
    print(f"🗑️ Сброс базы данных: {db_path}")
    
    try:
        # Удаляем файл базы данных если он существует
        if db_path.exists():
            print(f"📁 Удаляем существующий файл базы данных...")
            os.remove(db_path)
            print("✅ Файл базы данных удален")
        else:
            print("ℹ️ Файл базы данных не найден")
        
        # Создаем новую пустую базу данных
        print("🆕 Создаем новую базу данных...")
        conn = sqlite3.connect(str(db_path))
        
        # Создаем базовые таблицы
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            full_name TEXT,
            password_hash TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Таблица игроков
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            current_rating REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Таблица лиг
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS leagues (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            level INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Таблица матчей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id TEXT PRIMARY KEY,
            date DATE NOT NULL,
            time TIME,
            player1_id TEXT NOT NULL,
            player2_id TEXT NOT NULL,
            winner_id TEXT,
            score TEXT,
            sets_player1 INTEGER,
            sets_player2 INTEGER,
            stage TEXT,
            league_id TEXT,
            match_sl_id INTEGER,
            is_final BOOLEAN DEFAULT FALSE,
            is_semifinal BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player1_id) REFERENCES players (id),
            FOREIGN KEY (player2_id) REFERENCES players (id),
            FOREIGN KEY (winner_id) REFERENCES players (id),
            FOREIGN KEY (league_id) REFERENCES leagues (id)
        )
        """)
        
        # Таблица статистики игроков
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            matches_played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            sets_won INTEGER DEFAULT 0,
            sets_lost INTEGER DEFAULT 0,
            points_won INTEGER DEFAULT 0,
            points_lost INTEGER DEFAULT 0,
            win_percentage REAL DEFAULT 0.0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        """)
        
        # Таблица триггеров
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_triggers (
            id TEXT PRIMARY KEY,
            player_id TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            trigger_subtype TEXT,
            trigger_value TEXT,
            severity_level INTEGER,
            period_start DATE,
            period_end DATE,
            is_active BOOLEAN DEFAULT TRUE,
            trigger_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (player_id) REFERENCES players (id)
        )
        """)
        
        # Таблица чатов
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Таблица сообщений
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            model TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
        )
        """)
        
        conn.commit()
        conn.close()
        
        print("✅ Новая база данных создана успешно!")
        print(f"📊 Путь к базе данных: {db_path}")
        
        # Выводим размер файла
        file_size = db_path.stat().st_size
        print(f"📏 Размер файла: {file_size} байт")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при сбросе базы данных: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Запуск сброса базы данных...")
    print("⚠️ ВНИМАНИЕ: Все данные будут удалены!")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        print("🚀 Принудительный сброс...")
        success = reset_database()
    else:
        confirm = input("Вы уверены, что хотите сбросить базу данных? (yes/no): ")
        if confirm.lower() in ['yes', 'y', 'да', 'д']:
            success = reset_database()
        else:
            print("❌ Сброс отменен")
            success = False
    
    if success:
        print("🎉 Сброс базы данных завершен успешно!")
        sys.exit(0)
    else:
        print("💥 Ошибка при сбросе базы данных!")
        sys.exit(1)
