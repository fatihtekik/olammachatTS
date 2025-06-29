from pathlib import Path
from alembic.config import Config
from alembic import command

def run_migrations():
    """Запуск миграций базы данных с помощью Alembic"""
    
    # Путь к директории с миграциями
    migrations_dir = Path(__file__).parent / "migrations"
    
    # Создаем директорию для миграций, если она не существует
    migrations_dir.mkdir(exist_ok=True)
    
    # Настройка Alembic
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", "postgresql://postgres:password@localhost/olammachat")
    
    # Создание файла миграций
    command.init(alembic_cfg)
    
    # Создание ревизии
    command.revision(alembic_cfg, autogenerate=True, message="Initial migration")
    
    # Применение миграций
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    run_migrations()
