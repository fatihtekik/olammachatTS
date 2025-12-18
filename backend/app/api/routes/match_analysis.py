from datetime import datetime
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from sympy import re
from app.database.db import get_db
from app.services.match_analysis_service import MatchAnalysisService
from app.schemas.match_analysis import (
    ExcelMatchData, AnalysisRequest, AnalysisResponse,
    PlayerResponse, MatchResponse, TriggerResponse,
    UpdateStatsRequest, TriggerAIAnalysisRequest, TriggerAIAnalysisResponse
)
from app.models.match import Player, Match, PlayerTrigger, PlayerStats
import pandas as pd
import io
import logging
from fastapi.encoders import jsonable_encoder
from app.analysisbypairs.triggers import H2HAnalysisService
from app.models.match import MatchSet

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/match-analysis", tags=["Match Analysis"])



@router.post("/upload-excel")  # РАБОТАЕТ
async def upload_excel_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    print(f"📁 Получен файл для загрузки: {file.filename}")

    try:
        if not file.filename.endswith(('.xlsx', '.xls')):
            print(f"❌ Неподдерживаемый тип файла: {file.filename}")
            raise HTTPException(status_code=400, detail="Поддерживаются только Excel файлы (.xlsx, .xls)")

        print("📖 Читаем содержимое файла...")
        contents = await file.read()
        print(f"📏 Размер файла: {len(contents)} байт")

        try:
            import pandas as pd, io, re
            print("✅ Pandas доступен")
        except ImportError:
            print("❌ Pandas не установлен")
            raise HTTPException(status_code=500, detail="Pandas не установлен на сервере. Обратитесь к администратору.")

        try:
            df = pd.read_excel(io.BytesIO(contents))
            # Нормализуем заголовки сразу и один раз
            df.rename(columns=lambda x: str(x).strip().replace('Счет', 'Счёт').replace('счет', 'счёт'), inplace=True)
            print(f"📊 Excel файл прочитан. Строк: {len(df)}, Столбцов: {len(df.columns)}")
            print(f"🏷️  Столбцы: {list(df.columns)[:20]}...")
            
            # Проверяем наличие колонок с сетами после нормализации
            set_cols = [c for c in df.columns if 'сет' in c.lower() and 'счёт' in c.lower()]
            print(f"🎾 Колонки с СЧЕТАМИ сетов ({len(set_cols)}):")
            for sc in set_cols:
                print(f"   - {sc}")
            
            # DEBUG: Проверим первую строку данных для сетов 4-5
            if len(df) > 0:
                first_row = df.iloc[0]
                print(f"\n🔍 DEBUG: Первая строка (сеты 4-5):")
                for i in [4, 5]:
                    col1 = f'Счёт {i} сета Игрок 1'
                    col2 = f'Счёт {i} сета Игрок 2'
                    val1 = first_row.get(col1, 'НЕТ КОЛОНКИ')
                    val2 = first_row.get(col2, 'НЕТ КОЛОНКИ')
                    print(f"   Сет {i}: '{val1}' : '{val2}' (тип: {type(val1).__name__})")
        except Exception as e:
            print(f"❌ Ошибка чтения Excel: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Не удалось прочитать Excel файл: {str(e)}")

        if len(df) == 0:
            print("⚠️  Excel файл пустой")
            raise HTTPException(status_code=400, detail="Excel файл не содержит данных")

        # Проверяем обязательные колонки 1 раз
        required_cols = ['Дата', 'Игрок 1', 'Игрок 2']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"В Excel отсутствуют колонки: {missing_cols}")

        # Проверяем наличие счета - новый формат (приоритет) или старый
        # ВАЖНО: проверяем ПОСЛЕ нормализации, поэтому ищем с буквой Ё
        has_new_score_format = all(c in df.columns for c in ["Счёт матча игрока 1", "Счёт матча игрока 2"])
        has_old_score_format = "Счёт" in df.columns
        
        if not has_new_score_format and not has_old_score_format:
            print(f"❌ Доступные колонки: {list(df.columns)}")
            raise HTTPException(status_code=400, detail="В Excel нет колонок 'Счёт матча игрока 1/2' или 'Счёт'")
        
        print(f"📊 Формат счета: {'НОВЫЙ (Счёт матча игрока 1/2)' if has_new_score_format else 'СТАРЫЙ (Счёт)'}")

        # Вспомогательные парсеры
        import re

        def split_name_and_rating(val):
            if val is None:
                return "", None
            s = str(val)
            m = re.search(r"(.+?)\s+rating[: ]+([\d.,]+)", s, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                rating = m.group(2).replace(",", ".")
                return name, rating
            return s.strip(), None

        def get_match_score(row):
            """Получить счет матча по СЕТАМ из нового или старого формата"""
            # НОВЫЙ формат: отдельные колонки "Счёт матча игрока 1" и "Счёт матча игрока 2"
            # Это счет по СЕТАМ (например 3:1 означает 3 сета к 1)
            # ВАЖНО: после нормализации все 'Счет' стали 'Счёт'
            if has_new_score_format:
                score1 = row.get('Счёт матча игрока 1')
                score2 = row.get('Счёт матча игрока 2')
                if pd.notna(score1) and pd.notna(score2):
                    try:
                        s1 = int(float(score1))
                        s2 = int(float(score2))
                        return f"{s1}:{s2}"
                    except (ValueError, TypeError):
                        pass
            
            # СТАРЫЙ формат: единая колонка "Счёт" 
            # Может содержать счет типа "3:1" или детальный счет
            if has_old_score_format:
                val = row.get('Счёт')  # После нормализации всегда 'Счёт'
                if pd.notna(val):
                    s = str(val).strip()
                    # Извлекаем счёт формата X:Y или X-Y
                    m = re.match(r"\s*([0-9]+)[\:\-]([0-9]+)", s)
                    if m:
                        return f"{m.group(1)}:{m.group(2)}"
                    return s
            
            return "0:0"

        # Конвертируем строки
        excel_data = []
        errors = []
        
        def safe_get(row, col_name):
            """Безопасное получение значения из строки с проверкой на NaN"""
            val = row.get(col_name)
            if pd.notna(val) and str(val).strip() not in ['', 'nan']:
                return str(val).strip()
            return None

        for idx, row in df.iterrows():
            try:
                # Получаем счет матча ПО СЕТАМ (новый или старый формат)
                main_score = get_match_score(row)
                
                # Получаем имена и рейтинги игроков
                p1, r1 = split_name_and_rating(row.get('Игрок 1'))
                p2, r2 = split_name_and_rating(row.get('Игрок 2'))
                
                # Логируем первые 3 матча для отладки
                if idx < 3:
                    print(f"🔍 Матч {idx+1}: {p1} vs {p2}")
                    print(f"   Счет по сетам: {main_score}")
                    if has_new_score_format:
                        print(f"   Из колонок: [{row.get('Счёт матча игрока 1')}:{row.get('Счёт матча игрока 2')}]")
                    print(f"   Сет 1: {row.get('Счёт 1 сета Игрок 1')}:{row.get('Счёт 1 сета Игрок 2')}")
                    print(f"   Сет 2: {row.get('Счёт 2 сета Игрок 1')}:{row.get('Счёт 2 сета Игрок 2')}")
                    print(f"   Сет 3: {row.get('Счёт 3 сета Игрок 1')}:{row.get('Счёт 3 сета Игрок 2')}")
                    print(f"   Сет 4: {row.get('Счёт 4 сета Игрок 1')}:{row.get('Счёт 4 сета Игрок 2')}")
                    print(f"   Сет 5: {row.get('Счёт 5 сета Игрок 1')}:{row.get('Счёт 5 сета Игрок 2')}")
                    print(f"   🔍 safe_get результаты:")
                    print(f"      Сет 4 после safe_get: {safe_get(row, 'Счёт 4 сета Игрок 1')} : {safe_get(row, 'Счёт 4 сета Игрок 2')}")
                    print(f"      Сет 5 после safe_get: {safe_get(row, 'Счёт 5 сета Игрок 1')} : {safe_get(row, 'Счёт 5 сета Игрок 2')}")
                
                # Если рейтинги не в именах, берем из отдельных колонок
                if not r1 and 'Рейтинг игрока 1' in df.columns:
                    r1_val = row.get('Рейтинг игрока 1')
                    if pd.notna(r1_val):
                        r1 = str(r1_val).replace(',', '.')
                
                if not r2 and 'Рейтинг игрока 2' in df.columns:
                    r2_val = row.get('Рейтинг игрока 2')
                    if pd.notna(r2_val):
                        r2 = str(r2_val).replace(',', '.')

                match_data = ExcelMatchData(
                    дата=str(row.get('Дата', '')),
                    время=safe_get(row, 'Время'),
                    игрок_1=p1,
                    рейтинг_игрок_1=r1,
                    игрок_2=p2,
                    рейтинг_игрок_2=r2,
                    счёт=main_score,  # Общий счет (для совместимости)
                    
                    # НОВЫЕ ПОЛЯ: Счет матча по сетам (ПОСЛЕ нормализации используем 'Счёт')
                    счет_матча_игрока_1=safe_get(row, 'Счёт матча игрока 1'),
                    счет_матча_игрока_2=safe_get(row, 'Счёт матча игрока 2'),
                    
                    стадия=safe_get(row, 'Стадия'),
                    турнир=safe_get(row, 'Турнир'),
                    турнир_sl_id=safe_get(row, 'Турнир SL-ID'),
                    sl_id=safe_get(row, 'SL-ID'),
                    fon_id=safe_get(row, 'FON-ID'),
                    
                    # Счета по сетам (ПОСЛЕ нормализации все "Счет" → "Счёт")
                    счёт_1_сета_игрок_1=safe_get(row, 'Счёт 1 сета Игрок 1'),
                    счёт_1_сета_игрок_2=safe_get(row, 'Счёт 1 сета Игрок 2'),
                    счёт_2_сета_игрок_1=safe_get(row, 'Счёт 2 сета Игрок 1'),
                    счёт_2_сета_игрок_2=safe_get(row, 'Счёт 2 сета Игрок 2'),
                    счёт_3_сета_игрок_1=safe_get(row, 'Счёт 3 сета Игрок 1'),
                    счёт_3_сета_игрок_2=safe_get(row, 'Счёт 3 сета Игрок 2'),
                    счёт_4_сета_игрок_1=safe_get(row, 'Счёт 4 сета Игрок 1'),
                    счёт_4_сета_игрок_2=safe_get(row, 'Счёт 4 сета Игрок 2'),
                    счёт_5_сета_игрок_1=safe_get(row, 'Счёт 5 сета Игрок 1'),
                    счёт_5_сета_игрок_2=safe_get(row, 'Счёт 5 сета Игрок 2'),
                    
                    # Эффективность в матче
                    эффективность_подачи_игрока_1_в_матче=safe_get(row, 'Эффективность подачи игрока 1 в матче'),
                    эффективность_приёма_игрока_1_в_матче=safe_get(row, 'Эффективность приёма игрока 1 в матче'),
                    эффективность_подачи_игрока_2_в_матче=safe_get(row, 'Эффективность подачи игрока 2 в матче'),
                    эффективность_приёма_игрока_2_в_матче=safe_get(row, 'Эффективность приёма игрока 2 в матче'),
                    
                    # Эффективность в сетах
                    эффективность_подачи_игрока_1_в_1_сете=safe_get(row, 'Эффективность подачи игрока 1 в 1 сете'),
                    эффективность_приёма_игрока_1_в_1_сете=safe_get(row, 'Эффективность приёма игрока 1 в 1 сете'),
                    эффективность_подачи_игрока_2_в_1_сете=safe_get(row, 'Эффективность подачи игрока 2 в 1 сете'),
                    эффективность_приёма_игрока_2_в_1_сете=safe_get(row, 'Эффективность приёма игрока 2 в 1 сете'),
                    
                    эффективность_подачи_игрока_1_в_2_сете=safe_get(row, 'Эффективность подачи игрока 1 в 2 сете'),
                    эффективность_приёма_игрока_1_в_2_сете=safe_get(row, 'Эффективность приёма игрока 1 в 2 сете'),
                    эффективность_подачи_игрока_2_в_2_сете=safe_get(row, 'Эффективность подачи игрока 2 в 2 сете'),
                    эффективность_приёма_игрока_2_в_2_сете=safe_get(row, 'Эффективность приёма игрока 2 в 2 сете'),
                    
                    эффективность_подачи_игрока_1_в_3_сете=safe_get(row, 'Эффективность подачи игрока 1 в 3 сете'),
                    эффективность_приёма_игрока_1_в_3_сете=safe_get(row, 'Эффективность приёма игрока 1 в 3 сете'),
                    эффективность_подачи_игрока_2_в_3_сете=safe_get(row, 'Эффективность подачи игрока 2 в 3 сете'),
                    эффективность_приёма_игрока_2_в_3_сете=safe_get(row, 'Эффективность приёма игрока 2 в 3 сете'),
                    
                    эффективность_подачи_игрока_1_в_4_сете=safe_get(row, 'Эффективность подачи игрока 1 в 4 сете'),
                    эффективность_приёма_игрока_1_в_4_сете=safe_get(row, 'Эффективность приёма игрока 1 в 4 сете'),
                    эффективность_подачи_игрока_2_в_4_сете=safe_get(row, 'Эффективность подачи игрока 2 в 4 сете'),
                    эффективность_приёма_игрока_2_в_4_сете=safe_get(row, 'Эффективность приёма игрока 2 в 4 сете'),
                    
                    эффективность_подачи_игрока_1_в_5_сете=safe_get(row, 'Эффективность подачи игрока 1 в 5 сете'),
                    эффективность_приёма_игрока_1_в_5_сете=safe_get(row, 'Эффективность приёма игрока 1 в 5 сете'),
                    эффективность_подачи_игрока_2_в_5_сете=safe_get(row, 'Эффективность подачи игрока 2 в 5 сете'),
                    эффективность_приёма_игрока_2_в_5_сете=safe_get(row, 'Эффективность приёма игрока 2 в 5 сете'),
                    
                    # Время
                    время_матча=safe_get(row, 'Время матча'),
                    время_1_сета=safe_get(row, 'Время 1 сета'),
                    время_2_сета=safe_get(row, 'Время 2 сета'),
                    время_3_сета=safe_get(row, 'Время 3 сета'),
                    время_4_сета=safe_get(row, 'Время 4 сета'),
                    время_5_сета=safe_get(row, 'Время 5 сета'),
                    
                    # Таймауты
                    таймауты_игрок_1=safe_get(row, 'Таймауты Игрок 1'),
                    таймауты_игрок_2=safe_get(row, 'Таймауты Игрок 2'),
                    
                    # Карточки
                    жёлтые_карточки_игрок_1=safe_get(row, 'Жёлтые карточки Игрок 1'),
                    жёлтые_карточки_игрок_2=safe_get(row, 'Жёлтые карточки Игрок 2'),
                    красные_карточки_игрок_1=safe_get(row, 'Красные карточки Игрок 1'),
                    красные_карточки_игрок_2=safe_get(row, 'Красные карточки Игрок 2'),
                    
                    # Балансы
                    балансы_в_игре=safe_get(row, 'Балансы в игре'),
                    баланс_в_1_сете=safe_get(row, 'Баланс в 1 сете'),
                    баланс_в_2_сете=safe_get(row, 'Баланс в 2 сете'),
                    баланс_в_3_сете=safe_get(row, 'Баланс в 3 сете'),
                    баланс_в_4_сете=safe_get(row, 'Баланс в 4 сете'),
                    баланс_в_5_сете=safe_get(row, 'Баланс в 5 сете')
                )
                d = row.get('Дата')
                print("DEBUG Дата:", d, type(d))
                
                # DEBUG: Логируем первые 2 матча для проверки сетов
                if idx < 2:
                    print(f"\n🔍 DEBUG Матч {idx+1}:")
                    print(f"   Счет: {safe_get(row, 'Счёт')}")
                    print(f"   Сет 1: {match_data.счёт_1_сета_игрок_1} : {match_data.счёт_1_сета_игрок_2}")
                    print(f"   Сет 2: {match_data.счёт_2_сета_игрок_1} : {match_data.счёт_2_сета_игрок_2}")
                    print(f"   Сет 3: {match_data.счёт_3_сета_игрок_1} : {match_data.счёт_3_сета_игрок_2}")
                    print(f"   Сет 4: {match_data.счёт_4_сета_игрок_1} : {match_data.счёт_4_сета_игрок_2}")
                    print(f"   Сет 5: {match_data.счёт_5_сета_игрок_1} : {match_data.счёт_5_сета_игрок_2}")
                
                excel_data.append(match_data)
            except Exception as e:
                err = f"Строка {idx+1}: {e.__class__.__name__}: {e}"
                print("⚠️", err)
                errors.append(err)
                continue
        # saved = db.query(Match).limit(5).all()
        # for m in saved:
        #     print(m.id, m.date, m.player1_id, m.player2_id, m.score)
        if not excel_data:
            print("❌ Не удалось обработать ни одной строки из Excel")
            if errors:
                print("Примеры ошибок:", errors[:5])
            raise HTTPException(status_code=400, detail="Не удалось обработать данные из Excel файла")

        print(f"✅ Обработано {len(excel_data)} строк из {len(df)}")

        print(f"🔄 Начинаем обработку данных {excel_data}🔄")
        service = MatchAnalysisService(db)
        result = await service.process_excel_data(excel_data)

        if errors:
            result.setdefault('errors', []).extend(errors)

        print(f"🎉 Обработка завершена: {result}")
        
        encoded = jsonable_encoder(result)
        print("📋📋📋 Игроков в файле (encoded):", encoded)
        # пусть FastAPI сам сериализует — просто вернём примитивную структуру
        return JSONResponse(content=encoded)

    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Неожиданная ошибка при загрузке Excel файла: {str(e)}", exc_info=True)
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
            # query = query.filter(PlayerTrigger.is_active == True)
            query = query.filter(PlayerTrigger.is_pair == False)
            
        
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
            # query = query.filter(PlayerTrigger.is_active == True)
            query = query.filter(PlayerTrigger.is_pair == False)
        
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
        # active_triggers = db.query(PlayerTrigger).filter(PlayerTrigger.is_active == True).count()
        active_triggers = db.query(PlayerTrigger.is_pair == False).count()
        
        # Топ триггеры по типам
        trigger_stats = db.query(
            PlayerTrigger.trigger_type,
            db.func.count(PlayerTrigger.id).label('count')
        ).filter(
            # PlayerTrigger.is_active == True
            PlayerTrigger.is_pair == False
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

# @router.delete("/triggers/{trigger_id}")
# async def deactivate_trigger(
#     trigger_id: str,
#     db: Session = Depends(get_db)
# ):
#     """Деактивация триггера"""
#     try:
#         trigger = db.query(PlayerTrigger).filter(PlayerTrigger.id == trigger_id).first()
#         if not trigger:
#             raise HTTPException(status_code=404, detail="Триггер не найден")
        
#         trigger.is_active = False
#         db.commit()
        
#         return {"message": "Триггер успешно деактивирован"}
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Ошибка при деактивации триггера: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Ошибка при обновлении данных: {str(e)}")

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

@router.post("/analyze-database") # РАБОТАЕТ
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

@router.post("/triggers/{trigger_id}/ai-analysis", response_model=TriggerAIAnalysisResponse)
async def generate_single_trigger_ai_analysis(
    trigger_id: str,
    request: TriggerAIAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Генерация ИИ-анализа только для одного триггера (краткий вывод)
    Возвращает сжатый (по количеству слов) анализ без потери ключевой информации.
    """
    try:
        trigger = db.query(PlayerTrigger).filter(PlayerTrigger.id == trigger_id).first()
        if not trigger:
            raise HTTPException(status_code=404, detail="Триггер не найден")

        player = db.query(Player).filter(Player.id == trigger.player_id).first()

        # Минимальная статистика игрока для контекста
        service = MatchAnalysisService(db)
        player_stats = service._get_player_stats_for_trigger(trigger.player_id, trigger.period_start, trigger.period_end)
        if not player_stats:
            player_stats = {
                'wins': 0, 'losses': 0, 'win_rate': 0.0, 'matches_played': 0, 'recent_form': ''
            }

        # Используем внутренний метод генерации анализа (правильный порядок параметров)
        full_text = await service._generate_ai_analysis(
            player.full_name if player else 'Неизвестный игрок',
            trigger.trigger_value,
            player_stats,
            provider=request.provider or "lmstudio"
        )

        # Ограничиваем по количеству слов
        words = full_text.split()
        if len(words) > request.word_limit:
            # Сохраняем первую часть и добавляем многоточие
            trimmed = ' '.join(words[:request.word_limit]) + '...'
        else:
            trimmed = full_text

        # Обновляем запись в БД (опционально можно сохранить в trigger_metadata)
        trigger.trigger_metadata = trigger.trigger_metadata or '{}'
        db.commit()

        return TriggerAIAnalysisResponse(trigger_id=trigger.id, ai_analysis=trimmed)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации ИИ-анализа триггера {trigger_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка генерации анализа")

@router.get("/triggers-enhanced")
async def get_triggers_enhanced(
    player_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    severity_level: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    enable_ai_analysis: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение триггеров с evidence (детали матчей) и опциональным AI-анализом
    
    Расширенный эндпоинт который возвращает триггеры вместе с доказательствами
    из матчей (evidence) включая детали по сетам.
    """
    logger.info(f"📊 Получение расширенных триггеров: player_id={player_id}, type={trigger_type}, AI={enable_ai_analysis}")
    
    try:
        query = db.query(PlayerTrigger).join(Player)
        
        if player_id:
            query = query.filter(PlayerTrigger.player_id == player_id)
        
        if trigger_type:
            query = query.filter(PlayerTrigger.trigger_type == trigger_type)
            
        if severity_level:
            query = query.filter(PlayerTrigger.severity_level == severity_level)
        
        # Фильтр по датам если указаны
        if start_date:
            query = query.filter(PlayerTrigger.period_start >= start_date)
        if end_date:
            query = query.filter(PlayerTrigger.period_end <= end_date)
        
        triggers = query.order_by(PlayerTrigger.created_at.desc()).limit(limit).all()
        
        service = MatchAnalysisService(db)
        result = []
        
        for trigger in triggers:
            player = db.query(Player).filter(Player.id == trigger.player_id).first()
            if not player:
                continue
            
            # Получаем матчи игрока за период триггера
            matches = db.query(Match).filter(
                and_(
                    Match.date >= trigger.period_start,
                    Match.date <= trigger.period_end,
                    or_(Match.player1_id == player.id, Match.player2_id == player.id)
                )
            ).order_by(Match.date.desc()).all()
            
            # Извлекаем evidence для триггера
            trigger_evidence = service._extract_trigger_evidence(
                player,
                trigger.trigger_type,
                matches
            )
            
            # Получаем статистику игрока
            player_stats = service._get_player_stats_for_trigger(
                trigger.player_id,
                trigger.period_start,
                trigger.period_end
            )
            
            # Опционально генерируем AI-анализ
            ai_analysis = None
            if enable_ai_analysis:
                ai_analysis = await service._generate_ai_analysis(
                    player.full_name,
                    trigger.trigger_value,
                    player_stats or {},
                    provider="lmstudio"
                )
            
            trigger_dict = {
                'id': trigger.id,
                'player_id': trigger.player_id,
                'player_name': player.full_name,
                'player_rating': player.current_rating,
                'trigger_type': trigger.trigger_type,
                'trigger_subtype': trigger.trigger_subtype,
                'trigger_value': trigger.trigger_value,
                'severity_level': trigger.severity_level,
                'period_start': trigger.period_start,
                'period_end': trigger.period_end,
                # 'is_active': trigger.is_active,
                'is_pair': trigger.is_pair,
                'trigger_metadata': trigger.trigger_metadata,
                'created_at': trigger.created_at,
                'player_stats': player_stats,
                'evidence': trigger_evidence,  # Доказательства с сетами
                'ai_analysis': ai_analysis
            }
            result.append(trigger_dict)
        
        logger.info(f"✅ Найдено триггеров с evidence: {len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении расширенных триггеров: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@router.get("/triggers")
async def get_all_triggers(
    player_id: Optional[str] = None,
    trigger_type: Optional[str] = None,
    severity_level: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Получение списка всех триггеров с фильтрацией (базовая версия без evidence)
    
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
                # 'is_active': trigger.is_active,
                'is_pair': trigger.is_pair,
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


@router.get("/dashboard-stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Получить статистику для дашборда:
    - Количество игроков в базе
    - Количество матчей
    - Количество активных триггеров
    - Количество загрузок за последнюю неделю
    """
    try:
        from datetime import datetime, timedelta
        
        # Общее количество игроков
        total_players = db.query(Player).count()
        
        # Общее количество матчей
        total_matches = db.query(Match).count()
        
        # # Количество активных триггеров
        # active_triggers = db.query(PlayerTrigger).filter(
        #     PlayerTrigger.is_active == True
        # ).count()
        
        # Количество загрузок за последнюю неделю (матчи созданные за последние 7 дней)
        week_ago = datetime.now() - timedelta(days=7)
        recent_uploads = db.query(Match).filter(
            Match.created_at >= week_ago
        ).count()
        
        return {
            "total_players": total_players,
            "total_matches": total_matches,
            # "active_triggers": active_triggers,
            "recent_uploads": recent_uploads
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения статистики дашборда: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка получения статистики: {str(e)}")


# @router.get("/h2h/{player1_id}/{player2_id}")
# async def get_h2h_analysis(
#     player1_id: str,
#     player2_id: str,
#     match_date: Optional[str] = None,
#     db: Session = Depends(get_db)
# ):
#     try:
#         from datetime import datetime
#         from app.models.match import MatchSet
        
#         player1 = db.query(Player).filter(Player.id == player1_id).first()
#         player2 = db.query(Player).filter(Player.id == player2_id).first()
        
#         if not player1 or not player2:
#             raise HTTPException(status_code=404, detail="Один или оба игрока не найдены")
        
#         query = db.query(Match).filter(
#             or_(
#                 and_(Match.player1_id == player1_id, Match.player2_id == player2_id),
#                 and_(Match.player1_id == player2_id, Match.player2_id == player1_id)
#             )
#         )
        
#         if match_date:
#             try:
#                 target_date = datetime.strptime(match_date, "%Y-%m-%d").date()
#                 query = query.filter(Match.date == target_date)
#             except ValueError:
#                 raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
#         matches = query.order_by(Match.date.desc()).all()
        
#         if not matches:
#             return {
#                 "player1": {
#                     "id": player1.id,
#                     "full_name": player1.full_name,
#                     "current_rating": player1.current_rating,
#                     "triggers": []
#                 },
#                 "player2": {
#                     "id": player2.id,
#                     "full_name": player2.full_name,
#                     "current_rating": player2.current_rating,
#                     "triggers": []
#                 },
#                 "matches": [],
#                 "ai_analysis": "Матчи между этими игроками не найдены"
#             }
        
#         matches_data = []
#         for match in matches:
#             sets = db.query(MatchSet).filter(
#                 MatchSet.match_id == match.id
#             ).order_by(MatchSet.set_number).all()
            
#             is_player1_first = match.player1_id == player1_id
            
#             match_triggers_p1 = db.query(PlayerTrigger).filter(
#                 PlayerTrigger.player_id == player1_id,
#                 PlayerTrigger.match_id == match.id
#             ).all()
            
#             match_triggers_p2 = db.query(PlayerTrigger).filter(
#                 PlayerTrigger.player_id == player2_id,
#                 PlayerTrigger.match_id == match.id
#             ).all()
            
#             sets_details = []
#             for s in sets:
#                 sets_details.append({
#                     "set_number": s.set_number,
#                     "player1_points": s.player1_points if is_player1_first else s.player2_points,
#                     "player2_points": s.player2_points if is_player1_first else s.player1_points
#                 })
            
#             winner_id = match.winner_id
#             match_data = {
#                 "id": match.id,
#                 "date": match.date.isoformat(),
#                 "score": match.score,
#                 "stage": match.stage,
#                 "league_id": match.league_id,
#                 "winner_id": winner_id,
#                 "sets": sets_details,
#                 "player1_triggers": [{"type": t.trigger_type, "severity": t.severity_level} for t in match_triggers_p1],
#                 "player2_triggers": [{"type": t.trigger_type, "severity": t.severity_level} for t in match_triggers_p2],
#                 "serve_efficiency_p1": match.serve_efficiency_p1 if is_player1_first else match.serve_efficiency_p2,
#                 "receive_efficiency_p1": match.receive_efficiency_p1 if is_player1_first else match.receive_efficiency_p2,
#                 "serve_efficiency_p2": match.serve_efficiency_p2 if is_player1_first else match.serve_efficiency_p1,
#                 "receive_efficiency_p2": match.receive_efficiency_p2 if is_player1_first else match.receive_efficiency_p1
#             }
#             matches_data.append(match_data)
        
#         # Получаем ID всех матчей между игроками
#         match_ids = [m.id for m in matches]

#         # Фильтруем триггеры для player1 только внутри этих матчей
#         player1_triggers = db.query(PlayerTrigger).filter(
#             PlayerTrigger.player_id == player1_id,
#             PlayerTrigger.match_id.in_(match_ids),
#             PlayerTrigger.is_active == True
#         ).all()

#         # Фильтруем триггеры для player2 только внутри этих матчей
#         player2_triggers = db.query(PlayerTrigger).filter(
#             PlayerTrigger.player_id == player2_id,
#             PlayerTrigger.match_id.in_(match_ids),
#             PlayerTrigger.is_active == True
#         ).all()

        
#         player1_wins = sum(1 for m in matches if m.winner_id == player1_id)
#         player2_wins = sum(1 for m in matches if m.winner_id == player2_id)
        
#         ai_analysis = f"Анализ {len(matches)} матч{'а' if len(matches) < 5 else 'ей'} между {player1.full_name} и {player2.full_name}. "
#         ai_analysis += f"Счёт встреч: {player1_wins}:{player2_wins}. "
        
#         if player1_wins > player2_wins:
#             ai_analysis += f"{player1.full_name} доминирует в личных встречах. "
#         elif player2_wins > player1_wins:
#             ai_analysis += f"{player2.full_name} доминирует в личных встречах. "
#         else:
#             ai_analysis += "Равное противостояние. "
        
#         return {
#             "player1": {
#                 "id": player1.id,
#                 "full_name": player1.full_name,
#                 "current_rating": player1.current_rating,
#                 "triggers": [{"type": t.trigger_type, "severity": t.severity_level} for t in player1_triggers]
#             },
#             "player2": {
#                 "id": player2.id,
#                 "full_name": player2.full_name,
#                 "current_rating": player2.current_rating,
#                 "triggers": [{"type": t.trigger_type, "severity": t.severity_level} for t in player2_triggers]
#             },
#             "matches": matches_data,
#             "ai_analysis": ai_analysis.strip()
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Ошибка H2H анализа: {str(e)}")
#         raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@router.get("/h2h/{player1_id}/{player2_id}")
async def get_h2h_analysis(
    player1_id: str,
    player2_id: str,
    match_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:


        # Загружаем игроков
        player1 = db.query(Player).filter(Player.id == player1_id).first()
        player2 = db.query(Player).filter(Player.id == player2_id).first()
        print("Loaded players:", player1, player2)

        if not player1 or not player2:
            raise HTTPException(status_code=404, detail="Один или оба игрока не найдены")

        # Загружаем матчи, как раньше
        query = db.query(Match).filter(
            or_(
                and_(Match.player1_id == player1_id, Match.player2_id == player2_id),
                and_(Match.player1_id == player2_id, Match.player2_id == player1_id)
            )
        )



        target_date = None
        if match_date:
            try:
                target_date = datetime.strptime(match_date, "%Y-%m-%d").date()
                query = query.filter(Match.date == target_date)
                print("Filtered by date:", target_date)
            except:
                raise HTTPException(status_code=400, detail="Неверный формат даты")

        matches = query.order_by(Match.date.desc()).all()

        # Получаем НОВЫЕ H2H триггеры
        service = H2HAnalysisService(db)
        h2h_p1, h2h_p2, _ = service.analyze_h2h(player1_id, player2_id, target_date)
        # print("H2H triggers:", h2h_p1, h2h_p2)
        # print("!!!!!!!!!!!!!!!!!P1 triggers JSON:!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # print(json.dumps(jsonable_encoder(h2h_p1), indent=4, ensure_ascii=False))

        # print("P2 triggers JSON:")
        # print(json.dumps([t.to_dict() for t in h2h_p2], indent=4, ensure_ascii=False))

        # Если матчей нет — возвращаем пустой стандартный формат
        if not matches:
            return {
                "player1": {
                    "id": player1.id,
                    "full_name": player1.full_name,
                    "current_rating": player1.current_rating,
                    "triggers": [
                        {"type": t.trigger_type, "trigger_value": t.trigger_value, "severity": t.severity_level}
                        for t in h2h_p1
                    ]
                },
                "player2": {
                    "id": player2.id,
                    "full_name": player2.full_name,
                    "current_rating": player2.current_rating,
                    "triggers": [
                        {"type": t.trigger_type, "trigger_value": t.trigger_value, "severity": t.severity_level}
                        for t in h2h_p2
                    ]
                },
                "matches": [],
                "ai_analysis": "Матчи между этими игроками не найдены"
            }

        # Формируем matches, как раньше
        matches_data = []
        for match in matches:
            sets = db.query(MatchSet).filter(
                MatchSet.match_id == match.id
            ).order_by(MatchSet.set_number).all()

            is_p1_first = match.player1_id == player1_id

            sets_block = []
            for s in sets:
                sets_block.append({
                    "set_number": s.set_number,
                    "player1_points": s.player1_points if is_p1_first else s.player2_points,
                    "player2_points": s.player2_points if is_p1_first else s.player1_points
                })

            matches_data.append({
                "id": match.id,
                "date": match.date.isoformat(),
                "score": match.score,
                "stage": match.stage,
                "league_id": match.league_id,
                "winner_id": match.winner_id,
                "sets": sets_block,
                "player1_triggers": [],   # ❗ старые match triggers полностью убираем
                "player2_triggers": [],   # ❗ старые match triggers полностью убираем
                "serve_efficiency_p1": match.serve_efficiency_p1 if is_p1_first else match.serve_efficiency_p2,
                "receive_efficiency_p1": match.receive_efficiency_p1 if is_p1_first else match.receive_efficiency_p2,
                "serve_efficiency_p2": match.serve_efficiency_p2 if is_p1_first else match.serve_efficiency_p1,
                "receive_efficiency_p2": match.receive_efficiency_p2 if is_p1_first else match.receive_efficiency_p1,
            })
            # print("📌 MATCHES DATA:")
            # print(json.dumps(matches_data, indent=4, ensure_ascii=False))

            

        # AI текст — как раньше
        player1_wins = sum(1 for m in matches if m.winner_id == player1_id)
        player2_wins = sum(1 for m in matches if m.winner_id == player2_id)

        ai_text = (
            f"Анализ {len(matches)} матчей между {player1.full_name} и {player2.full_name}. "
            f"Счёт встреч: {player1_wins}:{player2_wins}. "
        )

        if player1_wins > player2_wins:
            ai_text += f"{player1.full_name} доминирует."
        elif player2_wins > player1_wins:
            ai_text += f"{player2.full_name} доминирует."
        else:
            ai_text += "Равное противостояние."

        # # Возвращаем в старом формате, но triggers = ТОЛЬКО новые H2H
        # return {
        #     "player1": {
        #         "id": player1.id,
        #         "full_name": player1.full_name,
        #         "current_rating": player1.current_rating,
        #         "triggers": [
        #             {"type": t.trigger_type, "severity": t.severity_level}
        #             for t in h2h_p1
        #         ]
        #     },
        #     "player2": {
        #         "id": player2.id,
        #         "full_name": player2.full_name,
        #         "current_rating": player2.current_rating,
        #         "triggers": [
        #             {"type": t.trigger_type, "severity": t.severity_level}
        #             for t in h2h_p2
        #         ]
        #     },
        #     "matches": matches_data,
        #     "ai_analysis": ai_text
        # }
        response_data = {
            "player1": {
                "id": player1.id,
                "full_name": player1.full_name,
                "current_rating": player1.current_rating,
                "triggers": [
                    {"type": t.trigger_type, "trigger_value": t.trigger_value, "severity": t.severity_level}
                    for t in h2h_p1
                ]
            },
            "player2": {
                "id": player2.id,
                "full_name": player2.full_name,
                "current_rating": player2.current_rating,
                "triggers": [
                    {"type": t.trigger_type, "trigger_value": t.trigger_value, "severity": t.severity_level}
                    for t in h2h_p2
                ]
            },
            "matches": matches_data,
            "ai_analysis": ai_text
        }
        response_data1 = {
            "player1": {
                "id": player1.id,
                "full_name": player1.full_name,
                "current_rating": player1.current_rating,
                "triggers": [
                    {"type": t.trigger_type, "trigger_value": t.trigger_value, "severity": t.severity_level}
                    for t in h2h_p1
                ]
            },
            "player2": {
                "id": player2.id,
                "full_name": player2.full_name,
                "current_rating": player2.current_rating,
                "triggers": [
                    {"type": t.trigger_type, "trigger_value": t.trigger_value, "severity": t.severity_level}
                    for t in h2h_p2
                ]
            },
            "ai_analysis": ai_text
        }

        # 👍 Делаем КОПИЮ в jsonable_encoder — оригинал не трогаем!
        encoded = jsonable_encoder(response_data1)

        print("📌 FINAL RESPONSE JSON:")
        print(json.dumps(encoded, indent=4, ensure_ascii=False))

        # ❗ Возвращаем ровно то, что ждет фронт
        return response_data
    

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/h2h-by-date/{date}")
async def get_h2h_by_date(
    date: str,
    db: Session = Depends(get_db)
):
    try:
        from datetime import datetime
        from app.models.match import MatchSet
        from collections import defaultdict
        
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
        matches = db.query(Match).filter(Match.date == target_date).all()
        
        if not matches:
            return {
                "date": date,
                "pairs": [],
                "total_matches": 0
            }
        
        pairs_dict = defaultdict(lambda: {
            "player1": None,
            "player2": None,
            "matches": [],
            "player1_wins": 0,
            "player2_wins": 0
        })
        
        for match in matches:
            player1 = db.query(Player).filter(Player.id == match.player1_id).first()
            player2 = db.query(Player).filter(Player.id == match.player2_id).first()
            
            if not player1 or not player2:
                continue
            
            pair_key = tuple(sorted([match.player1_id, match.player2_id]))
            
            if pairs_dict[pair_key]["player1"] is None:
                if pair_key[0] == match.player1_id:
                    pairs_dict[pair_key]["player1"] = player1
                    pairs_dict[pair_key]["player2"] = player2
                else:
                    pairs_dict[pair_key]["player1"] = player2
                    pairs_dict[pair_key]["player2"] = player1
            
            sets = db.query(MatchSet).filter(
                MatchSet.match_id == match.id
            ).order_by(MatchSet.set_number).all()
            
            match_triggers_p1 = db.query(PlayerTrigger).filter(
                PlayerTrigger.player_id == match.player1_id,
                PlayerTrigger.match_id == match.id
            ).all()
            
            match_triggers_p2 = db.query(PlayerTrigger).filter(
                PlayerTrigger.player_id == match.player2_id,
                PlayerTrigger.match_id == match.id
            ).all()
            
            is_player1_first = pair_key[0] == match.player1_id
            
            sets_details = []
            for s in sets:
                sets_details.append({
                    "set_number": s.set_number,
                    "player1_points": s.player1_points if is_player1_first else s.player2_points,
                    "player2_points": s.player2_points if is_player1_first else s.player1_points
                })
            
            match_data = {
                "id": match.id,
                "score": match.score,
                "stage": match.stage,
                "winner_id": match.winner_id,
                "sets": sets_details,
                "player1_triggers": [{"type": t.trigger_type, "severity": t.severity_level} for t in (match_triggers_p1 if is_player1_first else match_triggers_p2)],
                "player2_triggers": [{"type": t.trigger_type, "severity": t.severity_level} for t in (match_triggers_p2 if is_player1_first else match_triggers_p1)]
            }
            
            pairs_dict[pair_key]["matches"].append(match_data)
            
            if match.winner_id == pairs_dict[pair_key]["player1"].id:
                pairs_dict[pair_key]["player1_wins"] += 1
            elif match.winner_id == pairs_dict[pair_key]["player2"].id:
                pairs_dict[pair_key]["player2_wins"] += 1
        
        pairs_result = []
        for pair_key, pair_data in pairs_dict.items():
            if pair_data["player1"] is None or pair_data["player2"] is None:
                continue
                
            pairs_result.append({
                "player1": {
                    "id": pair_data["player1"].id,
                    "full_name": pair_data["player1"].full_name,
                    "current_rating": pair_data["player1"].current_rating
                },
                "player2": {
                    "id": pair_data["player2"].id,
                    "full_name": pair_data["player2"].full_name,
                    "current_rating": pair_data["player2"].current_rating
                },
                "matches": pair_data["matches"],
                "player1_wins": pair_data["player1_wins"],
                "player2_wins": pair_data["player2_wins"],
                "total_matches": len(pair_data["matches"])
            })
        
        return {
            "date": date,
            "pairs": pairs_result,
            "total_matches": len(matches)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка анализа по дате: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(e)}")

@router.get("/h2h/{player1_id}/{player2_id}/{trigger_type}")
async def get_h2h_trigger_details(
    player1_id: str,
    player2_id: str,
    trigger_type: str,
    db: Session = Depends(get_db)
):
    try:


        # ─────────────────────────────
        # 1. Проверяем игроков
        # ─────────────────────────────
        player1 = db.query(Player).filter(Player.id == player1_id).first()
        player2 = db.query(Player).filter(Player.id == player2_id).first()

        if not player1 or not player2:
            raise HTTPException(status_code=404, detail="Игрок не найден")

        # ─────────────────────────────
        # 2. Достаём триггер
        # ─────────────────────────────
        trigger = db.query(PlayerTrigger).filter(
            PlayerTrigger.player_id == player1_id,
            PlayerTrigger.trigger_type == trigger_type
        ).first()

        if not trigger:
            raise HTTPException(status_code=404, detail="Триггер не найден")

        # ─────────────────────────────
        # 3. Парсим trigger_metadata
        # ─────────────────────────────
        metadata = trigger.trigger_metadata

        while isinstance(metadata, str):
            metadata = json.loads(metadata)


        if metadata.get("opponent_id") != player2_id:
            raise HTTPException(status_code=404, detail="Триггер не относится к этому сопернику")

        match_ids = metadata.get("match_ids", [])
        if not match_ids:
            return {
                "ai_analysis": "Недостаточно данных для анализа",
                "trigger": {
                    "trigger_type": trigger.trigger_type,
                    "trigger_subtype": trigger.trigger_subtype,
                    "trigger_value": trigger.trigger_value,
                    "severity_level": trigger.severity_level
                },
                "matches": []
            }

        # ─────────────────────────────
        # 4. Загружаем матчи
        # ─────────────────────────────
        matches = db.query(Match).filter(
            Match.id.in_(match_ids)
        ).order_by(Match.date.desc()).all()

        matches_data = []

        for match in matches:
            sets = db.query(MatchSet).filter(
                MatchSet.match_id == match.id
            ).order_by(MatchSet.set_number).all()

            is_p1_first = match.player1_id == player1_id

            sets_block = [
                {
                    "set_number": s.set_number,
                    "player1_points": s.player1_points if is_p1_first else s.player2_points,
                    "player2_points": s.player2_points if is_p1_first else s.player1_points
                }
                for s in sets
            ]

            # Корректируем score если порядок игроков в матче отличается от запроса
            original_score = match.score
            if not is_p1_first and ":" in original_score:
                parts = original_score.split(":")
                corrected_score = f"{parts[1]}:{parts[0]}"
            else:
                corrected_score = original_score

            matches_data.append({
                "id": match.id,
                "date": match.date.isoformat() if match.date else None,
                "score": corrected_score,
                "winner_id": match.winner_id,
                "player1_id": player1_id,
                "player2_id": player2_id,

                "rating1": player1.current_rating,
                "rating2": player2.current_rating,

                "league1": match.league_id,
                "league2": match.league_id,

                "sets": sets_block
            })


        # ─────────────────────────────
        # 5. Ответ
        # ─────────────────────────────
        return {
            "ai_analysis": (
                f"Анализ противостояния {player1.full_name} против "
                f"{player2.full_name} по триггеру '{trigger_type}'. "
                "ИИ-анализ будет добавлен позже."
            ),
            "trigger": {
                "trigger_type": trigger.trigger_type,
                "trigger_subtype": trigger.trigger_subtype,
                "trigger_value": trigger.trigger_value,
                "severity_level": trigger.severity_level
            },
            "matches": matches_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
