"""
Инструменты для работы с базой данных и данными приложения.

Доступные модули:
    - db_manager: Управление базой данных (создание, очистка, статистика)
    - db_reset: Полный сброс базы данных
    - migrate: Миграции базы данных
    - stats: Аналитика и статистика данных

Использование CLI:
    python -m tools.db_reset           # Полный сброс БД
    python -m tools.db_manager         # Интерактивный менеджер
    python -m tools.migrate run        # Миграции
    python -m tools.stats              # Аналитика
"""

from .db_manager import (
    show_stats,
    create_database,
    clear_matches_only,
    clear_all_data,
    delete_database,
    get_db_stats,
    add_column_if_missing
)

from .db_reset import reset_database

from .migrate import run_migrations, show_schema

from .stats import (
    check_score_statistics,
    check_match_sets_integrity,
    find_matches_with_issues,
    check_specific_match
)

__all__ = [
    # db_manager
    'show_stats',
    'create_database', 
    'clear_matches_only',
    'clear_all_data',
    'delete_database',
    'get_db_stats',
    'add_column_if_missing',
    # db_reset
    'reset_database',
    # migrate
    'run_migrations',
    'show_schema',
    # stats
    'check_score_statistics',
    'check_match_sets_integrity',
    'find_matches_with_issues',
    'check_specific_match'
]
