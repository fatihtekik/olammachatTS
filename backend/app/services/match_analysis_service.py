from typing import List, Optional, Dict, Any, Set
from datetime import datetime, date, time, timedelta
import asyncio
import re
import os
import httpx
import json
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
from langchain.sport import search, load_data
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Настройка логирования матчей в файл
MATCH_ANALYSIS_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "analysis_logs")
os.makedirs(MATCH_ANALYSIS_LOG_DIR, exist_ok=True)

def log_match_analysis(message: str):
    """Записывает сообщение в лог файл анализа матчей"""
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(MATCH_ANALYSIS_LOG_DIR, f"match_analysis_{timestamp}.txt")
    
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{message}\n")
    except Exception as e:
        logger.error(f"Ошибка записи в лог: {e}")

class MatchAnalysisService:
    """Сервис для анализа матчей и выявления триггеров"""
    
    def __init__(self, db: Session):
        self.db = db
        self.last_uploaded_player_ids = []  # Инстансовый список ID игроков из последнего загруженного файла
        self._found_duplicates = []  # Список найденных дубликатов для вывода в конце

        # Настройки AI анализа
        self._ai_analysis_enabled = True  # Флаг для включения/выключения ИИ
        self._selected_model = None  # Выбранная модель
        self._max_tokens = 2000  # Лимит токенов

        # === КЕШИ для предзагрузки (заполняются в analyze_triggers) ===
        self._players_cache: Dict[Any, Player] = {}       # player_id -> Player
        self._matches_cache: List[Match] = []              # все матчи за период
        self._matches_by_player: Dict[Any, List[Match]] = {}  # player_id -> [Match]
        self._sets_by_match: Dict[Any, List[MatchSet]] = {}   # match_id -> [MatchSet] (отсортированные)
        self._holidays_cache: List[Holiday] = []           # все праздники

        self.trigger_methods = {
            "top_performers": self._analyze_top_performers, 
            "losers_50_percent": self._analyze_losers_50_percent,
            "endgame_problems": self._analyze_endgame_problems, #еще нет
            "lead_4_lost": self._analyze_lead_4_lost, #еще нет
            "balance_problems": self._analyze_balance_problems, #еще нет
            # "led_2_sets_lost": self._analyze_led_2_sets_lost,
            # "led_1_set_lost": self._analyze_led_1_set_lost,
            "early_final_exit": self._analyze_early_final_exit, #еще нет
            "league_promotion_failed": self._analyze_league_promotion_failed, #еще нет
            "won_2_lost_3rd": self._analyze_won_2_lost_3rd, #еще нет
            "close_score_losses": self._analyze_close_score_losses, #еще нет
            "post_holiday_problems": self._analyze_post_holiday_problems,
            "time_performance": self._analyze_time_performance,
            "shutout_losses": self._analyze_shutout_losses, #еще нет
            "losing_streaks": self._analyze_losing_streaks,
            "weaker_opponent_losses": self._analyze_weaker_opponent_losses, #еще нет
            "long_match_losses": self._analyze_long_match_losses, #еще нет
            "higher_league_struggles": self._analyze_higher_league_struggles, #еще нет
            "reception_problems": self._analyze_reception_problems, #еще нет
            "defeat_0_3": self._analyze_defeat_0_3,
            "won_2_lost_3rd_set": self._analyze_won_2_lost_3rd_set,
            "early_final_exit_advanced": self._analyze_early_final_exit_advanced,
            "led_1_set_lost_match": self._analyze_led_1_set_lost_match,
            "led_2_sets_lost_match": self._analyze_led_2_sets_lost_match,
            "psychological_breakdown": self._analyze_psychological_breakdown,
            "comeback_inability": self._analyze_comeback_inability,
            "pressure_situations": self._analyze_pressure_situations
        }
    
    async def process_excel_data(self, excel_data: List[ExcelMatchData]) -> Dict[str, Any]: #РАБОТАЕТ
        """Обрабатывает данные из Excel файла"""
        try:
            created_players = 0
            created_matches = 0
            skipped_duplicates = 0
            errors = []
            file_player_ids = set()  # Отслеживаем ID игроков из этого файла
            self._found_duplicates = []  # Очищаем список дубликатов перед новой загрузкой
            
            print(f"🔄 Начинаем обработку {len(excel_data)} строк из Excel...")
            
            for idx, match_data in enumerate(excel_data):
                try:
                    msg = f"📝 Обрабатываем строку {idx + 1}: {match_data.игрок_1} vs {match_data.игрок_2}"
                    print(msg)
                    log_match_analysis(msg)
                    
                    # Получаем или создаем игроков
                    # Обрабатываем игроков с рейтингами
                    player1, player1_created = await self._get_or_create_player(match_data.игрок_1, match_data.рейтинг_игрок_1)
                    player2, player2_created = await self._get_or_create_player(match_data.игрок_2, match_data.рейтинг_игрок_2)
                    
                    # Добавляем игроков в список из файла
                    file_player_ids.add(player1.id)
                    file_player_ids.add(player2.id)
                    
                    # Увеличиваем счетчик созданных игроков
                    if player1_created:
                        created_players += 1
                    if player2_created:
                        created_players += 1
                    
                    if player1.id == player2.id:
                        logger.warning(f"⚠️  Пропускаем матч: один и тот же игрок")
                        continue  # Пропускаем если это один игрок
                    
                    # Парсим дату для проверки дубликата
                    match_date = self._parse_date(match_data.дата)
                    
                    # Получаем SL-ID и Part iD для проверки дубликатов
                    sl_id = match_data.sl_id if hasattr(match_data, 'sl_id') else None
                    part_id = getattr(match_data, 'part_id', None)  # Пока нет в схеме
                    
                    # Проверяем, не существует ли уже такой матч (приоритет по SL-ID)
                    is_duplicate, duplicate_info = self._match_exists(
                        sl_id=sl_id,
                        part_id=part_id,
                        date=match_date, 
                        player1_id=player1.id, 
                        player2_id=player2.id, 
                        score=match_data.счёт, 
                        time_str=match_data.время
                    )
                    if is_duplicate:
                        skipped_duplicates += 1
                        # Сохраняем информацию о дубликате
                        self._found_duplicates.append({
                            "sl_id": sl_id,
                            "player1": match_data.игрок_1,
                            "player2": match_data.игрок_2,
                            "date": str(match_date),
                            "score": match_data.счёт,
                            "reason": duplicate_info
                        })
                        msg = f"⏭️  Пропускаем дубликат: {match_data.игрок_1} vs {match_data.игрок_2} от {match_date}"
                        print(msg)
                        log_match_analysis(msg)
                        continue
                    
                    # Создаем матч
                    match = await self._create_match_from_excel(match_data, player1, player2)
                    created_matches += 1
                    msg = f"✅ Создан матч: {match_data.игрок_1} vs {match_data.игрок_2}"
                    print(msg)
                    log_match_analysis(msg)
                    
                except Exception as e:
                    error_msg = f"Строка {idx + 1}: Ошибка при обработке матча {match_data.игрок_1} vs {match_data.игрок_2}: {str(e)}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
            # Сохраняем список игроков из этого файла (в рамках текущего объекта)
            self.last_uploaded_player_ids = list(file_player_ids)
            print(f"💾 Сохранен список из {len(file_player_ids)} игроков из загруженного файла")

            result = {
                "created_players": created_players,
                "created_matches": created_matches,
                "skipped_duplicates": skipped_duplicates,
                "total_processed": len(excel_data),
                "file_player_ids": list(file_player_ids),  # Возвращаем список ID игроков из файла
                "errors": errors,
                "success": True
            }

            print(f"📊 Результат обработки:")
            print(f"  - Всего строк: {len(excel_data)}")
            print(f"  - Создано матчей: {created_matches}")
            print(f"  - Пропущено дубликатов: {skipped_duplicates}")
            print(f"  - Игроков в файле: {len(file_player_ids)}")
            print(f"  - Ошибок: {len(errors)}")
            
            # Выводим детальную информацию о дубликатах
            if self._found_duplicates:
                print(f"\n{'='*60}")
                print(f"📋 СПИСОК НАЙДЕННЫХ ДУБЛИКАТОВ ({len(self._found_duplicates)} шт.):")
                print(f"{'='*60}")
                for i, dup in enumerate(self._found_duplicates, 1):
                    print(f"  {i}. SL-ID: {dup['sl_id'] or 'N/A'}")
                    print(f"     Матч: {dup['player1']} vs {dup['player2']}")
                    print(f"     Дата: {dup['date']}, Счёт: {dup['score']}")
                    print(f"     Причина: {dup['reason']}")
                    print(f"     {'-'*40}")
                print(f"{'='*60}\n")
            
            # Добавляем информацию о дубликатах в результат
            result["duplicates_details"] = self._found_duplicates

            return result
            
        except Exception as e:
            print(f"💥 Ошибка при обработке Excel данных: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_or_create_player(self, player_name: str, rating_str: Optional[str] = None) -> tuple[Player, bool]: #РАБОТАЕТ
        """Получает существующего игрока или создает нового с рейтингом"""
        # Извлекаем рейтинг из отдельного поля или из имени игрока
        rating = 1000  # значение по умолчанию
        
        # Сначала пробуем получить рейтинг из отдельного поля
        if rating_str:
            try:
                cleaned = rating_str.replace(',', '.').strip()
                rating_float = float(cleaned)
                rating = int(round(rating_float))  # Округляем до ближайшего
                msg = f"📊 Рейтинг из поля: {rating_str} -> {rating}"
                print(msg)
                log_match_analysis(msg)
            except (ValueError, AttributeError):
                logger.warning(f"Не удалось извлечь рейтинг из поля рейтинга: {rating_str}")
        
        # Если не получилось, пробуем извлечь из имени (для обратной совместимости)
        if rating == 1000:  # Только если не получили рейтинг из поля
            name_parts = player_name.split('rating:')
            if len(name_parts) > 1:
                try:
                    rating_from_name = float(name_parts[1].strip())
                    rating = int(rating_from_name)  # Округляем до целого
                    player_name = name_parts[0].strip()  # Очищаем имя от рейтинга
                    print(f"📊 Рейтинг из имени: {rating_from_name} -> {rating} для игрока {player_name}")
                except ValueError:
                    logger.warning(f"Не удалось извлечь рейтинг из имени игрока: {player_name}")

        player = self.db.query(Player).filter(Player.full_name == player_name).first()
        
        if not player:
            player = Player(full_name=player_name, current_rating=rating)
            self.db.add(player)
            self.db.commit()
            self.db.refresh(player)
            
            # Создаем начальную статистику
            stats = PlayerStats(player_id=player.id)
            self.db.add(stats)
            self.db.commit()
            
            logger.info(f"✅ Создан новый игрок: {player_name} с рейтингом {rating}")
            return player, True  # Игрок был создан
        else:
            # Обновляем рейтинг если:
            # 1) У игрока дефолт 1000, а новый рейтинг != 1000
            # 2) Рейтинг изменился более чем на 0 (любое отличие) и новый != 1000
            if rating != 1000 and (player.current_rating == 1000 or player.current_rating != rating):
                old_rating = player.current_rating
                player.current_rating = rating
                self.db.commit()
                logger.info(f"🔄 Обновлен рейтинг игрока {player_name}: {old_rating} -> {rating}")
        
        return player, False  # Игрок уже существовал
    


    def parse_time(self, value): #
        if not value or str(value).strip() in ["", "nan", "NaT"]:
            return None
        if isinstance(value, time):  # уже time
            return value
        try:
            return datetime.strptime(str(value), "%H:%M:%S").time()
        except ValueError:
            try:
                return datetime.strptime(str(value), "%H:%M").time()
            except ValueError:
                return None



    async def _create_match_from_excel(self, data: ExcelMatchData, player1: Player, player2: Player) -> Match:
        """
        Создает матч из данных Excel и, при наличии, сохраняет построчно результаты сетов в MatchSet.
        Теперь также сохраняет эффективность подачи/приёма для каждого игрока в матче и сетах.
        """

        # 1) Парсим дату и время
        match_date = self._parse_date(data.дата)
        time_parser = getattr(self, "parse_time", None)
        if callable(time_parser):
            match_time = time_parser(data.время)
        else:
            try:
                from datetime import datetime
                match_time = datetime.strptime(str(data.время), "%H:%M:%S").time() if data.время else None
            except Exception:
                match_time = None

        raw_score = str(data.счёт).strip() if data.счёт is not None else ""

        # 2) Регекс: извлечь общий счёт и содержимое скобок
        m = re.match(r'^\s*([0-9]+[\:\-][0-9]+)\s*(?:\((.*)\))?\s*$', raw_score)
        overall_part = None
        sets_part = None
        if m:
            overall_part = m.group(1)
            sets_part = m.group(2)
        else:
            overall_part = raw_score
            sets_part = None

        def parse_pair(s):
            s = s.strip()
            sep = ':' if ':' in s else '-'
            left, right = s.split(sep)
            return int(left), int(right)
        
        def safe_int(val):
            """Безопасное преобразование в int (поддерживает float строки типа '8.0')"""
            if val is None or str(val).strip() == '':
                return None
            try:
                # Сначала в float, потом в int - чтобы обработать "8.0"
                return int(float(val))
            except (ValueError, TypeError):
                return None

        # 3) Парсим детальные сеты из новых полей Excel или из sets_part
        per_set_scores = []
        
        # Сначала пытаемся получить счета из отдельных колонок
        for i in range(1, 6):  # Обрабатываем до 5 сетов
            p1_score_field = getattr(data, f'счёт_{i}_сета_игрок_1', None)
            p2_score_field = getattr(data, f'счёт_{i}_сета_игрок_2', None)
            
            p1_score = safe_int(p1_score_field)
            p2_score = safe_int(p2_score_field)
            
            # Логируем для отладки
            if p1_score is None or p2_score is None:
                if i <= 3:  # Первые 3 сета - это проблема
                    msg = f"   ⚠️ Сет {i}: p1={p1_score_field}, p2={p2_score_field} (не число)"
                    print(msg)
                    log_match_analysis(msg)
            
            if p1_score is not None and p2_score is not None:
                per_set_scores.append((p1_score, p2_score))
        
        if per_set_scores:
            msg = f"   🎾 Детальные сеты из колонок ({len(per_set_scores)}): {per_set_scores}"
            print(msg)
            log_match_analysis(msg)
        
        # Если не получили из колонок, пробуем из sets_part (старый метод)
        if not per_set_scores and sets_part:
            found = re.findall(r'(\d+\s*[-–—]\s*\d+)', sets_part)
            for token in found:
                token_clean = token.strip()
                parts = re.split(r'[-–—]', token_clean)
                try:
                    p1 = int(parts[0].strip())
                    p2 = int(parts[1].strip())
                    per_set_scores.append((p1, p2))
                except Exception:
                    continue
            if per_set_scores:
                msg = f"   🎾 Детальные сеты из sets_part: {per_set_scores}"
                print(msg)
                log_match_analysis(msg)

        # 4) Подсчитываем sets_player1/sets_player2 из детальных сетов
        sets_player1 = None
        sets_player2 = None
        
        # ПРИОРИТЕТ 1: Берём из raw_score (поле "Счёт" в экселе) - это ИСТОЧНИК ИСТИНЫ!
        if raw_score and ':' in raw_score:
            try:
                score_parts = raw_score.strip().split(':')
                sets_player1 = int(score_parts[0])
                sets_player2 = int(score_parts[1])
                msg = f"   📊 Счёт из поля Score (истина): {sets_player1}:{sets_player2}"
                print(msg)
                log_match_analysis(msg)
            except Exception as e:
                print(f"⚠️ Не удалось распарсить score '{raw_score}': {e}")
        
        # ПРИОРИТЕТ 2: Используем новые поля "Счет матча игрока 1/2" если нет raw_score
        if sets_player1 is None and hasattr(data, 'счет_матча_игрока_1') and data.счет_матча_игрока_1:
            s1 = safe_int(data.счет_матча_игрока_1)
            s2 = safe_int(data.счет_матча_игрока_2)
            if s1 is not None and s2 is not None:
                sets_player1 = s1
                sets_player2 = s2
                msg = f"   📊 Счёт из новых колонок: {sets_player1}:{sets_player2}"
                print(msg)
                log_match_analysis(msg)
        
        # ПРИОРИТЕТ 3: Подсчитываем из детальных сетов (последний вариант)
        if sets_player1 is None and per_set_scores:
            sets_player1 = sum(1 for p1, p2 in per_set_scores if p1 > p2)
            sets_player2 = sum(1 for p1, p2 in per_set_scores if p2 > p1)
            msg = f"   📊 Подсчет из детальных сетов: {sets_player1}:{sets_player2} (из {len(per_set_scores)} сетов)"
            print(msg)
            log_match_analysis(msg)

        # Если всё плохо, ставим 0:0
        if sets_player1 is None or sets_player2 is None:
            sets_player1, sets_player2 = 0, 0
            print(f"⚠️ Не удалось определить счёт, используем 0:0")

        # 5) Определяем победителя по сетам
        if sets_player1 > sets_player2:
            winner_id = player1.id
            msg = f"   🏆 Победитель: {player1.full_name} ({sets_player1}:{sets_player2})"
            print(msg)
            log_match_analysis(msg)
        elif sets_player2 > sets_player1:
            winner_id = player2.id
            msg = f"   🏆 Победитель: {player2.full_name} ({sets_player1}:{sets_player2})"
            print(msg)
            log_match_analysis(msg)
        else:
            winner_id = None
            print(f"   ⚠️ Ничья или счёт 0:0")

        # 6) Получаем/создаём лигу
        league = None
        if data.турнир:
            league = await self._get_or_create_league(data.турнир)

        # 7) Парсим эффективность подачи/приёма для матча
        serve_eff_p1 = safe_int(data.эффективность_подачи_игрока_1_в_матче)
        receive_eff_p1 = safe_int(data.эффективность_приёма_игрока_1_в_матче)
        serve_eff_p2 = safe_int(data.эффективность_подачи_игрока_2_в_матче)
        receive_eff_p2 = safe_int(data.эффективность_приёма_игрока_2_в_матче)
        
        # Парсим таймауты и карточки
        timeouts_p1 = safe_int(data.таймауты_игрок_1)
        timeouts_p2 = safe_int(data.таймауты_игрок_2)
        yellow_p1 = safe_int(data.жёлтые_карточки_игрок_1)
        yellow_p2 = safe_int(data.жёлтые_карточки_игрок_2)
        red_p1 = safe_int(data.красные_карточки_игрок_1)
        red_p2 = safe_int(data.красные_карточки_игрок_2)
        
        # Парсим баланс
        game_balance = safe_int(data.балансы_в_игре)

        # 8) Создаём объект Match с новыми полями
        match = Match(
            date=match_date,
            time=match_time,
            player1_id=player1.id,
            player2_id=player2.id,
            winner_id=winner_id,
            score=raw_score,
            sets_player1=sets_player1,
            sets_player2=sets_player2,
            stage=(data.стадия if data.стадия else None),
            league_id=league.id if league else None,
            match_sl_id=int(data.sl_id) if data.sl_id else None,
            is_final=(bool(data.стадия) and "финал" in str(data.стадия).lower()),
            is_semifinal=(bool(data.стадия) and "полуфинал" in str(data.стадия).lower()),
            
            # Новые поля эффективности
            serve_efficiency_p1=serve_eff_p1,
            receive_efficiency_p1=receive_eff_p1,
            serve_efficiency_p2=serve_eff_p2,
            receive_efficiency_p2=receive_eff_p2,
            
            # Время матча
            match_duration_formatted=data.время_матча,
            
            # Таймауты и карточки
            timeouts_p1=timeouts_p1,
            timeouts_p2=timeouts_p2,
            yellow_cards_p1=yellow_p1,
            yellow_cards_p2=yellow_p2,
            red_cards_p1=red_p1,
            red_cards_p2=red_p2,
            
            # Баланс
            game_balance=game_balance
        )

        # 9) Сохраняем матч + сеты (дубликаты уже проверены в process_excel_data)
        try:
            self.db.add(match)
            try:
                self.db.flush()
            except Exception:
                self.db.commit()
                self.db.refresh(match)

            # Сохраняем сеты с эффективностью
            if per_set_scores:
                    for i, (p1_pts, p2_pts) in enumerate(per_set_scores, start=1):
                        if p1_pts > p2_pts:
                            set_winner = player1.id
                        elif p2_pts > p1_pts:
                            set_winner = player2.id
                        else:
                            set_winner = None

                        # Получаем эффективность для конкретного сета
                        serve_eff_p1_set = safe_int(getattr(data, f'эффективность_подачи_игрока_1_в_{i}_сете', None))
                        receive_eff_p1_set = safe_int(getattr(data, f'эффективность_приёма_игрока_1_в_{i}_сете', None))
                        serve_eff_p2_set = safe_int(getattr(data, f'эффективность_подачи_игрока_2_в_{i}_сете', None))
                        receive_eff_p2_set = safe_int(getattr(data, f'эффективность_приёма_игрока_2_в_{i}_сете', None))
                        
                        # Время сета
                        set_time = getattr(data, f'время_{i}_сета', None)
                        
                        # Баланс сета
                        set_balance = safe_int(getattr(data, f'баланс_в_{i}_сете', None))

                        match_set = MatchSet(
                            match_id=match.id,
                            set_number=i,
                            player1_points=p1_pts,
                            player2_points=p2_pts,
                            winner_id=set_winner,
                            
                            # Эффективность в сете
                            serve_efficiency_p1=serve_eff_p1_set,
                            receive_efficiency_p1=receive_eff_p1_set,
                            serve_efficiency_p2=serve_eff_p2_set,
                            receive_efficiency_p2=receive_eff_p2_set,
                            
                            # Время сета
                            set_duration_formatted=set_time,
                            
                            # Баланс сета
                            set_balance=set_balance
                        )
                        self.db.add(match_set)

            self.db.commit()
            self.db.refresh(match)

        except SQLAlchemyError as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            print(f"❌ Ошибка при сохранении матча/сетов: {e}")
            raise

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
    
    async def analyze_triggers(self, request: AnalysisRequest) -> AnalysisResponse:  #Работает
            """Выполняет анализ триггеров для игроков (новая версия, игрок-ориентированная)"""
            logger.info("🔍 Начинаем анализ триггеров...")

            # Устанавливаем настройки AI из запроса
            self._ai_analysis_enabled = getattr(request, 'ai_analysis_enabled', True)
            self._selected_model = getattr(request, 'selected_model', None)
            self._max_tokens = getattr(request, 'max_tokens', 2000)
            
            print(f"🤖 AI анализ: {'ВКЛЮЧЕН' if self._ai_analysis_enabled else 'ВЫКЛЮЧЕН'}")
            if self._ai_analysis_enabled:
                print(f"   📦 Модель: {self._selected_model or 'по умолчанию'}")
                print(f"   🎯 Max токенов: {self._max_tokens}")

            # Определяем период анализа
            end_date = request.period_end or date.today()
            start_date = request.period_start or (end_date - timedelta(days=90))
            

            print(f"📅 Период анализа: {start_date} - {end_date}")

            # Очищаем старые триггеры
            deleted_count = self.db.query(PlayerTrigger).filter(
                and_(
                    PlayerTrigger.period_start == start_date,
                    PlayerTrigger.period_end == end_date
                )
            ).delete()
            print(f"🧹 Удалено старых триггеров: {deleted_count}")

            # Получаем игроков
            query = self.db.query(Player)
            if request.player_ids:
                query = query.filter(Player.id.in_(request.player_ids))
                print(f"👥 Анализируем указанных игроков: {len(request.player_ids)}")
            elif request.analyze_recent_upload_only and self.last_uploaded_player_ids:
                query = query.filter(Player.id.in_(self.last_uploaded_player_ids))
                print(f"👥 Анализ игроков только из последней загрузки: {len(self.last_uploaded_player_ids)}")

            players = query.all()
            print(f"👥 Найдено игроков для анализа: {len(players)}")

            if not players:
                return AnalysisResponse(
                    period_start=start_date,
                    period_end=end_date,
                    total_players=0,
                    total_matches=0,
                    triggers_found=0,
                    top_performers=[],
                    problem_players=[],
                    triggers=[]
                )

            # ====================================================================
            # 🚀 ПРЕДЗАГРУЗКА ВСЕХ ДАННЫХ ОДНИМИ ЗАПРОСАМИ (вместо N+1)
            # ====================================================================
            print(f"🚀 Предзагрузка данных...")
            
            # 1) Все игроки — один запрос вместо сотен отдельных
            all_players = self.db.query(Player).all()
            self._players_cache = {p.id: p for p in all_players}
            print(f"   ✅ Игроки в кеше: {len(self._players_cache)}")
            
            # 2) Все матчи за период — один запрос
            self._matches_cache = self.db.query(Match).filter(
                and_(Match.date >= start_date, Match.date <= end_date)
            ).order_by(Match.date.desc()).all()
            print(f"   ✅ Матчи за период: {len(self._matches_cache)}")
            
            # 3) Группируем матчи по игрокам — без запросов к БД
            self._matches_by_player = {}
            for match in self._matches_cache:
                for pid in [match.player1_id, match.player2_id]:
                    self._matches_by_player.setdefault(pid, []).append(match)
            
            # 4) Все сеты за период — ОДИН запрос вместо запроса на каждый матч
            match_ids = [m.id for m in self._matches_cache]
            if match_ids:
                all_sets = self.db.query(MatchSet).filter(
                    MatchSet.match_id.in_(match_ids)
                ).order_by(MatchSet.match_id, MatchSet.set_number).all()
            else:
                all_sets = []
            
            self._sets_by_match = {}
            for s in all_sets:
                self._sets_by_match.setdefault(s.match_id, []).append(s)
            print(f"   ✅ Сеты в кеше: {len(all_sets)} (для {len(self._sets_by_match)} матчей)")
            
            # 5) Все праздники — один запрос
            self._holidays_cache = self.db.query(Holiday).filter(
                and_(
                    Holiday.end_date >= start_date - timedelta(days=30),
                    Holiday.start_date <= end_date + timedelta(days=10)
                )
            ).all()
            print(f"   ✅ Праздники в кеше: {len(self._holidays_cache)}")
            
            print(f"🚀 Предзагрузка завершена!")
            # ====================================================================

            total_triggers = 0
            all_triggers = []

            # Определяем триггеры для анализа
            trigger_types = request.trigger_types or list(self.trigger_methods.keys())
            print(f"🎯 Типы триггеров для анализа: {trigger_types}")

            # Идём по игрокам
            for player in players:
                player_matches = self._matches_by_player.get(player.id, [])
                print(f"\n🔎 Игрок {player.full_name} ({player.id}), матчей: {len(player_matches)}")

                for trigger_type in trigger_types:
                    if trigger_type in self.trigger_methods:
                        method = self.trigger_methods[trigger_type]
                        triggers = await method(player, player_matches, start_date, end_date)
                        print(f"   ✅ {trigger_type}: найдено {len(triggers)}")
                        all_triggers.extend(triggers)
                        total_triggers += len(triggers)

            # Собираем статистику — используем уже загруженные данные
            total_matches = len(self._matches_cache)
            top_performers = await self._get_top_performers(start_date, end_date)
            problem_players = await self._get_problem_players(start_date, end_date)
            
            # Передаём провайдер из request (если указан, иначе lmstudio)
            provider = getattr(request, 'ai_provider', 'lmstudio')
            triggers = await self._get_all_triggers(start_date, end_date, provider=provider)

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

            print("\n🎉 АНАЛИЗ ЗАВЕРШЁН")
            print(f"🏃 Игроков: {len(players)} | ⚽ Матчей: {total_matches} | 🎯 Триггеров: {total_triggers}")
            return response
            

    
    def _count_matches_in_period(self, start_date: date, end_date: date) -> int:
        """Подсчитывает количество матчей в периоде"""
        return self.db.query(Match).filter(
            and_(Match.date >= start_date, Match.date <= end_date)
        ).count()
    
    async def _get_top_performers(self, start_date: date, end_date: date) -> List[dict]:
        """Получает топ игроков по результативности (оптимизировано — 0 запросов к БД)"""
        top_performers = []
        player_stats = []
        
        # Используем кеш вместо db.query(Player).all()
        for player_id, player in self._players_cache.items():
            # Используем кеш вместо db.query(Match) для каждого игрока
            matches = self._matches_by_player.get(player_id, [])
            
            if len(matches) >= 3:
                wins = len([m for m in matches if m.winner_id == player.id])
                win_rate = (wins / len(matches)) * 100
                
                if win_rate >= 70:
                    player_stats.append({
                        'player': player,
                        'win_rate': win_rate,
                        'matches': len(matches),
                        'wins': wins,
                        'all_matches': matches  # сохраняем чтобы не запрашивать повторно
                    })
        
        player_stats.sort(key=lambda x: x['win_rate'], reverse=True)
        
        for idx, stat in enumerate(player_stats[:10]):
            losses = stat['matches'] - stat['wins']
            sets_won = 0
            sets_lost = 0
            recent_form = []
            
            # Берём из уже загруженных матчей, сортируем по дате desc
            sorted_matches = sorted(stat['all_matches'], key=lambda m: m.date, reverse=True)
            recent_matches = sorted_matches[:5]
            
            for match in recent_matches:
                if match.winner_id == stat['player'].id:
                    recent_form.append('W')
                else:
                    recent_form.append('L')
                
                if match.player1_id == stat['player'].id:
                    sets_won += match.sets_player1 or 0
                    sets_lost += match.sets_player2 or 0
                else:
                    sets_won += match.sets_player2 or 0
                    sets_lost += match.sets_player1 or 0
            
            player_dict = {
                'id': stat['player'].id,
                'full_name': stat['player'].full_name,
                'current_rating': stat['player'].current_rating,
                'rank': idx + 1,
                'matches_played': stat['matches'],
                'wins': stat['wins'],
                'losses': losses,
                'win_rate': round(stat['win_rate'], 1),
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'sets_ratio': round(sets_won / sets_lost, 2) if sets_lost > 0 else sets_won,
                'recent_form': ''.join(recent_form),
                'created_at': stat['player'].created_at,
                'updated_at': stat['player'].updated_at
            }
            top_performers.append(player_dict)
        
        return top_performers
    
    async def _get_problem_players(self, start_date: date, end_date: date) -> List[dict]:
        """Получает игроков с проблемами (оптимизировано — 1 запрос вместо N*3)"""
        problem_players = []
        player_stats = []
        
        # Используем кеш вместо db.query(Player).all()
        for player_id, player in self._players_cache.items():
            # Используем кеш вместо db.query(Match) для каждого игрока
            matches = self._matches_by_player.get(player_id, [])
            
            if len(matches) >= 3:
                wins = len([m for m in matches if m.winner_id == player.id])
                losses = len([m for m in matches if m.winner_id and m.winner_id != player.id])
                loss_rate = (losses / len(matches)) * 100
                
                if loss_rate >= 60:
                    player_stats.append({
                        'player': player,
                        'loss_rate': loss_rate,
                        'matches': len(matches),
                        'wins': wins,
                        'losses': losses,
                        'all_matches': matches
                    })
        
        player_stats.sort(key=lambda x: x['loss_rate'], reverse=True)
        
        # Один запрос на все триггеры вместо N отдельных count()
        trigger_counts = {}
        trigger_rows = self.db.query(
            PlayerTrigger.player_id, func.count(PlayerTrigger.id)
        ).filter(
            and_(
                PlayerTrigger.period_start == start_date,
                PlayerTrigger.period_end == end_date
            )
        ).group_by(PlayerTrigger.player_id).all()
        for pid, cnt in trigger_rows:
            trigger_counts[pid] = cnt
        
        for idx, stat in enumerate(player_stats[:10]):
            sets_won = 0
            sets_lost = 0
            recent_form = []
            current_streak = 0
            
            # Сортируем из кеша вместо отдельного запроса
            sorted_matches = sorted(stat['all_matches'], key=lambda m: m.date, reverse=True)
            
            for match in sorted_matches[:5]:
                if match.winner_id == stat['player'].id:
                    recent_form.append('W')
                else:
                    recent_form.append('L')
            
            for match in sorted_matches:
                if match.winner_id != stat['player'].id:
                    current_streak += 1
                else:
                    break
            
            for match in sorted_matches:
                if match.player1_id == stat['player'].id:
                    sets_won += match.sets_player1 or 0
                    sets_lost += match.sets_player2 or 0
                else:
                    sets_won += match.sets_player2 or 0
                    sets_lost += match.sets_player1 or 0
            
            # Используем предзагруженные trigger_counts
            triggers_count = trigger_counts.get(stat['player'].id, 0)
            
            player_dict = {
                'id': stat['player'].id,
                'full_name': stat['player'].full_name,
                'current_rating': stat['player'].current_rating,
                'rank': idx + 1,
                'matches_played': stat['matches'],
                'wins': stat['wins'],
                'losses': stat['losses'],
                'loss_rate': round(stat['loss_rate'], 1),
                'win_rate': round((stat['wins'] / stat['matches']) * 100, 1),
                'sets_won': sets_won,
                'sets_lost': sets_lost,
                'sets_ratio': round(sets_won / sets_lost, 2) if sets_lost > 0 else 0,
                'recent_form': ''.join(recent_form),
                'current_losing_streak': current_streak,
                'triggers_count': triggers_count,
                'created_at': stat['player'].created_at,
                'updated_at': stat['player'].updated_at
            }
            problem_players.append(player_dict)
        
        return problem_players
    
    async def _get_all_triggers(self, start_date: date, end_date: date, provider: str = "lmstudio") -> List[dict]:
        """
        Получает все триггеры за период (оптимизировано — 1 запрос вместо N*3).
        Генерирует персональный ИИ-анализ **параллельно** (до 3 одновременно),
        один раз на игрока, объединяя все триггеры (лимит 8).
        """
        # Получаем все триггеры за период
        triggers = self.db.query(PlayerTrigger).join(Player).filter(
            and_(
                PlayerTrigger.period_start == start_date,
                PlayerTrigger.period_end == end_date
            )
        ).all()

        # Группируем триггеры по игрокам
        players_triggers: dict[int, list[PlayerTrigger]] = {}
        for trigger in triggers:
            players_triggers.setdefault(trigger.player_id, []).append(trigger)

        # ====================================================================
        # 🚀 ПАРАЛЛЕЛЬНЫЙ AI-АНАЛИЗ (до 3 одновременных запросов)
        # ====================================================================
        # 1) Подготавливаем данные для каждого игрока (без AI — мгновенно)
        player_data: Dict[Any, dict] = {}  # player_id -> {player, stats, trigger_text}
        for player_id, player_triggers in players_triggers.items():
            player = self._players_cache.get(player_id)
            player_stats = self._get_player_stats_for_trigger(player_id, start_date, end_date) or {}
            limited_triggers = player_triggers[:8]
            trigger_values_combined = "\n".join([t.trigger_value for t in limited_triggers])
            player_data[player_id] = {
                "player": player,
                "player_stats": player_stats,
                "trigger_text": trigger_values_combined,
            }

        # 2) Запускаем все AI-запросы параллельно с ограничением concurrency
        # Для LMStudio оптимально 1-2 одновременных запроса (модель тяжелая)
        ai_semaphore = asyncio.Semaphore(2)  # максимум 2 одновременных запроса к LLM

        async def _ai_task(pid: Any) -> tuple:
            """Обёртка для одного AI-запроса с семафором и retry логикой"""
            async with ai_semaphore:
                data = player_data[pid]
                player = data["player"]
                player_name = player.full_name if player else "Неизвестный игрок"
                print(f"🤖 [PARALLEL] Запуск AI для {player_name}...")
                
                # Retry логика: до 2 попыток
                for attempt in range(2):
                    try:
                        ai_text = await self._generate_ai_analysis(
                            player_name,
                            data["trigger_text"],
                            data["player_stats"],
                            provider=provider
                        )
                        
                        # Проверяем, не таймаут ли это
                        if ai_text and "Таймаут" not in ai_text:
                            print(f"✅ [PARALLEL] AI для {player_name} завершён ({len(ai_text or '')} символов)")
                            return pid, ai_text
                        elif attempt == 0:
                            print(f"⚠️ [RETRY] Таймаут для {player_name}, повтор...")
                            await asyncio.sleep(2)  # Пауза перед повтором
                            continue
                        else:
                            return pid, ai_text  # Последняя попытка, возвращаем даже с ошибкой
                    except Exception as e:
                        if attempt == 0:
                            print(f"⚠️ [RETRY] Ошибка для {player_name}: {e}, повтор...")
                            await asyncio.sleep(2)
                            continue
                        else:
                            print(f"❌ [FAILED] AI для {player_name} не удался: {e}")
                            return pid, f"Ошибка AI: {str(e)}"
                
                return pid, None

        # Запускаем ВСЕ задачи параллельно (семафор ограничит до 2 одновременных)
        player_ids_to_analyze = list(players_triggers.keys())
        print(f"\n🚀 Запуск параллельного AI-анализа для {len(player_ids_to_analyze)} игроков...")
        print(f"⚙️ Режим: максимум 2 запроса одновременно (баланс скорости и стабильности)")
        print(f"⏱️ Ожидаемое время: ~{len(player_ids_to_analyze)} минут")

        if self._ai_analysis_enabled and player_ids_to_analyze:
            ai_tasks = [_ai_task(pid) for pid in player_ids_to_analyze]
            ai_results_list = await asyncio.gather(*ai_tasks, return_exceptions=True)

            # Собираем результаты в словарь
            ai_results: Dict[Any, str] = {}
            for item in ai_results_list:
                if isinstance(item, Exception):
                    logger.error(f"💥 Ошибка AI-анализа: {item}")
                    continue
                pid, ai_text = item
                ai_results[pid] = ai_text

            print(f"✅ Параллельный AI-анализ завершён: {len(ai_results)}/{len(player_ids_to_analyze)} успешно (max 2 одновременно)")
        else:
            ai_results = {}
            if not self._ai_analysis_enabled:
                print(f"⚠️ AI-анализ отключен, пропускаем")

        # ====================================================================
        # 3) Собираем итоговый результат (мгновенно — все данные уже есть)
        # ====================================================================
        result = []

        for player_id, player_triggers in players_triggers.items():
            data = player_data[player_id]
            player = data["player"]
            player_stats = data["player_stats"]
            ai_text = ai_results.get(player_id)  # уже готовый AI-текст

            # Матчи игрока из кеша
            player_matches = self._matches_by_player.get(player_id, [])
            player_matches_sorted = sorted(player_matches, key=lambda m: m.date, reverse=True)

            for trigger in player_triggers:
                trigger_evidence = self._extract_trigger_evidence(
                    player,
                    trigger.trigger_type,
                    player_matches_sorted
                )

                trigger_dict = {
                    "id": trigger.id,
                    "player_id": trigger.player_id,
                    "player_name": player.full_name if player else "Неизвестный игрок",
                    "player_rating": player.current_rating if player else None,
                    "trigger_type": trigger.trigger_type,
                    "trigger_subtype": trigger.trigger_subtype,
                    "trigger_value": trigger.trigger_value,
                    "severity_level": trigger.severity_level,
                    "period_start": trigger.period_start,
                    "period_end": trigger.period_end,
                    # "is_active": trigger.is_active,
                    "is_pair": trigger.is_pair,
                    "trigger_metadata": trigger.trigger_metadata,
                    "created_at": trigger.created_at,
                    "player_stats": player_stats if player_stats else None,
                    "ai_analysis": ai_text,  # один AI-анализ на игрока
                    "evidence": trigger_evidence  # доказательства триггера
                }
                result.append(trigger_dict)

        # Сортируем по уровню серьезности (от самых серьезных к менее серьезным)
        result.sort(key=lambda x: x["severity_level"] or 0, reverse=True)

        return result

    
    async def _analyze_top_performers(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]: #РАБОТАЕТ!
        """Анализ топ игрока по результативности"""
        triggers = []

        if len(matches) < 5:  # Минимум 5 матчей для анализа
            return triggers

        wins = len([m for m in matches if m.winner_id == player.id])
        win_rate = (wins / len(matches)) * 100

        # Топ игрок = win_rate >= 70%
        if win_rate >= 70:
            trigger = PlayerTrigger(
                player_id=player.id,
                trigger_type="top_performers",
                trigger_value=f"Топ исполнитель: {win_rate:.1f}% побед ({wins}/{len(matches)})",
                severity_level=1,  # Позитивный триггер
                period_start=start_date,
                period_end=end_date,
                # is_active=True
                is_pair=False
            )
            trigger.set_metadata({
                "win_rate": win_rate,
                "total_matches": len(matches),
                "wins": wins,
                "rank": "top_performer"
            })

            self.db.add(trigger)
            triggers.append(trigger)

        return triggers
    
    async def _analyze_losers_50_percent(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        """Анализ игроков, проигравших больше 50% матчей"""
        triggers = []
            
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
                        # is_active=True
                        is_pair=False
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
    
    async def _analyze_losing_streaks(
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ серий поражений игрока с учётом последних матчей"""
        triggers = []

        if not matches:
            return triggers

        # Сортируем матчи по дате, чтобы идти от старых к новым
        matches_sorted = sorted(matches, key=lambda m: m.date)

        max_streak = 0
        temp_streak = 0

        # Проходим по всем матчам, считаем максимальную серию поражений
        for match in matches_sorted:
            if match.winner_id and match.winner_id != player.id:
                temp_streak += 1
            else:
                max_streak = max(max_streak, temp_streak)
                temp_streak = 0
        # Проверяем последнюю серию
        max_streak = max(max_streak, temp_streak)

        # Считаем текущую серию поражений только по последним 5 матчам
        last_matches = matches_sorted[-5:]  # берём последние 5 матчей
        current_streak = 0
        for match in last_matches:
            if match.winner_id and match.winner_id != player.id:
                current_streak += 1
            else:
                break  # текущая серия прервалась

        # Создаём триггер при условиях
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
                # is_active=True
                is_pair=False
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

    
    async def _analyze_post_holiday_problems(   #РАБОТАЕТ
    self,
    player: Player,
    matches: List[Match],
    start_date: date,
    end_date: date,
    post_holiday_window_days: int = 14,   # <-- решает проблему 3 (расширяем окно)
    min_matches_per_holiday: int = 2,      # минимум матчей в окне, чтобы учитывать праздник
    poor_loss_rate_threshold: float = 0.6, # 60%
    unexpected_loss_rate_threshold: float = 0.4, # если много "неожиданных" поражений
    unexpected_rating_delta: int = 50      # если соперник слабее на >=50 => "ожидаемо выиграть"
) -> List[PlayerTrigger]:
        """
        Анализ проблем после праздников с:
        - корректным подбором holidays (пересечение интервалов),
        - настраиваемым пост-праздничным окном (по умолчанию 14 дней),
        - учётом силы соперника (отмечаем 'неожиданные' поражения против слабее рейтингов).
        """

        triggers: List[PlayerTrigger] = []

        # 1) Используем кеш праздников вместо db.query(Holiday)
        holidays = self._holidays_cache if self._holidays_cache else self.db.query(Holiday).filter(
            and_(
                Holiday.end_date >= start_date - timedelta(days=30),
                Holiday.start_date <= end_date + timedelta(days=10)
            )
        ).all()

        if not holidays:
            return triggers

        # 2) Для быстродействия — подготовим словарь рейтингов соперников из всех матчей (кеш)
        opponent_ids: Set[str] = set()
        for m in matches:
            if m.player1_id == player.id:
                opponent_ids.add(m.player2_id)
            elif m.player2_id == player.id:
                opponent_ids.add(m.player1_id)
        if opponent_ids:
            rows = self.db.query(Player.id, Player.current_rating).filter(Player.id.in_(list(opponent_ids))).all()
            rating_by_id: Dict[str, int] = {r[0]: (r[1] or 1000) for r in rows}  # default 1000 если нет
        else:
            rating_by_id = {}

        poor_performance_after_holidays = 0
        total_post_holiday_matches = 0
        seen_match_ids: Set[str] = set()  # чтобы матч не учитывался дважды при перекрытии окон

        player_rating = getattr(player, "current_rating", 1000) or 1000

        for holiday in holidays:
            post_start = holiday.end_date + timedelta(days=1)
            post_end = holiday.end_date + timedelta(days=post_holiday_window_days)

            # обрезаем окно в границах анализа
            window_start = max(post_start, start_date)
            window_end = min(post_end, end_date)
            if window_start > window_end:
                continue

            # берем матчи из переданного списка, которые попадают в окно и ещё не посчитаны
            post_holiday_matches = [
                m for m in matches
                if (m.id not in seen_match_ids) and (window_start <= m.date <= window_end)
            ]

            if not post_holiday_matches:
                continue

            # добавляем их в seen, чтобы не счётались повторно
            for m in post_holiday_matches:
                seen_match_ids.add(m.id)

            # требуем минимум матчей в окне, иначе шум
            if len(post_holiday_matches) < min_matches_per_holiday:
                continue

            total_post_holiday_matches += len(post_holiday_matches)

            # подсчёт: обычные поражения и "неожиданные" поражения (против слабого соперника)
            losses = 0
            unexpected_losses = 0

            for m in post_holiday_matches:
                # считаем проигрыш если winner_id != player.id
                if m.winner_id != player.id:
                    losses += 1

                    # определяем соперника и его рейтинг
                    if m.player1_id == player.id:
                        opp_id = m.player2_id
                    else:
                        opp_id = m.player1_id
                    opp_rating = rating_by_id.get(opp_id, 1000)

                    # Если соперник существенно слабее => "неожиданный" проигрыш
                    # Рассчёт ожидаемой вероятности победы игрока против соперника
                    expected_win_prob = 1 / (1 + 10 ** ((opp_rating - player_rating) / 400))

                    # Если шанс победы был высоким (> 0.7), но игрок всё же проиграл => неожиданный проигрыш
                    if expected_win_prob >= 0.7:
                        unexpected_losses += 1

                    else:
                        # можно также использовать ожидаемую вероятность (ELO) — пример ниже (закомментирован)
                        pass

            # считаем доли
            loss_rate = losses / len(post_holiday_matches) if post_holiday_matches else 0.0
            unexpected_loss_rate = unexpected_losses / len(post_holiday_matches) if post_holiday_matches else 0.0

            # Правило: праздник считается "проблемным", если:
            #  - либо высокая общая доля поражений (>= poor_loss_rate_threshold)
            #  - либо высокая доля неожиданных поражений (>= unexpected_loss_rate_threshold)
            if (loss_rate >= poor_loss_rate_threshold) or (unexpected_loss_rate >= unexpected_loss_rate_threshold):
                poor_performance_after_holidays += 1

        # Условие создания триггера — как и раньше, можно настроить
        if poor_performance_after_holidays >= 2 and total_post_holiday_matches >= 4:
            trigger = PlayerTrigger(
                player_id=player.id,
                trigger_type="post_holiday_problems",
                trigger_value=f"Слабые результаты после {poor_performance_after_holidays} праздников из {len(holidays)}",
                severity_level=2,
                period_start=start_date,
                period_end=end_date,
                # is_active=True
                is_pair=False
            )
            trigger.set_metadata({
                "poor_performance_count": poor_performance_after_holidays,
                "total_holidays": len(holidays),
                "total_post_holiday_matches": total_post_holiday_matches,
                "settings": {
                    "post_holiday_window_days": post_holiday_window_days,
                    "min_matches_per_holiday": min_matches_per_holiday,
                    "poor_loss_rate_threshold": poor_loss_rate_threshold,
                    "unexpected_loss_rate_threshold": unexpected_loss_rate_threshold,
                    "unexpected_rating_delta": unexpected_rating_delta
                },
                "recommendation": "Рекомендуется усиленная подготовка после отпусков"
            })
            self.db.add(trigger)
            return [trigger]

        return []
    
    async def _analyze_time_performance(
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ результативности игрока по времени суток с учётом силы соперников и счёта"""
        triggers = []

        filtered_matches = [m for m in matches if m.time is not None and m.winner_id]

        if len(filtered_matches) >= 5:  # минимум 5 матчей
            # 2) Делим матчи по времени суток
            day_matches = []     # 08:00 - 17:59
            evening_matches = [] # 18:00 - 21:59
            night_matches = []   # 22:00 - 07:59

            for match in filtered_matches:
                hour = match.time.hour
                if 8 <= hour < 18:
                    day_matches.append(match)
                elif 18 <= hour < 22:
                    evening_matches.append(match)
                else:
                    night_matches.append(match)

            # 3) Анализируем каждый период
            periods = [
                ("day", day_matches, "дневное время"),
                ("evening", evening_matches, "вечернее время"),
                ("night", night_matches, "ночное время"),
            ]

            for period_name, period_matches, period_desc in periods:
                if len(period_matches) >= 3:
                    weighted_losses = 0
                    total_matches = len(period_matches)

                    for m in period_matches:
                        if m.winner_id != player.id:  # поражение
                            # --- Определяем соперника из кеша
                            opponent_id = m.player1_id if m.player2_id == player.id else m.player2_id
                            opponent = self._players_cache.get(opponent_id)

                            # --- Базовый вес поражения
                            loss_weight = 1

                            # --- Учет разницы рейтингов
                            if opponent and opponent.current_rating is not None and player.current_rating is not None:
                                rating_diff = player.current_rating - opponent.current_rating
                                if rating_diff >= 400:   # сильно слабее
                                    loss_weight += 2
                                elif rating_diff >= 200: # слабее
                                    loss_weight += 1

                            # --- Учет счета по сетам
                            if m.sets_player1 is not None and m.sets_player2 is not None:
                                if player.id == m.player1_id:
                                    sets_won, sets_lost = m.sets_player1, m.sets_player2
                                else:
                                    sets_won, sets_lost = m.sets_player2, m.sets_player1

                                if sets_won == 0:              # поражение 0:X
                                    loss_weight += 1
                                elif sets_won == 1 and sets_lost >= 3:  # поражение 1:3
                                    loss_weight += 1
                                # 2:3 — мягче, без доп. штрафа

                            weighted_losses += loss_weight

                    # --- Рассчитываем взвешанный процент поражений
                    weighted_loss_rate = (weighted_losses / total_matches) * 100

                    # --- Создаём триггер, если проблемы заметны
                    if weighted_loss_rate >= 70:
                        trigger = PlayerTrigger(
                            player_id=player.id,
                            trigger_type="time_performance",
                            trigger_subtype=period_name,
                            trigger_value=(
                                f"Слабые результаты в {period_desc}: "
                                f"{weighted_loss_rate:.1f}% взвешенных поражений"
                            ),
                            severity_level=2 if weighted_loss_rate >= 80 else 1,
                            period_start=start_date,
                            period_end=end_date,
                            # is_active=True
                            is_pair=False
                        )
                        trigger.set_metadata({
                            "time_period": period_name,
                            "weighted_loss_rate": weighted_loss_rate,
                            "matches_in_period": total_matches,
                            "weighted_losses": weighted_losses,
                            "recommendation": (
                                f"Избегать матчей в {period_desc} или усилить подготовку"
                            )
                        })

                        self.db.add(trigger)
                        triggers.append(trigger)

        return triggers

    
    # Остальные методы анализа триггеров будут добавлены аналогично
    async def _analyze_endgame_problems(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_lead_4_lost(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_balance_problems(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_led_2_sets_lost(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_led_1_set_lost(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_early_final_exit(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_league_promotion_failed(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_won_2_lost_3rd(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_close_score_losses(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    # async def _analyze_post_holiday_problems(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
    #     triggers = []
    #     return triggers
    
    # async def _analyze_time_performance(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
    #     triggers = []
    #     return triggers
    
    async def _analyze_shutout_losses(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    # async def _analyze_losing_streaks(self, players: List[Player], start_date: date, end_date: date) -> List[PlayerTrigger]:
    #     triggers = []
    #     return triggers
    
    async def _analyze_weaker_opponent_losses(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_long_match_losses(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_higher_league_struggles(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    async def _analyze_reception_problems(self, player: Player, matches: List[Match], start_date: date, end_date: date) -> List[PlayerTrigger]:
        triggers = []
        return triggers
    
    def _parse_date(self, date_str) -> date:
        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y.%m.%d",
            "%Y/%m/%d",
        ]

        date_str = str(date_str).strip()
        print(f"   🔍  Парсим дату: '{date_str}'")
        last_error = None

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError as error:
                last_error = error

        try:
            if date_str.replace('.', '').isdigit():
                excel_date = float(date_str)
                base_date = datetime(1899, 12, 30)
                return (base_date + timedelta(days=excel_date)).date()
        except Exception as error:
            last_error = error

        raise ValueError(
            f"Не удалось распарсить дату: '{date_str}'. "
            f"Причина: {last_error}"
        )

        
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
        
    def _match_exists(self, sl_id: str = None, part_id: str = None, 
                      date: date = None, player1_id: int = None, player2_id: int = None, 
                      score: str = None, time_str: str = None) -> tuple:
        """
        Проверяет существование матча в базе данных.
        
        ПРИОРИТЕТ 1: По уникальным ID из Excel (SL-ID или Part iD)
        ПРИОРИТЕТ 2: По комбинации даты, игроков, времени и счета (для старых данных)
        
        Args:
            sl_id: Уникальный ID матча из SL-ID
            part_id: Уникальный ID матча из Part iD  
            date: Дата матча
            player1_id: ID первого игрока
            player2_id: ID второго игрока
            score: Счет матча
            time_str: Время матча
            
        Returns:
            tuple: (is_duplicate: bool, reason: str) - флаг дубликата и причина
        """
        from datetime import datetime

        # ПРИОРИТЕТ 1: Проверка по SL-ID (самый надежный способ)
        if sl_id:
            try:
                sl_id_int = int(sl_id)
                existing = self.db.query(Match).filter(Match.match_sl_id == sl_id_int).first()
                if existing:
                    reason = f"SL-ID {sl_id} уже существует в БД (match_id={existing.id})"
                    print(f"   ⏭️  Найден дубликат по SL-ID: {sl_id}")
                    return (True, reason)
            except (ValueError, TypeError):
                pass
        
        # ПРИОРИТЕТ 2: Проверка по Part iD (если SL-ID нет)
        # TODO: Добавить поле part_id в модель Match если нужно
        
        # ПРИОРИТЕТ 3: Проверка по комбинации параметров (fallback для старых данных без ID)
        # ЗАКОММЕНТИРОВАНО: Проверка по дате/времени/счету временно отключена
        # Оставлена только проверка по SL-ID
        """
        if not date or not player1_id or not player2_id:
            return (False, "")

        # Преобразуем строку времени в datetime.time, если возможно
        try:
            match_time = datetime.strptime(time_str.strip(), "%H:%M").time() if time_str else None
        except Exception:
            match_time = None

        # Нормализуем счёт (удаляем пробелы, стандартный формат через ':')
        normalized_score = score.replace(" ", "").replace("-", ":").strip() if score else ""

        # Получаем все матчи на эту дату между этими игроками (любой порядок)
        potential_matches = self.db.query(Match).filter(
            and_(
                Match.date == date,
                or_(
                    and_(Match.player1_id == player1_id, Match.player2_id == player2_id),
                    and_(Match.player1_id == player2_id, Match.player2_id == player1_id)
                )
            )
        ).all()

        # Проверяем каждый матч на совпадение времени и счёта
        for m in potential_matches:
            match_score = (m.score or "").replace(" ", "").replace("-", ":").strip()
            match_time_db = m.time

            time_match = True if match_time is None or match_time_db is None else match_time == match_time_db
            score_match = normalized_score == match_score

            if time_match and score_match:
                reason = f"Совпадение по дате/игрокам/времени/счету (match_id={m.id})"
                print(f"   ⏭️  Найден дубликат по дате/игрокам/времени/счету")
                return (True, reason)
        """

        return (False, "")



    # ========== НОВЫЕ ТРИГГЕРЫ ==========
    
    async def _analyze_defeat_0_3(
        self, player: Player, matches: List[Match], start_date: date, end_date: date
    ) -> List[PlayerTrigger]:
        """Анализ поражений со счетом 0:3 для одного игрока"""
        triggers = []

        # Фильтруем матчи игрока за период, где он проиграл
        filtered_matches = [
            m for m in matches
            if start_date <= m.date <= end_date
            and m.winner_id is not None
            and m.winner_id != player.id
            and (m.player1_id == player.id or m.player2_id == player.id)
        ]

        defeat_0_3_count = 0
        total_defeats = len(filtered_matches)

        for match in filtered_matches:
            if match.player1_id == player.id:
                player_sets = match.sets_player1 or 0
                opponent_sets = match.sets_player2 or 0
            else:
                player_sets = match.sets_player2 or 0
                opponent_sets = match.sets_player1 or 0

            if player_sets == 0 and opponent_sets == 3:
                defeat_0_3_count += 1

        # Триггер если больше 20% поражений со счетом 0:3 и минимум 3 поражения
        if defeat_0_3_count > 0 and total_defeats >= 3:
            percentage = (defeat_0_3_count / total_defeats) * 100
            if percentage >= 20:
                severity = 3 if percentage >= 40 else 2

                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="defeat_0_3",
                    trigger_subtype="shutout_losses",
                    trigger_value=f"Поражения 0:3 - {defeat_0_3_count} из {total_defeats} поражений ({percentage:.1f}%)",
                    severity_level=severity,
                    period_start=start_date,
                    period_end=end_date,
                    # is_active=True
                    is_pair=False
                )
                trigger.set_metadata({
                    "defeat_0_3_count": defeat_0_3_count,
                    "total_defeats": total_defeats,
                    "percentage": percentage,
                    "recommendation": "Требуется работа над психологической устойчивостью и стартовой готовностью"
                })

                self.db.add(trigger)
                triggers.append(trigger)

        return triggers


    async def _analyze_won_2_lost_3rd_set(
            self, player: Player, matches: List[Match], start_date: date, end_date: date,
            threshold_percentage: float = 20.0   # минимум % таких поражений
        ) -> List[PlayerTrigger]:
            """
            Анализ случаев, когда игрок вел 2:0, но проиграл 2:3.
            Триггер создается, только если такие матчи составляют значимый процент
            от всех поражений игрока.
            """

            triggers = []

            # --- 1) Фильтруем поражения игрока ---
            defeats = [
                m for m in matches
                if start_date <= m.date <= end_date
                and m.winner_id is not None
                and m.winner_id != player.id
                and (m.player1_id == player.id or m.player2_id == player.id)
            ]

            total_defeats = len(defeats)
            if total_defeats < 3:
                return []  # слишком мало данных как и в defeat_0_3

            collapse_count = 0
            collapse_match_ids = []

            # --- 2) Из поражений выбираем те, где было 2:0 → 2:3 ---
            for match in defeats:
                is_p1 = match.player1_id == player.id
                player_sets = match.sets_player1 if is_p1 else match.sets_player2
                opp_sets = match.sets_player2 if is_p1 else match.sets_player1

                if player_sets == 2 and opp_sets == 3:
                    # Из кеша вместо db.query(MatchSet)
                    sets = self._sets_by_match.get(match.id, [])
                    if len(sets) >= 3 and sets[0].winner_id == player.id and sets[1].winner_id == player.id:
                        collapse_count += 1
                        collapse_match_ids.append(match.id)

            if collapse_count == 0:
                return []

            # --- 3) Считаем процент ---
            percentage = (collapse_count / total_defeats) * 100

            # --- 4) Проверяем порог ---
            if percentage < threshold_percentage:
                return []

            # --- 5) Severity по процентам ---
            if percentage >= 50:
                severity = 3
            elif percentage >= 30:
                severity = 2
            else:
                severity = 1

            # --- Создаем один триггер ---
            trigger = PlayerTrigger(
                player_id=player.id,
                trigger_type="won_2_lost_3rd_set",
                trigger_subtype="led_2_0_lost_match",
                trigger_value=(
                    f"Поражения после лидерства 2:0 — {collapse_count} из {total_defeats} "
                    f"({percentage:.1f}%)"
                ),
                severity_level=severity,
                period_start=start_date,
                period_end=end_date,
                # is_active=True
                is_pair=False
            )

            trigger.set_metadata({
                "collapse_count": collapse_count,
                "total_defeats": total_defeats,
                "percentage": percentage,
                "match_ids": collapse_match_ids,
                "recommendation": (
                    "Игрок систематически теряет матчи после уверенного старта 2:0. "
                    "Требуется психологическая стабилизация и повышение физподготовки."
                )
            })

            self.db.add(trigger)
            self.db.commit()

            return [trigger]



    
    async def _analyze_early_final_exit_advanced( #РАБОТАЕТ
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ досрочного выхода из финала (расширенный)"""
        triggers = []

        player_matches = [
            m for m in matches
            if start_date <= m.date <= end_date and
            (m.player1_id == player.id or m.player2_id == player.id) and
            m.is_final and m.winner_id != player.id
        ]

        final_losses = len(player_matches)
        early_exits = 0

        for match in player_matches:
            if match.player1_id == player.id:
                player_sets = match.sets_player1 or 0
                opponent_sets = match.sets_player2 or 0
            else:
                player_sets = match.sets_player2 or 0
                opponent_sets = match.sets_player1 or 0

            if player_sets <= 1 and opponent_sets == 3:
                early_exits += 1

        if final_losses >= 2 and early_exits > 0:
            percentage = (early_exits / final_losses) * 100
            if percentage >= 50:
                severity = 3 if early_exits >= 3 else 2

                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="early_final_exit_advanced",
                    trigger_subtype="final_performance",
                    trigger_value=f"Досрочный выход из финала: {early_exits} из {final_losses} финалов ({percentage:.1f}%)",
                    severity_level=severity,
                    period_start=start_date,
                    period_end=end_date,
                    # is_active=True
                    is_pair=False
                )
                trigger.set_metadata({
                    "early_exits": early_exits,
                    "total_finals": final_losses,
                    "percentage": percentage,
                    "recommendation": "Проблемы с игрой под давлением в решающих матчах"
                })

                self.db.add(trigger)
                triggers.append(trigger)

        return triggers


    async def _analyze_led_1_set_lost_match(
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ случаев: игрок выиграл 1-й сет, но проиграл матч"""
        triggers = []

        # Берём все поражения игрока за период
        losing_matches = [
            m for m in matches
            if start_date <= m.date <= end_date and
            (m.player1_id == player.id or m.player2_id == player.id) and
            m.winner_id != player.id
        ]

        led_1_lost_count = 0
        total_losses = len(losing_matches)

        for match in losing_matches:
            # Из кеша вместо db.query(MatchSet)
            match_sets = self._sets_by_match.get(match.id, [])

            if not match_sets:
                continue  # если нет информации по сетам, пропускаем

            # Определяем, кто выиграл первый сет
            first_set = match_sets[0]
            if first_set.winner_id == player.id:
                led_1_lost_count += 1

        # Создаём триггер, если таких матчей достаточно
        if led_1_lost_count > 0 and total_losses >= 3:
            percentage = (led_1_lost_count / total_losses) * 100
            if percentage >= 40:
                severity = 2 if percentage >= 60 else 1

                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="led_1_set_lost_match",
                    trigger_subtype="lead_blown",
                    trigger_value=f"Вёл в первом сете и проиграл матч: {led_1_lost_count} из {total_losses} поражений ({percentage:.1f}%)",
                    severity_level=severity,
                    period_start=start_date,
                    period_end=end_date,
                    # is_active=True
                    is_pair=False
                )
                trigger.set_metadata({
                    "led_1_lost_count": led_1_lost_count,
                    "total_losses": total_losses,
                    "percentage": percentage,
                    "recommendation": "Проблемы с удержанием преимущества после первого сета"
                })

                self.db.add(trigger)
                triggers.append(trigger)

        return triggers



    async def _analyze_led_2_sets_lost_match(
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ случаев: игрок выиграл 2 сета и проиграл матч"""
        triggers = []

        player_matches = [
            m for m in matches
            if start_date <= m.date <= end_date and
            (m.player1_id == player.id or m.player2_id == player.id) and
            m.winner_id != player.id
        ]

        led_2_lost_count = 0
        total_matches = len(player_matches)

        led_2_match_ids = []  # ID матчей для метаданных

        for match in player_matches:
            # Из кеша вместо db.query(MatchSet)
            match_sets = self._sets_by_match.get(match.id, [])
            if len(match_sets) < 3:
                continue  # нужно минимум 3 сета (2 выигранных + хотя бы 1 проигранный)

            # Строим словарь сетов по номеру для надёжности
            sets_by_number = {s.set_number: s for s in match_sets}

            set1 = sets_by_number.get(1)
            set2 = sets_by_number.get(2)

            if not set1 or not set2:
                continue

            # Проверяем что игрок выиграл ИМЕННО 1-й И 2-й сет
            won_set_1 = (set1.winner_id == player.id)
            won_set_2 = (set2.winner_id == player.id)

            if won_set_1 and won_set_2:
                # Дополнительно проверяем: после 2:0 по сетам проиграл матч
                # Считаем сеты после 2-го
                remaining_sets_lost = sum(
                    1 for s in match_sets if s.set_number > 2 and s.winner_id and s.winner_id != player.id
                )
                if remaining_sets_lost >= 2:  # Проиграл минимум 2 из оставшихся (т.е. соперник отыграл 2+)
                    led_2_lost_count += 1
                    led_2_match_ids.append(str(match.id))
                    is_p1 = match.player1_id == player.id
                    opp = self._players_cache.get(match.player2_id if is_p1 else match.player1_id)
                    opp_name = opp.full_name if opp else '?'
                    print(f"      🔴 led_2_sets_lost_match: {player.full_name} вёл 2:0, проиграл vs {opp_name} (матч {match.id}, {match.date})")

        if led_2_lost_count >= 2:
            percentage = (led_2_lost_count / total_matches) * 100 if total_matches > 0 else 0
            severity = 3 if led_2_lost_count >= 3 else 2

            trigger = PlayerTrigger(
                player_id=player.id,
                trigger_type="led_2_sets_lost_match",
                trigger_subtype="major_lead_blown",
                trigger_value=f"Вёл 2:0 по сетам и проиграл: {led_2_lost_count} случаев из {total_matches} матчей",
                severity_level=severity,
                period_start=start_date,
                period_end=end_date,
                # is_active=True
                is_pair=False
            )
            trigger.set_metadata({
                "led_2_lost_count": led_2_lost_count,
                "total_matches": total_matches,
                "percentage": percentage,
                "match_ids": led_2_match_ids,
                "recommendation": "Критические проблемы с психологической устойчивостью при большом преимуществе"
            })

            self.db.add(trigger)
            triggers.append(trigger)

        return triggers

    
    async def _analyze_psychological_breakdown(
        self, player: Player, matches: List[Match], start_date: date, end_date: date
    ) -> List[PlayerTrigger]:
        """Анализ психологических срывов (комбинированный триггер с сетами)"""
        triggers = []
        psychological_issues = 0
        issue_details = []

        for match in matches:
            if not (start_date <= match.date <= end_date):
                continue

            # Из кеша вместо db.query(MatchSet)
            match_sets = self._sets_by_match.get(match.id, [])
            if not match_sets:
                continue

            # Определяем количество сетов игрока и соперника
            player_set_wins = 0
            opponent_set_wins = 0
            for s in match_sets:
                if s.winner_id == player.id:
                    player_set_wins += 1
                else:
                    opponent_set_wins += 1

            # 1️⃣ Проигрыш после ведения 2:0
            if player_set_wins == 2 and opponent_set_wins >= 2 and match.winner_id != player.id:
                psychological_issues += 2
                issue_details.append(f"Проиграл после 2:0 (Match ID: {match.id})")

            # 2️⃣ Полное поражение 0:3
            if player_set_wins == 0 and opponent_set_wins >= 3:
                psychological_issues += 2
                issue_details.append(f"Поражение 0:3 (Match ID: {match.id})")

            # 3️⃣ Досрочный проигрыш в финале
            if match.is_final and match.winner_id != player.id and player_set_wins <= 1:
                psychological_issues += 2
                issue_details.append(f"Досрочный проигрыш в финале (Match ID: {match.id})")

        total_matches = len([m for m in matches if start_date <= m.date <= end_date])

        if total_matches >= 5 and psychological_issues > 0:
            issue_rate = (psychological_issues / total_matches) * 100
            if issue_rate >= 30:
                severity = 3 if issue_rate >= 50 else 2

                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="psychological_breakdown",
                    trigger_subtype="mental_resilience",
                    trigger_value=f"Психологические срывы: {psychological_issues} индикаторов в {total_matches} матчах ({issue_rate:.1f}%)",
                    severity_level=severity,
                    period_start=start_date,
                    period_end=end_date,
                    # is_active=True
                    is_pair=False
                )
                trigger.set_metadata({
                    "psychological_issues": psychological_issues,
                    "total_matches": total_matches,
                    "issue_rate": issue_rate,
                    "issue_details": issue_details[:10],
                    "recommendation": "Требуется работа со спортивным психологом"
                })

                self.db.add(trigger)
                triggers.append(trigger)

        return triggers


    async def _analyze_comeback_inability(
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ неспособности совершать камбеки по реальным сетам"""
        triggers = []
        comeback_opportunities = 0
        successful_comebacks = 0

        for match in matches:
            # Из кеша вместо db.query(MatchSet)
            sets = self._sets_by_match.get(match.id, [])
            if not sets:
                continue

            # Определяем очки игрока по сетам
            player_set_wins = 0
            opponent_set_wins = 0
            for s in sets:
                if s.winner_id == player.id:
                    player_set_wins += 1
                else:
                    opponent_set_wins += 1

            total_sets = player_set_wins + opponent_set_wins

            # Считаем попытки камбеков:
            # Игрок проигрывал первые 2 сета и выиграл матч → успешный камбек
            if total_sets >= 3:
                first_two_sets = sets[:2]
                player_lost_first_two = sum(1 for s in first_two_sets if s.winner_id != player.id) == 2

                if player_lost_first_two:
                    comeback_opportunities += 1
                    if player_set_wins > opponent_set_wins:
                        successful_comebacks += 1
                # Также можно учитывать ситуации 1:2, если матч больше 3 сетов
                elif len(sets) >= 3:
                    first_three_sets = sets[:3]
                    player_down_1_2 = sum(1 for s in first_three_sets if s.winner_id != player.id) == 2 and sum(1 for s in first_three_sets if s.winner_id == player.id) == 1
                    if player_down_1_2:
                        comeback_opportunities += 1
                        if player_set_wins > opponent_set_wins:
                            successful_comebacks += 1

        if comeback_opportunities >= 3:
            failure_rate = ((comeback_opportunities - successful_comebacks) / comeback_opportunities) * 100
            if failure_rate >= 70:
                severity = 2 if failure_rate >= 85 else 1
                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="comeback_inability",
                    trigger_subtype="mental_toughness",
                    trigger_value=f"Проблемы с камбеками: {successful_comebacks} из {comeback_opportunities} попыток ({100-failure_rate:.1f}% успеха)",
                    severity_level=severity,
                    period_start=start_date,
                    period_end=end_date,
                    # is_active=True
                    is_pair=False
                )
                trigger.set_metadata({
                    "comeback_opportunities": comeback_opportunities,
                    "successful_comebacks": successful_comebacks,
                    "failure_rate": failure_rate,
                    "recommendation": "Работа над ментальной выносливостью и тактической гибкостью"
                })
                self.db.add(trigger)
                triggers.append(trigger)

        return triggers



    async def _analyze_pressure_situations(
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ игры в ситуациях давления с учётом сетов и силы соперника"""
        triggers = []

        # Отбираем матчи под давлением
        pressure_matches = [
            m for m in matches 
            if start_date <= m.date <= end_date and
            (m.is_final or m.is_semifinal or 
            (m.stage and ('финал' in m.stage.lower() or 'полуфинал' in m.stage.lower())))
        ]

        total_pressure_matches = len(pressure_matches)
        weighted_losses = 0

        for m in pressure_matches:
            if m.winner_id != player.id:
                # Определяем соперника из кеша
                opponent_id = m.player1_id if m.player2_id == player.id else m.player2_id
                opponent = self._players_cache.get(opponent_id)

                # Базовый вес поражения
                loss_weight = 1

                # Учитываем разницу рейтинга
                if opponent and opponent.current_rating is not None and player.current_rating is not None:
                    rating_diff = player.current_rating - opponent.current_rating
                    if rating_diff >= 400:
                        loss_weight += 2
                    elif rating_diff >= 200:
                        loss_weight += 1

                # Учитываем сетовый счёт
                if m.sets_player1 is not None and m.sets_player2 is not None:
                    if player.id == m.player1_id:
                        player_sets = m.sets_player1
                        opponent_sets = m.sets_player2
                    else:
                        player_sets = m.sets_player2
                        opponent_sets = m.sets_player1

                    # Большие поражения весятся сильнее
                    if player_sets == 0 and opponent_sets >= 2:
                        loss_weight += 2
                    elif player_sets == 1 and opponent_sets >= 2:
                        loss_weight += 1
                    # 2:3 или другие узкие поражения — базовый вес

                weighted_losses += loss_weight

        if total_pressure_matches >= 3 and weighted_losses > 0:
            weighted_loss_rate = (weighted_losses / total_pressure_matches) * 100

            # Триггер при слабой игре под давлением
            if weighted_loss_rate >= 30:
                severity = 3 if weighted_loss_rate >= 50 else 2
                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="pressure_situations",
                    trigger_subtype="important_matches",
                    trigger_value=f"Слабая игра под давлением: {weighted_loss_rate:.1f}% взвешенных поражений",
                    severity_level=severity,
                    period_start=start_date,
                    period_end=end_date,
                    # is_active=True
                    is_pair=False
                )
                trigger.set_metadata({
                    "pressure_matches": total_pressure_matches,
                    "weighted_losses": weighted_losses,
                    "weighted_loss_rate": weighted_loss_rate,
                    "recommendation": "Специальная подготовка к ответственным матчам, работа над психологической устойчивостью"
                })

                self.db.add(trigger)
                triggers.append(trigger)

        return triggers



        
    def _log_trigger_with_specific_matches(self, trigger: PlayerTrigger, trigger_count: int, total_triggers: int):
        """Логирует детали найденного триггера с конкретными матчами, где проявился триггер"""
        # Из кеша вместо db.query(Player)
        player = self._players_cache.get(trigger.player_id)
        if not player:
            logger.warning(f"Игрок с ID {trigger.player_id} не найден")
            return
        # Prepare directory for logs
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
        logs_dir = os.path.join(project_root, 'trigger_logs')
        os.makedirs(logs_dir, exist_ok=True)
        # Build file path
        file_name = f"{trigger.trigger_type}_{trigger.id}.txt"
        file_path = os.path.join(logs_dir, file_name)
        # Collect log lines
        lines = []
        lines.append(f"Название триггера: {trigger.trigger_type}")
        lines.append("Список игроков:")
        lines.append(f"- {player.full_name}")
        # Лига игрока неизвестна в модели, выводим как н/д
        lines.append(f"    • Лига: н/д")
        lines.append(f"    • Рейтинг: {player.current_rating}")
        # Матчи, где игрок ловит триггер
        matches = self._get_trigger_specific_matches(player, trigger)
        if matches:
            lines.append(f"    • Список матчей:")
            for idx, match in enumerate(matches, 1):
                opp_id = match.player2_id if match.player1_id == player.id else match.player1_id
                # Из кеша вместо db.query(Player)
                opponent = self._players_cache.get(opp_id)
                opp_name = opponent.full_name if opponent else "Неизвестный игрок"
                result = 'W' if match.winner_id == player.id else 'L'
                time_str = match.time.strftime("%H:%M") if match.time else "н/д"
                lines.append(f"       {idx}. {match.date} | {opp_name} ({result}, {match.score}, {time_str})")
        else:
            lines.append(f"    • Матчи не найдены")
        # Write collected lines to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        logger.info(f"Trigger details written to {file_path}")
    
    def _get_trigger_specific_matches(self, player: Player, trigger: PlayerTrigger) -> List[Match]:
        """Получает конкретные матчи, где проявился данный триггер (оптимизировано)"""
        # Из кеша вместо db.query(Match)
        all_player_matches = self._matches_by_player.get(player.id, [])
        base_matches = sorted(
            [m for m in all_player_matches 
             if trigger.period_start <= m.date <= trigger.period_end],
            key=lambda m: m.date, reverse=True
        )
        
        # Фильтруем матчи в зависимости от типа триггера
        trigger_matches = []
        
        if trigger.trigger_type == "defeat_0_3":
            # Показываем матчи с поражением 0:3
            for match in base_matches:
                if match.winner_id != player.id:  # Только поражения
                    if match.player1_id == player.id:
                        player_sets = match.sets_player1 or 0
                        opponent_sets = match.sets_player2 or 0
                    else:
                        player_sets = match.sets_player2 or 0
                        opponent_sets = match.sets_player1 or 0
                    
                    if player_sets == 0 and opponent_sets == 3:
                        trigger_matches.append(match)
        
        elif trigger.trigger_type == "won_2_lost_3rd_set":
            # Показываем матчи где выиграл 2 сета, но проиграл матч 2:3
            for match in base_matches:
                if match.player1_id == player.id:
                    player_sets = match.sets_player1 or 0
                    opponent_sets = match.sets_player2 or 0
                else:
                    player_sets = match.sets_player2 or 0
                    opponent_sets = match.sets_player1 or 0
                
                if player_sets == 2 and opponent_sets == 3:
                    trigger_matches.append(match)
        
        elif trigger.trigger_type == "losing_streaks":
            # Показываем последние поражения подряд
            consecutive_losses = []
            for match in base_matches:
                if match.winner_id != player.id and match.winner_id is not None:
                    consecutive_losses.append(match)
                else:
                    break
            trigger_matches = consecutive_losses[:5]  # Максимум 5 последних поражений
        
        elif trigger.trigger_type == "losers_50_percent":
            # Показываем все поражения за период
            for match in base_matches:
                if match.winner_id and match.winner_id != player.id:
                    trigger_matches.append(match)
        
        elif trigger.trigger_type == "top_performers":
            # Показываем все победы за период
            for match in base_matches:
                if match.winner_id == player.id:
                    trigger_matches.append(match)
        
        elif trigger.trigger_type == "time_performance":
            # Показываем матчи в проблемное время
            for match in base_matches:
                if match.time:
                    hour = match.time.hour
                    # Определяем проблемное время из метаданных триггера
                    if hasattr(trigger, 'trigger_subtype'):
                        if trigger.trigger_subtype == "day" and 8 <= hour < 18:
                            trigger_matches.append(match)
                        elif trigger.trigger_subtype == "evening" and 18 <= hour < 22:
                            trigger_matches.append(match)
                        elif trigger.trigger_subtype == "night" and (hour >= 22 or hour < 8):
                            trigger_matches.append(match)
        
        elif trigger.trigger_type == "early_final_exit_advanced":
            # Показываем финальные матчи с поражениями
            for match in base_matches:
                if match.is_final and match.winner_id != player.id:
                    trigger_matches.append(match)
        
        elif trigger.trigger_type == "post_holiday_problems":
            # Показываем матчи после праздников (если есть информация о праздниках)
            trigger_matches = base_matches[:5]  # Показываем последние матчи
        
        else:
            # Для остальных типов триггеров показываем все матчи
            trigger_matches = base_matches[:10]  # Максимум 10 матчей
        
        return trigger_matches[:10]  # Ограничиваем 10 матчами для читаемости
    
    def _analyze_opponent_strength(self, player: Player, matches: List[Match]) -> Dict:
        """Анализирует результаты против соперников разной силы"""
        strong_opp = {"matches": 0, "wins": 0}  # Соперник сильнее на 200+
        equal_opp = {"matches": 0, "wins": 0}   # Соперник ±200
        weak_opp = {"matches": 0, "wins": 0}    # Соперник слабее на 200+
        
        for match in matches:
            opponent_id = match.player2_id if match.player1_id == player.id else match.player1_id
            # Из кеша вместо db.query(Player)
            opponent = self._players_cache.get(opponent_id)
            
            if not opponent or not opponent.current_rating or not player.current_rating:
                continue
            
            rating_diff = player.current_rating - opponent.current_rating
            won = match.winner_id == player.id
            
            if rating_diff <= -200:  # Соперник сильнее
                strong_opp["matches"] += 1
                if won: strong_opp["wins"] += 1
            elif -200 < rating_diff < 200:  # Примерно равные
                equal_opp["matches"] += 1
                if won: equal_opp["wins"] += 1
            else:  # Соперник слабее
                weak_opp["matches"] += 1
                if won: weak_opp["wins"] += 1
        
        return {
            "strong": {
                "matches": strong_opp["matches"],
                "wins": strong_opp["wins"],
                "winrate": (strong_opp["wins"] / strong_opp["matches"] * 100) if strong_opp["matches"] > 0 else 0
            },
            "equal": {
                "matches": equal_opp["matches"],
                "wins": equal_opp["wins"],
                "winrate": (equal_opp["wins"] / equal_opp["matches"] * 100) if equal_opp["matches"] > 0 else 0
            },
            "weak": {
                "matches": weak_opp["matches"],
                "wins": weak_opp["wins"],
                "winrate": (weak_opp["wins"] / weak_opp["matches"] * 100) if weak_opp["matches"] > 0 else 0
            }
        }
    
    def _analyze_time_of_day_performance(self, player: Player, matches: List[Match]) -> Dict:
        """Анализирует результаты по времени суток"""
        time_stats = {
            "morning": {"matches": 0, "wins": 0},    # 6-12
            "day": {"matches": 0, "wins": 0},        # 12-18
            "evening": {"matches": 0, "wins": 0},    # 18-22
            "night": {"matches": 0, "wins": 0}       # 22-6
        }
        
        for match in matches:
            if not match.time:
                continue
            
            hour = match.time.hour if isinstance(match.time, datetime) else int(match.time.split(':')[0]) if isinstance(match.time, str) else None
            if hour is None:
                continue
            
            won = match.winner_id == player.id
            
            if 6 <= hour < 12:
                period = "morning"
            elif 12 <= hour < 18:
                period = "day"
            elif 18 <= hour < 22:
                period = "evening"
            else:
                period = "night"
            
            time_stats[period]["matches"] += 1
            if won:
                time_stats[period]["wins"] += 1
        
        result = {}
        for period, stats in time_stats.items():
            result[period] = {
                "matches": stats["matches"],
                "wins": stats["wins"],
                "winrate": (stats["wins"] / stats["matches"] * 100) if stats["matches"] > 0 else 0
            }
        
        return result
    
    def _analyze_serve_receive_efficiency(self, player: Player, matches: List[Match]) -> Dict:
        """Анализирует эффективность подачи и приёма"""
        serve_total = []
        receive_total = []
        serve_wins = []
        receive_wins = []
        serve_losses = []
        receive_losses = []
        
        for match in matches:
            won = match.winner_id == player.id
            
            # Получаем эффективность из матча (правильные имена полей!)
            if match.player1_id == player.id:
                serve_eff = match.serve_efficiency_p1
                receive_eff = match.receive_efficiency_p1
            else:
                serve_eff = match.serve_efficiency_p2
                receive_eff = match.receive_efficiency_p2
            
            if serve_eff is not None:
                serve_total.append(serve_eff)
                if won:
                    serve_wins.append(serve_eff)
                else:
                    serve_losses.append(serve_eff)
            
            if receive_eff is not None:
                receive_total.append(receive_eff)
                if won:
                    receive_wins.append(receive_eff)
                else:
                    receive_losses.append(receive_eff)
        
        return {
            "serve": {
                "avg": sum(serve_total) / len(serve_total) if serve_total else 0,
                "in_wins": sum(serve_wins) / len(serve_wins) if serve_wins else 0,
                "in_losses": sum(serve_losses) / len(serve_losses) if serve_losses else 0
            },
            "receive": {
                "avg": sum(receive_total) / len(receive_total) if receive_total else 0,
                "in_wins": sum(receive_wins) / len(receive_wins) if receive_wins else 0,
                "in_losses": sum(receive_losses) / len(receive_losses) if receive_losses else 0
            }
        }
    
    def _analyze_favorite_underdog_performance(self, player: Player, matches: List[Match]) -> Dict:
        """Анализирует игру в роли фаворита и аутсайдера"""
        favorite_stats = {"matches": 0, "wins": 0}
        underdog_stats = {"matches": 0, "wins": 0}
        
        for match in matches:
            opponent_id = match.player2_id if match.player1_id == player.id else match.player1_id
            # Из кеша вместо db.query(Player)
            opponent = self._players_cache.get(opponent_id)
            
            if not opponent or not opponent.current_rating or not player.current_rating:
                continue
            
            won = match.winner_id == player.id
            is_favorite = player.current_rating > opponent.current_rating
            
            if is_favorite:
                favorite_stats["matches"] += 1
                if won: favorite_stats["wins"] += 1
            else:
                underdog_stats["matches"] += 1
                if won: underdog_stats["wins"] += 1
        
        return {
            "favorite": {
                "matches": favorite_stats["matches"],
                "wins": favorite_stats["wins"],
                "winrate": (favorite_stats["wins"] / favorite_stats["matches"] * 100) if favorite_stats["matches"] > 0 else 0
            },
            "underdog": {
                "matches": underdog_stats["matches"],
                "wins": underdog_stats["wins"],
                "winrate": (underdog_stats["wins"] / underdog_stats["matches"] * 100) if underdog_stats["matches"] > 0 else 0
            }
        }

    def _extract_trigger_evidence(self, player: Player, trigger_type: str, matches: List[Match]) -> List[Dict]:
        """
        Извлекает конкретные матчи-доказательства для триггера.
        Оптимизировано: использует self._players_cache и self._sets_by_match (0 запросов к БД).
        """
        evidence = []
        
        def _get_opponent(match, is_player1):
            """Helper: получаем соперника из кеша"""
            opponent_id = match.player2_id if is_player1 else match.player1_id
            return self._players_cache.get(opponent_id)
        
        def _get_sets_details(match_id, is_player1):
            """Helper: получаем детали сетов из кеша"""
            match_sets = self._sets_by_match.get(match_id, [])
            details = []
            for set_data in match_sets:
                player_points = set_data.player1_points if is_player1 else set_data.player2_points
                opponent_points = set_data.player2_points if is_player1 else set_data.player1_points
                won_set = set_data.winner_id == player.id
                details.append({
                    'set_number': set_data.set_number,
                    'player_points': player_points,
                    'opponent_points': opponent_points,
                    'won': won_set
                })
            return details
        
        def _build_evidence_entry(match, is_player1, highlight):
            """Helper: собираем evidence запись без запросов к БД"""
            opponent = _get_opponent(match, is_player1)
            player_sets = match.sets_player1 if is_player1 else match.sets_player2
            opponent_sets = match.sets_player2 if is_player1 else match.sets_player1
            rating_diff = (player.current_rating or 0) - (opponent.current_rating or 0) if opponent and opponent.current_rating else 0
            
            return {
                'date': match.date.strftime('%d.%m.%Y'),
                'time': match.time.strftime('%H:%M') if match.time else None,
                'opponent': opponent.full_name if opponent else 'Неизвестный',
                'opponent_rating': opponent.current_rating if opponent else None,
                'score': f"{player_sets}:{opponent_sets}",
                'sets': _get_sets_details(match.id, is_player1),
                'highlight': highlight,
                'serve_efficiency': match.serve_efficiency_p1 if is_player1 else match.serve_efficiency_p2,
                'receive_efficiency': match.receive_efficiency_p1 if is_player1 else match.receive_efficiency_p2,
                'was_favorite': rating_diff > 0,
                'rating_diff': rating_diff,
                'red_flags': self._identify_match_red_flags(match, player, is_player1)
            }
        
        if trigger_type in ['led_2_sets_lost_match', 'won_2_lost_3rd_set', 'led_2_sets_lost']:
            for match in matches:
                if match.winner_id == player.id:
                    continue  # Интересуют только проигранные матчи
                
                is_player1 = match.player1_id == player.id
                
                # Проверяем по сетам: игрок выиграл ИМЕННО 1-й И 2-й сет
                match_sets = self._sets_by_match.get(match.id, [])
                if len(match_sets) < 3:
                    continue
                
                sets_by_number = {s.set_number: s for s in match_sets}
                set1 = sets_by_number.get(1)
                set2 = sets_by_number.get(2)
                
                if not set1 or not set2:
                    continue
                
                won_set_1 = (set1.winner_id == player.id)
                won_set_2 = (set2.winner_id == player.id)
                
                if won_set_1 and won_set_2:
                    # Проверяем что проиграл оставшиеся сеты
                    remaining_lost = sum(1 for s in match_sets if s.set_number > 2 and s.winner_id and s.winner_id != player.id)
                    if remaining_lost >= 2:
                        player_sets = match.sets_player1 if is_player1 else match.sets_player2
                        opponent_sets = match.sets_player2 if is_player1 else match.sets_player1
                        evidence.append(_build_evidence_entry(match, is_player1, f'Вёл 2:0 по сетам, проиграл {player_sets}:{opponent_sets}'))
        
        elif trigger_type in ['weaker_opponent_losses', 'loses_to_weaker']:
            for match in matches:
                if match.winner_id == player.id:
                    continue
                    
                is_player1 = match.player1_id == player.id
                opponent = _get_opponent(match, is_player1)
                
                if not opponent or not opponent.current_rating or not player.current_rating:
                    continue
                
                rating_diff = player.current_rating - opponent.current_rating
                
                if rating_diff >= 200:
                    evidence.append(_build_evidence_entry(match, is_player1, f'Проиграл слабому (-{rating_diff} рейтинга)'))
        
        elif trigger_type in ['defeat_0_3', 'shutout_losses']:
            for match in matches:
                if match.winner_id == player.id:
                    continue
                    
                is_player1 = match.player1_id == player.id
                player_sets = match.sets_player1 if is_player1 else match.sets_player2
                opponent_sets = match.sets_player2 if is_player1 else match.sets_player1
                
                if player_sets == 0 and opponent_sets == 3:
                    evidence.append(_build_evidence_entry(match, is_player1, 'Сухое поражение 0:3'))
        
        elif trigger_type in ['losing_streaks']:
            consecutive_losses = []
            for match in matches:
                if match.winner_id != player.id and match.winner_id is not None:
                    consecutive_losses.append(match)
                else:
                    break
            
            for match in consecutive_losses[:10]:
                is_player1 = match.player1_id == player.id
                evidence.append(_build_evidence_entry(match, is_player1, f'Поражение #{len(evidence)+1} в серии'))
        
        elif trigger_type in ['time_performance', 'night_performance']:
            for match in matches:
                if not match.time:
                    continue
                    
                hour = match.time.hour
                if hour < 22 and hour >= 6:
                    continue
                
                is_player1 = match.player1_id == player.id
                won = match.winner_id == player.id
                
                if won:
                    continue
                
                evidence.append(_build_evidence_entry(match, is_player1, f'Ночной матч ({hour}:00 - подозрительное время)'))
        
        return evidence[:10]
    
    def _identify_match_red_flags(self, match: Match, player: Player, is_player1: bool) -> List[str]:
        """
        Выявляет подтриггеры/аномалии в конкретном матче
        """
        flags = []
        
        # Получаем данные игрока
        serve_eff = match.serve_efficiency_p1 if is_player1 else match.serve_efficiency_p2
        receive_eff = match.receive_efficiency_p1 if is_player1 else match.receive_efficiency_p2
        player_sets = match.sets_player1 if is_player1 else match.sets_player2
        opponent_sets = match.sets_player2 if is_player1 else match.sets_player1
        
        # Подтриггер 1: Критически низкая подача
        if serve_eff is not None and serve_eff < 0.40:
            flags.append(f"Низкая подача ({serve_eff*100:.0f}%)")
        
        # Подтриггер 2: Критически низкий прием
        if receive_eff is not None and receive_eff < 0.35:
            flags.append(f"Низкий прием ({receive_eff*100:.0f}%)")
        
        # Подтриггер 3: Коллапс после лидерства 2:0
        if player_sets == 2 and opponent_sets == 3:
            flags.append("Коллапс 2:3")
        
        # Подтриггер 4: Сухое поражение
        if player_sets == 0 and opponent_sets == 3:
            flags.append("Поражение 0:3")
        
        # Подтриггер 5: Ночное время (22:00-06:00)
        if match.time:
            hour = match.time.hour
            if hour >= 22 or hour < 6:
                flags.append(f"Ночной матч ({match.time.strftime('%H:%M')})")
            # Подтриггер 6: Раннее утро (06:00-09:00)
            elif 6 <= hour < 9:
                flags.append(f"Ранний матч ({match.time.strftime('%H:%M')})")
        
        # Подтриггер 7: Очень низкая комбинированная эффективность
        if serve_eff is not None and receive_eff is not None:
            combined = (serve_eff + receive_eff) / 2
            if combined < 0.35:
                flags.append(f"Общая эффективность {combined*100:.0f}%")
        
        return flags

    def _calculate_collapse_rate(self, player: Player, matches: List[Match]) -> float:
        """
        Рассчитывает процент матчей, где игрок вел 2:0 по сетам и проиграл.
        Это один из ключевых индикаторов потенциального мошенничества.
        """
        collapses = 0
        lead_situations = 0
        
        for match in matches:
            is_player1 = match.player1_id == player.id
            
            # Получаем количество сетов
            player_sets = match.sets_player1 if is_player1 else match.sets_player2
            opponent_sets = match.sets_player2 if is_player1 else match.sets_player1
            
            if player_sets is None or opponent_sets is None:
                continue
            
            # Проверяем ситуацию лидерства 2:0
            # Если игрок выиграл 2 сета, но проиграл матч (противник выиграл 3)
            if player_sets == 2 and opponent_sets == 3:
                lead_situations += 1
                collapses += 1
            # Если игрок выиграл 2+ сета и в итоге выиграл - это НЕ коллапс
            elif player_sets >= 2 and match.winner_id == player.id:
                lead_situations += 1
        
        return (collapses / lead_situations * 100) if lead_situations > 0 else 0
    
    def _calculate_serve_efficiency_variance(self, player: Player, matches: List[Match]) -> float:
        """
        Рассчитывает стандартное отклонение эффективности подачи.
        Высокая волатильность может указывать на непредсказуемое поведение.
        """
        import numpy as np
        
        serve_efficiencies = []
        
        for match in matches:
            is_player1 = match.player1_id == player.id
            serve_eff = match.serve_efficiency_p1 if is_player1 else match.serve_efficiency_p2
            
            if serve_eff is not None:
                serve_efficiencies.append(serve_eff)
        
        if len(serve_efficiencies) < 3:
            return 0.0
        
        return float(np.std(serve_efficiencies))
    
    def _calculate_suspicion_score(self, player_stats: Dict) -> float:
        """
        Вычисляет общий балл подозрительности игрока (0-1).
        
        Использует взвешенную сумму различных индикаторов:
        - Поражения от слабых соперников (25%)
        - Коллапсы после лидерства 2:0 (30%)
        - Волатильность эффективности подачи (20%)
        - Временные аномалии (день/ночь) (15%)
        - Разница в игре фаворит/андердог (10%)
        
        Returns:
            float: Балл от 0 до 1, где 1 = максимально подозрительно
        """
        score = 0.0
        
        # 1. Поражения от слабых соперников (вес 0.25)
        opponent_analysis = player_stats.get('opponent_analysis', {})
        vs_weaker = opponent_analysis.get('vs_weaker', {})
        vs_weaker_winrate = vs_weaker.get('winrate', 100) / 100  # нормализуем в [0, 1]
        
        if vs_weaker_winrate < 0.50:  # винрейт против слабых < 50%
            # Чем ниже винрейт против слабых, тем подозрительнее
            score += 0.25 * (1 - vs_weaker_winrate)
        
        # 2. Коллапсы после лидерства (вес 0.30) - САМЫЙ ВАЖНЫЙ ИНДИКАТОР
        collapse_rate = player_stats.get('collapse_rate', 0) / 100  # нормализуем
        score += 0.30 * collapse_rate
        
        # 3. Волатильность эффективности подачи (вес 0.20)
        serve_variance = player_stats.get('serve_efficiency_variance', 0)
        if serve_variance > 0.20:  # стандартное отклонение > 20%
            # Нормализуем к 50% как максимум
            normalized_variance = min(serve_variance / 0.5, 1.0)
            score += 0.20 * normalized_variance
        
        # 4. Временные аномалии - разница день/ночь (вес 0.15)
        time_performance = player_stats.get('time_performance', {})
        night_wr = time_performance.get('night', {}).get('winrate', 50) / 100
        day_wr = time_performance.get('day', {}).get('winrate', 50) / 100
        time_diff = abs(night_wr - day_wr)
        
        if time_diff > 0.30:  # разница > 30%
            score += 0.15 * (time_diff / 0.5)  # нормализуем к 50% как максимум
        
        # 5. Разница в роли фаворит/андердог (вес 0.10)
        role_performance = player_stats.get('role_performance', {})
        favorite_wr = role_performance.get('favorite', {}).get('winrate', 50) / 100
        underdog_wr = role_performance.get('underdog', {}).get('winrate', 50) / 100
        
        if favorite_wr > 0 and underdog_wr > 0:
            role_gap = abs(favorite_wr - underdog_wr)
            if role_gap > 0.40:  # разница > 40%
                score += 0.10 * (role_gap / 0.6)  # нормализуем к 60% как максимум
        
        # Ограничиваем результат [0, 1]
        return min(score, 1.0)

    def _get_player_stats_for_trigger(self, player_id: str, start_date: date, end_date: date) -> dict:
        """Получает статистику игрока для триггера (оптимизировано — 0 запросов к БД)"""
        # Из кеша вместо db.query(Player)
        player = self._players_cache.get(player_id)
        if not player:
            return {}
        
        # Из кеша вместо db.query(Match)
        matches = self._matches_by_player.get(player_id, [])
        matches = sorted(matches, key=lambda m: m.date, reverse=True)
        
        if not matches:
            return {}
        
        # Подсчитываем базовую статистику
        wins = len([m for m in matches if m.winner_id == player.id])
        losses = len([m for m in matches if m.winner_id and m.winner_id != player.id])
        
        sets_won = 0
        sets_lost = 0
        recent_form = []
        recent_matches = []
        
        # Анализируем последние 5 матчей для формы
        for match in matches[:5]:
            if match.winner_id == player.id:
                recent_form.append('W')
            else:
                recent_form.append('L')
            
            # Определяем оппонента из кеша
            opponent_id = match.player2_id if match.player1_id == player.id else match.player1_id
            opponent = self._players_cache.get(opponent_id)
            opponent_name = opponent.full_name if opponent else "Неизвестный игрок"
            
            # Получаем результат и счет
            result = 'W' if match.winner_id == player.id else 'L'
            
            # Подсчитываем сеты
            if match.player1_id == player.id:
                player_sets = match.sets_player1 or 0
                opponent_sets = match.sets_player2 or 0
            else:
                player_sets = match.sets_player2 or 0
                opponent_sets = match.sets_player1 or 0
            
            sets_won += player_sets
            sets_lost += opponent_sets
            
            # Формируем информацию о матче
            match_info = {
                "date": match.date.strftime("%d.%m.%Y"),
                "opponent": opponent_name,
                "result": result,
                "score": match.score or f"{player_sets}:{opponent_sets}",
                "time": match.time.strftime("%H:%M") if match.time else None
            }
            recent_matches.append(match_info)
        
        # Общая статистика по всем матчам за период
        for match in matches[5:]:
            if match.player1_id == player.id:
                sets_won += match.sets_player1 or 0
                sets_lost += match.sets_player2 or 0
            else:
                sets_won += match.sets_player2 or 0
                sets_lost += match.sets_player1 or 0
        
        win_rate = (wins / len(matches)) * 100 if matches else 0
        set_win_rate = (sets_won / (sets_won + sets_lost) * 100) if (sets_won + sets_lost) > 0 else 0
        
        # НОВОЕ: Расширенный анализ
        opponent_analysis = self._analyze_opponent_strength(player, matches)
        time_performance = self._analyze_time_of_day_performance(player, matches)
        serve_receive = self._analyze_serve_receive_efficiency(player, matches)
        role_performance = self._analyze_favorite_underdog_performance(player, matches)
        
        # Динамика формы (последние 10 и 20 матчей)
        last10_wins = len([m for m in matches[:10] if m.winner_id == player.id])
        last20_wins = len([m for m in matches[:20] if m.winner_id == player.id])
        last10_winrate = (last10_wins / min(10, len(matches)) * 100) if len(matches) > 0 else 0
        last20_winrate = (last20_wins / min(20, len(matches)) * 100) if len(matches) > 0 else 0
        
        # Определяем тренд
        if len(matches) >= 20:
            if last10_winrate > last20_winrate + 10:
                trend = "улучшается"
                trend_icon = "↗️"
            elif last10_winrate < last20_winrate - 10:
                trend = "ухудшается"
                trend_icon = "↘️"
            else:
                trend = "стабилен"
                trend_icon = "→"
        else:
            trend = "недостаточно данных"
            trend_icon = "?"
        
        # НОВОЕ: Метрики подозрительности
        collapse_rate = self._calculate_collapse_rate(player, matches)
        serve_efficiency_variance = self._calculate_serve_efficiency_variance(player, matches)
        
        # Формируем полную статистику
        stats = {
            "matches_played": len(matches),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "sets_won": sets_won,
            "sets_lost": sets_lost,
            "set_win_rate": set_win_rate,
            "recent_form": ''.join(recent_form),
            "recent_matches": recent_matches,
            "opponent_analysis": opponent_analysis,
            "time_performance": time_performance,
            "serve_receive": serve_receive,
            "role_performance": role_performance,
            "last10_winrate": last10_winrate,
            "last20_winrate": last20_winrate,
            "trend": trend,
            "trend_icon": trend_icon,
            "collapse_rate": collapse_rate,
            "serve_efficiency_variance": serve_efficiency_variance
        }
        
        suspicion_score = self._calculate_suspicion_score(stats)
        stats["suspicion_score"] = suspicion_score
        
        return stats

    async def _generate_ai_analysis(self, player_name: str, trigger_value: str ,  player_stats: Dict, provider: str = "lmstudio") -> str:
        """Генерирует ИИ-анализ для игрока (поддерживает Ollama и LM Studio)"""
        if not self._ai_analysis_enabled:
            print(f"⚠️ AI-анализ отключен для игрока {player_name}")
            return None  
        
        try:
            print(f"\n{'='*60}")
            print(f"🤖 Генерация AI-анализа")
            print(f"👤 Игрок: {player_name}")
            print(f"🎯 Провайдер: {provider}")
            print(f"📦 Модель: {self._selected_model or 'по умолчанию'}")
            print(f"🎯 Max токенов: {self._max_tokens}")
            print(f"{'='*60}\n")
            print("AHHAHAHAHAHAHHAAHHAHAHAHAHAHHAHAHAHAHA")
            prompt = self._create_analysis_prompt(player_name, trigger_value, player_stats)
            
            # Определяем провайдера и модель из settings
            from app.core.config import settings
            
            # Используем переданный провайдер (или lmstudio по умолчанию)
            provider = provider or "lmstudio"
            logger.info(f"🎯 AI-анализ: провайдер={provider}, игрок={player_name}")
            
            if provider == "lmstudio":
                api_url = f"{settings.LM_STUDIO_API_URL}/v1/chat/completions"
                model = self._selected_model or "gpt-oss-20b"
                logger.info(f"🔷 Используем LM Studio для AI-анализа: {api_url}")
                print(f"🔷 API URL: {api_url}")
                print(f"🔷 Модель: {model}")
            else:
                # Ollama использует свой формат API
                api_url = f"{settings.OLLAMA_API_URL}/api/chat"
                # Для Ollama используем другую модель (GPT-OSS доступен только в LM Studio)
                model = self._selected_model or "llama3.1:8b"
                logger.info(f"🟢 Используем Ollama для AI-анализа: {api_url}")
                print(f"🟢 API URL: {api_url}")
                print(f"🟢 Модель: {model}")
            
            # Отправляем запрос
            print(f"📤 Отправка запроса...")
            print("AHHAHAHAHAHAHHAAHHAHAHAHAHAHHAHAHAHAHA")
            request_data = {
                "model": model,
                "stream": True,
                "messages": [
                    {
                        "role": "system", 
                        "content": "Ты аналитик по настольному теннису. Пиши на русском языке подробный анализ причин нестандартного поведения игрока на основе предоставленных статистических данных. Приводи конкретные примеры из статистики. Отвечай только на основе предоставленных данных. Если данных недостаточно, честно скажи, что не можешь сделать выводы."
                    },
                    {"role": "user", "content": prompt}
                ]
            }
            
            # Добавляем max_tokens для LM Studio (OpenAI API)
            if provider == "lmstudio":
                request_data["max_tokens"] = self._max_tokens  # Используем настройку из фронтенда
            
            # Увеличенный таймаут: 120 сек для LMStudio (загрузка модели + генерация)
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", api_url, json=request_data) as response:
                    
                    # Проверяем статус ответа
                    print(f"📨 Статус ответа: {response.status_code}")
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_msg = f"HTTP {response.status_code}: {error_text[:200]}"
                        logger.error(f"❌ {error_msg}")
                        print(f"❌ Ошибка: {error_msg}")
                        return f"Ошибка {provider}: {error_msg}"
                    
                    print(f"✅ Соединение установлено, получаем ответ...")
                    analysis_text = ""
                    chunk_count = 0
                    error_count = 0
                    first_raw_line_shown = False
                    
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        
                        # Показываем первую сырую строку для диагностики
                        if not first_raw_line_shown:
                            print(f"🔍 Первая строка от сервера (длина {len(line)}):")
                            print(f"   [{line[:200]}...]" if len(line) > 200 else f"   [{line}]")
                            first_raw_line_shown = True
                        
                        # LM Studio отправляет в формате SSE с префиксом "data: "
                        if line.startswith("data: "):
                            line = line[6:]  # Убираем "data: " (6 символов)
                        
                        # Пропускаем маркер окончания SSE
                        if line.strip() == "[DONE]":
                            print(f"🏁 Получен маркер окончания [DONE]")
                            break
                        
                        try:
                            data = json.loads(line)
                            chunk_count += 1
                            
                            # Ollama формат: {"message": {"content": "..."}}
                            if "message" in data and "content" in data["message"]:
                                chunk = data["message"]["content"]
                                analysis_text += chunk
                                if chunk_count == 1 or chunk_count % 20 == 0:
                                    print(f"📥 Получено чанков: {chunk_count}, длина: {len(analysis_text)}")
                            
                            # LM Studio (OpenAI) формат: {"choices": [{"delta": {"content": "..."}}]}
                            elif "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                
                                chunk = delta.get("content", "")
                                
                                if chunk:  # Добавляем только если есть текст
                                    analysis_text += chunk
                                    if chunk_count == 1 or chunk_count % 20 == 0:
                                        print(f"📥 Получено чанков: {chunk_count}, длина: {len(analysis_text)}")
                            
                            # Показываем структуру первого JSON для диагностики        
                            elif chunk_count <= 2:  # Показываем первые 2 неожиданных
                                print(f"⚠️ Неожиданная структура JSON (чанк #{chunk_count}):")
                                print(f"   Ключи: {list(data.keys())}")
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    print(f"   delta ключи: {list(delta.keys())}")
                                print(f"   Данные: {str(data)[:300]}")
                                    
                        except json.JSONDecodeError as json_err:
                            error_count += 1
                            if error_count <= 3:  # Показываем первые 3 ошибки
                                print(f"⚠️ Ошибка JSON #{error_count}: {json_err}")
                                print(f"   Строка (первые 100 символов): [{line[:100]}]")
                            continue
                    
                    print(f"\n✅ Анализ завершен!")
                    print(f"📊 Всего чанков: {chunk_count}")
                    print(f"⚠️ Ошибок JSON: {error_count}")
                    print(f"📏 Длина текста: {len(analysis_text)} символов")
                    print(f"{'='*60}\n")
                    
                    if analysis_text.strip():
                        # НЕ удаляем <think>...</think> блоки - фронт сам обрежет
                        # analysis_text = re.sub(r'<think>.*?</think>', '', analysis_text, flags=re.DOTALL)
                        return analysis_text.strip()
                    else:
                        logger.warning(f"⚠️ Пустой ответ от {provider}")
                        print(f"⚠️ ВНИМАНИЕ: Получен пустой ответ!")
                        print(f"   Возможные причины:")
                        print(f"   1. Сервер вернул не JSON (проверьте строку выше)")
                        print(f"   2. Неправильный формат ответа")
                        print(f"   3. Модель не загружена")
                        return f"Модель не вернула анализ для {player_name}"
                    
        except httpx.TimeoutException as timeout_err:
            error_msg = f"Таймаут подключения к {provider} (30 сек)"
            logger.error(f"⏱️ {error_msg}: {timeout_err}")
            print(f"⏱️ {error_msg}")
            return f"⏱️ {error_msg}. Проверьте что сервер запущен."
            
        except httpx.ConnectError as conn_err:
            error_msg = f"Не удалось подключиться к {provider}"
            logger.error(f"🔌 {error_msg}: {conn_err}")
            print(f"🔌 {error_msg}")
            print(f"🔌 Проверьте:")
            print(f"   - Запущен ли {provider}?")
            print(f"   - Правильный ли URL: {api_url if 'api_url' in locals() else 'N/A'}?")
            return f"🔌 {error_msg}. Запустите сервер."
            
        except Exception as e:
            logger.error(f"💥 Неожиданная ошибка: {e}", exc_info=True)
            print(f"💥 КРИТИЧЕСКАЯ ОШИБКА:")
            print(f"   Тип: {type(e).__name__}")
            print(f"   Сообщение: {str(e)}")
            import traceback
            print(f"   Трейс:\n{traceback.format_exc()}")
            return f"💥 Ошибка: {str(e)}"
    
    def _create_analysis_prompt(self, player_name: str, trigger_value: str, player_stats: Dict) -> str:
        """Создает РАСШИРЕННЫЙ промпт для ИИ-анализа с использованием всех доступных данных"""
        # Пытаемся загрузить RAG данные
        dop_infa = []
        try:
            embeddings, metadata = load_data()
            dop_infa = search(trigger_value, embeddings, metadata, top_k=3)
            print(f"✅ RAG: Найдено {len(dop_infa)} релевантных фрагментов")
        except Exception as e:
            print(f"⚠️ RAG недоступен, продолжаем без базы знаний: {e}")
        
        # Извлекаем данные
        matches = player_stats.get('matches_played', 0)
        wins = player_stats.get('wins', 0)
        losses = player_stats.get('losses', 0)
        win_rate = player_stats.get('win_rate', 0)
        sets_won = player_stats.get('sets_won', 0)
        sets_lost = player_stats.get('sets_lost', 0)
        set_win_rate = player_stats.get('set_win_rate', 0)
        recent_form = player_stats.get('recent_form', '')
        
        # Расширенная статистика
        opponent_analysis = player_stats.get('opponent_analysis', {})
        time_performance = player_stats.get('time_performance', {})
        serve_receive = player_stats.get('serve_receive', {})
        role_performance = player_stats.get('role_performance', {})
        last10_winrate = player_stats.get('last10_winrate', 0)
        last20_winrate = player_stats.get('last20_winrate', 0)
        trend = player_stats.get('trend', 'неизвестно')
        trend_icon = player_stats.get('trend_icon', '?')
        
        # НОВОЕ: Метрики подозрительности
        suspicion_score = player_stats.get('suspicion_score', 0)
        collapse_rate = player_stats.get('collapse_rate', 0)
        serve_variance = player_stats.get('serve_efficiency_variance', 0)
        
        # Определяем уровень риска по suspicion_score
        if suspicion_score >= 0.7:
            risk_level = "КРИТИЧЕСКИЙ"
            risk_emoji = ""
        elif suspicion_score >= 0.5:
            risk_level = "ВЫСОКИЙ"
            risk_emoji = ""
        elif suspicion_score >= 0.3:
            risk_level = "СРЕДНИЙ"
            risk_emoji = ""
        else:
            risk_level = "НИЗКИЙ"
            risk_emoji = ""
        
        # Последние матчи
        recent_matches = player_stats.get('recent_matches', [])
        recent_matches_text = "\n".join([
            f"  • {m['date']}: vs {m['opponent']} - {m['result']} ({m['score']}) {m['time'] or ''}"
            for m in recent_matches[:5]
        ]) if recent_matches else "Нет данных"
        
        # RAG секция
        rag_section = ""
        if dop_infa:
            rag_texts = [f"  • {item['text']}" for item in dop_infa]
            rag_section = f"""
 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ:
{chr(10).join(rag_texts)}
"""
        
        prompt = f"""
Игрок: {player_name}

Статистика за период:
- Матчей сыграно: {matches}
- Побед: {wins} ({win_rate:.1f}%)
- Поражений: {losses}
- Последняя форма: {recent_form}

Обнаруженные триггеры:
{trigger_value}

Дополнительная информация из базы знаний:
{chr(10).join([item["text"] for item in dop_infa])}

Сделай профессиональный анализ игрока в 2-3 предложениях: объясни возможные причины проблем, сделай примерный прогноз дальнейшего развития игрока.
Не давай рекомендации по тренировкам или общие советы — только анализ поведения на основе статистики.
"""
        
        return prompt

