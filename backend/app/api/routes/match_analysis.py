from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.services.match_analysis_service import MatchAnalysisService
from app.schemas.match_analysis import (
    ExcelMatchData, AnalysisRequest, AnalysisResponse,
    PlayerResponse, MatchResponse, TriggerResponse,
    UpdateStatsRequest
)
from app.models.match import Player, Match, PlayerTrigger, PlayerStats
import pandas as pd
import io
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match-analysis", tags=["Match Analysis"])

@router.post("/upload-excel", response_model=dict)
async def upload_excel_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Загрузка Excel файла с матчами
    
    Публичный эндпоинт - доступен всем пользователям без аутентификации.
    Позволяет загружать Excel файлы с данными о матчах для последующего анализа.
    """
    logger.info(f"📁 Получен файл для загрузки: {file.filename}")
    
    try:
        # Проверяем тип файла
        if not file.filename.endswith(('.xlsx', '.xls')):
            logger.warning(f"❌ Неподдерживаемый тип файла: {file.filename}")
            raise HTTPException(status_code=400, detail="Поддерживаются только Excel файлы (.xlsx, .xls)")
        
        # Читаем файл
        logger.info("📖 Читаем содержимое файла...")
        contents = await file.read()
        logger.info(f"📏 Размер файла: {len(contents)} байт")
        
        # Проверяем, что pandas доступен
        try:
            import pandas as pd
            logger.info("✅ Pandas доступен")
        except ImportError as e:
            logger.error("❌ Pandas не установлен")
            raise HTTPException(status_code=500, detail="Pandas не установлен на сервере. Обратитесь к администратору.")
        
        # Читаем Excel файл
        try:
            df = pd.read_excel(io.BytesIO(contents))
            logger.info(f"📊 Excel файл прочитан. Строк: {len(df)}, Столбцов: {len(df.columns)}")
            logger.info(f"🏷️  Столбцы: {list(df.columns)}")
        except Exception as e:
            logger.error(f"❌ Ошибка чтения Excel: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Не удалось прочитать Excel файл: {str(e)}")
        
        if len(df) == 0:
            logger.warning("⚠️  Excel файл пустой")
            raise HTTPException(status_code=400, detail="Excel файл не содержит данных")
        
        # Конвертируем в список объектов ExcelMatchData
        excel_data = []
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Проверяем обязательные поля
                required_fields = ['Дата', 'Игрок 1', 'Счёт', 'Игрок 2']
                missing_fields = [field for field in required_fields if field not in df.columns or pd.isna(row.get(field))]
                
                if missing_fields:
                    error_msg = f"Строка {idx + 1}: отсутствуют поля {missing_fields}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                    continue
                
                match_data = ExcelMatchData(
                    дата=str(row.get('Дата', '')),
                    время=str(row.get('Время', '')) if pd.notna(row.get('Время')) else None,
                    игрок_1=str(row.get('Игрок 1', '')),
                    счёт=str(row.get('Счёт', '')),
                    игрок_2=str(row.get('Игрок 2', '')),
                    стадия=str(row.get('Стадия', '')) if pd.notna(row.get('Стадия')) else None,
                    турнир=str(row.get('Турнир', '')) if pd.notna(row.get('Турнир')) else None,
                    турнир_sl_id=str(row.get('Турнир SL-ID', '')) if pd.notna(row.get('Турнир SL-ID')) else None,
                    sl_id=str(row.get('SL-ID', '')) if pd.notna(row.get('SL-ID')) else None,
                    fon_id=str(row.get('FON-ID', '')) if pd.notna(row.get('FON-ID')) else None
                )
                excel_data.append(match_data)
            except Exception as e:
                error_msg = f"Строка {idx + 1}: {str(e)}"
                errors.append(error_msg)
                logger.warning(error_msg)
                continue
        
        if not excel_data:
            logger.error("❌ Не удалось обработать ни одной строки из Excel")
            raise HTTPException(status_code=400, detail="Не удалось обработать данные из Excel файла")
        
        logger.info(f"✅ Обработано {len(excel_data)} строк из {len(df)}")
        
        # Обрабатываем данные
        logger.info("🔄 Начинаем обработку данных...")
        service = MatchAnalysisService(db)
        result = await service.process_excel_data(excel_data)
        
        # Добавляем ошибки парсинга в результат
        if errors:
            if 'errors' not in result:
                result['errors'] = []
            result['errors'].extend(errors)
        
        logger.info(f"🎉 Обработка завершена: {result}")
        return result
        
    except HTTPException:
        # Пробрасываем HTTP исключения как есть
        raise
    except Exception as e:
        logger.error(f"💥 Неожиданная ошибка при загрузке Excel файла: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")

@router.post("/update-stats", response_model=dict)
async def update_player_stats(
    request: UpdateStatsRequest,
    db: Session = Depends(get_db)
):
    """Обновление статистики игроков"""
    try:
        service = MatchAnalysisService(db)
        result = await service.update_player_statistics(request.player_ids)
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении статистики: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении статистики: {str(e)}")

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_triggers(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Запуск анализа триггеров
    
    Публичный эндпоинт - доступен всем пользователям без аутентификации.
    Анализирует матчи игроков и выявляет различные паттерны поведения (триггеры).
    """
    try:
        logger.info("🔍 Запуск публичного анализа триггеров...")
        service = MatchAnalysisService(db)
        result = await service.analyze_triggers(request)
        logger.info("✅ Анализ триггеров завершен успешно")
        return result
        
    except Exception as e:
        logger.error(f"Ошибка при анализе триггеров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при анализе: {str(e)}")

