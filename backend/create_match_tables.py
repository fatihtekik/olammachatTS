#!/usr/bin/env python3
"""
Скрипт для создания новых таблиц анализа матчей
"""
import sys
import os

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db import init_db, engine
from app.models.match import *  # Импортируем все новые модели
from sqlmodel import SQLModel
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_match_analysis_tables():
    """Создает таблицы для анализа матчей"""
    try:
        logger.info("Начинаем создание таблиц для анализа матчей...")
        
        # Создаем все таблицы
        SQLModel.metadata.create_all(bind=engine)
        
        logger.info("✅ Таблицы успешно созданы!")
        
        # Выводим список созданных таблиц
        logger.info("📋 Созданные таблицы:")
        for table_name in SQLModel.metadata.tables.keys():
            logger.info(f"  - {table_name}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        raise

if __name__ == "__main__":
    create_match_analysis_tables()
