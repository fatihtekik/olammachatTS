"""
Создание резервной копии базы данных SportAI
Копирует файл БД с добавлением timestamp
"""
import sys
from pathlib import Path
from datetime import datetime
import shutil

# Добавляем корневую директорию backend в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def backup_database():
    """Создание резервной копии БД"""
    db_path = backend_dir / "ollamachat.db"
    backups_dir = backend_dir / "database_backups"
    
    # Создаём директорию для бэкапов если её нет
    backups_dir.mkdir(exist_ok=True)
    
    # Проверяем существование БД
    if not db_path.exists():
        print(f"❌ Файл БД не найден: {db_path}")
        return
    
    # Генерируем имя файла с timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"ollamachat_backup_{timestamp}.db"
    backup_path = backups_dir / backup_filename
    
    print(f"💾 Создание резервной копии...")
    print(f"   Исходный файл: {db_path}")
    print(f"   Резервная копия: {backup_path}")
    
    try:
        # Копируем файл БД
        shutil.copy2(db_path, backup_path)
        
        # Проверяем размер
        original_size = db_path.stat().st_size / (1024 * 1024)
        backup_size = backup_path.stat().st_size / (1024 * 1024)
        
        print(f"\n✅ Резервная копия создана успешно!")
        print(f"   📊 Размер оригинала: {original_size:.2f} MB")
        print(f"   📊 Размер копии: {backup_size:.2f} MB")
        print(f"   📁 Расположение: {backup_path}")
        
        # Показываем все существующие бэкапы
        list_backups(backups_dir)
        
    except Exception as e:
        print(f"❌ Ошибка при создании резервной копии: {e}")
        raise

def list_backups(backups_dir):
    """Список всех резервных копий"""
    backups = sorted(backups_dir.glob("ollamachat_backup_*.db"), reverse=True)
    
    if not backups:
        return
    
    print(f"\n📋 Доступные резервные копии ({len(backups)}):")
    for i, backup in enumerate(backups[:5], 1):  # Показываем последние 5
        size_mb = backup.stat().st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(backup.stat().st_mtime)
        print(f"   {i}. {backup.name}")
        print(f"      Размер: {size_mb:.2f} MB | Дата: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if len(backups) > 5:
        print(f"   ... и ещё {len(backups) - 5} копий")
    
    # Показываем общий размер всех бэкапов
    total_size = sum(b.stat().st_size for b in backups) / (1024 * 1024)
    print(f"\n   📊 Общий размер бэкапов: {total_size:.2f} MB")

if __name__ == "__main__":
    backup_database()