@router.get("/players", response_model=List[PlayerResponse])
async def get_players(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Получение списка игроков"""
    try:
        players = db.query(Player).offset(skip).limit(limit).all()
        return players
        
    except Exception as e:
        logger.error(f"Ошибка при получении игроков: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")

@router.get("/players/{player_id}", response_model=PlayerResponse)
async def get_player(
    player_id: str,
    db: Session = Depends(get_db)
):
    """Получение данных конкретного игрока"""
    try:
        player = db.query(Player).filter(Player.id == player_id).first()
        if not player:
            raise HTTPException(status_code=404, detail="Игрок не найден")
        return player
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении игрока: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")

@router.get("/players/{player_id}/triggers", response_model=List[TriggerResponse])
async def get_player_triggers(
    player_id: str,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Получение триггеров игрока"""
    try:
        query = db.query(PlayerTrigger).filter(PlayerTrigger.player_id == player_id)
        
        if active_only:
            query = query.filter(PlayerTrigger.is_active == True)
        
        triggers = query.order_by(PlayerTrigger.created_at.desc()).all()
        return triggers
        
    except Exception as e:
        logger.error(f"Ошибка при получении триггеров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")

@router.get("/triggers", response_model=List[TriggerResponse])
async def get_all_triggers(
    skip: int = 0,
    limit: int = 100,
    trigger_type: Optional[str] = None,
    severity_level: Optional[int] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """Получение всех триггеров с фильтрацией"""
    try:
        query = db.query(PlayerTrigger)
        
        if trigger_type:
            query = query.filter(PlayerTrigger.trigger_type == trigger_type)
            
        if severity_level:
            query = query.filter(PlayerTrigger.severity_level >= severity_level)
            
        if active_only:
            query = query.filter(PlayerTrigger.is_active == True)
        
        triggers = query.order_by(
            PlayerTrigger.severity_level.desc(),
            PlayerTrigger.created_at.desc()
        ).offset(skip).limit(limit).all()
        
        return triggers
        
    except Exception as e:
        logger.error(f"Ошибка при получении триггеров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")

@router.get("/statistics/summary", response_model=dict)
async def get_statistics_summary(db: Session = Depends(get_db)):
    """Получение общей статистики"""
    try:
        total_players = db.query(Player).count()
        total_matches = db.query(Match).count()
        active_triggers = db.query(PlayerTrigger).filter(PlayerTrigger.is_active == True).count()
        
        # Топ триггеры по типам
        trigger_stats = db.query(
            PlayerTrigger.trigger_type,
            db.func.count(PlayerTrigger.id).label('count')
        ).filter(
            PlayerTrigger.is_active == True
        ).group_by(PlayerTrigger.trigger_type).all()
        
        return {
            "total_players": total_players,
            "total_matches": total_matches,
            "active_triggers": active_triggers,
            "trigger_types": [{"type": t.trigger_type, "count": t.count} for t in trigger_stats]
        }
        
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении данных: {str(e)}")

@router.delete("/triggers/{trigger_id}")
async def deactivate_trigger(
    trigger_id: str,
    db: Session = Depends(get_db)
):
    """Деактивация триггера"""
    try:
        trigger = db.query(PlayerTrigger).filter(PlayerTrigger.id == trigger_id).first()
        if not trigger:
            raise HTTPException(status_code=404, detail="Триггер не найден")
        
        trigger.is_active = False
        db.commit()
        
        return {"message": "Триггер успешно деактивирован"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при деактивации триггера: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении данных: {str(e)}")

@router.get("/all-matches", response_model=List[dict])
async def get_all_matches(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    """
    Получение всех матчей из базы данных
    
    Публичный эндпоинт - доступен всем пользователям без аутентификации.
    Возвращает список всех матчей с подробной информацией об игроках.
    """
    try:
        logger.info(f"📋 Запрос матчей: limit={limit}, offset={offset}")
        
        # Получаем матчи с информацией об игроках
        matches = db.query(Match).offset(offset).limit(limit).all()
        
        result = []
        for match in matches:
            # Получаем информацию об игроках
            player1 = db.query(Player).filter(Player.id == match.player1_id).first()
            player2 = db.query(Player).filter(Player.id == match.player2_id).first()
            winner = None
            if match.winner_id:
                winner = db.query(Player).filter(Player.id == match.winner_id).first()
            
            match_dict = {
                'id': match.id,
                'date': match.date.strftime('%Y-%m-%d') if match.date else '',
                'time': match.time.strftime('%H:%M') if match.time else None,
                'player1': player1.full_name if player1 else 'Неизвестен',
                'player2': player2.full_name if player2 else 'Неизвестен',
                'player1_id': match.player1_id,
                'player2_id': match.player2_id,
                'score': match.score or '',
                'sets_player1': match.sets_player1 or 0,
                'sets_player2': match.sets_player2 or 0,
                'winner': winner.full_name if winner else 'Ничья',
                'winner_id': match.winner_id,
                'tournament': '',  # Будет добавлено позже из League
                'stage': match.stage or '',
                'is_final': match.is_final or False,
                'is_semifinal': match.is_semifinal or False,
                'created_at': match.created_at.isoformat() if match.created_at else ''
            }
            
            # Добавляем информацию о турнире/лиге если есть
            if match.league_id:
                from app.models.match import League
                league = db.query(League).filter(League.id == match.league_id).first()
                if league:
                    match_dict['tournament'] = league.name
            
            result.append(match_dict)
        
        logger.info(f"✅ Найдено матчей: {len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении матчей: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении матчей: {str(e)}")

@router.get("/ping")
async def ping():
    """
    Тестовый эндпоинт для проверки доступности API
    
    Публичный эндпоинт - доступен всем без аутентификации.
    Используется для проверки, что API работает и доступно.
    """
    return {
        "message": "API Match Analysis доступно", 
        "status": "ok",
        "endpoints": {
            "upload": "/api/v1/match-analysis/upload-excel",
            "analyze": "/api/v1/match-analysis/analyze", 
            "matches": "/api/v1/match-analysis/all-matches",
            "analyze-database": "/api/v1/match-analysis/analyze-database",
            "triggers": "/api/v1/match-analysis/triggers",
            "players": "/api/v1/match-analysis/players",
            "ping": "/api/v1/match-analysis/ping"
        }
    }

@router.post("/analyze-database")
async def analyze_database_matches(
    request: AnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Анализ матчей из базы данных на предмет триггеров
    
    Публичный эндпоинт для анализа существующих матчей в базе данных.
    Выявляет различные триггеры и проблемные паттерны в игре игроков.
    """
    logger.info("🔍 Запуск анализа матчей из базы данных...")
    
    try:
        service = MatchAnalysisService(db)
        result = await service.analyze_triggers(request)
        
        logger.info(f"✅ Анализ завершен. Найдено триггеров: {result.triggers_found}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка при анализе базы данных: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при анализе: {str(e)}")

@router.get("/triggers")
async def get_all_triggers(
    player_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    severity_level: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение списка всех триггеров с фильтрацией
    
    Публичный эндпоинт для получения триггеров с возможностью фильтрации
    по игроку, типу триггера и уровню серьезности.
    """
    logger.info(f"📊 Получение триггеров с фильтрами: player_id={player_id}, type={trigger_type}, severity={severity_level}")
    
    try:
        query = db.query(PlayerTrigger).join(Player)
        
        if player_id:
            query = query.filter(PlayerTrigger.player_id == player_id)
        
        if trigger_type:
            query = query.filter(PlayerTrigger.trigger_type == trigger_type)
            
        if severity_level:
            query = query.filter(PlayerTrigger.severity_level == severity_level)
        
        triggers = query.order_by(PlayerTrigger.created_at.desc()).limit(limit).all()
        
        result = []
        for trigger in triggers:
            player = db.query(Player).filter(Player.id == trigger.player_id).first()
            
            trigger_dict = {
                'id': trigger.id,
                'player_id': trigger.player_id,
                'player_name': player.full_name if player else 'Неизвестный игрок',
                'player_rating': player.current_rating if player else None,
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
        
        logger.info(f"✅ Найдено триггеров: {len(result)}")
        return {
            "triggers": result,
            "count": len(result),
            "filters_applied": {
                "player_id": player_id,
                "trigger_type": trigger_type,
                "severity_level": severity_level,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении триггеров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении триггеров: {str(e)}")

@router.get("/players")
async def get_all_players(
    limit: int = 100,
    include_stats: bool = True,
    db: Session = Depends(get_db)
):
    """
    Получение списка всех игроков с их статистикой
    
    Публичный эндпоинт для получения списка игроков
    с возможностью включения статистики.
    """
    logger.info(f"👥 Получение списка игроков (limit={limit}, include_stats={include_stats})")
    
    try:
        players = db.query(Player).limit(limit).all()
        
        result = []
        for player in players:
            player_dict = {
                'id': player.id,
                'full_name': player.full_name,
                'current_rating': player.current_rating,
                'created_at': player.created_at,
                'updated_at': player.updated_at
            }
            
            if include_stats:
                stats = db.query(PlayerStats).filter(PlayerStats.player_id == player.id).first()
                if stats:
                    player_dict['stats'] = {
                        'matches_played': stats.matches_played,
                        'wins': stats.wins,
                        'losses': stats.losses,
                        'draws': stats.draws,
                        'win_percentage': stats.win_percentage,
                        'sets_won': stats.sets_won,
                        'sets_lost': stats.sets_lost,
                        'last_updated': stats.last_updated
                    }
                else:
                    player_dict['stats'] = None
            
            result.append(player_dict)
        
        logger.info(f"✅ Найдено игроков: {len(result)}")
        return {
            "players": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении игроков: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении игроков: {str(e)}")

@router.get("/trigger-types")
async def get_trigger_types():
    """
    Получение списка доступных типов триггеров
    
    Публичный эндпоинт для получения всех типов триггеров,
    которые может анализировать система.
    """
    trigger_types = {
        "defeat_0_3": {
            "name": "Поражения 0:3",
            "description": "Анализ частых поражений со счетом 0:3",
            "severity": "Высокая"
        },
        "won_2_lost_3rd_set": {
            "name": "Выиграл 2 сета, проиграл 3-й",
            "description": "Проблемы с завершением матчей после ведения 2:0",
            "severity": "Высокая"
        },
        "early_final_exit_advanced": {
            "name": "Досрочный выход из финала",
            "description": "Плохая игра в финальных матчах",
            "severity": "Высокая"
        },
        "led_1_set_lost_match": {
            "name": "Вёл 1 сет и проиграл",
            "description": "Неспособность удержать преимущество",
            "severity": "Средняя"
        },
        "led_2_sets_lost_match": {
            "name": "Вёл 2 сета и проиграл",
            "description": "Критические проблемы с удержанием большого преимущества",
            "severity": "Критическая"
        },
        "psychological_breakdown": {
            "name": "Психологические срывы",
            "description": "Комбинированный анализ психологических проблем",
            "severity": "Высокая"
        },
        "comeback_inability": {
            "name": "Неспособность к камбекам",
            "description": "Проблемы с отыгрыванием отставания",
            "severity": "Средняя"
        },
        "pressure_situations": {
            "name": "Игра под давлением",
            "description": "Плохие результаты в важных матчах",
            "severity": "Высокая"
        },
        "losing_streaks": {
            "name": "Серии поражений",
            "description": "Анализ длительных серий поражений",
            "severity": "Средняя"
        },
        "top_performers": {
            "name": "Топ игроки",
            "description": "Выявление лучших игроков периода",
            "severity": "Позитивная"
        }
    }
    
    return {
        "trigger_types": trigger_types,
        "count": len(trigger_types),
        "message": "Доступные типы триггеров для анализа"
    }
