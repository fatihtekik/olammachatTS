import os
import sys
from pathlib import Path

def reset_database():
    """Удаляет файл базы данных"""
    
    # Получаем путь к базе данных
    current_dir = Path(__file__).parent
    db_path = current_dir / "ollamachat.db"
    
    print(f"🗑️ Сброс базы данных: {db_path}")
    
    try:
        # Удаляем файл базы данных если он существует
        if db_path.exists():
            print("📁 Удаляем существующий файл базы данных...")
            os.remove(db_path)
            print("✅ Файл базы данных удален")
        else:
            print("ℹ️ Файл базы данных не найден (ничего удалять)")
        
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