from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.database.db import init_db
from app.core.config import settings

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
)

# Подключение роутеров API
app.include_router(api_router, prefix="/api/v1")

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
