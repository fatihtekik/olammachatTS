"""Сервис для работы с Ollama API"""
from typing import List, Dict, Any, Optional
import httpx
import asyncio
import logging
import time
import json
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

# Большие модели, требующие особого подхода
LARGE_MODELS = ['deepseek', 'llama3-70b', 'mixtral-8x7b', 'qwen', 'solar-10b']

def is_large_model(model_name: str) -> bool:
    """Проверка, является ли модель "большой" и требующей особого подхода"""
    return any(name.lower() in model_name.lower() for name in LARGE_MODELS)

def convert_messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """Конвертирует сообщения чата в текстовый промпт для формата /api/generate"""
    prompt = ""
    
    for msg in messages:
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        
        if role == "system":
            prompt += f"[SYSTEM]: {content}\n\n"
        elif role == "user":
            prompt += f"[USER]: {content}\n\n"
        elif role == "assistant":
            prompt += f"[ASSISTANT]: {content}\n\n"
        else:
            prompt += f"{content}\n\n"
    
    # Добавляем метку для ответа ассистента, если последнее сообщение от пользователя
    if messages and messages[-1]["role"].lower() == "user":
        prompt += "[ASSISTANT]: "
    
    return prompt.strip()

async def send_generate_request(model: str, prompt: str) -> str:
    """Отправляет запрос через эндпоинт /api/generate"""    # Таймаут для больших моделей
    is_model_large = is_large_model(model)
    timeout_duration = 1000 if is_model_large else 180  # секунды
    
    logger.info(f"Запрос к модели: {model}, таймаут: {timeout_duration}s")
    
    start_time = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=timeout_duration) as client:
            response = await client.post(
                f"{settings.OLLAMA_API_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_ctx": 8192,
                        "temperature": 0.7,
                        "top_k": 50,
                    }
                }
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Error response from Ollama API: {response.status_code} - {error_text}")
                
                # Обрабатываем специфичные ошибки
                if response.status_code == 404 and "model" in error_text and "not found" in error_text:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Model '{model}' not found. You need to download it first using the command: ollama pull {model}"
                    )
                
                if response.status_code in [500, 502, 504]:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Model '{model}' is having trouble loading or responding (Error {response.status_code}). Large models may take several minutes to load. Try restarting Ollama or checking the Ollama logs."
                    )
                
                raise HTTPException(status_code=response.status_code, detail=f"API error: {error_text}")
            
            data = response.json()
            logger.info(f"Response received after {time.time() - start_time:.2f}s")
            
            # Получаем ответ из поля "response" в соответствии с API /api/generate
            if "response" in data:
                return data["response"]
            else:
                logger.error(f"Unexpected response format from Ollama API: {data}")
                raise HTTPException(status_code=500, detail="Unexpected response format from Ollama API")
    
    except httpx.TimeoutException:
        error_message = f"Request to model '{model}' timed out after {timeout_duration} seconds.\n\n"
        
        if is_large_model(model):
            error_message += (
                "This is a very large model that takes significant time to load. The model might still be loading in the background. You can try:\n"
                "1. Wait a few minutes and try again\n"
                "2. Check Ollama logs in the terminal\n"
                "3. Restart the Ollama service\n"
                "4. Consider using a smaller model if immediate responses are needed"
            )
        else:
            error_message += "The model might be still loading or the response is taking too long. You may need to restart Ollama."
        
        logger.error(f"Timeout error: {error_message}")
        raise HTTPException(status_code=504, detail=error_message)
    
    except Exception as error:
        logger.error(f"Error in send_generate_request: {error}")
        raise HTTPException(status_code=500, detail=str(error))

