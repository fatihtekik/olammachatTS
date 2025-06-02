from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import ChatSessionCreate, ChatSessionUpdate, MessageCreate
from uuid import uuid4

class ChatService:
    def __init__(self, db: Session):
        self.db = db
        
    def get_user_sessions(self, user_id: str, skip: int = 0, limit: int = 100) -> List[ChatSession]:
        """Получить список всех сессий чата пользователя"""
        statement = select(ChatSession).where(ChatSession.user_id == user_id).offset(skip).limit(limit)
        return self.db.execute(statement).scalars().all()
    
    def get_session_by_id(self, session_id: str) -> Optional[ChatSession]:
        """Получить сессию чата по ID"""
        statement = select(ChatSession).where(ChatSession.id == session_id)
        return self.db.execute(statement).scalar_one_or_none()
    
    def create_session(self, user_id: str, session_data: ChatSessionCreate) -> ChatSession:
        """Создать новую сессию чата"""
        session = ChatSession(
            id=str(uuid4()),
            title=session_data.title,
            model=session_data.model,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        # Если есть сообщения, добавляем их
        if session_data.messages:
            for message_data in session_data.messages:
                self.add_message(
                    session_id=session.id,
                    message_data=message_data
                )
        
        return session
    
    def update_session(self, session_id: str, session_data: ChatSessionUpdate) -> Optional[ChatSession]:
        """Обновить сессию чата"""
        session = self.get_session_by_id(session_id)
        if not session:
            return None
            
        session_data_dict = session_data.model_dump(exclude_unset=True)
        
        # Обновляем поля сессии
        for field, value in session_data_dict.items():
            setattr(session, field, value)
            
        session.updated_at = datetime.utcnow()
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Удалить сессию чата"""
        session = self.get_session_by_id(session_id)
        if not session:
            return False
            
        # Сначала удаляем все связанные сообщения
        statement = select(ChatMessage).where(ChatMessage.session_id == session_id)
        messages = self.db.execute(statement).scalars().all()
        for message in messages:
            self.db.delete(message)
            
        self.db.delete(session)
        self.db.commit()
        return True
    
    def get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """Получить все сообщения в сессии чата"""
        statement = select(ChatMessage).where(ChatMessage.session_id == session_id)
        return self.db.execute(statement).scalars().all()
    
    def delete_session_messages(self, session_id: str) -> bool:
        """Удалить все сообщения в сессии чата"""
        statement = select(ChatMessage).where(ChatMessage.session_id == session_id)
        messages = self.db.execute(statement).scalars().all()
        for message in messages:
            self.db.delete(message)
        self.db.commit()
        return True
        
    def add_message(self, session_id: str, message_data: MessageCreate) -> ChatMessage:
        """Добавить сообщение в сессию чата"""
        message = ChatMessage(
            id=str(uuid4()),
            session_id=session_id,
            role=message_data.role,
            content=message_data.content,
            timestamp=message_data.timestamp or datetime.utcnow(),
            error=message_data.error or False,
            attachments=message_data.attachments
        )
        self.db.add(message)
        
        # Обновляем дату обновления сессии
        session = self.get_session_by_id(session_id)
        if session:
            session.updated_at = datetime.utcnow()
            self.db.add(session)
            
        self.db.commit()
        self.db.refresh(message)
        return message
