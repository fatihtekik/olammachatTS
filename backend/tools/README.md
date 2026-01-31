# 🛠️ Database Tools

Инструменты для работы с базой данных приложения.

## 📋 Содержимое

| Модуль | Описание |
|--------|----------|
| `db_reset.py` | Полный сброс БД (удаление + создание таблиц) |
| `db_manager.py` | Интерактивный менеджер БД |
| `migrate.py` | Миграции (добавление колонок) |
| `stats.py` | Аналитика и проверка данных |

---

## 🔄 db_reset.py - Полный сброс БД

Удаляет файл БД и создаёт заново все таблицы на основе актуальных моделей.

```bash
# Интерактивный режим (с подтверждением)
python -m tools.db_reset

# Принудительный сброс (без подтверждения)
python -m tools.db_reset --force
python -m tools.db_reset -f
```

---

## 📊 db_manager.py - Менеджер БД

Интерактивное меню для управления базой данных.

```bash
# Интерактивное меню
python -m tools.db_manager

# Команды CLI
python -m tools.db_manager stats          # Статистика БД
python -m tools.db_manager create         # Создать новую БД
python -m tools.db_manager clear-matches  # Очистить матчи (игроки остаются)
python -m tools.db_manager clear-all      # Очистить все данные
python -m tools.db_manager delete         # Удалить файл БД
python -m tools.db_manager migrate        # Добавить недостающие колонки
```

### Возможности:
- 📊 Показать статистику по всем таблицам
- 🆕 Создать новую БД
- 🏓 Очистить только матчи (игроки сохраняются)
- 🗑️ Очистить все данные (структура сохраняется)
- 💥 Полное удаление БД

---

## 🔧 migrate.py - Миграции

Добавляет недостающие колонки в таблицы без потери данных.

```bash
# Интерактивный режим
python -m tools.migrate

# Запуск миграций
python -m tools.migrate run
python -m tools.migrate run --force  # Без подтверждения

# Показать схему БД
python -m tools.migrate schema
```

### Поддерживаемые миграции:
- `playertrigger.is_pair` - для H2H триггеров
- Колонки эффективности в `match` и `matchset`

---

## 📈 stats.py - Аналитика

Проверка целостности данных и статистика.

```bash
# Все проверки
python -m tools.stats

# Отдельные команды
python -m tools.stats scores       # Статистика счетов
python -m tools.stats sets         # Проверка сетов
python -m tools.stats issues       # Поиск проблем
python -m tools.stats match <id>   # Детали матча
```

---

## 🔥 Частые сценарии

### 1. Первый запуск / Чистая установка
```bash
python -m tools.db_reset --force
```

### 2. После обновления моделей
```bash
python -m tools.migrate run --force
```

### 3. Очистить данные перед новой загрузкой
```bash
python -m tools.db_manager clear-matches
```

### 4. Проверить состояние БД
```bash
python -m tools.db_manager stats
```

### 5. Найти проблемы в данных
```bash
python -m tools.stats issues
```

---

## 📝 Использование в коде

```python
from tools import (
    reset_database,
    show_stats,
    create_database,
    clear_matches_only,
    clear_all_data,
    delete_database,
    get_db_stats
)

# Получить статистику
stats = get_db_stats()
print(f"Матчей в БД: {stats['matches']}")

# Сбросить БД программно
reset_database(force=True)
```

---

## ⚠️ Важно

- Все операции удаления требуют подтверждения (кроме `--force`)
- Резервные копии НЕ создаются автоматически
- При сбросе БД все данные будут **безвозвратно удалены**