async def send_message(model: str, messages: List[Dict[str, str]]) -> str:
    """Отправляет сообщение через API Ollama, используя формат /api/generate"""
    try:
        logger.info(f"Preparing to send message to model: {model}")
        
        # Для больших моделей пропускаем проверку доступности для улучшения UX
        is_model_large = is_large_model(model)
        
        if not is_model_large:
            # Сначала проверим, доступна ли модель
            is_available = await is_model_available(model)
            if not is_available:
                raise HTTPException(
                    status_code=400,
                    detail=f"Model '{model}' not found. You need to download it first using the command: ollama pull {model}"                )
        else:
            logger.info(f"Skipping strict availability check for large model: {model}")
        
        # Конвертируем сообщения в единый промпт
        prompt = convert_messages_to_prompt(messages)
        
        # Отправляем запрос через /api/generate
        return await send_generate_request(model, prompt)
    
    except httpx.HTTPError as error:
        logger.error(f"Error communicating with local Ollama instance: {error}")
        
        error_message = str(error)
        # Если ошибка содержит указание о загрузке модели, добавляем дополнительную помощь
        if "pull" in error_message:
            error_message += "\n\nYou can install models using the Ollama command line. For example: 'ollama pull phi3'"
        
        # Для больших моделей добавляем дополнительные инструкции
        if is_large_model(model) and "large model" not in error_message:
            error_message += "\n\nThis is a large model that may take several minutes to load the first time. If it worked in your terminal, try waiting for a while and making the request again."
        
        raise HTTPException(status_code=500, detail=error_message)

async def send_streaming_message(model: str, messages: List[Dict[str, str]]) -> str:
    """Отправляет сообщение с использованием потокового режима"""    # Таймаут для больших моделей
    is_model_large = is_large_model(model)
    timeout_duration = 1000 if is_model_large else 180  # секунды
    
    logger.info(f"Стриминг запрос к модели: {model}, таймаут: {timeout_duration}s")
    
    start_time = time.time()
    full_response = ""
    has_started_receiving_content = False
    last_progress_update = time.time()
    
    try:
        async with httpx.AsyncClient(timeout=timeout_duration) as client:
            response = await client.post(
                f"{settings.OLLAMA_API_URL}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,  # Включаем стриминг
                    "options": {
                        "num_ctx": 8192,  # Увеличенный размер контекста для лучшей обработки больших моделей
                        "temperature": 0.7,
                        "top_k": 50,
                    }
                }
            )
            
            if response.status_code != 200:
                error_text = response.text
                logger.error(f"Error response from Ollama API: {response.status_code} - {error_text}")
                
                # Обрабатываем специфичные ошибки с более детальными объяснениями
                if response.status_code == 404 and "model" in error_text and "not found" in error_text:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Model '{model}' not found. You need to download it first using the command: ollama pull {model}"
                    )
                
                # Обрабатываем ошибки таймаута/загрузки с лучшим объяснением
                if response.status_code in [500, 502, 504]:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Model '{model}' is having trouble loading or responding (Error {response.status_code}). Large models may take several minutes to load. Try restarting Ollama or checking the Ollama logs."
                    )
                
                raise HTTPException(status_code=response.status_code, detail=f"API error: {error_text}")
            
            # Читаем ответ построчно
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                
                try:
                    json_data = httpx.loads(line)
                    
                    # Извлекаем контент сообщения, может быть в разных форматах
                    content = None
                    if 'message' in json_data and 'content' in json_data['message']:
                        content = json_data['message']['content']
                    elif 'response' in json_data:
                        content = json_data['response']
                    
                    if content:
                        if not has_started_receiving_content:
                            has_started_receiving_content = True
                            logger.info(f"First content received after {time.time() - start_time:.2f}s")
                        
                        full_response += content
                        last_progress_update = time.time()
                    
                    # Логируем прогресс для длинных ответов
                    if time.time() - last_progress_update > 10:
                        logger.info(f"Получено {len(full_response)} символов от {model}")
                        last_progress_update = time.time()
                        
                except Exception as e:                logger.warning(f'Failed to parse streaming response chunk: {line} - {str(e)}')
            
            logger.info(f"Ответ получен за {time.time() - start_time:.2f}s")
        return full_response
    
    except httpx.TimeoutException:
        error_message = f"Request to model '{model}' timed out after {timeout_duration} seconds.\n\n"
        
        if is_large_model(model):
            error_message += (
                "This is a very large model that takes significant time to load. The model might still be loading in the background. You can try:\n"
                "1. Wait a few minutes and try again\n"
                "2. Check Ollama logs in the terminal\n"
                "3. Restart the Ollama service\n"
                "4. Consider using a smaller model if immediate responses are needed"
            )
        else:
            error_message += "The model might be still loading or the response is taking too long. You may need to restart Ollama."
        
        logger.error(f"Streaming error (timeout): {error_message}")
        raise HTTPException(status_code=504, detail=error_message)
    
    except Exception as error:
        logger.error(f"Streaming error: {error}")
        raise HTTPException(status_code=500, detail=str(error))

