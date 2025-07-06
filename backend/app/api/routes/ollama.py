"""
🛣️ МАРШРУТЫ ДЛЯ OLLAMA API

Это файл определяет все HTTP эндпоинты (адреса) для работы с Ollama:
- POST /chat - отправить сообщение модели
- GET /models - получить список доступных моделей  
- GET /status - проверить, работает ли Ollama

ДЛЯ ЧАЙНИКОВ: если фронтенд не может отправить сообщение,
проверьте, правильно ли работают эти эндпоинты в браузере:
http://localhost:8000/api/v1/ollama/models
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Optional
from app.services.auth_service import get_current_active_user
from app.services.ollama_service import (
    send_message,
    send_streaming_message,  # 🌊 Потоковый режим - быстрее для больших моделей
    get_available_models,    # 📋 Получение списка моделей из Ollama
    test_connection,         # 🔌 Проверка соединения с Ollama
    trigger
)
from pydantic import BaseModel

# 🎯 Создаем группу маршрутов для Ollama
router = APIRouter(tags=["ollama"])

# 📋 Схемы данных (что принимаем и отдаем)

class ChatRequest(BaseModel):
    """📨 Что нам присылает фронтенд для чата"""
    model: str                          # Какую модель использовать (например, "phi3")
    messages: List[Dict[str, str]]      # История сообщений [{"role": "user", "content": "привет"}]

class ChatResponse(BaseModel):
    """📤 Что мы отправляем обратно фронтенду"""
    content: str                        # Ответ от модели ИИ
    model: str                          # Какая модель ответила

class OllamaModel(BaseModel):
    """🤖 Информация о модели"""
    id: str                             # Техническое имя модели (phi3, llama2, etc.)
    name: str                           # Красивое имя для показа пользователю

# 🔐 ВСЕ ЭНДПОИНТЫ ТРЕБУЮТ АВТОРИЗАЦИИ!
# current_user = Depends(get_current_active_user) проверяет токен

@router.post("/chat", response_model=ChatResponse)
async def chat_with_model(
    request: ChatRequest,
    current_user = Depends(get_current_active_user)  # 🔒 Только для авторизованных!
):
    """
    💬 ГЛАВНЫЙ ЭНДПОИНТ ДЛЯ ЧАТА С ИИ
    
    Принимает сообщения от фронтенда и отправляет их в Ollama.
    Использует потоковый режим для быстрой работы.
    
    Для чайников: если чат не работает, проблема либо здесь, 
    либо в ollama_service.py, либо Ollama не запущена.
    """
    try:
        # 📊 Логируем для отладки (смотрите в консоли бэкенда)
        print(f"🎯 Запрос к модели {request.model} от пользователя {current_user.username}")
        print(f"Количество сообщений в истории: {len(request.messages)}")
        
        # 🌊 Используем потоковый режим - быстрее и надежнее!
        response = await send_streaming_message(model=request.model, messages=request.messages)
        
        # 🚨 Проверяем, что модель что-то ответила
        if not response or response.strip() == "":
            print("ВНИМАНИЕ: Получен пустой ответ от модели!")
            response = "Модель вернула пустой ответ. Пожалуйста, попробуйте еще раз или выберите другую модель."
        else:
            print(f"✅ Модель {request.model} успешно ответила (длина: {len(response)} символов)")
        
        print(f"Получен ответ длиной {len(response)} символов")
        
        return ChatResponse(
            content=response,
            model=request.model
        )
    except HTTPException as e:
        # HTTP ошибки пробрасываем как есть (401, 404, 500 и т.д.)
        raise e
    except Exception as e:
        # Все остальные ошибки превращаем в HTTP 500
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=List[OllamaModel])
async def list_models(
    current_user = Depends(get_current_active_user)  # 🔒 Только для авторизованных!
):
    """
    📋 ПОЛУЧЕНИЕ СПИСКА ДОСТУПНЫХ МОДЕЛЕЙ
    
    Фронтенд вызывает этот эндпоинт, чтобы показать пользователю 
    какие модели можно выбрать в селекторе.
    
    Для чайников: если в селекторе моделей пусто, проблема здесь!
    Проверьте, что Ollama запущена и в ней есть скачанные модели.
    """
    try:
        print(f"Получение списка моделей для пользователя: {current_user.username}")
        
        # 🔌 Сначала проверяем, что Ollama вообще работает
        is_connected = await test_connection()
        if not is_connected:
            print("Нет соединения с Ollama API")
            raise HTTPException(status_code=503, 
                               detail="Cannot connect to Ollama API. Please make sure Ollama is running.")
        
        # 📥 Получаем список моделей из Ollama
        models = await get_available_models()
        print(f"Найдено моделей: {len(models)}")
        
        # 🚨 Если моделей нет, подсказываем пользователю что делать
        if len(models) == 0:
            print("Модели не найдены, хотя Ollama доступна")
            return [{"id": "none", "name": "No models found. Use 'ollama pull MODEL_NAME' to download models."}]
        
        return models
    except HTTPException as e:
        # HTTP ошибки пробрасываем дальше
        print(f"HTTP ошибка при получении списка моделей: {e}")
        raise e
    except Exception as e:
        print(f"Ошибка получения списка моделей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status", status_code=200)
async def check_status():
    """
    Проверяет статус подключения к Ollama.
    Эта конечная точка доступна без аутентификации для проверки доступности.
    """
    try:
        is_connected = await test_connection()
        return {"status": "connected" if is_connected else "disconnected"}
    except Exception as e:
        # Логируем ошибку, но всегда возвращаем 200 статус код
        print(f"Ошибка проверки статуса Ollama: {e}")
        return {"status": "disconnected", "error": str(e)}



# Модель запроса для данных о матче
class MatchData(BaseModel):
    игрок_1: str
    игрок_2: str
    рейтинг_1: float
    рейтинг_2: float
    счёт: str
    этап: str
    турнир: str
    лига: str
    model: str = "DEFAULT_MODEL_NOT_SELECTED"  # Изменяем дефолт для отладки

# Новый маршрут
@router.post("/check-trigger")
async def check_trigger_and_ask_ollama(
    match_data: MatchData,
    current_user=Depends(get_current_active_user)
):
    """
    Проверяет триггер по данным матча и отправляет результат в Ollama.
    """
    try:
        print(f"🔍 Получен запрос на анализ матча от пользователя {current_user.username}")
        print(f"🔍 Данные запроса: {match_data.model_dump()}")
        print(f"🔍 Выбранная модель: '{match_data.model}'")
        
        # 1. Проверяем триггер (пока пустая заглушка)
        trigger_context = trigger(match_data.model_dump())
        print(f"Контекст от триггера: {trigger_context}")
        print(f"🎯 Анализ матча будет выполнен с помощью модели: {match_data.model}")
        
        # 2. Создаём сообщения для Ollama
        messages = [
            {"role": "system", "content": "Ты — спортивный аналитик настольного тенниса."},
            {"role": "user", "content": trigger_context}
        ]
        
        # 3. Отправляем в Ollama с выбранной пользователем моделью
        response = await send_streaming_message(model=match_data.model, messages=messages)
        print(f"✅ Модель {match_data.model} успешно проанализировала матч")

        return {
            "context": trigger_context,
            "ollama_response": response
        }
    except Exception as e:
        print(f"Ошибка при проверке триггера: {e}")
        raise HTTPException(status_code=500, detail=str(e))