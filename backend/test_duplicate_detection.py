#!/usr/bin/env python3
"""
Тест для проверки логики определения дубликатов матчей
"""
import sys
import os
from datetime import date, time

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db import get_db
from app.models.match import Player, Match, PlayerStats
from app.services.match_analysis_service import MatchAnalysisService
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def cleanup_test_data(db):
    """Очистка тестовых данных"""
    # Удаляем тестовые матчи
    db.query(Match).filter(Match.stage == "TEST_DUPLICATE_CHECK").delete()
    # Удаляем тестовых игроков
    test_players = ["Test Player 1", "Test Player 2", "Test Player  1", " Test Player 1"]
    db.query(PlayerStats).filter(
        PlayerStats.player_id.in_(
            db.query(Player.id).filter(Player.full_name.in_(test_players))
        )
    ).delete(synchronize_session=False)
    db.query(Player).filter(Player.full_name.in_(test_players)).delete()
    db.commit()

def test_duplicate_detection():
    """Тестирует логику определения дубликатов"""
    db = next(get_db())
    
    try:
        logger.info("=" * 80)
        logger.info("🧪 ТЕСТ: Проверка логики определения дубликатов")
        logger.info("=" * 80)
        
        # Очищаем старые тестовые данные
        cleanup_test_data(db)
        
        service = MatchAnalysisService(db)
        
        # Создаем тестовых игроков
        logger.info("\n📝 Создаем тестовых игроков...")
        player1 = Player(full_name="Test Player 1", current_rating=1200)
        player2 = Player(full_name="Test Player 2", current_rating=1150)
        db.add(player1)
        db.add(player2)
        db.commit()
        db.refresh(player1)
        db.refresh(player2)
        logger.info(f"✅ Создан игрок: {player1.full_name} (ID: {player1.id})")
        logger.info(f"✅ Создан игрок: {player2.full_name} (ID: {player2.id})")
        
        test_date = date(2024, 12, 15)
        test_time = time(18, 0)
        
        # ТЕСТ 1: Создаем первый матч
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 1: Создание первого матча")
        logger.info("=" * 80)
        match1 = Match(
            date=test_date,
            time=test_time,
            player1_id=player1.id,
            player2_id=player2.id,
            score="3:1",
            sets_player1=3,
            sets_player2=1,
            stage="TEST_DUPLICATE_CHECK"
        )
        db.add(match1)
        db.commit()
        logger.info(f"✅ Создан матч 1: {player1.full_name} vs {player2.full_name}, счёт 3:1, время {test_time}")
        
        # ТЕСТ 2: Проверяем, что точная копия определяется как дубликат
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 2: Точная копия (должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="3:1",
            time_str="18:00"
        )
        logger.info(f"Результат: {'✅ ДУБЛИКАТ НАЙДЕН' if is_duplicate else '❌ ДУБЛИКАТ НЕ НАЙДЕН'}")
        assert is_duplicate, "Точная копия должна определяться как дубликат"
        
        # ТЕСТ 3: Разные форматы счёта (3:1 vs 3-1)
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 3: Разные форматы счёта (3-1 вместо 3:1, должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="3-1",
            time_str="18:00"
        )
        logger.info(f"Результат: {'✅ ДУБЛИКАТ НАЙДЕН' if is_duplicate else '❌ ДУБЛИКАТ НЕ НАЙДЕН'}")
        assert is_duplicate, "Разные форматы счёта должны нормализоваться"
        
        # ТЕСТ 4: Счёт с пробелами
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 4: Счёт с пробелами (3 : 1, должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="3 : 1",
            time_str="18:00"
        )
        logger.info(f"Результат: {'✅ ДУБЛИКАТ НАЙДЕН' if is_duplicate else '❌ ДУБЛИКАТ НЕ НАЙДЕН'}")
        assert is_duplicate, "Счёт с пробелами должен нормализоваться"
        
        # ТЕСТ 5: Счёт с деталями в скобках
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 5: Счёт с деталями в скобках (3:1 (11-9, 11-7, 9-11, 11-5), должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="3:1 (11-9, 11-7, 9-11, 11-5)",
            time_str="18:00"
        )
        logger.info(f"Результат: {'✅ ДУБЛИКАТ НАЙДЕН' if is_duplicate else '❌ ДУБЛИКАТ НЕ НАЙДЕН'}")
        assert is_duplicate, "Счёт с деталями в скобках должен игнорировать детали"
        
        # ТЕСТ 6: Другое время (должен быть дубликат, т.к. счёт и дата совпадают)
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 6: Другое время (19:00 вместо 18:00, НЕ должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="3:1",
            time_str="19:00"
        )
        logger.info(f"Результат: {'✅ НЕ ДУБЛИКАТ' if not is_duplicate else '❌ ОШИБОЧНО ОПРЕДЕЛЁН КАК ДУБЛИКАТ'}")
        assert not is_duplicate, "Разное время должно означать разные матчи"
        
        # ТЕСТ 7: Без времени в новом матче (должен проверять только счёт)
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 7: Новый матч без времени, но с тем же счётом (должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="3:1",
            time_str=None
        )
        logger.info(f"Результат: {'✅ ДУБЛИКАТ НАЙДЕН' if is_duplicate else '❌ ДУБЛИКАТ НЕ НАЙДЕН'}")
        assert is_duplicate, "Без времени должен проверяться только счёт"
        
        # ТЕСТ 8: Создаём матч без времени
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 8: Создаём второй матч без времени с другим счётом")
        logger.info("=" * 80)
        match2 = Match(
            date=test_date,
            time=None,
            player1_id=player1.id,
            player2_id=player2.id,
            score="2:3",
            sets_player1=2,
            sets_player2=3,
            stage="TEST_DUPLICATE_CHECK"
        )
        db.add(match2)
        db.commit()
        logger.info(f"✅ Создан матч 2: {player1.full_name} vs {player2.full_name}, счёт 2:3, время None")
        
        # ТЕСТ 9: Проверяем, что другой счёт без времени НЕ дубликат
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 9: Проверка матча с другим счётом без времени (НЕ должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="0:3",
            time_str=None
        )
        logger.info(f"Результат: {'✅ НЕ ДУБЛИКАТ' if not is_duplicate else '❌ ОШИБОЧНО ОПРЕДЕЛЁН КАК ДУБЛИКАТ'}")
        assert not is_duplicate, "Разный счёт должен означать разные матчи, даже без времени"
        
        # ТЕСТ 10: Проверяем, что тот же счёт без времени - дубликат
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 10: Проверка матча с тем же счётом без времени (должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player1.id,
            player2_id=player2.id,
            score="2:3",
            time_str=None
        )
        logger.info(f"Результат: {'✅ ДУБЛИКАТ НАЙДЕН' if is_duplicate else '❌ ДУБЛИКАТ НЕ НАЙДЕН'}")
        assert is_duplicate, "Тот же счёт без времени должен быть дубликатом"
        
        # ТЕСТ 11: Обратный порядок игроков
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 11: Обратный порядок игроков (должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=test_date,
            player1_id=player2.id,  # Поменяли местами
            player2_id=player1.id,
            score="3:1",
            time_str="18:00"
        )
        logger.info(f"Результат: {'✅ ДУБЛИКАТ НАЙДЕН' if is_duplicate else '❌ ДУБЛИКАТ НЕ НАЙДЕН'}")
        assert is_duplicate, "Обратный порядок игроков должен определяться как дубликат"
        
        # ТЕСТ 12: Другая дата (НЕ должен быть дубликат)
        logger.info("\n" + "=" * 80)
        logger.info("ТЕСТ 12: Другая дата (НЕ должен быть дубликат)")
        logger.info("=" * 80)
        is_duplicate = service._match_exists(
            date=date(2024, 12, 16),
            player1_id=player1.id,
            player2_id=player2.id,
            score="3:1",
            time_str="18:00"
        )
        logger.info(f"Результат: {'✅ НЕ ДУБЛИКАТ' if not is_duplicate else '❌ ОШИБОЧНО ОПРЕДЕЛЁН КАК ДУБЛИКАТ'}")
        assert not is_duplicate, "Другая дата должна означать другой матч"
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        logger.info("=" * 80)
        
        # Очищаем тестовые данные
        cleanup_test_data(db)
        logger.info("\n🧹 Тестовые данные очищены")
        
        return True
        
    except AssertionError as e:
        logger.error(f"\n❌ ТЕСТ ПРОВАЛЕН: {e}")
        cleanup_test_data(db)
        return False
    except Exception as e:
        logger.error(f"\n💥 ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        cleanup_test_data(db)
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_duplicate_detection()
    sys.exit(0 if success else 1)