async def get_available_models() -> List[Dict[str, str]]:
    """Получает список доступных моделей из локального Ollama"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.OLLAMA_API_URL}/api/tags")
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"API error: {response.status_code}")
            data = response.json()
            
            # Проверка на пустой список моделей
            if not data.get("models") or len(data["models"]) == 0:
                logger.warning("Нет доступных моделей")
                return []
            
            logger.info(f"Найдено моделей: {len(data['models'])}")
            
            # Преобразуем формат списка моделей Ollama в формат нашего приложения
            # Добавляем более описательные имена для распространенных моделей
            result = []
            for model in data["models"]:
                model_name = model["name"].lower()
                display_name = model["name"]
                
                # Улучшенное именование моделей
                if "phi3" in model_name:
                    display_name = f"Phi-3 {'Mini' if 'mini' in model_name else ''}"
                elif "llama3" in model_name:
                    display_name = f"Llama 3 {'8B' if '8b' in model_name else '70B' if '70b' in model_name else ''}"
                elif "llama2" in model_name:
                    display_name = f"Llama 2 {'7B' if '7b' in model_name else '13B' if '13b' in model_name else ''}"
                elif "gemma" in model_name:
                    display_name = f"Gemma {'2B' if '2b' in model_name else '7B' if '7b' in model_name else ''}"
                elif "mistral" in model_name:
                    display_name = f"Mistral {'7B' if '7b' in model_name else ''}"
                
                result.append({
                    "id": model["name"],
                    "name": display_name
                })
            
            return result
            
    except Exception as error:
        logger.error(f"Error fetching models from local Ollama: {error}")
        # Если не удалось получить модели из Ollama, возвращаем пустой массив
        return []

async def test_connection() -> bool:
    """Проверяет соединение с локальным экземпляром Ollama"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_API_URL}/api/version")
            return response.status_code == 200
    except Exception as error:
        logger.error(f"Cannot connect to local Ollama instance: {error}")
        return False

async def is_model_available(model_name: str) -> bool:
    """Проверяет доступность указанной модели"""
    try:
        models = await get_available_models()
        model_exists = any(model["id"] == model_name for model in models)
        
        # Если модель не найдена в списке, делаем прямую проверку для верификации
        # (Иногда список моделей не обновляется мгновенно)
        if not model_exists:
            try:
                async with httpx.AsyncClient(timeout=8.0) as client:
                    response = await client.post(
                        f"{settings.OLLAMA_API_URL}/api/generate",
                        json={
                            "model": model_name,
                            "prompt": "Hello",
                            "stream": False,
                            "options": {"num_predict": 1}  # Минимальное предсказание токенов для проверки существования модели
                        }
                    )
                    return response.status_code == 200
            except Exception as probe_error:
                logger.info(f"Direct model probe failed: {probe_error}")
                return False
        
        return model_exists
    
    except Exception as error:
        logger.error(f"Error checking model availability: {error}")
        return False

async def query_ollama(prompt: str, model: str = "llama3") -> str:
    """Прямой метод запроса к Ollama через /api/generate"""
    try:
        logger.info(f"Querying Ollama with model {model}")
        
        async with httpx.AsyncClient(timeout=600) as client:
            response = await client.post(
                f"{settings.OLLAMA_API_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data["response"]
    except Exception as error:
        logger.error(f"Error in query_ollama: {error}")
        raise HTTPException(status_code=500, detail=str(error))
