from datetime import datetime, date, time as time_type
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
import uuid

if TYPE_CHECKING:
    from app.models.user import User

class PlayerBase(SQLModel):
    """Базовая модель игрока"""
    full_name: str = Field(unique=True, index=True)
    current_rating: int = Field(default=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Player(PlayerBase, table=True):  # РАБОТАЕТ
    """Модель игрока в базе данных"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Связи с другими таблицами
    stats: Optional["PlayerStats"] = Relationship(back_populates="player")
    triggers: List["PlayerTrigger"] = Relationship(back_populates="player")
    matches_as_player1: List["Match"] = Relationship(
        back_populates="player1",
        sa_relationship_kwargs={"foreign_keys": "[Match.player1_id]"}
    )
    matches_as_player2: List["Match"] = Relationship(
        back_populates="player2", 
        sa_relationship_kwargs={"foreign_keys": "[Match.player2_id]"}
    )
    won_matches: List["Match"] = Relationship(
        back_populates="winner",
        sa_relationship_kwargs={"foreign_keys": "[Match.winner_id]"}
    )
    ratings_history: List["PlayerRatingHistory"] = Relationship(back_populates="player")
    period_stats: List["PlayerPeriodStats"] = Relationship(back_populates="player")
    scenario_stats: List["ScenarioStats"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"foreign_keys": "[ScenarioStats.player_id]"}
    )
    match_scenarios: List["MatchScenario"] = Relationship(
        back_populates="player",
        sa_relationship_kwargs={"foreign_keys": "[MatchScenario.player_id]"}
    )

class PlayerStatsBase(SQLModel):
    """Базовая модель статистики игрока"""
    matches_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    draws: int = Field(default=0)
    sets_won: int = Field(default=0)
    sets_lost: int = Field(default=0)
    points_won: int = Field(default=0)
    points_lost: int = Field(default=0)
    win_percentage: float = Field(default=0.0)
    avg_match_duration: int = Field(default=0)  # в минутах
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class PlayerStats(PlayerStatsBase, table=True):
    """Модель статистики игрока"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    player_id: str = Field(foreign_key="player.id")
    
    # Связь с игроком
    player: Player = Relationship(back_populates="stats")

class LeagueBase(SQLModel):
    """Базовая модель лиги"""
    name: str
    level: int  # уровень лиги (1 - высшая, 2 - первая, и т.д.)
    sl_id: Optional[int] = None
    fon_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class League(LeagueBase, table=True):
    """Модель лиги в базе данных"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # Связи с матчами
    matches: List["Match"] = Relationship(back_populates="league")

class MatchBase(SQLModel):
    """Базовая модель матча"""
    date: date
    time: Optional[time_type] = None
    score: str  # формат "3:1" или "2:3"
    sets_player1: Optional[int] = None
    sets_player2: Optional[int] = None
    stage: Optional[str] = None
    match_sl_id: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_final: bool = Field(default=False)
    is_semifinal: bool = Field(default=False)
    
    # Новые поля для эффективности игроков в матче
    serve_efficiency_p1: Optional[int] = None  # Эффективность подачи игрока 1 в матче (%)
    receive_efficiency_p1: Optional[int] = None  # Эффективность приёма игрока 1 в матче (%)
    serve_efficiency_p2: Optional[int] = None  # Эффективность подачи игрока 2 в матче (%)
    receive_efficiency_p2: Optional[int] = None  # Эффективность приёма игрока 2 в матче (%)
    
    # Временные характеристики матча
    match_duration_formatted: Optional[str] = None  # Время матча в формате "ЧЧ:ММ:СС"
    
    # Дисциплинарные действия
    timeouts_p1: Optional[int] = None  # Таймауты игрока 1
    timeouts_p2: Optional[int] = None  # Таймауты игрока 2
    yellow_cards_p1: Optional[int] = None  # Жёлтые карточки игрока 1
    yellow_cards_p2: Optional[int] = None  # Жёлтые карточки игрока 2
    red_cards_p1: Optional[int] = None  # Красные карточки игрока 1
    red_cards_p2: Optional[int] = None  # Красные карточки игрока 2
    
    # Баланс игры
    game_balance: Optional[int] = None  # Баланс в игре (общий)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Match(MatchBase, table=True):
    """Модель матча в базе данных"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    time: Optional[time_type] = None
    player1_id: str = Field(foreign_key="player.id")
    player2_id: str = Field(foreign_key="player.id")
    winner_id: Optional[str] = Field(foreign_key="player.id")
    league_id: Optional[str] = Field(foreign_key="league.id")
    
    # Связи с другими моделями
    player1: Player = Relationship(
        back_populates="matches_as_player1",
        sa_relationship_kwargs={"foreign_keys": "[Match.player1_id]"}
    )
    player2: Player = Relationship(
        back_populates="matches_as_player2",
        sa_relationship_kwargs={"foreign_keys": "[Match.player2_id]"}
    )
    winner: Optional[Player] = Relationship(
        back_populates="won_matches",
        sa_relationship_kwargs={"foreign_keys": "[Match.winner_id]"}
    )
    league: Optional[League] = Relationship(back_populates="matches")
    sets: List["MatchSet"] = Relationship(back_populates="match")
    critical_moments: List["MatchCriticalMoment"] = Relationship(back_populates="match")
    match_scenarios: List["MatchScenario"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={"foreign_keys": "[MatchScenario.match_id]"}
    )

class MatchSetBase(SQLModel):
    """Базовая модель сета матча"""
    set_number: int  # номер сета (1, 2, 3, 4, 5)
    player1_points: int
    player2_points: int
    duration_minutes: Optional[int] = None
    
    # Эффективность игроков в конкретном сете
    serve_efficiency_p1: Optional[int] = None  # Эффективность подачи игрока 1 в сете (%)
    receive_efficiency_p1: Optional[int] = None  # Эффективность приёма игрока 1 в сете (%)
    serve_efficiency_p2: Optional[int] = None  # Эффективность подачи игрока 2 в сете (%)
    receive_efficiency_p2: Optional[int] = None  # Эффективность приёма игрока 2 в сете (%)
    
    # Время сета
    set_duration_formatted: Optional[str] = None  # Время сета в формате "ММ:СС"
    
    # Баланс в сете
    set_balance: Optional[int] = None  # Баланс в конкретном сете
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MatchSet(MatchSetBase, table=True):
    """Модель сета матча"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    match_id: str = Field(foreign_key="match.id")
    winner_id: str = Field(foreign_key="player.id")
    
    # Связи
    match: Match = Relationship(back_populates="sets")
    winner: Player = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MatchSet.winner_id]"}
    )
    critical_moments: List["MatchCriticalMoment"] = Relationship(back_populates="set")

class MatchCriticalMomentBase(SQLModel):
    """Базовая модель критического момента"""
    moment_type: str  # 'lead_lost', 'close_finish', 'comeback', etc.
    score_before: Optional[str] = None
    score_after: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MatchCriticalMoment(MatchCriticalMomentBase, table=True):
    """Модель критического момента в матче"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    match_id: str = Field(foreign_key="match.id")
    set_id: Optional[str] = Field(foreign_key="matchset.id")
    player_id: str = Field(foreign_key="player.id")
    
    # Связи
    match: Match = Relationship(back_populates="critical_moments")
    set: Optional[MatchSet] = Relationship(back_populates="critical_moments")
    player: Player = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MatchCriticalMoment.player_id]"}
    )

