"""
Схемы для сценарного анализа
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class ScenarioStatsResponse(BaseModel):
    """Ответ со статистикой по сценарию"""
    scenario_code: str
    scenario_name: str
    matches_total: int
    wins: int
    losses: int
    win_rate: float
    fight_score: Optional[float]
    fight_score_interpretation: str
    behavior_label: str
    updated_at: Optional[str]

    class Config:
        from_attributes = True


class SetDetail(BaseModel):
    """Детали сета"""
    set_number: int
    player1_points: int
    player2_points: int
    winner_id: str


class ScenarioMatchDetail(BaseModel):
    """Детали матча в сценарии"""
    match_id: str
    date: Optional[str]
    player1_name: str
    player2_name: str
    score: str
    winner_id: Optional[str]
    is_win: bool
    fight_score: Optional[float]
    sets: List[SetDetail]

    class Config:
        from_attributes = True


class PlayerScenariosResponse(BaseModel):
    """Ответ со всеми сценариями игрока"""
    player_id: str
    scenarios: List[ScenarioStatsResponse]


class AnalyzePlayerResponse(BaseModel):
    """Ответ на запрос анализа игрока"""
    player_id: str
    scenarios_analyzed: int
    total_matches: int
    message: str
