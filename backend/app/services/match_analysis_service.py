from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import re
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from app.models.match import (
    Player, PlayerStats, Match, League, MatchSet, 
    PlayerTrigger, PlayerPeriodStats, Holiday
)
from app.schemas.match_analysis import (
    ExcelMatchData, AnalysisRequest, AnalysisResponse,
    PlayerCreate, MatchCreate
)
import logging

logger = logging.getLogger(__name__)

class MatchAnalysisService:
    """Сервис для анализа матчей и выявления триггеров"""
    
    def __init__(self, db: Session):
        self.db = db
        self.trigger_methods = {
            "top_performers": self._analyze_top_performers,
            "losers_50_percent": self._analyze_losers_50_percent,
            "endgame_problems": self._analyze_endgame_problems,
            "lead_4_lost": self._analyze_lead_4_lost,
            "balance_problems": self._analyze_balance_problems,
            "led_2_sets_lost": self._analyze_led_2_sets_lost,
            "led_1_set_lost": self._analyze_led_1_set_lost,
            "early_final_exit": self._analyze_early_final_exit,
            "league_promotion_failed": self._analyze_league_promotion_failed,
            "won_2_lost_3rd": self._analyze_won_2_lost_3rd,
            "close_score_losses": self._analyze_close_score_losses,
            "post_holiday_problems": self._analyze_post_holiday_problems,
            "time_performance": self._analyze_time_performance,
            "shutout_losses": self._analyze_shutout_losses,
            "losing_streaks": self._analyze_losing_streaks,
            "weaker_opponent_losses": self._analyze_weaker_opponent_losses,
            "long_match_losses": self._analyze_long_match_losses,
            "higher_league_struggles": self._analyze_higher_league_struggles,
            "reception_problems": self._analyze_reception_problems
        }
    
    async def process_excel_data(self, excel_data: List[ExcelMatchData]) -> Dict[str, Any]:
        """Обрабатывает данные из Excel файла"""
        try:
            created_players = 0
            created_matches = 0
            errors = []
            
            for match_data in excel_data:
                try:
                    # Получаем или создаем игроков
                    player1 = await self._get_or_create_player(match_data.игрок_1)
                    player2 = await self._get_or_create_player(match_data.игрок_2)
                    
                    if player1.id == player2.id:
                        continue  # Пропускаем если это один игрок
                    
                    # Создаем матч
                    match = await self._create_match_from_excel(match_data, player1, player2)
                    created_matches += 1
                    
                except Exception as e:
                    error_msg = f"Ошибка при обработке матча {match_data.игрок_1} vs {match_data.игрок_2}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return {
                "created_players": created_players,
                "created_matches": created_matches,
                "errors": errors,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обработке Excel данных: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_or_create_player(self, player_name: str) -> Player:
        """Получает существующего игрока или создает нового"""
        player = self.db.query(Player).filter(Player.full_name == player_name).first()
        
        if not player:
            player = Player(full_name=player_name)
            self.db.add(player)
            self.db.commit()
            self.db.refresh(player)
            
            # Создаем начальную статистику
            stats = PlayerStats(player_id=player.id)
            self.db.add(stats)
            self.db.commit()
        
        return player
    
    async def _create_match_from_excel(self, data: ExcelMatchData, player1: Player, player2: Player) -> Match:
        """Создает матч из данных Excel"""
        # Парсим дату - поддерживаем разные форматы
        match_date = self._parse_date(data.дата)
        
        # Определяем победителя по счету
        sets_player1, sets_player2 = self._parse_score(data.счёт)
        
        winner_id = player1.id if sets_player1 > sets_player2 else player2.id
        
        # Получаем или создаем лигу
        league = None
        if data.турнир:
            league = await self._get_or_create_league(data.турнир)
        
        match = Match(
            date=match_date,
            player1_id=player1.id,
            player2_id=player2.id,
            winner_id=winner_id,
            score=data.счёт,
            sets_player1=sets_player1,
            sets_player2=sets_player2,
            stage=data.стадия,
            league_id=league.id if league else None,
            match_sl_id=int(data.sl_id) if data.sl_id else None,
            is_final=data.стадия and "финал" in data.стадия.lower(),
            is_semifinal=data.стадия and "полуфинал" in data.стадия.lower()
        )
        
        self.db.add(match)
        self.db.commit()
        self.db.refresh(match)
        
        return match
    
    async def _get_or_create_league(self, league_name: str) -> League:
        """Получает существующую лигу или создает новую"""
        league = self.db.query(League).filter(League.name == league_name).first()
        
        if not league:
            league = League(name=league_name, level=1)  # По умолчанию уровень 1
            self.db.add(league)
            self.db.commit()
            self.db.refresh(league)
        
        return league
    
    async def update_player_statistics(self, player_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Обновляет статистику игроков"""
        try:
            query = self.db.query(Player)
            if player_ids:
                query = query.filter(Player.id.in_(player_ids))
            
            players = query.all()
            updated_count = 0
            
            for player in players:
                await self._calculate_player_stats(player)
                updated_count += 1
            
            return {
                "success": True,
                "updated_players": updated_count
            }
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _calculate_player_stats(self, player: Player):
        """Вычисляет статистику для конкретного игрока"""
        # Получаем все матчи игрока
        matches = self.db.query(Match).filter(
            or_(Match.player1_id == player.id, Match.player2_id == player.id)
        ).all()
        
        stats = {
            "matches_played": len(matches),
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "sets_won": 0,
            "sets_lost": 0,
            "points_won": 0,
            "points_lost": 0
        }
        
        for match in matches:
            if match.winner_id == player.id:
                stats["wins"] += 1
            elif match.winner_id:
                stats["losses"] += 1
            else:
                stats["draws"] += 1
            
            # Подсчет сетов
            if match.player1_id == player.id:
                stats["sets_won"] += match.sets_player1 or 0
                stats["sets_lost"] += match.sets_player2 or 0
            else:
                stats["sets_won"] += match.sets_player2 or 0
                stats["sets_lost"] += match.sets_player1 or 0
        
        # Вычисляем процент побед
        win_percentage = (stats["wins"] / stats["matches_played"]) * 100 if stats["matches_played"] > 0 else 0
        
        # Обновляем или создаем статистику
        player_stats = self.db.query(PlayerStats).filter(PlayerStats.player_id == player.id).first()
        
        if player_stats:
            for key, value in stats.items():
                setattr(player_stats, key, value)
            player_stats.win_percentage = win_percentage
            player_stats.last_updated = datetime.utcnow()
        else:
            player_stats = PlayerStats(
                player_id=player.id,
                win_percentage=win_percentage,
                **stats
            )
            self.db.add(player_stats)
        
        self.db.commit()
    
    async def analyze_triggers(self, request: AnalysisRequest) -> AnalysisResponse:
        """Выполняет анализ триггеров для игроков"""
        logger.info("🔍 Начинаем анализ триггеров...")
        try:
            # Определяем период анализа
            end_date = request.period_end or date.today()
            start_date = request.period_start or (end_date - timedelta(days=90))  # По умолчанию 3 месяца
            
            logger.info(f"📅 Период анализа: {start_date} - {end_date}")
            
            # Очищаем старые триггеры для этого периода
            deleted_count = self.db.query(PlayerTrigger).filter(
                and_(
                    PlayerTrigger.period_start == start_date,
                    PlayerTrigger.period_end == end_date
                )
            ).delete()
            logger.info(f"🧹 Удалено старых триггеров: {deleted_count}")
            
            # Получаем игроков для анализа
            query = self.db.query(Player)
            if request.player_ids:
                query = query.filter(Player.id.in_(request.player_ids))
                logger.info(f"👥 Анализируем указанных игроков: {len(request.player_ids)}")
            
            players = query.all()
            logger.info(f"👥 Найдено игроков для анализа: {len(players)}")
            
            total_triggers = 0
            
            # Запускаем анализ по каждому типу триггера
            trigger_types = request.trigger_types or list(self.trigger_methods.keys())
            logger.info(f"🎯 Типы триггеров для анализа: {trigger_types}")
            
            for trigger_type in trigger_types:
                if trigger_type in self.trigger_methods:
                    logger.info(f"🔬 Анализируем триггер: {trigger_type}")
                    method = self.trigger_methods[trigger_type]
                    triggers = await method(players, start_date, end_date)
                    logger.info(f"✅ Найдено триггеров типа {trigger_type}: {len(triggers)}")
                    total_triggers += len(triggers)
            
            logger.info(f"📊 Сбираем данные для ответа...")
            
            # Получаем данные для ответа
            total_matches = self._count_matches_in_period(start_date, end_date)
            top_performers = await self._get_top_performers(start_date, end_date)
            problem_players = await self._get_problem_players(start_date, end_date)
            triggers = await self._get_all_triggers(start_date, end_date)
            
            logger.info(f"📈 Статистика анализа:")
            logger.info(f"  - Игроков: {len(players)}")
            logger.info(f"  - Матчей: {total_matches}")
            logger.info(f"  - Триггеров: {total_triggers}")
            logger.info(f"  - Топ игроков: {len(top_performers)}")
            logger.info(f"  - Проблемных игроков: {len(problem_players)}")
            
            # Формируем ответ
            response = AnalysisResponse(
                period_start=start_date,
                period_end=end_date,
                total_players=len(players),
                total_matches=total_matches,
                triggers_found=total_triggers,
                top_performers=top_performers,
                problem_players=problem_players,
                triggers=triggers
            )
            
            logger.info("✅ Анализ триггеров завершен успешно")
            return response
            
        except Exception as e:
            logger.error(f"💥 Ошибка при анализе триггеров: {str(e)}", exc_info=True)
            raise
    
    def _count_matches_in_period(self, start_date: date, end_date: date) -> int:
        """Подсчитывает количество матчей в периоде"""
        return self.db.query(Match).filter(
            and_(Match.date >= start_date, Match.date <= end_date)
        ).count()
    
    async def _get_top_performers(self, start_date: date, end_date: date) -> List[dict]:
        """Получает топ игроков по результативности"""
        # Получаем игроков с высоким win rate за период
        top_performers = []
        
        players = self.db.query(Player).all()
        player_stats = []
        
        for player in players:
            matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    or_(Match.player1_id == player.id, Match.player2_id == player.id)
                )
            ).all()
            
            if len(matches) >= 3:  # Минимум 3 матча для статистики
                wins = len([m for m in matches if m.winner_id == player.id])
                win_rate = (wins / len(matches)) * 100
                
                if win_rate >= 70:  # Топ игроки с win rate >= 70%
                    player_stats.append({
                        'player': player,
                        'win_rate': win_rate,
                        'matches': len(matches),
                        'wins': wins
                    })
        
        # Сортируем по win_rate и берем топ 10
        player_stats.sort(key=lambda x: x['win_rate'], reverse=True)
        
        for stat in player_stats[:10]:
            player_dict = {
                'id': stat['player'].id,
                'full_name': stat['player'].full_name,
                'current_rating': stat['player'].current_rating,
                'created_at': stat['player'].created_at,
                'updated_at': stat['player'].updated_at
            }
            top_performers.append(player_dict)
        
        return top_performers
    
    async def _get_problem_players(self, start_date: date, end_date: date) -> List[dict]:
        """Получает игроков с проблемами"""
        problem_players = []
        
        players = self.db.query(Player).all()
        
        for player in players:
            matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    or_(Match.player1_id == player.id, Match.player2_id == player.id)
                )
            ).all()
            
            if len(matches) >= 3:  # Минимум 3 матча
                losses = len([m for m in matches if m.winner_id and m.winner_id != player.id])
                loss_rate = (losses / len(matches)) * 100
                
                if loss_rate >= 60:  # Проблемные игроки с loss rate >= 60%
                    player_dict = {
                        'id': player.id,
                        'full_name': player.full_name,
                        'current_rating': player.current_rating,
                        'created_at': player.created_at,
                        'updated_at': player.updated_at
                    }
                    problem_players.append(player_dict)
        
        return problem_players[:10]  # Топ 10 проблемных игроков
    
    async def _get_all_triggers(self, start_date: date, end_date: date) -> List[dict]:
        """Получает все триггеры за период"""
        triggers = self.db.query(PlayerTrigger).filter(
            and_(
                PlayerTrigger.period_start == start_date,
                PlayerTrigger.period_end == end_date
            )
        ).all()
        
        result = []
        for trigger in triggers:
            trigger_dict = {
                'id': trigger.id,
                'player_id': trigger.player_id,
                'trigger_type': trigger.trigger_type,
                'trigger_subtype': trigger.trigger_subtype,
                'trigger_value': trigger.trigger_value,
                'severity_level': trigger.severity_level,
                'period_start': trigger.period_start,
                'period_end': trigger.period_end,
                'is_active': trigger.is_active,
                'trigger_metadata': trigger.trigger_metadata,
                'created_at': trigger.created_at
            }
            result.append(trigger_dict)
        
        return result
    
    # Методы для анализа конкретных триггеров
    async def _analyze_top_performers(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        """Анализ топ игроков по результативности"""
        triggers = []
        
        # Получаем статистику за период для всех игроков
        player_stats = []
        for player in players:
            matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    or_(Match.player1_id == player.id, Match.player2_id == player.id)
                )
            ).all()
            
            if len(matches) >= 5:  # Минимум 5 матчей для анализа
                wins = len([m for m in matches if m.winner_id == player.id])
                win_rate = (wins / len(matches)) * 100
                
                player_stats.append({
                    'player': player,
                    'matches': len(matches),
                    'wins': wins,
                    'win_rate': win_rate
                })
        
        # Сортируем по win_rate и берем топ 20%
        player_stats.sort(key=lambda x: x['win_rate'], reverse=True)
        top_count = max(1, len(player_stats) // 5)
        top_players = player_stats[:top_count]
        
        for stat in top_players:
            if stat['win_rate'] >= 70:  # Топ игроки с win rate >= 70%
                trigger = PlayerTrigger(
                    player_id=stat['player'].id,
                    trigger_type="top_performers",
                    trigger_value=f"Топ исполнитель: {stat['win_rate']:.1f}% побед ({stat['wins']}/{stat['matches']})",
                    severity_level=1,  # Позитивный триггер
                    period_start=start_date,
                    period_end=end_date,
                    is_active=True
                )
                trigger.set_metadata({
                    "win_rate": stat['win_rate'],
                    "total_matches": stat['matches'],
                    "wins": stat['wins'],
                    "rank": "top_performer"
                })
                
                self.db.add(trigger)
                triggers.append(trigger)
        
        self.db.commit()
        return triggers
    
    async def _analyze_losers_50_percent(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        """Анализ игроков, проигравших больше 50% матчей"""
        triggers = []
        
        for player in players:
            matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    or_(Match.player1_id == player.id, Match.player2_id == player.id)
                )
            ).all()
            
            if len(matches) >= 5:  # Минимум 5 матчей
                losses = len([m for m in matches if m.winner_id and m.winner_id != player.id])
                loss_rate = (losses / len(matches)) * 100
                
                if loss_rate > 50:
                    severity = 2 if loss_rate > 70 else 1
                    
                    trigger = PlayerTrigger(
                        player_id=player.id,
                        trigger_type="losers_50_percent",
                        trigger_value=f"Высокий процент поражений: {loss_rate:.1f}% ({losses}/{len(matches)})",
                        severity_level=severity,
                        period_start=start_date,
                        period_end=end_date,
                        is_active=True
                    )
                    trigger.set_metadata({
                        "loss_rate": loss_rate,
                        "total_matches": len(matches),
                        "losses": losses,
                        "concern_level": "high" if loss_rate > 70 else "medium"
                    })
                    
                    self.db.add(trigger)
                    triggers.append(trigger)
        
        self.db.commit()
        return triggers
    
    async def _analyze_losing_streaks(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        """Анализ серий поражений"""
        triggers = []
        
        for player in players:
            matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    or_(Match.player1_id == player.id, Match.player2_id == player.id)
                )
            ).order_by(Match.date.desc()).all()
            
            # Ищем текущую серию поражений
            current_streak = 0
            max_streak = 0
            temp_streak = 0
            
            for match in matches:
                if match.winner_id and match.winner_id != player.id:
                    temp_streak += 1
                    if matches.index(match) < 5:  # Последние 5 матчей
                        current_streak += 1
                else:
                    max_streak = max(max_streak, temp_streak)
                    temp_streak = 0
            
            max_streak = max(max_streak, temp_streak)
            
            # Триггер при серии из 3+ поражений подряд
            if current_streak >= 3 or max_streak >= 4:
                severity = 3 if current_streak >= 5 or max_streak >= 6 else 2
                
                trigger_value = f"Серия поражений: {current_streak} текущих"
                if max_streak > current_streak:
                    trigger_value += f", максимум {max_streak} за период"
                
                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="losing_streaks",
                    trigger_value=trigger_value,
                    severity_level=severity,
                    period_start=start_date,
                    period_end=end_date,
                    is_active=True
                )
                trigger.set_metadata({
                    "current_streak": current_streak,
                    "max_streak": max_streak,
                    "total_matches": len(matches),
                    "recommendation": "Требуется анализ техники и психологической подготовки"
                })
                
                self.db.add(trigger)
                triggers.append(trigger)
        
        self.db.commit()
        return triggers
    
    async def _analyze_post_holiday_problems(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        """Анализ проблем после праздников"""
        triggers = []
        
        # Получаем праздники в периоде
        holidays = self.db.query(Holiday).filter(
            and_(
                Holiday.start_date >= start_date - timedelta(days=30),
                Holiday.end_date <= end_date + timedelta(days=10)
            )
        ).all()
        
        for player in players:
            poor_performance_after_holidays = 0
            total_post_holiday_matches = 0
            
            for holiday in holidays:
                # Матчи в течение 7 дней после праздника
                post_holiday_start = holiday.end_date + timedelta(days=1)
                post_holiday_end = holiday.end_date + timedelta(days=7)
                
                post_holiday_matches = self.db.query(Match).filter(
                    and_(
                        Match.date >= post_holiday_start,
                        Match.date <= post_holiday_end,
                        or_(Match.player1_id == player.id, Match.player2_id == player.id)
                    )
                ).all()
                
                if post_holiday_matches:
                    total_post_holiday_matches += len(post_holiday_matches)
                    losses = len([m for m in post_holiday_matches if m.winner_id and m.winner_id != player.id])
                    
                    # Считаем плохой результат если больше 60% поражений
                    if losses / len(post_holiday_matches) > 0.6:
                        poor_performance_after_holidays += 1
            
            # Триггер если плохие результаты после 2+ праздников
            if poor_performance_after_holidays >= 2 and total_post_holiday_matches >= 4:
                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="post_holiday_problems",
                    trigger_value=f"Слабые результаты после {poor_performance_after_holidays} праздников из {len(holidays)}",
                    severity_level=2,
                    period_start=start_date,
                    period_end=end_date,
                    is_active=True
                )
                trigger.set_metadata({
                    "poor_performance_count": poor_performance_after_holidays,
                    "total_holidays": len(holidays),
                    "total_post_holiday_matches": total_post_holiday_matches,
                    "recommendation": "Рекомендуется усиленная подготовка после отпусков"
                })
                
                self.db.add(trigger)
                triggers.append(trigger)
        
        self.db.commit()
        return triggers
    
    async def _analyze_time_performance(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        """Анализ результативности по времени суток"""
        triggers = []
        
        for player in players:
            matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    Match.time.isnot(None),
                    or_(Match.player1_id == player.id, Match.player2_id == player.id)
                )
            ).all()
            
            if len(matches) >= 8:  # Минимум 8 матчей с указанным временем
                day_matches = []  # 8:00 - 17:59
                evening_matches = []  # 18:00 - 21:59
                night_matches = []  # 22:00 - 7:59
                
                for match in matches:
                    hour = match.time.hour
                    if 8 <= hour < 18:
                        day_matches.append(match)
                    elif 18 <= hour < 22:
                        evening_matches.append(match)
                    else:
                        night_matches.append(match)
                
                # Анализируем каждый период
                periods = [
                    ("day", day_matches, "дневное время"),
                    ("evening", evening_matches, "вечернее время"),
                    ("night", night_matches, "ночное время")
                ]
                
                for period_name, period_matches, period_desc in periods:
                    if len(period_matches) >= 3:
                        losses = len([m for m in period_matches if m.winner_id and m.winner_id != player.id])
                        loss_rate = (losses / len(period_matches)) * 100
                        
                        # Триггер при высоком проценте поражений в конкретное время
                        if loss_rate >= 70:
                            trigger = PlayerTrigger(
                                player_id=player.id,
                                trigger_type="time_performance",
                                trigger_subtype=period_name,
                                trigger_value=f"Слабые результаты в {period_desc}: {loss_rate:.1f}% поражений ({losses}/{len(period_matches)})",
                                severity_level=2 if loss_rate >= 80 else 1,
                                period_start=start_date,
                                period_end=end_date,
                                is_active=True
                            )
                            trigger.set_metadata({
                                "time_period": period_name,
                                "loss_rate": loss_rate,
                                "matches_in_period": len(period_matches),
                                "losses": losses,
                                "recommendation": f"Избегать матчей в {period_desc} или усилить подготовку"
                            })
                            
                            self.db.add(trigger)
                            triggers.append(trigger)
        
        self.db.commit()
        return triggers
    
    # Остальные методы анализа триггеров будут добавлены аналогично
    async def _analyze_endgame_problems(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_lead_4_lost(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_balance_problems(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_led_2_sets_lost(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_led_1_set_lost(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_early_final_exit(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_league_promotion_failed(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_won_2_lost_3rd(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_close_score_losses(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_post_holiday_problems(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_time_performance(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_shutout_losses(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_losing_streaks(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_weaker_opponent_losses(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_long_match_losses(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_higher_league_struggles(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_reception_problems(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    def _parse_date(self, date_str: str) -> date:
        """Парсит дату из различных форматов"""
        date_formats = [
            "%Y-%m-%d",      # 2025-05-04
            "%d.%m.%Y",      # 04.05.2025
            "%d/%m/%Y",      # 04/05/2025
            "%d-%m-%Y",      # 04-05-2025
            "%Y.%m.%d",      # 2025.05.04
            "%Y/%m/%d",      # 2025/05/04
        ]
        
        # Удаляем лишние пробелы
        date_str = str(date_str).strip()
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Если ни один формат не подошел, пытаемся обработать как числовой формат Excel
        try:
            # Excel может возвращать дату как число дней с 1900-01-01
            if date_str.replace('.', '').isdigit():
                excel_date = float(date_str)
                # Excel считает 1900-01-01 как день 1, но на самом деле это 1899-12-30
                base_date = datetime(1899, 12, 30)
                return (base_date + timedelta(days=excel_date)).date()
        except:
            pass
        
        raise ValueError(f"Не удалось распарсить дату: {date_str}")
    
    def _parse_score(self, score_str: str) -> tuple[int, int]:
        """Парсит счёт матча из различных форматов"""
        # Убираем лишние пробелы
        score_str = str(score_str).strip()
        
        # Ищем основной счёт в формате "X-Y" или "X:Y" в начале строки
        # Игнорируем всё что в скобках
        main_score_match = re.match(r'^(\d+)[-:](\d+)', score_str)
        if main_score_match:
            sets_player1 = int(main_score_match.group(1))
            sets_player2 = int(main_score_match.group(2))
            return sets_player1, sets_player2
        
        # Если не найден основной счёт, пытаемся разделить по ":" или "-"
        for separator in [':', '-']:
            if separator in score_str:
                parts = score_str.split(separator, 1)
                if len(parts) == 2:
                    try:
                        sets_player1 = int(parts[0].strip())
                        # Берём только цифры из второй части до первого пробела или скобки
                        second_part = parts[1].strip().split()[0].split('(')[0]
                        sets_player2 = int(second_part)
                        return sets_player1, sets_player2
                    except ValueError:
                        continue
        
        raise ValueError(f"Не удалось распарсить счёт: {score_str}")
