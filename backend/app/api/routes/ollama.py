"""API маршруты для работы с Ollama"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.services import ollama_service
from app.services.auth_service import get_current_active_user

# Модели данных для API
class OllamaMessage(BaseModel):
    role: str
    content: str

class OllamaRequest(BaseModel):
    model: str
    messages: List[OllamaMessage]

class OllamaModelResponse(BaseModel):
    id: str
    name: str

class OllamaStatusResponse(BaseModel):
    connected: bool
    message: str

# Дополнительная модель для прямого запроса
class GenerateRequest(BaseModel):
    model: str = "llama3"
    prompt: str
    stream: bool = False

# Создаем роутер для Ollama API
router = APIRouter(prefix="/ollama", tags=["ollama"])

@router.post("/chat", response_model=Dict[str, str])
async def chat_with_model(
    request: OllamaRequest,
    current_user = Depends(get_current_active_user)
):
    """Запрос к модели через API чата"""
    try:
        # Преобразуем сообщения в формат, ожидаемый сервисом
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Отправляем запрос и получаем ответ
        response = await ollama_service.send_message(request.model, messages)
        
        return {"response": response}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=List[OllamaModelResponse])
async def get_models(
    current_user = Depends(get_current_active_user)
):
    """Получает список моделей"""
    models = await ollama_service.get_available_models()
    return models

@router.get("/status", response_model=OllamaStatusResponse)
async def get_status(
    current_user = Depends(get_current_active_user)
):
    """Проверяет статус Ollama"""
    connected = await ollama_service.test_connection()
    
    if connected:
        return {"connected": True, "message": "Successfully connected to Ollama API"}
    else:
        return {"connected": False, "message": "Failed to connect to Ollama API. Make sure Ollama is running."}

@router.get("/model/{model_name}/status", response_model=Dict[str, bool])
async def check_model_availability(
    model_name: str,
    current_user = Depends(get_current_active_user)
):
    """Проверяет доступность модели"""
    is_available = await ollama_service.is_model_available(model_name)
    return {"available": is_available}

@router.post("/generate", response_model=Dict[str, str])
async def generate_text(
    request: GenerateRequest,
    current_user = Depends(get_current_active_user)
):
    """Прямой запрос через /api/generate"""
    try:
        # Отправляем запрос и получаем ответ
        response = await ollama_service.query_ollama(
            prompt=request.prompt,
            model=request.model
        )
        
        return {"response": response}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
