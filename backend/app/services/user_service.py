from sqlmodel import Session, select
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from datetime import datetime

class UserService:
    def __init__(self, db: Session):
        self.db = db
    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Получить список пользователей"""
        statement = select(User).offset(skip).limit(limit)
        return self.db.execute(statement).scalars().all()
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Получить пользователя по ID"""
        statement = select(User).where(User.id == user_id)
        return self.db.execute(statement).scalar_one_or_none()
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        statement = select(User).where(User.email == email)
        return self.db.execute(statement).scalar_one_or_none()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Получить пользователя по имени пользователя"""
        statement = select(User).where(User.username == username)
        return self.db.execute(statement).scalar_one_or_none()
    
    def create_user(self, user_data: UserCreate) -> User:
        """Создать нового пользователя"""
        hashed_password = User.hash_password(user_data.password)
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=user_data.full_name
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """Обновить пользователя"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
            
        user_data_dict = user_data.model_dump(exclude_unset=True)
        if 'password' in user_data_dict:
            user_data_dict['hashed_password'] = User.hash_password(user_data_dict.pop('password'))
        
        # Обновляем поля пользователя
        for field, value in user_data_dict.items():
            setattr(user, field, value)
            
        user.updated_at = datetime.utcnow()
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """Удалить пользователя"""
        user = self.get_user_by_id(user_id)
        if not user:
            return False
            
        self.db.delete(user)
        self.db.commit()
        return True
