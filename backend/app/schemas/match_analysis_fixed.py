from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time as time_type

class PlayerCreate(BaseModel):
    """Схема для создания игрока"""
    full_name: str
    current_rating: Optional[int] = 1000

class PlayerResponse(BaseModel):
    """Схема ответа с данными игрока"""
    id: str
    full_name: str
    current_rating: int
    created_at: datetime
    updated_at: datetime

class MatchCreate(BaseModel):
    """Схема для создания матча"""
    date: date
    time: Optional[time_type] = None
    player1_name: str  # будем искать или создавать игрока по имени
    player2_name: str
    score: str
    stage: Optional[str] = None
    league_name: Optional[str] = None
    match_sl_id: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_final: bool = False
    is_semifinal: bool = False

class MatchResponse(BaseModel):
    """Схема ответа с данными матча"""
    id: str
    date: date
    time: Optional[time_type]
    score: str
    stage: Optional[str]
    duration_minutes: Optional[int]
    is_final: bool
    is_semifinal: bool
    player1: PlayerResponse
    player2: PlayerResponse
    winner: Optional[PlayerResponse]
    league: Optional[Dict[str, Any]]
    created_at: datetime

class ExcelMatchData(BaseModel):
    """Схема для данных матча из Excel файла"""
    дата: str
    время: Optional[str] = None
    игрок_1: str
    счёт: str
    игрок_2: str
    стадия: Optional[str] = None
    турнир: Optional[str] = None
    турнир_sl_id: Optional[str] = None
    sl_id: Optional[str] = None
    fon_id: Optional[str] = None

class PlayerStatsResponse(BaseModel):
    """Схема ответа со статистикой игрока"""
    id: str
    player_id: str
    matches_played: int
    wins: int
    losses: int
    draws: int
    sets_won: int
    sets_lost: int
    points_won: int
    points_lost: int
    win_percentage: float
    avg_match_duration: int
    last_updated: datetime

class TriggerResponse(BaseModel):
    """Схема ответа с триггером"""
    id: str
    player_id: str
    trigger_type: str
    trigger_subtype: Optional[str]
    trigger_value: str
    severity_level: int
    period_start: Optional[date]
    period_end: Optional[date]
    is_active: bool
    trigger_metadata: Optional[str]  # JSON строка
    created_at: datetime
    
    @property 
    def metadata(self) -> Optional[Dict[str, Any]]:
        """Возвращает распарсенные метаданные"""
        if not self.trigger_metadata:
            return None
        import json
        try:
            return json.loads(self.trigger_metadata)
        except:
            return None

class AnalysisRequest(BaseModel):
    """Схема для запроса анализа"""
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    player_ids: Optional[List[str]] = None
    trigger_types: Optional[List[str]] = None

class AnalysisResponse(BaseModel):
    """Схема ответа с результатами анализа"""
    period_start: date
    period_end: date
    total_players: int
    total_matches: int
    triggers_found: int
    top_performers: List[PlayerResponse]
    problem_players: List[PlayerResponse]
    triggers: List[TriggerResponse]
    
class UpdateStatsRequest(BaseModel):
    """Схема для запроса обновления статистики"""
    player_ids: Optional[List[str]] = None  # если None, обновляем всех
    force_recalculate: bool = False
