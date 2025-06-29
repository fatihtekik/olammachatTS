#!/usr/bin/env python3
"""
Скрипт для добавления российских праздников в базу данных
"""
import sys
import os
from datetime import date

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db import get_db
from app.models.match import Holiday
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_russian_holidays():
    """Добавляет основные российские праздники"""
    
    # Получаем сессию БД
    db = next(get_db())
    
    holidays_2024 = [
        # Новогодние каникулы
        Holiday(name="Новогодние каникулы", start_date=date(2024, 1, 1), end_date=date(2024, 1, 8)),
        # Защитника Отечества
        Holiday(name="День защитника Отечества", start_date=date(2024, 2, 23), end_date=date(2024, 2, 23)),
        # Международный женский день
        Holiday(name="Международный женский день", start_date=date(2024, 3, 8), end_date=date(2024, 3, 8)),
        # Праздник Весны и Труда (с переносами)
        Holiday(name="Праздник Весны и Труда", start_date=date(2024, 4, 29), end_date=date(2024, 5, 1)),
        # День Победы (с переносами)
        Holiday(name="День Победы", start_date=date(2024, 5, 9), end_date=date(2024, 5, 10)),
        # День России
        Holiday(name="День России", start_date=date(2024, 6, 12), end_date=date(2024, 6, 12)),
        # День народного единства
        Holiday(name="День народного единства", start_date=date(2024, 11, 4), end_date=date(2024, 11, 4)),
    ]
    
    holidays_2025 = [
        # Новогодние каникулы
        Holiday(name="Новогодние каникулы", start_date=date(2025, 1, 1), end_date=date(2025, 1, 8)),
        # Защитника Отечества
        Holiday(name="День защитника Отечества", start_date=date(2025, 2, 23), end_date=date(2025, 2, 24)),
        # Международный женский день
        Holiday(name="Международный женский день", start_date=date(2025, 3, 8), end_date=date(2025, 3, 10)),
        # Праздник Весны и Труда
        Holiday(name="Праздник Весны и Труда", start_date=date(2025, 5, 1), end_date=date(2025, 5, 2)),
        # День Победы
        Holiday(name="День Победы", start_date=date(2025, 5, 9), end_date=date(2025, 5, 9)),
        # День России
        Holiday(name="День России", start_date=date(2025, 6, 12), end_date=date(2025, 6, 13)),
        # День народного единства
        Holiday(name="День народного единства", start_date=date(2025, 11, 4), end_date=date(2025, 11, 4)),
    ]
    
    try:
        logger.info("Добавляем праздники в базу данных...")
        
        all_holidays = holidays_2024 + holidays_2025
        
        for holiday in all_holidays:
            # Проверяем, нет ли уже такого праздника
            existing = db.query(Holiday).filter(
                Holiday.name == holiday.name,
                Holiday.start_date == holiday.start_date
            ).first()
            
            if not existing:
                db.add(holiday)
                logger.info(f"✅ Добавлен праздник: {holiday.name} ({holiday.start_date} - {holiday.end_date})")
            else:
                logger.info(f"⏭️  Праздник уже существует: {holiday.name}")
        
        db.commit()
        logger.info("🎉 Все праздники успешно добавлены!")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении праздников: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_russian_holidays()
