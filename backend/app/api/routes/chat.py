from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
from pydantic import BaseModel

from app.database.db import get_db
from app.models.chat import ChatSession
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
    MessageCreate,
    MessageResponse,
    MessagesUpdate
)
from app.services.chat_service import ChatService
from app.services.auth_service import get_current_user, get_current_active_user

# Создание роутера для чат-сессий
router = APIRouter(prefix="/chat-sessions", tags=["chat"])

@router.post("/", response_model=ChatSessionResponse)
def create_chat_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Создать новую сессию чата для текущего пользователя
    """
    chat_service = ChatService(db)
    return chat_service.create_session(current_user.id, session_data)

@router.get("/", response_model=List[ChatSessionResponse])
def get_user_chat_sessions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Получить список всех сессий чата текущего пользователя
    """
    chat_service = ChatService(db)
    return chat_service.get_user_sessions(current_user.id, skip, limit)

@router.get("/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Получить конкретную сессию чата по ID
    """
    chat_service = ChatService(db)
    session = chat_service.get_session_by_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
        
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой сессии"
        )
        
    return session

@router.put("/{session_id}", response_model=ChatSessionResponse)
def update_chat_session(
    session_id: str,
    session_data: ChatSessionUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Обновить сессию чата
    """
    chat_service = ChatService(db)
    
    session = chat_service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
        
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой сессии"
        )
    
    updated_session = chat_service.update_session(session_id, session_data)
    return updated_session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Удалить сессию чата
    """
    chat_service = ChatService(db)
    
    session = chat_service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
        
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой сессии"
        )
    
    chat_service.delete_session(session_id)
    return None

@router.post("/{session_id}/messages", response_model=MessageResponse)
def add_message_to_session(
    session_id: str,
    message_data: MessageCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Добавить новое сообщение в сессию чата
    """
    chat_service = ChatService(db)
    
    # Проверка существования и принадлежности
    session = chat_service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
        
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой сессии"
        )
    
    return chat_service.add_message(session_id, message_data)

@router.get("/{session_id}/messages", response_model=List[MessageResponse])
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Получить все сообщения в сессии чата
    """
    chat_service = ChatService(db)
    
    # Проверка существования и принадлежности
    session = chat_service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
        
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой сессии"
        )
    
    return chat_service.get_session_messages(session_id)

@router.put("/{session_id}/messages", response_model=ChatSessionResponse)
def update_session_messages(
    session_id: str,
    messages_data: MessagesUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """
    Обновить все сообщения в сессии чата
    """
    chat_service = ChatService(db)
    
    # Проверка существования и принадлежности
    session = chat_service.get_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена"
        )
        
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет доступа к этой сессии"
        )
    
    # Удаляем все существующие сообщения
    chat_service.delete_session_messages(session_id)
      # Добавляем новые сообщения
    for message_data in messages_data.messages:
        chat_service.add_message(session_id, message_data)
    
    return chat_service.get_session_by_id(session_id)
