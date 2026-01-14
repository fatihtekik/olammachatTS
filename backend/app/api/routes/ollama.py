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

from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import List, Dict, Optional

from fastapi.responses import StreamingResponse
from app.services.auth_service import get_current_active_user
from app.services.ollama_service import (
    ollama_stream,
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

class LMStudioSettingsModel(BaseModel):
    """⚙️ Настройки LM Studio"""
    temperature: Optional[float] = 0.7
    maxCompletionTokens: Optional[int] = 4000
    maxReasoningTokens: Optional[int] = 5000
    topP: Optional[float] = 1.0
    topK: Optional[int] = 40
    repeatPenalty: Optional[float] = 1.1
    reasoningEffort: Optional[str] = "medium"
    showReasoning: Optional[bool] = False

class ChatRequest(BaseModel):
    """📨 Что нам присылает фронтенд для чата"""
    model: str                          # Какую модель использовать (например, "phi3")
    messages: List[Dict[str, str]]      # История сообщений [{"role": "user", "content": "привет"}]
    stream: Optional[bool] = False      # Включить потоковую передачу
    lmstudioSettings: Optional[LMStudioSettingsModel] = None  # Настройки LM Studio

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

@router.post("/chat")
async def chat_with_model(
    request: ChatRequest,
    current_user = Depends(get_current_active_user)  # 🔒 Только для авторизованных!
):
    """
    💬 ГЛАВНЫЙ ЭНДПОИНТ ДЛЯ ЧАТА С ИИ
    
    Принимает сообщения от фронтенда и отправляет их в Ollama.
    Поддерживает потоковый режим для быстрой работы.
    
    Для чайников: если чат не работает, проблема либо здесь, 
    либо в ollama_service.py, либо Ollama не запущена.
    """
    try:
        # 📊 Логируем для отладки (смотрите в консоли бэкенда)
        print(f"🎯 Запрос к модели {request.model} от пользователя {current_user.username}")
        print(f"Количество сообщений в истории: {len(request.messages)}")
        print(f"Режим стриминга: {request.stream}")
        
        # Если включен стриминг, возвращаем StreamingResponse
        if request.stream:
            async def generate():
                try:
                    async for chunk in ollama_stream(model=request.model, messages=request.messages):
                        # Отправляем chunk в формате NDJSON (newline-delimited JSON)
                        import json
                        yield json.dumps({"content": chunk}) + "\n"
                except Exception as e:
                    import json
                    yield json.dumps({"error": str(e)}) + "\n"
            
            return StreamingResponse(generate(), media_type="application/x-ndjson")
        else:
            # Обычный режим без стриминга
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


# НОВЫЕ ЭНДПОИНТЫ ДЛЯ LM STUDIO
@router.get("/lmstudio/status", status_code=200)
async def check_lmstudio_status():
    """
    Проверяет статус подключения к LM Studio
    """
    try:
        from app.services.lm_studio_service import test_lm_studio_connection
        is_connected = await test_lm_studio_connection()
        return {"status": "connected" if is_connected else "disconnected"}
    except Exception as e:
        print(f"Ошибка проверки статуса LM Studio: {e}")
        return {"status": "disconnected", "error": str(e)}


@router.get("/lmstudio/models", response_model=List[OllamaModel])
async def list_lmstudio_models(
    current_user = Depends(get_current_active_user)
):
    """
    Получение списка доступных моделей из LM Studio
    """
    try:
        from app.services.lm_studio_service import get_lm_studio_models, test_lm_studio_connection
        print(f"Получение списка моделей LM Studio для пользователя: {current_user.username}")
        
        is_connected = await test_lm_studio_connection()
        if not is_connected:
            print("Нет соединения с LM Studio API")
            raise HTTPException(status_code=503, 
                               detail="Cannot connect to LM Studio API. Please make sure LM Studio is running.")
        
        models = await get_lm_studio_models()
        print(f"Найдено моделей LM Studio: {len(models)}")
        
        if len(models) == 0:
            return [{"id": "none", "name": "No models loaded in LM Studio"}]
        
        return models
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Ошибка получения списка моделей LM Studio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lmstudio/chat")
async def chat_with_lmstudio(
    request: ChatRequest,
    current_user = Depends(get_current_active_user)
):
    """
    Отправка сообщения в LM Studio и получение ответа
    Поддерживает потоковый режим для быстрой работы.
    """
    try:
        from app.services.lm_studio_service import (
            send_message_to_lm_studio, 
            test_lm_studio_connection,
            stream_message_to_lm_studio
        )
        print(f"Запрос к LM Studio модели {request.model} от пользователя {current_user.username}")
        print(f"Количество сообщений в истории: {len(request.messages)}")
        print(f"Режим стриминга: {request.stream}")
        
        # Получаем настройки LM Studio (или None)
        lmstudio_settings = request.lmstudioSettings.model_dump() if request.lmstudioSettings else None
        if lmstudio_settings:
            print(f"Настройки LM Studio: {lmstudio_settings}")
        
        # Проверяем подключение
        is_connected = await test_lm_studio_connection()
        if not is_connected:
            raise HTTPException(status_code=503, 
                               detail="Cannot connect to LM Studio API. Please make sure LM Studio is running.")
        
        # Если включен стриминг
        if request.stream:
            async def generate():
                try:
                    async for chunk in stream_message_to_lm_studio(
                        model=request.model, 
                        messages=request.messages,
                        settings=lmstudio_settings
                    ):
                        # Отправляем chunk в формате NDJSON
                        import json
                        yield json.dumps({"content": chunk}) + "\n"
                except Exception as e:
                    import json
                    yield json.dumps({"error": str(e)}) + "\n"
            
            return StreamingResponse(generate(), media_type="application/x-ndjson")
        else:
            # Обычный режим без стриминга
            response = await send_message_to_lm_studio(
                model=request.model, 
                messages=request.messages,
                settings=lmstudio_settings
            )
            
            if not response or response.strip() == "":
                print("ВНИМАНИЕ: Получен пустой ответ от LM Studio!")
                response = "LM Studio вернула пустой ответ. Пожалуйста, попробуйте еще раз."
            else:
                print(f"Модель {request.model} успешно ответила (длина: {len(response)} символов)")
            
            return ChatResponse(
                content=response,
                model=request.model
            )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Ошибка отправки сообщения в LM Studio: {e}")
        raise HTTPException(status_code=500, detail=str(e))



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
    







# async def ollama_stream(prompt: str):
#     async with httpx.AsyncClient(timeout=None) as client:
#         async with client.stream("POST", "http://localhost:11434/api/chat", json={
#             "model": "llama3",  # замените на нужную модель
#             "stream": True,
#             "messages": [
#                 {"role": "user", "content": prompt}
#             ]
#         }) as response:
#             async for line in response.aiter_lines():
#                 if not line.strip():
#                     continue
#                 try:
#                     data = json.loads(line)
#                     if "message" in data and "content" in data["message"]:
#                         yield data["message"]["content"]
#                 except json.JSONDecodeError:
#                     continue

@router.post("/newchat")
async def chat_stream(request: Request):
    body = await request.json()
    prompt = body.get("prompt", "")

    return StreamingResponse(ollama_stream(prompt), media_type="text/plain")