# База данных SportAI - Структура и Утилиты

## 📊 Тип БД
**SQLite** - файловая база данных `ollamachat.db`

## 📁 Структура таблиц

### 1. **User** - Пользователи системы
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID пользователя |
| email | String | Email (уникальный) |
| username | String | Имя пользователя |
| hashed_password | String | Хешированный пароль |
| is_active | Boolean | Активен ли пользователь |
| created_at | DateTime | Дата создания |

---

### 2. **ChatSession** - Сессии чата
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID сессии |
| user_id | String (FK) | ID пользователя |
| title | String | Название сессии |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата обновления |

---

### 3. **ChatMessage** - Сообщения в чате
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID сообщения |
| session_id | String (FK) | ID сессии |
| role | String | Роль (user/assistant/system) |
| content | Text | Содержимое сообщения |
| created_at | DateTime | Дата создания |

---

### 4. **Player** - Игроки
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID игрока |
| full_name | String | ФИО игрока (уникальное) |
| current_rating | Float | Текущий рейтинг |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата обновления |

**Связи:**
- `stats` → PlayerStats (один-к-одному)
- `matches_as_player1` → Match (один-ко-многим)
- `matches_as_player2` → Match (один-ко-многим)
- `triggers` → PlayerTrigger (один-ко-многим)

---

### 5. **PlayerStats** - Статистика игрока
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| player_id | String (FK) | ID игрока (уникальный) |
| matches_played | Integer | Сыграно матчей |
| wins | Integer | Победы |
| losses | Integer | Поражения |
| draws | Integer | Ничьи |
| sets_won | Integer | Выиграно сетов |
| sets_lost | Integer | Проиграно сетов |
| points_won | Integer | Выиграно очков |
| points_lost | Integer | Проиграно очков |
| win_percentage | Float | Процент побед |
| avg_match_duration | Integer | Средняя продолжительность матча (сек) |
| last_updated | DateTime | Дата обновления |

---

### 6. **League** - Лиги/Турниры
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| name | String | Название лиги (уникальное) |
| level | String | Уровень лиги |
| created_at | DateTime | Дата создания |

---

### 7. **Match** - Матчи
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID матча |
| date | Date | Дата матча |
| time | Time | Время матча |
| player1_id | String (FK) | ID первого игрока |
| player2_id | String (FK) | ID второго игрока |
| winner_id | String (FK) | ID победителя |
| score | String | Счет (формат "3:1") |
| sets_player1 | Integer | Сеты игрока 1 |
| sets_player2 | Integer | Сеты игрока 2 |
| stage | String | Стадия турнира |
| league_id | String (FK) | ID лиги |
| match_sl_id | Integer | SL-ID (уникальный идентификатор из Excel) |
| is_final | Boolean | Финал турнира? |
| is_semifinal | Boolean | Полуфинал турнира? |
| serve_efficiency_p1 | Integer | Эффективность подачи игрока 1 |
| receive_efficiency_p1 | Integer | Эффективность приёма игрока 1 |
| serve_efficiency_p2 | Integer | Эффективность подачи игрока 2 |
| receive_efficiency_p2 | Integer | Эффективность приёма игрока 2 |
| timeouts_p1 | Integer | Таймауты игрока 1 |
| timeouts_p2 | Integer | Таймауты игрока 2 |
| yellow_cards_p1 | Integer | Жёлтые карточки игрока 1 |
| yellow_cards_p2 | Integer | Жёлтые карточки игрока 2 |
| red_cards_p1 | Integer | Красные карточки игрока 1 |
| red_cards_p2 | Integer | Красные карточки игрока 2 |
| game_balance | Integer | Баланс в игре |
| created_at | DateTime | Дата создания |

**Связи:**
- `sets` → MatchSet (один-ко-многим)
- `critical_moments` → MatchCriticalMoment (один-ко-многим)

---

### 8. **MatchSet** - Сеты матча
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| match_id | String (FK) | ID матча |
| set_number | Integer | Номер сета (1-5) |
| player1_score | Integer | Очки игрока 1 |
| player2_score | Integer | Очки игрока 2 |
| winner_id | String (FK) | ID победителя сета |
| duration_seconds | Integer | Длительность сета (сек) |
| serve_eff_p1 | Integer | Эффективность подачи игрока 1 |
| receive_eff_p1 | Integer | Эффективность приёма игрока 1 |
| serve_eff_p2 | Integer | Эффективность подачи игрока 2 |
| receive_eff_p2 | Integer | Эффективность приёма игрока 2 |
| balance | Integer | Баланс в сете |

---

### 9. **MatchCriticalMoment** - Критические моменты матча
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| match_id | String (FK) | ID матча |
| set_number | Integer | Номер сета |
| moment_type | String | Тип момента |
| player_id | String (FK) | ID игрока |
| description | Text | Описание |
| timestamp | DateTime | Время момента |

---

### 10. **PlayerTrigger** - Триггеры игроков
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| player_id | String (FK) | ID игрока |
| trigger_type | String | Тип триггера |
| trigger_subtype | String | Подтип триггера |
| trigger_value | String | Значение триггера |
| severity_level | Integer | Уровень серьёзности (1-5) |
| period_start | Date | Начало периода |
| period_end | Date | Конец периода |
| is_active | Boolean | Активен ли триггер |
| trigger_metadata | JSON | Метаданные триггера |
| ai_analysis | Text | AI анализ триггера |
| created_at | DateTime | Дата создания |

