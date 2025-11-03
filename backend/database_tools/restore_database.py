"""
Восстановление базы данных SportAI из резервной копии
ВНИМАНИЕ: Заменяет текущую БД на версию из бэкапа!
"""
import sys
from pathlib import Path
import shutil
from datetime import datetime

# Добавляем корневую директорию backend в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def list_available_backups():
    """Показать доступные резервные копии"""
    backups_dir = backend_dir / "database_backups"
    
    if not backups_dir.exists():
        print("❌ Директория с бэкапами не найдена")
        return []
    
    backups = sorted(backups_dir.glob("ollamachat_backup_*.db"), reverse=True)
    
    if not backups:
        print("❌ Резервные копии не найдены")
        return []
    
    print("\n📋 Доступные резервные копии:")
    for i, backup in enumerate(backups, 1):
        size_mb = backup.stat().st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"   {i}. {backup.name}")
        print(f"      Размер: {size_mb:.2f} MB | Дата: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return backups

def confirm_restore(backup_path):
    """Запрос подтверждения восстановления"""
    print(f"\n⚠️  ВНИМАНИЕ!")
    print(f"   Текущая база данных будет ЗАМЕНЕНА на версию из бэкапа!")
    print(f"   Файл бэкапа: {backup_path.name}")
    print("")
    response = input("Продолжить? Введите 'YES' для подтверждения: ")
    return response == "YES"

def restore_database(backup_path=None):
    """Восстановление БД из резервной копии"""
    db_path = backend_dir / "ollamachat.db"
    
    # Если путь не указан, показываем список
    if backup_path is None:
        backups = list_available_backups()
        if not backups:
            return
        
        print("\n💡 Использование:")
        print("   python database_tools/restore_database.py <путь_к_бэкапу>")
        print("   или")
        print(f"   python database_tools/restore_database.py database_backups/{backups[0].name}")
        return
    
    backup_path = Path(backup_path)
    
    # Проверяем существование файла бэкапа
    if not backup_path.exists():
        # Пробуем найти в директории database_backups
        alt_path = backend_dir / "database_backups" / backup_path.name
        if alt_path.exists():
            backup_path = alt_path
        else:
            print(f"❌ Файл бэкапа не найден: {backup_path}")
            return
    
    # Запрос подтверждения
    if not confirm_restore(backup_path):
        print("❌ Операция отменена пользователем")
        return
    
    print(f"\n💾 Восстановление базы данных...")
    
    try:
        # Создаём бэкап текущей БД перед восстановлением
        if db_path.exists():
            print("   📦 Создание бэкапа текущей БД...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_backup = backend_dir / f"ollamachat_before_restore_{timestamp}.db"
            shutil.copy2(db_path, safety_backup)
            print(f"   ✓ Текущая БД сохранена: {safety_backup.name}")
        
        # Восстанавливаем из бэкапа
        print(f"   🔄 Восстановление из бэкапа...")
        shutil.copy2(backup_path, db_path)
        
        # Проверяем размеры
        restored_size = db_path.stat().st_size / (1024 * 1024)
        backup_size = backup_path.stat().st_size / (1024 * 1024)
        
        print(f"\n✅ База данных успешно восстановлена!")
        print(f"   📊 Размер бэкапа: {backup_size:.2f} MB")
        print(f"   📊 Размер восстановленной БД: {restored_size:.2f} MB")
        print(f"   📁 Восстановлена из: {backup_path.name}")
        
        if db_path.exists():
            modified = datetime.fromtimestamp(db_path.stat().st_mtime)
            print(f"   🕒 Дата изменения: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ Ошибка при восстановлении БД: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) > 1:
        restore_database(sys.argv[1])
    else:
        restore_database()
