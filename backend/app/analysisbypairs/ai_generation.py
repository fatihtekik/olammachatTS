import requests
from typing import Dict
from app.core.config import settings


LLM_MODEL = "deepseek/deepseek-r1-0528-qwen3-8b"  # ← имя модели из LLM Studio
llm_link = f"{settings.LM_STUDIO_API_URL}/v1/chat/completions"


def ai_generate(data: Dict) -> str:
    """
    data = {
        player1: { name, rating, triggers[] },
        player2: { name, rating, triggers[] },
        h2h: { matches_count, player1_wins, player2_wins }
    }
    """

    def format_triggers(triggers):
        if not triggers:
            return "нет выраженных триггеров"
        return "; ".join(
            # f"{t['type']} (значение: {t['value']}, серьёзность: {t['severity']})"
            f"{t['value']} (серьёзность: {t['severity']}); "
            for t in triggers
        )

    p1 = data["player1"]
    p2 = data["player2"]
    h2h = data["h2h"]

    system_prompt = (
        "Ты профессиональный аналитик по настольному теннису. "
        "Отвечай кратко, по делу, без воды."
    )

    user_prompt = f"""
Игрок 1:
Имя: {p1['name']}
Рейтинг: {p1['rating']}
Во время игры с {p2['name']} получает триггеры: {format_triggers(p1['triggers'])}

Игрок 2:
Имя: {p2['name']}
Рейтинг: {p2['rating']}
Во время игры с {p1['name']} получает триггеры: {format_triggers(p2['triggers'])}

История личных встреч:
Всего матчей: {h2h['matches_count']}
Победы {p1['name']}: {h2h['player1_wins']}
Победы {p2['name']}: {h2h['player2_wins']}

Сделай аналитический вывод:
- кто имеет преимущество
- влияние триггеров
- 3–5 предложений
- русский язык
-аргументируй выводы

Помимо этого если есть важные детали на которые нужно обратить внимание, добавь их в анализ. Сделай прогноз на будущие матчи между этими игроками.
"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt.strip()}
        ],
        "temperature": 0.7,
        # "max_tokens": 300
    }
    print("mrmrmrmrmrrr AI Generation Payload:", user_prompt)

    try:
        response = requests.post(
            llm_link,
            json=payload,
            # timeout=6000000
        )
        response.raise_for_status()

        result = response.json()

        return (
            result["choices"][0]["message"]["content"].strip()
            if result.get("choices")
            else "ИИ не вернул ответ"
        )

    except Exception as e:
        return f"Ошибка AI анализа: {str(e)}"
