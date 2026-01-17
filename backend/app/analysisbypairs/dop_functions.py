from collections import Counter, defaultdict
from datetime import date
import json
import traceback
from app.analysisbypairs.ai_generation import LLM_MODEL
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.match import Match, MatchSet, Player, PlayerTrigger
from sqlalchemy import create_engine
engine = create_engine(
    "postgresql://user:pass@localhost/dbname",
    echo=True  # <--- покажет все SQL-запросы
)
import requests
from app.core.config import settings
llm_link = f"{settings.LM_STUDIO_API_URL}/v1/chat/completions"




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



# def ai_generate_match(
#     match,
#     player1,
#     player2,
#     db,
#     triggers_player1=None,
#     triggers_player2=None,
#     model=None,
#     provider=None,
#     max_tokens=300
# ):
#     """
#     Генерация AI анализа конкретного матча с учетом триггеров игроков.
#     triggers_player1/2 — список объектов триггеров {type, trigger_value, severity}
#     """
#     player1_triggers = payload.get("triggers", {}).get("player1", [])
#     player2_triggers = payload.get("triggers", {}).get("player2", [])

#     # Чтобы получить строку значений для промпта
#     player1_triggers_str = ", ".join([t["value"] for t in player1_triggers]) or "нет активных триггеров"
#     player2_triggers_str = ", ".join([t["value"] for t in player2_triggers]) or "нет активных триггеров"


#     # Формируем строку с триггерами
#     def format_triggers(triggers):
#         if not triggers:
#             return "Нет заметных триггеров."
#         return "\n".join(
#             [f"- {t['type']}: {t.get('trigger_value', '')} (серьезность {t.get('severity', '-')})"
#              for t in triggers]
#         )

#     prompt = f"""
# Матч: {player1.full_name} vs {player2.full_name}
# Счёт: {match.score}
# Сеты:
# {''.join([f"Сет {s.set_number}: {s.player1_points}:{s.player2_points}\n" for s in getattr(match, 'sets', [])])}

# Триггеры {player1_triggers_str}:
# {format_triggers(triggers_player1)}

# Триггеры {player2.full_name}:
# {player2_triggers_str}

# Проанализируй матч очень подробно, в пределах одного матча:
# - Укажи моменты, где конкретные триггеры игроков проявились сильнее всего.
# - Определи ключевые точки поворота (сеты, очки), где один игрок получил преимущество.
# - Дай краткий, но информативный вывод (3–5 предложений), что можно узнать о стратегии, сильных и слабых сторонах каждого игрока.
# - Пиши так, чтобы тренер или аналитик мог быстро понять, что сработало у игроков и где проявились их триггеры.
# """
#     system_prompt = (
#         "Ты профессиональный аналитик по настольному теннису. "
#         "Отвечай кратко и по делу, с конкретными примерами из матчей. "
#         "Если триггеры игроков проявились — обязательно укажи, где именно."
#     )

#     payload = {
#         "model": model or "default-model",
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": prompt.strip()}
#         ],
#         "temperature": 0.7,
#         "max_tokens": max_tokens
#     }

#     print("AI Generation Payload for match:", prompt)

#     try:
#         llm_link = "http://localhost:1234/v1/chat/completions"  # или ссылка на Ollama
#         response = requests.post(llm_link, json=payload)
#         response.raise_for_status()
#         result = response.json()

#         return (
#             result["choices"][0]["message"]["content"].strip()
#             if result.get("choices")
#             else "ИИ не вернул ответ"
#         )

#     except Exception as e:
#         return f"Ошибка AI анализа: {str(e)}"
    



def ai_generate_match(
    match,
    player1,
    player2,
    triggers_player1,
    triggers_player2,
    winner_id,
    db,
    max_tokens=2000
):
    # Нежелательные триггеры
    unwanted_triggers = [
        "Серия поражений:"
    ]

    def filter_triggers(triggers):
        return [t for t in triggers if not any(t["value"].startswith(u) for u in unwanted_triggers)]

    triggers_player1 = filter_triggers(triggers_player1)
    triggers_player2 = filter_triggers(triggers_player2)

    player1_triggers_str = ", ".join([t["value"] for t in triggers_player1]) or "нет активных триггеров"
    player2_triggers_str = ", ".join([t["value"] for t in triggers_player2]) or "нет активных триггеров"

    if winner_id == str(player1.id):
        match.winner = player1  
    elif winner_id == str(player2.id):
        match.winner = player2
    else:
        match.winner = None

    # Формируем строки с сетами и победителем каждого сета
    sets_str = ""
    for s in getattr(match, 'sets', []):
        if s.player1_points > s.player2_points:
            set_winner = player1.full_name
        elif s.player2_points > s.player1_points:
            set_winner = player2.full_name
        else:
            set_winner = "Ничья"
        sets_str += f"СЕТ {s.set_number}: {s.player1_points}:{s.player2_points} — Выиграл {set_winner}\n"

    prompt = f"""
МАТЧ: {player1.full_name} vs {player2.full_name}
СЧЕТ: {match.score}
ВЫИГРАЛ: {match.winner.full_name if match.winner else 'Ничья'}
СЕТЫ:
{sets_str}

Проанализируй матч очень подробно, в пределах одного матча:
-ПИШИ СПЛОШНЫМ ТЕКСТОМ БЕЗ ПУНКТОВ, НОМЕРОВ И ЗВЕЗДОЧЕК.
-ОТВЕТ ТОЛЬКО 3-4 ПРЕДЛОЖЕНИЯ. 
-НЕ ПИШИ НИЧЕГО ПРО ПСИХОЛОГИЮ.
-БУДЬ ВНИМАТЕЛЕН К СЕТАМ И СЧЕТУ.
-Скажи как тебе матч и были ли там триггеры.

Возможные триггеры {player1.full_name}:
{player1_triggers_str}

Возможные триггеры {player2.full_name}:
{player2_triggers_str}
"""
    system_prompt = (
        "Ты профессиональный аналитик по настольному теннису. "
        "Отвечай кратко, но подробно по триггерам, давая полезную информацию для тренера."
    )

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt.strip()}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens
    }

    print("AI Generation Payload for match:", prompt)

    try:
        response = requests.post(llm_link, json=payload)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip() if result.get("choices") else "ИИ не вернул ответ"
    except Exception as e:
        return f"Ошибка AI анализа: {str(e)}"
