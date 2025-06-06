from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from app.api.api import api_router
from app.database.db import init_db
from app.core.config import settings
from app.services.ollama_service import test_connection

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание экземпляра FastAPI
app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="API для чата с локальными ИИ моделями через Ollama",
    version="0.1.0",
)

# Настройка CORS для взаимодействия с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все HTTP методы
    allow_headers=["*"],  # Разрешаем все заголовки
    expose_headers=["*"]  # Разрешаем доступ ко всем заголовкам ответа
)

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Логируем запрос
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Передаем запрос дальше
    response = await call_next(request)
    
    # Логируем ответ
    process_time = time.time() - start_time
    logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
    
    return response

# Подключение роутеров API
app.include_router(api_router, prefix="/api/v1")

# Add status endpoint directly to avoid authentication requirements
@app.get("/api/v1/ollama/status", tags=["ollama"])
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
        logger.error(f"Ошибка проверки статуса Ollama: {e}")
        return {"status": "disconnected", "error": str(e)}

# Инициализация базы данных при запуске приложения
@app.on_event("startup")
def startup_db_client():
    init_db()

@app.get("/")
async def root():
    return {"message": "Welcome to Ollama Chat API!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
