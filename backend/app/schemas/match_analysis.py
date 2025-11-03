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
    рейтинг_игрок_1: Optional[str] = None
    игрок_2: str
    рейтинг_игрок_2: Optional[str] = None
    счёт: Optional[str] = None  # Старый формат (может отсутствовать)
    
    # НОВЫЙ ФОРМАТ: Счет матча по сетам
    счет_матча_игрока_1: Optional[str] = None  # Количество выигранных сетов игроком 1
    счет_матча_игрока_2: Optional[str] = None  # Количество выигранных сетов игроком 2
    
    стадия: Optional[str] = None
    турнир: Optional[str] = None
    турнир_sl_id: Optional[str] = None
    sl_id: Optional[str] = None
    fon_id: Optional[str] = None
    
    # Счета по сетам (до 5 сетов)
    счёт_1_сета_игрок_1: Optional[str] = None
    счёт_1_сета_игрок_2: Optional[str] = None
    счёт_2_сета_игрок_1: Optional[str] = None
    счёт_2_сета_игрок_2: Optional[str] = None
    счёт_3_сета_игрок_1: Optional[str] = None
    счёт_3_сета_игрок_2: Optional[str] = None
    счёт_4_сета_игрок_1: Optional[str] = None
    счёт_4_сета_игрок_2: Optional[str] = None
    счёт_5_сета_игрок_1: Optional[str] = None
    счёт_5_сета_игрок_2: Optional[str] = None
    
    # Эффективность подачи и приёма игроков в матче
    эффективность_подачи_игрока_1_в_матче: Optional[str] = None
    эффективность_приёма_игрока_1_в_матче: Optional[str] = None
    эффективность_подачи_игрока_2_в_матче: Optional[str] = None
    эффективность_приёма_игрока_2_в_матче: Optional[str] = None
    
    # Эффективность подачи и приёма игроков в сетах
    эффективность_подачи_игрока_1_в_1_сете: Optional[str] = None
    эффективность_приёма_игрока_1_в_1_сете: Optional[str] = None
    эффективность_подачи_игрока_2_в_1_сете: Optional[str] = None
    эффективность_приёма_игрока_2_в_1_сете: Optional[str] = None
    
    эффективность_подачи_игрока_1_в_2_сете: Optional[str] = None
    эффективность_приёма_игрока_1_в_2_сете: Optional[str] = None
    эффективность_подачи_игрока_2_в_2_сете: Optional[str] = None
    эффективность_приёма_игрока_2_в_2_сете: Optional[str] = None
    
    эффективность_подачи_игрока_1_в_3_сете: Optional[str] = None
    эффективность_приёма_игрока_1_в_3_сете: Optional[str] = None
    эффективность_подачи_игрока_2_в_3_сете: Optional[str] = None
    эффективность_приёма_игрока_2_в_3_сете: Optional[str] = None
    
    эффективность_подачи_игрока_1_в_4_сете: Optional[str] = None
    эффективность_приёма_игрока_1_в_4_сете: Optional[str] = None
    эффективность_подачи_игрока_2_в_4_сете: Optional[str] = None
    эффективность_приёма_игрока_2_в_4_сете: Optional[str] = None
    
    эффективность_подачи_игрока_1_в_5_сете: Optional[str] = None
    эффективность_приёма_игрока_1_в_5_сете: Optional[str] = None
    эффективность_подачи_игрока_2_в_5_сете: Optional[str] = None
    эффективность_приёма_игрока_2_в_5_сете: Optional[str] = None
    
    # Время матча и сетов
    время_матча: Optional[str] = None
    время_1_сета: Optional[str] = None
    время_2_сета: Optional[str] = None
    время_3_сета: Optional[str] = None
    время_4_сета: Optional[str] = None
    время_5_сета: Optional[str] = None
    
    # Таймауты
    таймауты_игрок_1: Optional[str] = None
    таймауты_игрок_2: Optional[str] = None
    
    # Карточки
    жёлтые_карточки_игрок_1: Optional[str] = None
    жёлтые_карточки_игрок_2: Optional[str] = None
    красные_карточки_игрок_1: Optional[str] = None
    красные_карточки_игрок_2: Optional[str] = None
    
    # Балансы
    балансы_в_игре: Optional[str] = None
    баланс_в_1_сете: Optional[str] = None
    баланс_в_2_сете: Optional[str] = None
    баланс_в_3_сете: Optional[str] = None
    баланс_в_4_сете: Optional[str] = None
    баланс_в_5_сете: Optional[str] = None

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
    analyze_recent_upload_only: bool = False  # Анализировать только игроков из последнего загруженного файла
    ai_provider: Optional[str] = "lmstudio"  # AI провайдер: "ollama" или "lmstudio" (по умолчанию LM Studio)
    ai_analysis_enabled: bool = True  # Включение/выключение AI анализа
    selected_model: Optional[str] = None  # Конкретная модель для анализа
    max_tokens: Optional[int] = 2000  # Максимальное количество токенов для ответа AI

class AnalysisResponse(BaseModel):
    """Схема ответа с результатами анализа"""
    period_start: date
    period_end: date
    total_players: int
    total_matches: int
    triggers_found: int
    top_performers: List[Dict[str, Any]]
    problem_players: List[Dict[str, Any]]
    triggers: List[Dict[str, Any]]
    
class UpdateStatsRequest(BaseModel):
    """Схема для запроса обновления статистики"""
    player_ids: Optional[List[str]] = None  # если None, обновляем всех
    force_recalculate: bool = False

class TriggerAIAnalysisRequest(BaseModel):
    """Запрос на генерацию ИИ-анализа для одного триггера"""
    word_limit: int = 60  # Ограничение по количеству слов (сжатый, но информативный текст)
    provider: Optional[str] = "lmstudio"  # Провайдер AI (lmstudio или ollama)

class TriggerAIAnalysisResponse(BaseModel):
    """Ответ с ИИ-анализом конкретного триггера"""
    trigger_id: str
    ai_analysis: str
