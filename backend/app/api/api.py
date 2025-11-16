from fastapi import APIRouter
from app.api.routes import users, auth, chat, ollama, match_analysis, scenarios

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users")
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(ollama.router, prefix="/ollama")
api_router.include_router(chat.router, prefix="")
api_router.include_router(match_analysis.router, prefix="")
api_router.include_router(scenarios.router, prefix="")
