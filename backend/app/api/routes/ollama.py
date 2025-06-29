from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Optional
from app.services.auth_service import get_current_active_user
from app.services.ollama_service import (
    send_message,
    send_streaming_message,
    get_available_models,
    test_connection,
    trigger
)
from pydantic import BaseModel

# Определение маршрута для Ollama API
router = APIRouter(tags=["ollama"])

# Схема для запроса чата
class ChatRequest(BaseModel):
    model: str
    messages: List[Dict[str, str]]

# Схема для ответа от модели
class ChatResponse(BaseModel):
    content: str
    model: str

# Схема для моделей
class OllamaModel(BaseModel):
    id: str
    name: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_model(
    request: ChatRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Отправляет сообщение в модель Ollama и получает ответ.
    Использует потоковый режим для оптимальной обработки ответов даже от больших моделей.
    """
    try:
        # Логируем входящий запрос для диагностики
        print(f"🎯 Запрос к модели {request.model} от пользователя {current_user.username}")
        print(f"Количество сообщений в истории: {len(request.messages)}")
        
        # Использование потокового режима для всех моделей для более стабильной работы
        response = await send_streaming_message(model=request.model, messages=request.messages)
        
        # Убедимся, что ответ не пустой
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
        # Прокидываем HTTPException дальше
        raise e
    except Exception as e:
        # Остальные ошибки конвертируем в HTTP ошибки
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=List[OllamaModel])
async def list_models(
    current_user = Depends(get_current_active_user)
):
    """
    Получает список доступных моделей из локального Ollama
    """
    try:
        print(f"Получение списка моделей для пользователя: {current_user.username}")
        
        # Сначала проверяем соединение с Ollama
        is_connected = await test_connection()
        if not is_connected:
            print("Нет соединения с Ollama API")
            raise HTTPException(status_code=503, 
                               detail="Cannot connect to Ollama API. Please make sure Ollama is running.")
        
        models = await get_available_models()
        print(f"Найдено моделей: {len(models)}")
        
        # Если моделей нет, возможно Ollama запущена, но нет загруженных моделей
        if len(models) == 0:
            print("Модели не найдены, хотя Ollama доступна")
            return [{"id": "none", "name": "No models found. Use 'ollama pull MODEL_NAME' to download models."}]
        
        return models
    except HTTPException as e:
        # Пробрасываем HTTP ошибки дальше
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