class PlayerTriggerBase(SQLModel):
    """Базовая модель триггера игрока"""
    trigger_type: str
    trigger_subtype: Optional[str] = None
    trigger_value: str
    severity_level: int = Field(default=1)  # уровень серьезности (1-5)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    is_active: bool = Field(default=True)
    trigger_metadata: Optional[str] = Field(default=None)  # JSON строка для метаданных
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PlayerTrigger(PlayerTriggerBase, table=True): 
    """Модель триггера игрока"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    player_id: str = Field(foreign_key="player.id")
    match_id: Optional[str] = Field(foreign_key="match.id")
    
    # Связи
    player: Player = Relationship(back_populates="triggers")
    match: Optional[Match] = Relationship()
    
    def set_metadata(self, data: Dict[str, Any]) -> None:
        """Устанавливает метаданные в JSON формате"""
        import json
        self.trigger_metadata = json.dumps(data) if data else None
    
    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Получает метаданные из JSON формата"""
        if not self.trigger_metadata:
            return None
        import json
        try:
            return json.loads(self.trigger_metadata)
        except (json.JSONDecodeError, TypeError):
            return None

class PlayerPeriodStatsBase(SQLModel):
    """Базовая модель статистики игрока по периодам"""
    period_start: date
    period_end: date
    matches_played: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    win_percentage: Optional[float] = None
    avg_sets_per_match: Optional[float] = None
    comeback_wins: int = Field(default=0)
    close_match_wins: int = Field(default=0)
    night_matches: int = Field(default=0)
    day_matches: int = Field(default=0)
    after_holiday_matches: int = Field(default=0)
    streak_losses: int = Field(default=0)
    max_streak_losses: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PlayerPeriodStats(PlayerPeriodStatsBase, table=True):
    """Модель статистики игрока по периодам"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    player_id: str = Field(foreign_key="player.id")
    
    # Связи
    player: Player = Relationship(back_populates="period_stats")

class PlayerRatingHistoryBase(SQLModel):
    """Базовая модель истории рейтинга"""
    rating: int
    rating_date: date
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PlayerRatingHistory(PlayerRatingHistoryBase, table=True):
    """Модель истории рейтинга игрока"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    player_id: str = Field(foreign_key="player.id")
    league_id: Optional[str] = Field(foreign_key="league.id")
    match_id: Optional[str] = Field(foreign_key="match.id")
    
    # Связи
    player: Player = Relationship(back_populates="ratings_history")
    league: Optional[League] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[PlayerRatingHistory.league_id]"}
    )
    match: Optional[Match] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[PlayerRatingHistory.match_id]"}
    )

