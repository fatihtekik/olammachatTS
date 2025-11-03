"""
Главный скрипт управления базой данных SportAI
Предоставляет интерактивное меню для всех операций с БД
"""
import sys
from pathlib import Path

# Добавляем корневую директорию backend в путь
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

def show_menu():
    """Показать главное меню"""
    print("\n" + "="*60)
    print("🗄️  УПРАВЛЕНИЕ БАЗОЙ ДАННЫХ SPORTAI")
    print("="*60)
    print("\n📋 Доступные операции:\n")
    print("  1. 🔍 Проверить состояние БД")
    print("  2. 🆕 Создать новую БД (инициализация)")
    print("  3. 🗑️  Полная очистка БД (удалить ВСЕ данные)")
    print("  4. ♻️  Очистить только матчи (сохранить игроков)")
    print("  5. 🕒 Удалить старые матчи (указать количество дней)")
    print("  6. 💾 Создать резервную копию")
    print("  7. 🔄 Восстановить из резервной копии")
    print("  8. 📋 Показать список резервных копий")
    print("  0. 🚪 Выход")
    print("\n" + "="*60)

def check_db():
    """Проверка состояния БД"""
    from check_database import main as check_main
    check_main()

def init_db():
    """Инициализация новой БД"""
    from init_database import init_database
    
    db_path = backend_dir / "ollamachat.db"
    if db_path.exists():
        print("⚠️  База данных уже существует!")
        response = input("Пересоздать БД? (YES для подтверждения): ")
        if response != "YES":
            print("❌ Операция отменена")
            return
        
        # Создаём бэкап перед пересозданием
        print("\n💾 Создание резервной копии текущей БД...")
        from backup_database import backup_database
        backup_database()
        
        # Удаляем старую БД
        db_path.unlink()
        print("🗑️  Старая БД удалена\n")
    
    init_database()

def clean_db():
    """Полная очистка БД"""
    from clean_database import clean_database
    clean_database()

def reset_matches_all():
    """Очистка всех матчей"""
    from reset_matches import reset_matches
    reset_matches()

def reset_matches_old():
    """Удаление старых матчей"""
    print("\n🗑️  Удаление старых матчей")
    print("="*60)
    
    try:
        days = int(input("\nСколько дней хранить? (например, 30): "))
        if days <= 0:
            print("❌ Количество дней должно быть положительным числом")
            return
        
        from reset_matches import reset_matches_keep_recent
        reset_matches_keep_recent(days)
        
    except ValueError:
        print("❌ Неверный формат! Введите число.")

def backup_db():
    """Создание резервной копии"""
    from backup_database import backup_database
    backup_database()

def restore_db():
    """Восстановление из резервной копии"""
    from restore_database import list_available_backups, restore_database
    
    backups = list_available_backups()
    if not backups:
        return
    
    print("\n💡 Введите номер или полный путь к файлу бэкапа:")
    choice = input("Выбор: ").strip()
    
    try:
        # Пробуем как номер
        idx = int(choice) - 1
        if 0 <= idx < len(backups):
            restore_database(backups[idx])
        else:
            print("❌ Неверный номер")
    except ValueError:
        # Пробуем как путь
        restore_database(choice)

def list_backups():
    """Показать список резервных копий"""
    from restore_database import list_available_backups
    list_available_backups()
    input("\n📌 Нажмите Enter для продолжения...")

def main():
    """Главная функция"""
    while True:
        show_menu()
        
        try:
            choice = input("\n➡️  Выберите операцию (0-8): ").strip()
            
            if choice == "0":
                print("\n👋 До свидания!")
                break
            elif choice == "1":
                check_db()
            elif choice == "2":
                init_db()
            elif choice == "3":
                clean_db()
            elif choice == "4":
                reset_matches_all()
            elif choice == "5":
                reset_matches_old()
            elif choice == "6":
                backup_db()
            elif choice == "7":
                restore_db()
            elif choice == "8":
                list_backups()
            else:
                print("❌ Неверный выбор! Попробуйте снова.")
            
            if choice != "0":
                input("\n📌 Нажмите Enter для продолжения...")
                
        except KeyboardInterrupt:
            print("\n\n👋 Операция прервана пользователем. До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Произошла ошибка: {e}")
            import traceback
            traceback.print_exc()
            input("\n📌 Нажмите Enter для продолжения...")

if __name__ == "__main__":
    main()
