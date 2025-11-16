# Модуль: Сценарный анализ игроков

## ✅ Реализовано

### Backend (Python/FastAPI)

**Модели БД:**
- `ScenarioStats` - агрегированная статистика по сценариям
- `MatchScenario` - связь матчей со сценариями (для детализации)

**API Endpoints:**
```
GET  /api/v1/player/{id}/scenarios                    - Получить все сценарии игрока
GET  /api/v1/player/{id}/scenarios/{code}/matches     - Получить матчи по сценарию
POST /api/v1/player/{id}/scenarios/analyze            - Запустить анализ игрока
POST /api/v1/scenarios/analyze-all                    - Анализ всех игроков
```

**Сценарии (S1-S6):**
- **S1**: Выиграл 1-й сет → проиграл матч 1-3
- **S2**: Выиграл первые 2 сета → проиграл 2-3
- **S3**: Матч был 1-1 по сетам
- **S4**: Вёл по сетам 2-0
- **S5**: Fight Score в проигранных сетах ≥ 0.3
- **S6**: Fight Score < 0.3

**Fight Score:**
```python
Fight Score = среднее(Очки_игрока / Очки_соперника) по проигранным сетам
```

**Интерпретация:**
- ≥ 0.70: Доминирует даже в проигранных сетах
- 0.50-0.69: Равная борьба
- 0.30-0.49: Борется, но уступает
- < 0.30: Психологически «сыпется»

### Frontend (React/TypeScript)

**Компоненты:**

1. **PlayerCardModal** - Модальное окно карточки игрока с вкладками
   - Вкладка "Карточки" - информация о триггерах
   - Вкладка "СТАТИСТИЧЕСКИЙ АНАЛИЗ" - сценарный анализ

2. **ScenarioAnalysisTab** - Таблица со всеми сценариями игрока
   - Отображает статистику по каждому сценарию
   - Кнопка "Обновить анализ" для пересчёта
   - Кнопка "Подробнее" для каждого сценария

3. **ScenarioDetailsModal** - Модальное окно 1600×800px
   - Метрики: матчи, победы, поражения, Fight Score
   - Интерпретация и поведенческие ярлыки
   - Список всех матчей сценария с деталями

**API Client:**
```typescript
import { scenarioAPI } from '../services/scenarioApi';

// Получить сценарии игрока
const data = await scenarioAPI.getPlayerScenarios(playerId);

// Получить матчи сценария
const matches = await scenarioAPI.getScenarioMatches(playerId, 'S1');

// Запустить анализ
await scenarioAPI.analyzePlayer(playerId);
```

**Утилиты для UI:**
```typescript
import { scenarioUtils } from '../services/scenarioApi';

// Цвета для UI
scenarioUtils.getFightScoreColor(0.65);  // Возвращает цвет
scenarioUtils.getWinRateColor(55);       // Возвращает цвет
scenarioUtils.getBehaviorBadgeColor('Сыпется под давлением');
scenarioUtils.formatDate('2024-01-15');  // Форматирование даты
```

## 🚀 Как использовать

### 1. В карточке игрока (AnalysisPage)

На каждой карточке игрока в списке "Подозрительные игроки" теперь есть **кнопка "📊 Сценарии"** на баннере:

```
┌────────────────────────────────────────────┐
│ #85                                         │
│                                             │
│ Абельмасов Игорь  [📊 Сценарии] ← КНОПКА  │
│                                             │
│ Рейтинг: 511                               │
│ Побед: 1/4 (25.0%)                         │
│ ...                                        │
└────────────────────────────────────────────┘
```

**Клик на кнопку** → открывает модальное окно `PlayerCardModal` с двумя вкладками:
- **"Карточки"** - существующие триггеры
- **"СТАТИСТИЧЕСКИЙ АНАЛИЗ"** - новый сценарный анализ

```python
# В Python консоли или скрипте
from sqlalchemy.orm import Session
from app.database.db import SessionLocal
from app.services.scenario_analysis_service import ScenarioAnalysisService

db = SessionLocal()

# Анализ одного игрока
result = ScenarioAnalysisService.analyze_player_matches(db, player_id)

# Получение сценариев
scenarios = ScenarioAnalysisService.get_player_scenarios(db, player_id)

db.close()
```

### 2. Использование в React

```tsx
import PlayerCardModal from '../components/PlayerCardModal';

function MyComponent() {
  const [showModal, setShowModal] = useState(false);
  
  return (
    <>
      <button onClick={() => setShowModal(true)}>
        Открыть карточку игрока
      </button>
      
      {showModal && (
        <PlayerCardModal
          playerId="player-uuid"
          playerName="Иванов Иван"
          playerRating={1500}
          onClose={() => setShowModal(false)}
          triggerInfo={{
            trigger_type: 'top_performers',
            trigger_value: 'Отличные результаты',
            severity_level: 1,
            period_start: '2024-01-01',
            period_end: '2024-12-31',
            created_at: '2024-12-01',
            evidence: []
          }}
        />
      )}
    </>
  );
}
```

### 3. API вызовы (curl примеры)

```bash
# Получить сценарии игрока
curl http://localhost:8000/api/v1/player/{player_id}/scenarios

# Получить матчи сценария S1
curl http://localhost:8000/api/v1/player/{player_id}/scenarios/S1/matches

# Запустить анализ игрока
curl -X POST http://localhost:8000/api/v1/player/{player_id}/scenarios/analyze

# Анализ всех игроков
curl -X POST http://localhost:8000/api/v1/scenarios/analyze-all
```

## 📊 Структура данных

### ScenarioStats (Response)
```json
{
  "scenario_code": "S1",
  "scenario_name": "Выиграл 1-й сет → проиграл матч 1-3",
  "matches_total": 10,
  "wins": 2,
  "losses": 8,
  "win_rate": 20.0,
  "fight_score": 0.450,
  "fight_score_interpretation": "Борется, но уступает",
  "behavior_label": "Теряет уверенность после лидерства",
  "updated_at": "2024-11-08T12:00:00"
}
```

### ScenarioMatchDetail (Response)
```json
{
  "match_id": "uuid",
  "date": "2024-11-08",
  "player1_name": "Иванов Иван",
  "player2_name": "Петров Пётр",
  "score": "1:3",
  "winner_id": "uuid",
  "is_win": false,
  "fight_score": 0.450,
  "sets": [
    {
      "set_number": 1,
      "player1_points": 11,
      "player2_points": 8,
      "winner_id": "uuid"
    }
  ]
}
```

## 🎨 UI/UX Особенности

- **Цветовая индикация:**
  - Зелёный: хорошие показатели
  - Жёлтый: средние показатели
  - Оранжевый: проблемные зоны
  - Красный: критические проблемы

- **Модальное окно:**
  - Размер: 1600×800px (настраивается)
  - Два таба: "Карточки" и "СТАТИСТИЧЕСКИЙ АНАЛИЗ"
  - Адаптивная вёрстка

- **Таблица сценариев:**
  - Сортировка по умолчанию
  - Кнопка "Подробнее" для каждой строки
  - Кнопка "Обновить анализ" для пересчёта

## ⚡ Производительность

- Анализ кэшируется в таблице `scenario_stats`
- Детали матчей в `match_scenario`
- Пересчёт только по запросу через API
- Frontend использует оптимизированные запросы

## 📝 Примечания

1. Таблицы созданы автоматически через `init_db()`
2. Все компоненты готовы к использованию
3. Стили полностью реализованы
4. TypeScript типы корректно работают
5. API полностью функциональный