**Типы триггеров:**
- `losing_streaks` - Серии поражений
- `top_performers` - Топ игроки
- `losers_50_percent` - Игроки с 50%+ поражений
- `lead_collapse` - Потеря преимущества 2:0
- `psychological_breakdown` - Психологические срывы
- `comeback_inability` - Неспособность к камбекам
- `pressure_situations` - Игра под давлением

---

### 11. **PlayerPeriodStats** - Статистика игрока за период
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| player_id | String (FK) | ID игрока |
| period_start | Date | Начало периода |
| period_end | Date | Конец периода |
| matches_played | Integer | Сыграно матчей |
| wins | Integer | Победы |
| losses | Integer | Поражения |
| sets_won | Integer | Выиграно сетов |
| sets_lost | Integer | Проиграно сетов |
| win_rate | Float | Процент побед |
| recent_form | String | Последняя форма (WWLWL) |
| created_at | DateTime | Дата создания |

---

### 12. **PlayerRatingHistory** - История рейтинга игрока
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| player_id | String (FK) | ID игрока |
| rating | Float | Рейтинг |
| change | Float | Изменение рейтинга |
| match_id | String (FK) | ID матча |
| recorded_at | DateTime | Дата записи |

---

### 13. **Holiday** - Праздники
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| date | Date | Дата праздника |
| name | String | Название праздника |
| is_major | Boolean | Крупный праздник? |
| created_at | DateTime | Дата создания |

---

### 14. **TriggerConfiguration** - Конфигурация триггеров
| Колонка | Тип | Описание |
|---------|-----|----------|
| id | String (UUID) | Уникальный ID |
| trigger_type | String | Тип триггера |
| is_enabled | Boolean | Включен ли триггер |
| threshold_value | Float | Пороговое значение |
| severity_level | Integer | Уровень серьёзности |
| description | Text | Описание |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата обновления |

---

## 🔗 Связи между таблицами

```
User
 └─> ChatSession (один-ко-многим)
      └─> ChatMessage (один-ко-многим)

Player
 ├─> PlayerStats (один-к-одному)
 ├─> Match as player1 (один-ко-многим)
 ├─> Match as player2 (один-ко-многим)
 ├─> PlayerTrigger (один-ко-многим)
 ├─> PlayerPeriodStats (один-ко-многим)
 └─> PlayerRatingHistory (один-ко-многим)

Match
 ├─> MatchSet (один-ко-многим)
 ├─> MatchCriticalMoment (один-ко-многим)
 ├─> League (многие-к-одному)
 ├─> Player (player1_id)
 ├─> Player (player2_id)
 └─> Player (winner_id)
```

---

## 🛠️ Утилиты для работы с БД

### Доступные скрипты:

1. **`init_database.py`** - Инициализация новой БД
   ```bash
   python database_tools/init_database.py
   ```

2. **`clean_database.py`** - Полная очистка всех данных
   ```bash
   python database_tools/clean_database.py
   ```

3. **`reset_matches.py`** - Очистка только матчей (сохраняет игроков)
   ```bash
   python database_tools/reset_matches.py
   ```

4. **`check_database.py`** - Проверка структуры и статистики БД
   ```bash
   python database_tools/check_database.py
   ```

5. **`backup_database.py`** - Создание резервной копии
   ```bash
   python database_tools/backup_database.py
   ```

6. **`restore_database.py`** - Восстановление из резервной копии
   ```bash
   python database_tools/restore_database.py <файл_бэкапа>
   ```

---

## 📝 Индексы

Для оптимизации производительности созданы следующие индексы:

- **Match**: `date`, `player1_id`, `player2_id`, `winner_id`, `match_sl_id`
- **Player**: `full_name`
- **PlayerTrigger**: `player_id`, `trigger_type`, `is_active`
- **ChatSession**: `user_id`
- **ChatMessage**: `session_id`

---

## 🚀 Первоначальная настройка

1. **Создание БД:**
   ```bash
   cd backend
   python database_tools/init_database.py
   ```

2. **Проверка структуры:**
   ```bash
   python database_tools/check_database.py
   ```

3. **Загрузка данных:**
   - Через UI: Перейти в раздел "Загрузка" и загрузить Excel файл
   - Через API: POST `/api/v1/match-analysis/upload-excel`

---

## ⚠️ Важные заметки

1. **SL-ID** - уникальный идентификатор матча из Excel. Используется для предотвращения дубликатов.
2. **match_sl_id** - должен быть уникальным в таблице Match
3. **Каскадное удаление**: При удалении Player удаляются все связанные данные
4. **Автообновление**: PlayerStats обновляется автоматически после каждого матча
5. **Триггеры**: Автоматически создаются при анализе базы данных

---

## 🔧 Миграции

При изменении структуры моделей необходимо:

1. Создать резервную копию:
   ```bash
   python database_tools/backup_database.py
   ```

2. Удалить старую БД или использовать Alembic для миграций

3. Пересоздать БД:
   ```bash
   python database_tools/init_database.py
   ```

---

## 📊 Размер данных

**Примерные объёмы:**
- 1000 матчей ≈ 5 MB
- 100 игроков ≈ 100 KB
- 1000 триггеров ≈ 2 MB

**Рекомендации:**
- До 10,000 матчей: SQLite отлично справляется
- Более 50,000 матчей: рассмотреть PostgreSQL
