"""
СЕРВИС ДЛЯ РАБОТЫ С LM STUDIO API

LM Studio использует OpenAI-совместимый API
Стандартный адрес: http://localhost:1234
API Endpoints: /v1/models, /v1/chat/completions, /v1/completions, /v1/embeddings
"""

import httpx
import logging
from typing import List, Dict
from app.core.config import settings as settings_module

logger = logging.getLogger(__name__)


async def test_lm_studio_connection() -> bool:
    """
    Проверяет, доступен ли LM Studio
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # LM Studio использует /v1/models для проверки
            response = await client.get(f"{settings_module.LM_STUDIO_API_URL}/v1/models")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Ошибка подключения к LM Studio: {e}")
        return False


async def get_lm_studio_models() -> List[Dict[str, str]]:
    """
    Получает список доступных моделей из LM Studio
    
    LM Studio возвращает модели в формате OpenAI API
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings_module.LM_STUDIO_API_URL}/v1/models")
            
            if response.status_code == 200:
                data = response.json()
                models = []
                
                # LM Studio возвращает { "data": [{"id": "model-name", ...}] }
                if "data" in data:
                    for model in data["data"]:
                        model_id = model.get("id", "unknown")
                        models.append({
                            "id": model_id,
                            "name": model_id  # Можно улучшить форматирование имени
                        })
                
                logger.info(f"Найдено {len(models)} моделей в LM Studio")
                return models
            else:
                logger.error(f"LM Studio вернул статус: {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Ошибка получения моделей из LM Studio: {e}")
        return []


def _filter_messages_for_reset(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Оставляет только системные инструкции и последний пользовательский запрос.
    Используется для принудительного сброса контекста.
    """
    system_messages: List[Dict[str, str]] = [m for m in messages if m.get("role") == "system"]
    user_messages: List[Dict[str, str]] = [m for m in messages if m.get("role") == "user"]

    filtered: List[Dict[str, str]] = []
    # Сохраняем все системные сообщения (если есть)
    filtered.extend(system_messages)
    # Сохраняем только последний пользовательский запрос (если есть)
    if user_messages:
        filtered.append(user_messages[-1])
    # Если не нашли user, но был хоть какой‑то ввод, оставим последний элемент
    elif messages:
        filtered.append(messages[-1])
    return filtered


# Дефолтные настройки LM Studio
DEFAULT_LMSTUDIO_SETTINGS = {
    "temperature": 0.7,
    "maxCompletionTokens": 4000,
    "maxReasoningTokens": 5000,
    "topP": 1.0,
    "topK": 40,
    "repeatPenalty": 1.1,
    "reasoningEffort": "medium",
    "showReasoning": False
}


async def send_message_to_lm_studio(
    model: str, 
    messages: List[Dict[str, str]], 
    reset_history: bool = False,
    settings: Dict = None
) -> str:
    """
    Отправляет сообщение в LM Studio и получает ответ
    
    Использует OpenAI-совместимый формат запроса
    """
    # Используем переданные настройки или дефолтные
    cfg = {**DEFAULT_LMSTUDIO_SETTINGS, **(settings or {})}
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            # OpenAI-совместимый формат запроса
            messages_to_send = _filter_messages_for_reset(messages) if reset_history else messages
            payload = {
                "model": model,
                "messages": messages_to_send,
                "temperature": cfg["temperature"],
                "max_completion_tokens": cfg["maxCompletionTokens"],
                "max_reasoning_tokens": cfg["maxReasoningTokens"],
                "top_p": cfg["topP"],
                "top_k": cfg["topK"],
                "repeat_penalty": cfg["repeatPenalty"],
                "stream": False
            }
            
            response = await client.post(
                f"{settings_module.LM_STUDIO_API_URL}/v1/chat/completions",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                # OpenAI формат: {"choices": [{"message": {"content": "ответ"}}]}
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0].get("message", {}).get("content", "")
                    logger.info(f"Получен ответ от LM Studio, длина: {len(content)}")
                    logger.info(f"Ответ LM Studio: {content}")
                    # Дублируем вывод ответа в консоль для явной отладки
                    preview = content if len(content) <= 500 else content[:500] + "..."
                    print("LM Studio response:", preview)
                    return content
                else:
                    logger.error("LM Studio вернул пустой ответ")
                    return "Ошибка: LM Studio не вернул ответ"
            else:
                logger.error(f"LM Studio вернул статус {response.status_code}: {response.text}")
                return f"Ошибка: LM Studio вернул статус {response.status_code}"
                
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения в LM Studio: {e}")
        return f"Ошибка связи с LM Studio: {str(e)}"


async def stream_message_to_lm_studio(
    model: str, 
    messages: List[Dict[str, str]], 
    reset_history: bool = False,
    settings: Dict = None
):
    """
    Отправляет сообщение в LM Studio и получает потоковый ответ
    
    Использует OpenAI-совместимый формат с включенным streaming
    Возвращает асинхронный генератор для чанков текста
    """
    # Используем переданные настройки или дефолтные
    cfg = {**DEFAULT_LMSTUDIO_SETTINGS, **(settings or {})}
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            # OpenAI-совместимый формат с streaming
            messages_to_send = _filter_messages_for_reset(messages) if reset_history else messages
            payload = {
                "model": model,
                "messages": messages_to_send,
                "temperature": cfg["temperature"],
                "max_completion_tokens": cfg["maxCompletionTokens"],
                "max_reasoning_tokens": cfg["maxReasoningTokens"],
                "top_p": cfg["topP"],
                "top_k": cfg["topK"],
                "repeat_penalty": cfg["repeatPenalty"],
                "stream": True
            }
            
            async with client.stream(
                "POST",
                f"{settings_module.LM_STUDIO_API_URL}/v1/chat/completions",
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"LM Studio вернул статус {response.status_code}: {error_text}")
                    yield f"Ошибка: LM Studio вернул статус {response.status_code}"
                    return
                
                # Читаем потоковый ответ
                buffer = ""
                async for chunk in response.aiter_bytes():
                    buffer += chunk.decode('utf-8')
                    
                    # LM Studio возвращает SSE формат (Server-Sent Events)
                    # Каждая строка начинается с "data: " и содержит JSON
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        # Пропускаем пустые строки и комментарии
                        if not line or line.startswith(':'):
                            continue
                        
                        # Убираем префикс "data: "
                        if line.startswith('data: '):
                            line = line[6:]
                        
                        # Проверяем на финальный маркер
                        if line == '[DONE]':
                            break
                        
                        try:
                            import json
                            data = json.loads(line)
                            
                            # OpenAI streaming формат: {"choices": [{"delta": {"content": "текст"}}]}
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                
                                if content:
                                    # Дублируем потоковый ответ в консоль
                                    preview = content if len(content) <= 200 else content[:200] + "..."
                                    print("LM Studio stream chunk:", preview)
                                    yield content
                        except json.JSONDecodeError:
                            # Игнорируем некорректные JSON строки
                            continue
                
    except Exception as e:
        logger.error(f"Ошибка потоковой отправки в LM Studio: {e}")
        yield f"Ошибка связи с LM Studio: {str(e)}"
