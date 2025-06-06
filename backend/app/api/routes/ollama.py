from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Optional
from app.services.auth_service import get_current_active_user
from app.services.ollama_service import (
    send_message,
    send_streaming_message,
    get_available_models,
    test_connection
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
        print(f"Запрос к модели {request.model} от пользователя {current_user.username}")
        print(f"Количество сообщений в истории: {len(request.messages)}")
        
        # Использование потокового режима для всех моделей для более стабильной работы
        response = await send_streaming_message(model=request.model, messages=request.messages)
        
        # Убедимся, что ответ не пустой
        if not response or response.strip() == "":
            print("ВНИМАНИЕ: Получен пустой ответ от модели!")
            response = "Модель вернула пустой ответ. Пожалуйста, попробуйте еще раз или выберите другую модель."
        
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
