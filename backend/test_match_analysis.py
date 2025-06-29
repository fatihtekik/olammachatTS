#!/usr/bin/env python3
"""
Скрипт для тестирования системы анализа матчей
"""
import sys
import os
from datetime import date, time, datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.db import get_db
from app.models.match import Player, Match, League, PlayerStats
from app.services.match_analysis_service import MatchAnalysisService
from app.schemas.match_analysis import AnalysisRequest
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data():
    """Создает тестовые данные для проверки системы"""
    db = next(get_db())
    
    try:
        logger.info("🏗️  Создаем тестовые данные...")
        
        # Создаем тестовых игроков
        players_data = [
            ("Иванов Иван", 1200),
            ("Петров Петр", 1150),
            ("Сидоров Сидор", 1100),
            ("Козлов Андрей", 1050),
            ("Смирнов Олег", 1000),
        ]
        
        players = []
        for name, rating in players_data:
            existing_player = db.query(Player).filter(Player.full_name == name).first()
            if not existing_player:
                player = Player(full_name=name, current_rating=rating)
                db.add(player)
                db.flush()
                
                # Создаем статистику для игрока
                stats = PlayerStats(player_id=player.id)
                db.add(stats)
                
                players.append(player)
                logger.info(f"✅ Создан игрок: {name}")
            else:
                players.append(existing_player)
                logger.info(f"⏭️  Игрок уже существует: {name}")
        
        # Создаем тестовую лигу
        league_name = "Тестовая лига"
        existing_league = db.query(League).filter(League.name == league_name).first()
        if not existing_league:
            league = League(name=league_name, level=1)
            db.add(league)
            db.flush()
            logger.info(f"✅ Создана лига: {league_name}")
        else:
            league = existing_league
            logger.info(f"⏭️  Лига уже существует: {league_name}")
        
        # Создаем тестовые матчи
        matches_data = [
            (players[0], players[1], "3:1", players[0], date(2024, 12, 1)),
            (players[1], players[2], "2:3", players[2], date(2024, 12, 2)),
            (players[0], players[2], "3:0", players[0], date(2024, 12, 3)),
            (players[3], players[4], "1:3", players[4], date(2024, 12, 4)),
            (players[0], players[3], "3:2", players[0], date(2024, 12, 5)),
            (players[1], players[4], "0:3", players[4], date(2024, 12, 6)),
            (players[2], players[3], "3:1", players[2], date(2024, 12, 7)),
            (players[0], players[4], "2:3", players[4], date(2024, 12, 8)),
            (players[1], players[3], "1:3", players[3], date(2024, 12, 9)),
            (players[2], players[4], "3:0", players[2], date(2024, 12, 10)),
        ]
        
        for player1, player2, score, winner, match_date in matches_data:
            existing_match = db.query(Match).filter(
                Match.player1_id == player1.id,
                Match.player2_id == player2.id,
                Match.date == match_date
            ).first()
            
            if not existing_match:
                sets = score.split(":")
                match = Match(
                    date=match_date,
                    time=time(18, 0),  # 18:00
                    player1_id=player1.id,
                    player2_id=player2.id,
                    winner_id=winner.id,
                    score=score,
                    sets_player1=int(sets[0]),
                    sets_player2=int(sets[1]),
                    league_id=league.id,
                    stage="Групповой этап"
                )
                db.add(match)
                logger.info(f"✅ Создан матч: {player1.full_name} vs {player2.full_name} ({score})")
        
        db.commit()
        logger.info("🎉 Тестовые данные созданы успешно!")
        
        return len(players)
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании тестовых данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()

async def test_analysis():
    """Тестирует анализ триггеров"""
    db = next(get_db())
    
    try:
        logger.info("🔍 Запускаем тестовый анализ...")
        
        service = MatchAnalysisService(db)
        
        # Обновляем статистику
        logger.info("📊 Обновляем статистику игроков...")
        stats_result = await service.update_player_statistics()
        logger.info(f"✅ Обновлена статистика для {stats_result.get('updated_players', 0)} игроков")
        
        # Запускаем анализ
        logger.info("🎯 Запускаем анализ триггеров...")
        analysis_request = AnalysisRequest(
            trigger_types=["top_performers", "losers_50_percent", "losing_streaks"]
        )
        
        analysis_result = await service.analyze_triggers(analysis_request)
        
        logger.info(f"📈 Результаты анализа:")
        logger.info(f"   - Период: {analysis_result.period_start} - {analysis_result.period_end}")
        logger.info(f"   - Игроков проанализировано: {analysis_result.total_players}")
        logger.info(f"   - Матчей обработано: {analysis_result.total_matches}")
        logger.info(f"   - Триггеров найдено: {analysis_result.triggers_found}")
        
        if analysis_result.triggers:
            logger.info("🚨 Найденные триггеры:")
            for trigger in analysis_result.triggers:
                logger.info(f"   - {trigger.trigger_type}: {trigger.trigger_value}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка при тестировании анализа: {e}")
        return False
    finally:
        db.close()

async def main():
    """Основная функция"""
    logger.info("🚀 Начинаем тестирование системы анализа матчей")
    
    # Создаем тестовые данные
    players_count = create_test_data()
    
    # Тестируем анализ
    analysis_success = await test_analysis()
    
    if analysis_success:
        logger.info("✅ Тестирование завершено успешно!")
        logger.info("💡 Теперь вы можете:")
        logger.info("   1. Запустить сервер: python main.py")
        logger.info("   2. Открыть http://localhost:8000/match-analysis")
        logger.info("   3. Протестировать загрузку Excel файлов")
    else:
        logger.error("❌ Тестирование завершилось с ошибками")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
