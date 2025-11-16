"""
Сервис для анализа матчей игроков по сценариям
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.models.match import (
    Match, MatchSet, Player, ScenarioStats, MatchScenario
)


class ScenarioAnalysisService:
    """Сервис для анализа сценариев поведения игроков"""
    
    # Определения сценариев
    SCENARIOS = {
        "S1": "Выиграл 1-й сет → проиграл матч 1-3",
        "S2": "Выиграл первые 2 сета → проиграл 2-3",
        "S3": "Матч был 1-1 по сетам",
        "S4": "Вёл по сетам 2-0",
        "S5": "Fight Score в проигранных сетах ≥ 0.3",
        "S6": "Fight Score < 0.3"
    }
    
    @staticmethod
    def calculate_fight_score_for_match(match: Match, player_id: str, sets: List[MatchSet]) -> Optional[float]:
        """
        Рассчитывает Fight Score для конкретного матча
        
        Fight Score = средний показатель (очки игрока / очки соперника) по проигранным сетам
        """
        if not sets:
            return None
            
        lost_sets_scores = []
        
        for set_data in sets:
            # Определяем, проиграл ли игрок этот сет
            is_player1 = match.player1_id == player_id
            
            if is_player1:
                player_points = set_data.player1_points
                opponent_points = set_data.player2_points
                lost_set = set_data.winner_id != player_id
            else:
                player_points = set_data.player2_points
                opponent_points = set_data.player1_points
                lost_set = set_data.winner_id != player_id
            
            # Если игрок проиграл сет
            if lost_set and opponent_points > 0:
                fight_score_set = player_points / opponent_points
                lost_sets_scores.append(fight_score_set)
        
        # Возвращаем средний Fight Score
        if lost_sets_scores:
            return sum(lost_sets_scores) / len(lost_sets_scores)
        
        return None
    
    @staticmethod
    def classify_match_scenarios(
        match: Match, 
        player_id: str, 
        sets: List[MatchSet]
    ) -> List[Tuple[str, Optional[float], bool]]:
        """
        Классифицирует матч по сценариям для конкретного игрока
        
        Возвращает: List[(scenario_code, fight_score, is_win)]
        """
        if not sets or len(sets) < 3:
            return []
        
        scenarios = []
        is_player1 = match.player1_id == player_id
        is_winner = match.winner_id == player_id
        
        # Сортируем сеты по номеру
        sorted_sets = sorted(sets, key=lambda s: s.set_number)
        
        # Подсчитываем счёт по сетам
        sets_won = 0
        sets_lost = 0
        
        for set_data in sorted_sets:
            if set_data.winner_id == player_id:
                sets_won += 1
            else:
                sets_lost += 1
        
        # Определяем победителей первых сетов
        first_set_winner = sorted_sets[0].winner_id if len(sorted_sets) > 0 else None
        second_set_winner = sorted_sets[1].winner_id if len(sorted_sets) > 1 else None
        
        # Рассчитываем Fight Score
        fight_score = ScenarioAnalysisService.calculate_fight_score_for_match(
            match, player_id, sorted_sets
        )
        
        # S1: Выиграл 1-й сет → проиграл матч 1-3
        if (first_set_winner == player_id and 
            not is_winner and 
            sets_won == 1 and sets_lost == 3):
            scenarios.append(("S1", fight_score, False))
        
        # S2: Выиграл первые 2 сета → проиграл 2-3
        if (first_set_winner == player_id and 
            second_set_winner == player_id and
            not is_winner and 
            sets_won == 2 and sets_lost == 3):
            scenarios.append(("S2", fight_score, False))
        
        # S3: Матч был 1-1 по сетам (анализируем, если было хотя бы 3 сета)
        if len(sorted_sets) >= 3:
            # Проверяем, был ли счёт 1-1 после второго сета
            first_two_sets_won = sum(1 for s in sorted_sets[:2] if s.winner_id == player_id)
            if first_two_sets_won == 1:
                scenarios.append(("S3", fight_score, is_winner))
        
        # S4: Вёл по сетам 2-0
        if (first_set_winner == player_id and 
            second_set_winner == player_id):
            scenarios.append(("S4", fight_score, is_winner))
        
        # S5 и S6: Анализ по Fight Score
        if fight_score is not None:
            if fight_score >= 0.3:
                scenarios.append(("S5", fight_score, is_winner))
            else:
                scenarios.append(("S6", fight_score, is_winner))
        
        return scenarios
    
    @staticmethod
    def get_behavior_label(scenario_code: str, fight_score: Optional[float], win_rate: float) -> str:
        """
        Возвращает текстовую метку поведения игрока
        """
        if scenario_code == "S1" and fight_score and fight_score < 0.3:
            return "Теряет уверенность после лидерства"
        
        if scenario_code == "S2" and fight_score and fight_score >= 0.3:
            return "Не может закрыть матч, но продолжает борьбу"
        
        if scenario_code == "S2" and win_rate < 40:
            return "Проблемы с закрытием матчей"
        
        if scenario_code == "S3" and win_rate < 50:
            return "Слабая игра в равных решающих ситуациях"
        
        if scenario_code == "S4" and win_rate < 60:
            return "Не держит преимущество"
        
        if fight_score is not None:
            if fight_score < 0.3:
                return "Сыпется под давлением"
            elif fight_score < 0.5:
                return "Борется, но уступает"
            elif fight_score >= 0.5:
                return "Равный бой"
        
        return "Стандартная игра"
    
    @staticmethod
    def get_fight_score_interpretation(fight_score: Optional[float]) -> str:
        """
        Возвращает интерпретацию Fight Score
        """
        if fight_score is None:
            return "Нет данных"
        
        if fight_score >= 0.70:
            return "Доминирует даже в проигранных сетах"
        elif fight_score >= 0.50:
            return "Равная борьба"
        elif fight_score >= 0.30:
            return "Борется, но уступает"
        else:
            return "Психологически «сыпется»"
    
    @staticmethod
    def analyze_player_matches(db: Session, player_id: str) -> Dict[str, any]:
        """
        Анализирует все матчи игрока и обновляет статистику по сценариям
        """
        # Получаем все матчи игрока
        matches = db.execute(
            select(Match).where(
                (Match.player1_id == player_id) | (Match.player2_id == player_id)
            )
        ).scalars().all()
        
        # Словарь для агрегации статистики
        scenario_data = {}
        
        # Удаляем старые записи MatchScenario для этого игрока
        db.execute(
            select(MatchScenario).where(MatchScenario.player_id == player_id)
        )
        db.query(MatchScenario).filter(MatchScenario.player_id == player_id).delete()
        
        # Анализируем каждый матч
        for match in matches:
            # Получаем сеты матча
            sets = db.execute(
                select(MatchSet).where(MatchSet.match_id == match.id).order_by(MatchSet.set_number)
            ).scalars().all()
            
            # Классифицируем матч по сценариям
            scenarios = ScenarioAnalysisService.classify_match_scenarios(
                match, player_id, list(sets)
            )
            
            # Сохраняем связи матч-сценарий
            for scenario_code, fight_score, is_win in scenarios:
                # Создаём запись MatchScenario
                match_scenario = MatchScenario(
                    match_id=match.id,
                    player_id=player_id,
                    scenario_code=scenario_code,
                    fight_score=fight_score,
                    is_win=is_win
                )
                db.add(match_scenario)
                
                # Агрегируем статистику
                if scenario_code not in scenario_data:
                    scenario_data[scenario_code] = {
                        "matches": 0,
                        "wins": 0,
                        "losses": 0,
                        "fight_scores": []
                    }
                
                scenario_data[scenario_code]["matches"] += 1
                if is_win:
                    scenario_data[scenario_code]["wins"] += 1
                else:
                    scenario_data[scenario_code]["losses"] += 1
                
                if fight_score is not None:
                    scenario_data[scenario_code]["fight_scores"].append(fight_score)
        
        # Удаляем старые ScenarioStats для игрока
        db.query(ScenarioStats).filter(ScenarioStats.player_id == player_id).delete()
        
        # Создаём новые записи ScenarioStats
        for scenario_code, data in scenario_data.items():
            avg_fight_score = None
            if data["fight_scores"]:
                avg_fight_score = sum(data["fight_scores"]) / len(data["fight_scores"])
            
            scenario_stat = ScenarioStats(
                player_id=player_id,
                scenario_code=scenario_code,
                matches_total=data["matches"],
                wins=data["wins"],
                losses=data["losses"],
                fight_score=avg_fight_score,
                updated_at=datetime.utcnow()
            )
            db.add(scenario_stat)
        
        db.commit()
        
        return {
            "player_id": player_id,
            "scenarios_analyzed": len(scenario_data),
            "total_matches": len(matches)
        }
    
    @staticmethod
    def get_player_scenarios(db: Session, player_id: str) -> List[Dict]:
        """
        Получает статистику по сценариям для игрока
        """
        scenarios = db.execute(
            select(ScenarioStats).where(ScenarioStats.player_id == player_id)
        ).scalars().all()
        
        result = []
        for scenario in scenarios:
            win_rate = (scenario.wins / scenario.matches_total * 100) if scenario.matches_total > 0 else 0
            
            result.append({
                "scenario_code": scenario.scenario_code,
                "scenario_name": ScenarioAnalysisService.SCENARIOS.get(scenario.scenario_code, "Unknown"),
                "matches_total": scenario.matches_total,
                "wins": scenario.wins,
                "losses": scenario.losses,
                "win_rate": round(win_rate, 1),
                "fight_score": round(scenario.fight_score, 3) if scenario.fight_score else None,
                "fight_score_interpretation": ScenarioAnalysisService.get_fight_score_interpretation(scenario.fight_score),
                "behavior_label": ScenarioAnalysisService.get_behavior_label(
                    scenario.scenario_code, 
                    scenario.fight_score, 
                    win_rate
                ),
                "updated_at": scenario.updated_at.isoformat() if scenario.updated_at else None
            })
        
        return result
    
    @staticmethod
    def get_scenario_matches(db: Session, player_id: str, scenario_code: str) -> List[Dict]:
        """
        Получает детальный список матчей для конкретного сценария
        """
        match_scenarios = db.execute(
            select(MatchScenario).where(
                and_(
                    MatchScenario.player_id == player_id,
                    MatchScenario.scenario_code == scenario_code
                )
            )
        ).scalars().all()
        
        result = []
        for ms in match_scenarios:
            # Получаем матч
            match = db.execute(
                select(Match).where(Match.id == ms.match_id)
            ).scalar_one_or_none()
            
            if not match:
                continue
            
            # Получаем игроков
            player1 = db.execute(select(Player).where(Player.id == match.player1_id)).scalar_one_or_none()
            player2 = db.execute(select(Player).where(Player.id == match.player2_id)).scalar_one_or_none()
            
            # Получаем сеты
            sets = db.execute(
                select(MatchSet).where(MatchSet.match_id == match.id).order_by(MatchSet.set_number)
            ).scalars().all()
            
            sets_detail = []
            for set_data in sets:
                sets_detail.append({
                    "set_number": set_data.set_number,
                    "player1_points": set_data.player1_points,
                    "player2_points": set_data.player2_points,
                    "winner_id": set_data.winner_id
                })
            
            result.append({
                "match_id": match.id,
                "date": match.date.isoformat() if match.date else None,
                "player1_name": player1.full_name if player1 else "Unknown",
                "player2_name": player2.full_name if player2 else "Unknown",
                "score": match.score,
                "winner_id": match.winner_id,
                "is_win": ms.is_win,
                "fight_score": round(ms.fight_score, 3) if ms.fight_score else None,
                "sets": sets_detail
            })
        
        return result