class HolidayBase(SQLModel):
    """Базовая модель праздника"""
    name: str
    start_date: date
    end_date: date
    country: str = Field(default="RU")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Holiday(HolidayBase, table=True):
    """Модель праздника"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

class TriggerConfigurationBase(SQLModel):
    """Базовая модель конфигурации триггера"""
    trigger_name: str = Field(unique=True)
    description: Optional[str] = None
    threshold_value: Optional[float] = None
    period_days: Optional[int] = None
    is_enabled: bool = Field(default=True)
    config_parameters: Optional[str] = Field(default=None)  # JSON строка для параметров
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TriggerConfiguration(TriggerConfigurationBase, table=True):
    """Модель конфигурации триггеров"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    def set_parameters(self, data: Dict[str, Any]) -> None:
        """Устанавливает параметры в JSON формате"""
        import json
        self.config_parameters = json.dumps(data) if data else None
    
    def get_parameters(self) -> Optional[Dict[str, Any]]:
        """Получает параметры из JSON формата"""
        if not self.config_parameters:
            return None
        import json
        try:
            return json.loads(self.config_parameters)
        except (json.JSONDecodeError, TypeError):
            return None

class ScenarioStatsBase(SQLModel):
    """Базовая модель статистики по сценариям"""
    scenario_code: str  # S1, S2, S3, S4, S5, S6
    matches_total: int = Field(default=0)
    wins: int = Field(default=0)
    losses: int = Field(default=0)
    fight_score: Optional[float] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ScenarioStats(ScenarioStatsBase, table=True):
    """Модель статистики игрока по сценариям"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    player_id: str = Field(foreign_key="player.id")
    
    # Связь с игроком
    player: Player = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ScenarioStats.player_id]"}
    )

class MatchScenarioBase(SQLModel):
    """Базовая модель связи матча и сценария"""
    scenario_code: str  # S1, S2, S3, S4, S5, S6
    fight_score: Optional[float] = None
    is_win: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MatchScenario(MatchScenarioBase, table=True):
    """Модель связи матча со сценарием (для детализации)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    match_id: str = Field(foreign_key="match.id")
    player_id: str = Field(foreign_key="player.id")
    
    # Связи
    match: Match = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MatchScenario.match_id]"}
    )
    player: Player = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[MatchScenario.player_id]"}
    )
