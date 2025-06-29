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
from app.models.match import Player, Match, PlayerTrigger
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
    """Загрузка Excel файла с матчами"""
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
    """Запуск анализа триггеров"""
    try:
        service = MatchAnalysisService(db)
        result = await service.analyze_triggers(request)
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

@router.get("/matches", response_model=List[MatchResponse])
async def get_matches(
    skip: int = 0,
    limit: int = 100,
    player_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получение списка матчей"""
    try:
        query = db.query(Match)
        
        if player_id:
            query = query.filter(
                (Match.player1_id == player_id) | (Match.player2_id == player_id)
            )
        
        matches = query.order_by(Match.date.desc()).offset(skip).limit(limit).all()
        return matches
        
    except Exception as e:
        logger.error(f"Ошибка при получении матчей: {str(e)}")
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
