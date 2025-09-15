from typing import List, Optional, Dict, Any, Set
from datetime import datetime, date, time, timedelta
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

class MatchAnalysisService:
    """Сервис для анализа матчей и выявления триггеров"""
    
    def __init__(self, db: Session):
        self.db = db
        self.last_uploaded_player_ids = []  # Инстансовый список ID игроков из последнего загруженного файла

        # Добавляем функцию для ИИ-анализа
        self._ai_analysis_enabled = True  # Флаг для включения/выключения ИИ

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
    
    async def process_excel_data(self, excel_data: List[ExcelMatchData]) -> Dict[str, Any]:
        """Обрабатывает данные из Excel файла"""
        try:
            created_players = 0
            created_matches = 0
            skipped_duplicates = 0
            errors = []
            file_player_ids = set()  # Отслеживаем ID игроков из этого файла
            
            print(f"🔄 Начинаем обработку {len(excel_data)} строк из Excel...")
            
            for idx, match_data in enumerate(excel_data):
                try:
                    print(f"📝 Обрабатываем строку {idx + 1}: {match_data.игрок_1} vs {match_data.игрок_2}")
                    
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
                    
                    # Проверяем, не существует ли уже такой матч
                    if self._match_exists(match_date, player1.id, player2.id, match_data.счёт, match_data.время):
                        skipped_duplicates += 1
                        print(f"⏭️  Пропускаем дубликат: {match_data.игрок_1} vs {match_data.игрок_2} от {match_date} со счётом {match_data.счёт} со временем {match_data.время}")
                        continue
                    
                    # Создаем матч
                    match = await self._create_match_from_excel(match_data, player1, player2)
                    created_matches += 1
                    print(f"✅ Создан матч: {match_data.игрок_1} vs {match_data.игрок_2}")
                    
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

            return result
            
        except Exception as e:
            print(f"💥 Ошибка при обработке Excel данных: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_or_create_player(self, player_name: str, rating_str: Optional[str] = None) -> tuple[Player, bool]:
        """Получает существующего игрока или создает нового с рейтингом"""
        # Извлекаем рейтинг из отдельного поля или из имени игрока
        rating = 1000  # значение по умолчанию
        
        # Сначала пробуем получить рейтинг из отдельного поля
        if rating_str:
            try:
                cleaned = rating_str.replace(',', '.').strip()
                rating_float = float(cleaned)
                rating = int(round(rating_float))  # Округляем до ближайшего
                print(f"📊 Рейтинг из поля: {rating_str} -> {rating}")
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
        Ожидаемый формат data.счёт:
        - "2:3"                  -> только общий счёт
        - "2:3 (4-11 11-6 ...)"  -> общий счёт + результаты по сетам в скобках
        Функция корректно обрабатывает разные разделители и пробелы/запятые.
        """

        # 1) Парсим дату и время
        match_date = self._parse_date(data.дата)
        # попытка использовать метод parse_time, если есть
        time_parser = getattr(self, "parse_time", None)
        if callable(time_parser):
            match_time = time_parser(data.время)
        else:
            # если метода нет — попытка простого парсинга
            try:
                from datetime import datetime
                match_time = datetime.strptime(str(data.время), "%H:%M:%S").time() if data.время else None
            except Exception:
                match_time = None

        raw_score = str(data.счёт).strip() if data.счёт is not None else ""

        # 2) Регекс: извлечь общий счёт (например 2:3 или 2-3) и содержимое скобок (пересчёт сетов)
        # Поддерживаем формат: "2:3 (4-11 11-6)" или "2-3(4-11,11-6)" и т.п.
        m = re.match(r'^\s*([0-9]+[\:\-][0-9]+)\s*(?:\((.*)\))?\s*$', raw_score)
        overall_part = None
        sets_part = None
        if m:
            overall_part = m.group(1)
            sets_part = m.group(2)  # может быть None
        else:
            # если не подошёл шаблон — попробуем взять целиком как общий счёт
            overall_part = raw_score
            sets_part = None

        # Утилита — парсит пару "X:Y" или "X-Y" в ints
        def parse_pair(s):
            s = s.strip()
            sep = ':' if ':' in s else '-'
            left, right = s.split(sep)
            return int(left), int(right)

        # 3) Парсим детальные сеты из sets_part, если есть
        per_set_scores = []  # list of (p1_points, p2_points)
        if sets_part:
            # находим все вхождения "число[-–—]число" в скобочной части
            found = re.findall(r'(\d+\s*[-–—]\s*\d+)', sets_part)
            for token in found:
                # убираем пробелы вокруг дефиса и сплитим по любому типа дефиса
                token_clean = token.strip()
                parts = re.split(r'[-–—]', token_clean)
                try:
                    p1 = int(parts[0].strip())
                    p2 = int(parts[1].strip())
                    per_set_scores.append((p1, p2))
                except Exception:
                    # если парсинг конкретного сета не удался — пропускаем его
                    continue

        # 4) Если есть per_set_scores — подсчитываем sets_player1/sets_player2 по ним.
        sets_player1 = None
        sets_player2 = None
        if per_set_scores:
            sets_player1 = sum(1 for p1, p2 in per_set_scores if p1 > p2)
            sets_player2 = sum(1 for p1, p2 in per_set_scores if p2 > p1)

        # 5) Если per_set_scores отсутствуют или не дали корректный результат — используем общий результат
        if sets_player1 is None or sets_player2 is None:
            try:
                a, b = parse_pair(overall_part)
                sets_player1, sets_player2 = a, b
            except Exception:
                # не удалось распарсить общий результат — ставим 0:0 и логируем
                sets_player1, sets_player2 = 0, 0
                print(f"⚠️ Не удалось распарсить общий счёт '{raw_score}' для строки Excel.")

        # 6) Определяем победителя (если есть явный)
        if sets_player1 > sets_player2:
            winner_id = player1.id
        elif sets_player2 > sets_player1:
            winner_id = player2.id
        else:
            winner_id = None  # ничья/ошибка — оставим None

        # 7) Получаем/создаём лигу (как было)
        league = None
        if data.турнир:
            league = await self._get_or_create_league(data.турнир)

        # 8) Создаём объект Match
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
            is_semifinal=(bool(data.стадия) and "полуфинал" in str(data.стадия).lower())
        )

        # 9) Проверяем дубликат и сохраняем матч + сеты в транзакции
        try:
            # используем _match_exists как у тебя в коде (передавая те же параметры)
            if not self._match_exists(match_date, player1.id, player2.id, raw_score, data.время):
                self.db.add(match)
                # сначала flush, чтобы получить match.id (если используется автогенерация)
                try:
                    self.db.flush()
                except Exception:
                    # если flush не доступен в сессии - сделаем commit+refresh как запасной вариант
                    self.db.commit()
                    self.db.refresh(match)

                # если per_set_scores есть — сохраняем их в MatchSet
                if per_set_scores:
                    for i, (p1_pts, p2_pts) in enumerate(per_set_scores, start=1):
                        # кто победил в сете
                        if p1_pts > p2_pts:
                            set_winner = player1.id
                        elif p2_pts > p1_pts:
                            set_winner = player2.id
                        else:
                            set_winner = None

                        match_set = MatchSet(
                            match_id=match.id,
                            set_number=i,
                            player1_points=p1_pts,
                            player2_points=p2_pts,
                            winner_id=set_winner
                        )
                        self.db.add(match_set)

                # Финальный коммит
                self.db.commit()
                # Обновляем объект match из БД
                self.db.refresh(match)
            else:
                # дубликат — просто вернём существующий матч (если хочется, можно его загрузить)
                existing = self.db.query(Match).filter(
                    Match.date == match_date,
                    ((Match.player1_id == player1.id) & (Match.player2_id == player2.id)) | ((Match.player1_id == player2.id) & (Match.player2_id == player1.id)),
                    Match.score == raw_score
                ).first()
                if existing:
                    match = existing

        except SQLAlchemyError as e:
            # откатим транзакцию и вернём/запишем лог
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

            # Загружаем все матчи периода (одним запросом!)
            all_matches = self.db.query(Match).filter(
                and_(Match.date >= start_date, Match.date <= end_date)
            ).all()
            print(f"⚽ Загружено матчей за период: {len(all_matches)}")

            # Группируем матчи по игрокам
            matches_by_player = {}
            for match in all_matches:
                for pid in [match.player1_id, match.player2_id]:
                    matches_by_player.setdefault(pid, []).append(match)

            total_triggers = 0
            all_triggers = []

            # Определяем триггеры для анализа
            trigger_types = request.trigger_types or list(self.trigger_methods.keys())
            print(f"🎯 Типы триггеров для анализа: {trigger_types}")

            # Идём по игрокам
            for player in players:
                player_matches = matches_by_player.get(player.id, [])
                print(f"\n🔎 Игрок {player.full_name} ({player.id}), матчей: {len(player_matches)}")

                for trigger_type in trigger_types:
                    if trigger_type in self.trigger_methods:
                        method = self.trigger_methods[trigger_type]
                        triggers = await method(player, player_matches, start_date, end_date)
                        print(f"   ✅ {trigger_type}: найдено {len(triggers)}")
                        all_triggers.extend(triggers)
                        total_triggers += len(triggers)

            # Собираем статистику
            total_matches = len(all_matches)
            top_performers = await self._get_top_performers(start_date, end_date)
            problem_players = await self._get_problem_players(start_date, end_date)
            triggers = await self._get_all_triggers(start_date, end_date)

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
        
        for idx, stat in enumerate(player_stats[:10]):
            # Подсчитываем дополнительную статистику
            losses = stat['matches'] - stat['wins']
            sets_won = 0
            sets_lost = 0
            recent_form = []
            
            # Получаем последние 5 матчей для формы
            recent_matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    or_(Match.player1_id == stat['player'].id, Match.player2_id == stat['player'].id)
                )
            ).order_by(Match.date.desc()).limit(5).all()
            
            for match in recent_matches:
                if match.winner_id == stat['player'].id:
                    recent_form.append('W')
                else:
                    recent_form.append('L')
                
                # Подсчет сетов
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
        """Получает игроков с проблемами"""
        problem_players = []
        
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
            
            if len(matches) >= 3:  # Минимум 3 матча
                wins = len([m for m in matches if m.winner_id == player.id])
                losses = len([m for m in matches if m.winner_id and m.winner_id != player.id])
                loss_rate = (losses / len(matches)) * 100
                
                if loss_rate >= 60:  # Проблемные игроки с loss rate >= 60%
                    player_stats.append({
                        'player': player,
                        'loss_rate': loss_rate,
                        'matches': len(matches),
                        'wins': wins,
                        'losses': losses
                    })
        
        # Сортируем по loss_rate (по убыванию - самые проблемные сначала)
        player_stats.sort(key=lambda x: x['loss_rate'], reverse=True)
        
        for idx, stat in enumerate(player_stats[:10]):
            # Подсчитываем дополнительную статистику
            sets_won = 0
            sets_lost = 0
            recent_form = []
            losing_streak = 0
            current_streak = 0
            
            # Получаем все матчи игрока для анализа
            all_matches = self.db.query(Match).filter(
                and_(
                    Match.date >= start_date,
                    Match.date <= end_date,
                    or_(Match.player1_id == stat['player'].id, Match.player2_id == stat['player'].id)
                )
            ).order_by(Match.date.desc()).all()
            
            # Анализируем форму и серии поражений
            for match in all_matches[:5]:  # Последние 5 матчей для формы
                if match.winner_id == stat['player'].id:
                    recent_form.append('W')
                else:
                    recent_form.append('L')
            
            # Подсчет текущей серии поражений
            for match in all_matches:
                if match.winner_id != stat['player'].id:
                    current_streak += 1
                else:
                    break
            
            # Подсчет сетов
            for match in all_matches:
                if match.player1_id == stat['player'].id:
                    sets_won += match.sets_player1 or 0
                    sets_lost += match.sets_player2 or 0
                else:
                    sets_won += match.sets_player2 or 0
                    sets_lost += match.sets_player1 or 0
            
            # Подсчет количества триггеров для этого игрока
            triggers_count = self.db.query(PlayerTrigger).filter(
                and_(
                    PlayerTrigger.player_id == stat['player'].id,
                    PlayerTrigger.period_start == start_date,
                    PlayerTrigger.period_end == end_date
                )
            ).count()
            
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
    
    async def _get_all_triggers(self, start_date: date, end_date: date) -> List[dict]:
        """
        Получает все триггеры за период.
        Генерирует персональный ИИ-анализ **один раз на игрока**, объединяя все триггеры (лимит 8).
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

        result = []

        for player_id, player_triggers in players_triggers.items():
            player = self.db.query(Player).filter(Player.id == player_id).first()
            player_stats = self._get_player_stats_for_trigger(player_id, start_date, end_date) or {}

            # Генерируем ИИ-анализ один раз на игрока, объединяя первые 8 триггеров
            limited_triggers = player_triggers[:8]
            trigger_values_combined = "\n".join([t.trigger_value for t in limited_triggers])
            ai_text = await self._generate_ai_analysis(
                player.full_name if player else "Неизвестный игрок",
                trigger_values_combined,
                player_stats
            )

            # Добавляем каждый триггер в результат, но AI-анализ общий для игрока
            for trigger in player_triggers:
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
                    "is_active": trigger.is_active,
                    "trigger_metadata": trigger.trigger_metadata,
                    "created_at": trigger.created_at,
                    "player_stats": player_stats if player_stats else None,
                    "ai_analysis": ai_text  # один AI-анализ на игрока
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
                is_active=True
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

        # 1) Выбираем праздники, которые **пересекают** расширенный период анализа
        holidays = self.db.query(Holiday).filter(
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
                is_active=True
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
                            # --- Определяем соперника
                            opponent_id = m.player1_id if m.player2_id == player.id else m.player2_id
                            opponent = self.db.query(Player).filter(Player.id == opponent_id).first()

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
                            is_active=True
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
        
    def _match_exists(self, date: date, player1_id: int, player2_id: int, score: str, time_str: str) -> bool:
        from datetime import datetime

        # Преобразуем строку времени в datetime.time, если возможно
        try:
            match_time = datetime.strptime(time_str.strip(), "%H:%M").time()
        except Exception:
            match_time = None

        # Нормализуем счёт (удаляем пробелы, стандартный формат через ':')
        normalized_score = score.replace(" ", "").replace("-", ":").strip()

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
                return True

        return False



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
                    is_active=True
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


    async def _analyze_won_2_lost_3rd_set( #РАБОТАЕТ
    self, player: Player, matches: List[Match], start_date: date, end_date: date
) -> List[PlayerTrigger]:
        """Анализ случаев, когда игрок выиграл первые 2 сета, но проиграл 3-й сет"""
        triggers = []

        for match in matches:
            if not (start_date <= match.date <= end_date):
                continue

            # Получаем все сеты матча, отсортированные по номеру
            sets = sorted(
                self.db.query(MatchSet).filter(MatchSet.match_id == match.id).all(),
                key=lambda s: s.set_number
            )

            if len(sets) < 3:
                continue  # Триггер нужен только если есть хотя бы 3 сета

            # Определяем, кто первый и второй игрок в таблице MatchSet
            first_player_sets = []
            second_player_sets = []
            for s in sets:
                if s.match.player1_id == player.id:
                    first_player_sets.append(s.player1_points)
                    second_player_sets.append(s.player2_points)
                else:
                    first_player_sets.append(s.player2_points)
                    second_player_sets.append(s.player1_points)

            # Проверяем первые 3 сета
            first_set_won = first_player_sets[0] > second_player_sets[0]
            second_set_won = first_player_sets[1] > second_player_sets[1]
            third_set_won = first_player_sets[2] > second_player_sets[2]

            # Срабатывание триггера: первые два выиграны, третий проигран
            if first_set_won and second_set_won and not third_set_won:
                trigger = PlayerTrigger(
                    player_id=player.id,
                    trigger_type="won_2_lost_3rd_set",
                    trigger_subtype="decisive_set_problems",
                    trigger_value=f"Выиграл первые 2 сета, но проиграл 3-й в матче {match.id}",
                    severity_level=2,
                    period_start=start_date,
                    period_end=end_date,
                    is_active=True
                )
                trigger.set_metadata({
                    "match_id": match.id,
                    "first_set": first_player_sets[0:1],
                    "second_set": first_player_sets[1:2],
                    "third_set": first_player_sets[2:3],
                    "recommendation": "Проблемы с концентрацией в решающих сетах. Требуется психологическая работа"
                })

                self.db.add(trigger)
                triggers.append(trigger)

        self.db.commit()
        return triggers


    
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
                    is_active=True
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
            # Получаем сеты этого матча из таблицы MatchSet, отсортированные по set_number
            match_sets = self.db.query(MatchSet).filter(MatchSet.match_id == match.id).order_by(MatchSet.set_number).all()

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
                    is_active=True
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

        for match in player_matches:
            # Получаем сеты матча
            match_sets = self.db.query(MatchSet).filter(MatchSet.match_id == match.id).order_by(MatchSet.set_number).all()
            if len(match_sets) < 2:
                continue  # если меньше двух сетов, пропускаем

            # Проверяем первые два сета
            first_two_wins = 0
            for s in match_sets[:2]:
                if s.winner_id == player.id:
                    first_two_wins += 1

            # Если первые два сета выиграны, а матч проигран
            if first_two_wins == 2:
                led_2_lost_count += 1

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
                is_active=True
            )
            trigger.set_metadata({
                "led_2_lost_count": led_2_lost_count,
                "total_matches": total_matches,
                "percentage": percentage,
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

            # Получаем все сеты матча
            match_sets = self.db.query(MatchSet).filter(MatchSet.match_id == match.id).order_by(MatchSet.set_number).all()
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
                    is_active=True
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
            # Получаем сеты для текущего матча, сортируем по порядку
            sets = self.db.query(MatchSet).filter(MatchSet.match_id == match.id).order_by(MatchSet.set_number).all()
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
                    is_active=True
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
                # Определяем соперника
                opponent_id = m.player1_id if m.player2_id == player.id else m.player2_id
                opponent = self.db.query(Player).filter(Player.id == opponent_id).first()

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
                    is_active=True
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
        player = self.db.query(Player).filter(Player.id == trigger.player_id).first()
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
                opponent = self.db.query(Player).filter(Player.id == opp_id).first()
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
        """Получает конкретные матчи, где проявился данный триггер"""
        # Базовый запрос для получения матчей игрока за период триггера
        base_matches = self.db.query(Match).filter(
            and_(
                Match.date >= trigger.period_start,
                Match.date <= trigger.period_end,
                or_(Match.player1_id == player.id, Match.player2_id == player.id)
            )
        ).order_by(Match.date.desc()).all()
        
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
            # Показываем матчи где выиграл 2 сета, но проиграл 3-й
            for match in base_matches:
                if match.player1_id == player.id:
                    player_sets = match.sets_player1 or 0
                    opponent_sets = match.sets_player2 or 0
                else:
                    player_sets = match.sets_player2 or 0
                    opponent_sets = match.sets_player1 or 0
                
                if player_sets == 2 and opponent_sets == 1 and match.winner_id != player.id:
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
    
    def _get_player_stats_for_trigger(self, player_id: str, start_date: date, end_date: date) -> dict:
        """Получает статистику игрока для триггера, включая форму и последние матчи"""
        player = self.db.query(Player).filter(Player.id == player_id).first()
        if not player:
            return {}
        
        # Получаем матчи игрока за период
        matches = self.db.query(Match).filter(
            and_(
                Match.date >= start_date,
                Match.date <= end_date,
                or_(Match.player1_id == player.id, Match.player2_id == player.id)
            )
        ).order_by(Match.date.desc()).all()
        
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
            
            # Определяем оппонента
            opponent_id = match.player2_id if match.player1_id == player.id else match.player1_id
            opponent = self.db.query(Player).filter(Player.id == opponent_id).first()
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
        
        return {
            "matches_played": len(matches),
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "sets_won": sets_won,
            "sets_lost": sets_lost,
            "recent_form": ''.join(recent_form),  # ← Преобразуем массив в строку
            "recent_matches": recent_matches
        }

    async def _generate_ai_analysis(self, player_name: str, trigger_value: str ,  player_stats: Dict) -> str:
        """Генерирует ИИ-анализ для игрока"""
        if not self._ai_analysis_enabled:
            return f"Анализ игрока {player_name}"
        
        try:
            # Создаем контекст для ИИ
            prompt = self._create_analysis_prompt(player_name, trigger_value, player_stats)
            
            # Вызываем функцию стриминга из ollama_service
            async with httpx.AsyncClient(timeout=30.0) as client:
                print("AHAHAHHAHAHAHAHA")
                async with client.stream("POST", "http://localhost:11434/api/chat", json={
                    "model": "llama3.1:8b",  # ← ИЗМЕНИТЕ НА ВАШУ МОДЕЛЬ
                    "stream": True,
                    "messages": [
                        {"role": "system", "content": "Ты аналитик по настольному теннису."},
                        {"role": "user", "content": prompt}
                    ]
                }) as response:
                    analysis_text = ""
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                analysis_text += data["message"]["content"]
                        except json.JSONDecodeError:
                            continue
                    
                    return analysis_text if analysis_text.strip() else f"Анализ триггера для игрока {player_name}"
                    
        except Exception as e:
            print(f"Ошибка генерации ИИ-анализа: {e}")
            return f"Не удалось сгенерировать анализ для триггера"
    
    def _create_analysis_prompt(self, player_name: str, trigger_value: str, player_stats: Dict) -> str:
        """Создает промпт для ИИ-анализа"""
        embeddings, metadata = load_data()
        dop_infa = search(trigger_value, embeddings, metadata, top_k=3)
        # sorted_triggers = sorted(player_triggers, key=lambda t: t.severity_level or 0, reverse=True)[:8]
        # trigger_texts = "\n".join([f"- {t.trigger_type}: {t.trigger_value}" for t in sorted_triggers])
        # # Описания триггеров
        # trigger_descriptions = {
        #     "top_performers": "отличные результаты",
        #     "defeat_0_3": "частые поражения 0:3",
        #     "won_2_lost_3rd_set": "проигрыш после лидерства 2:0 по сетам",
        #     "early_final_exit_advanced": "досрочный уход с корта в финалах",
        #     "led_1_set_lost_match": "проигрыш после лидерства в счёте",
        #     "led_2_sets_lost_match": "критический проигрыш после лидерства 2:0",
        #     "psychological_breakdown": "психологические срывы",
        #     "comeback_inability": "неспособность к камбекам",
        #     "pressure_situations": "проблемы в важных матчах",
        #     "losers_50_percent": "низкий процент побед",
        #     "losing_streaks": "длинные серии поражений",
        #     "time_performance": "проблемы с выступлениями в определённое время суток",
        #     "post_holiday_problems": "плохая форма после праздников"
        # }
        
        
        wins = player_stats.get('wins', 0)
        losses = player_stats.get('losses', 0)
        win_rate = player_stats.get('win_rate', 0)
        matches = player_stats.get('matches_played', 0)
        recent_form = player_stats.get('recent_form', '')
        
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

Сделай профессиональный анализ игрока в 2-3 предложениях: объясни возможные причины проблем и дай рекомендации.
"""
        print("Промпты которые летят в олламу 🏃🏃🏃🏃🏃🏃🏃", prompt)
        
        return prompt

    # async def _generate_player_comprehensive_analysis(self, player_name: str, player_triggers: List[PlayerTrigger], player_stats: Dict) -> str:
    #     """Генерирует комплексный ИИ-анализ для всех триггеров игрока"""
    #     if not self._ai_analysis_enabled:
    #         return f"Комплексный анализ игрока {player_name}"
        
    #     try:
    #         # Создаем промпт для комплексного анализа
    #         prompt = self._create_comprehensive_analysis_prompt(player_name, player_triggers, player_stats)
            
    #         # Вызываем функцию стриминга из ollama_service
    #         async with httpx.AsyncClient(timeout=30.0) as client:
    #             print("FDFDFDFDFDFDFD")
    #             async with client.stream("POST", "http://localhost:11434/api/chat", json={
    #                 "model": "llama3.1:8b",
    #                 "stream": True,
    #                 "messages": [
    #                     {"role": "system", "content": "Ты аналитик по выявлению мошенничества в спорте. Твоя задача - анализировать подозрительные паттерны в игре спортсменов и выявлять признаки договорных матчей или намеренного проигрыша."},
    #                     {"role": "user", "content": prompt}
    #                 ]
    #             }) as response:
    #                 analysis_text = ""
    #                 async for line in response.aiter_lines():
    #                     if not line.strip():
    #                         continue
    #                     try:
    #                         data = json.loads(line)
    #                         if "message" in data and "content" in data["message"]:
    #                             analysis_text += data["message"]["content"]
    #                     except json.JSONDecodeError:
    #                         continue
                    
    #                 return analysis_text if analysis_text.strip() else f"Комплексный анализ игрока {player_name}"
                    
        # except Exception as e:
        #     logger.error(f"Ошибка генерации комплексного ИИ-анализа: {e}")
        #     return f"Не удалось сгенерировать комплексный анализ для игрока {player_name}"

#     def _create_comprehensive_analysis_prompt(self, player_name: str, player_triggers: List[PlayerTrigger], player_stats: Dict) -> str:
#         """Создает промпт для комплексного ИИ-анализа всех триггеров игрока"""
        
#         # Описания триггеров с точки зрения мошенничества
#         trigger_descriptions = {
#             "top_performers": "стабильно высокие результаты",
#             "defeat_0_3": "подозрительно частые разгромные поражения",
#             "won_2_lost_3rd_set": "намеренные проигрыши после лидерства 2:0",
#             "early_final_exit_advanced": "подозрительные досрочные сдачи в финалах",
#             "led_1_set_lost_match": "потеря преимущества в ключевые моменты",
#             "led_2_sets_lost_match": "крайне подозрительные развороты после лидерства 2:0",
#             "psychological_breakdown": "неестественные психологические срывы",
#             "comeback_inability": "подозрительная неспособность к возвращению в игру",
#             "pressure_situations": "провалы в важных матчах",
#             "losers_50_percent": "аномально низкий процент побед"
#         }
        
#         wins = player_stats.get('wins', 0)
#         losses = player_stats.get('losses', 0)
#         win_rate = player_stats.get('win_rate', 0)
#         matches = player_stats.get('matches_played', 0)
#         recent_form = player_stats.get('recent_form', '')
#         sets_won = player_stats.get('sets_won', 0)
#         sets_lost = player_stats.get('sets_lost', 0)
        
#         # Формируем список проблем
#         problems_list = []
#         positive_aspects = []
        
#         for trigger in player_triggers:
#             description = trigger_descriptions.get(trigger.trigger_type, trigger.trigger_type)
#             if trigger.trigger_type == 'top_performers':
#                 positive_aspects.append(f"- {description}: {trigger.trigger_value}")
#             else:
#                 problems_list.append(f"- {description}: {trigger.trigger_value}")
        
#         problems_text = "\n".join(problems_list) if problems_list else "Серьезных проблем не выявлено"
#         positives_text = "\n".join(positive_aspects) if positive_aspects else ""
        
#         prompt = f"""
# АНАЛИЗ ПОДОЗРИТЕЛЬНОГО ПОВЕДЕНИЯ ИГРОКА: {player_name}

# СТАТИСТИКА ЗА ПЕРИОД:
# - Матчей сыграно: {matches}
# - Побед: {wins} ({win_rate:.1f}%)
# - Поражений: {losses}
# - Соотношение сетов: {sets_won}:{sets_lost}
# - Последняя форма: {recent_form}

# ВЫЯВЛЕННЫЕ ПОДОЗРИТЕЛЬНЫЕ ПАТТЕРНЫ:
# {problems_text}

# ПОЛОЖИТЕЛЬНЫЕ ПОКАЗАТЕЛИ:
# {positives_text}

# Проанализируй этого игрока на предмет возможного мошенничества или договорных матчей. Укажи уровень подозрительности (низкий/средний/высокий) и объясни, какие паттерны могут указывать на намеренные проигрыши или подставную игру. Дай оценку в 3-4 предложениях.
# """
