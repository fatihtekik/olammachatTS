from collections import Counter, defaultdict
from datetime import date
import json
import traceback
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.match import Match, MatchSet, Player, PlayerTrigger
from sqlalchemy import create_engine
engine = create_engine(
    "postgresql://user:pass@localhost/dbname",
    echo=True  # <--- покажет все SQL-запросы
)




SEASONS = {
    "Зима": [12, 1, 2],
    "Весна": [3, 4, 5],
    "Лето": [6, 7, 8],
    "Осень": [9, 10, 11],
}

def get_season(date_obj):
    for season, months in SEASONS.items():
        if date_obj.month in months:
            return season
    return None



def calculate_severity_level(player: Player, opponent: Player, matches: list[Match], trigger_type: str, relevant_matches: list[Match]) -> int:
    """
    Универсальный расчет severity_level для триггеров.
    
    player: игрок, для которого считается триггер
    opponent: оппонент игрока
    matches: все очные матчи между player и opponent
    trigger_type: тип триггера (h2h_losing_streak, h2h_close_score_losses, h2h_score_pattern)
    relevant_matches: матчи, на которых основан текущий триггер (например, серия поражений)
    """
    if not relevant_matches:
        return 1

    # 1️⃣ Частота события
    total_matches = len(matches)
    trigger_matches = len(relevant_matches)
    frequency_ratio = trigger_matches / total_matches if total_matches else 0

    # 2️⃣ Серьёзность события по типу триггера
    type_factor = {
        "h2h_losing_streak": 1.5,        # серия поражений считается более серьёзной
        "h2h_close_score_losses": 1.0,   # близкие поражения средней серьёзности
        "h2h_score_pattern": 1.2,        # часто повторяющийся счет
        "h2h_deciding_set_behavior": 1.3, # поведение в решающем сете
        "h2h_set_anomalies": 1.4,        # аномалии в сетах
        "h2h_first_set_win": 1.2,        # победа в первом сете
        "h2h_seasonal_pattern": 1.0,     # сезонные паттерны
        "h2h_lead_2_0_behavior": 1.3,    # поведение при 2:0
    }.get(trigger_type, 1.0)

    # 3️⃣ Важность матчей (если есть поле is_final, is_deciding_set и т.п.)
    importance_factor = 1.0
    for m in relevant_matches:
        if getattr(m, "is_final", False):
            importance_factor += 0.3
        if getattr(m, "is_deciding_set", False):
            importance_factor += 0.2

    # 4️⃣ Итоговый расчет severity
    raw_severity = frequency_ratio * type_factor * importance_factor * 5  # шкала 1–5
    severity = max(1, min(5, round(raw_severity)))  # ограничиваем от 1 до 5

    return severity


def build_trigger_metadata(opponent=None, matches=None, pattern=None, **extra):
    """
    Универсальная сборка metadata для триггеров.
    Возвращает строку JSON с нормальной кодировкой.
    """

    meta = {}

    # Информация об оппоненте
    if opponent:
        meta["opponent_id"] = str(opponent.id)

    # Список матчей (их id)
    if matches:
        meta["match_ids"] = [str(m.id) for m in matches]

    # Паттерн/счёт
    if pattern:
        meta["pattern"] = pattern

    # Дополнительные значения
    if extra:
        meta.update(extra)

    # Возвращаем JSON-строку без escape последовательностей
    return json.dumps(meta, ensure_ascii=False)
