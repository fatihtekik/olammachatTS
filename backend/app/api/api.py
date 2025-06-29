from fastapi import APIRouter
from app.api.routes import users, auth, chat, ollama

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users")
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(ollama.router, prefix="/ollama")
api_router.include_router(chat.router, prefix="")
api_router.include_router(ollama.router, prefix="")
