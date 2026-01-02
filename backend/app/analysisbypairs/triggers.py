from collections import Counter, defaultdict
from datetime import date
import json
import traceback
from app.analysisbypairs.dop_functions import build_trigger_metadata, calculate_severity_level, get_season
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.match import Match, MatchSet, Player, PlayerTrigger
from sqlalchemy import create_engine
engine = create_engine(
    "postgresql://user:pass@localhost/dbname",
    echo=True  # <--- покажет все SQL-запросы
)




class H2HAnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def get_h2h_matches(self, player1_id: str, player2_id: str, match_date=None):
        query = self.db.query(Match).filter(
            or_(
                and_(Match.player1_id == player1_id, Match.player2_id == player2_id),
                and_(Match.player1_id == player2_id, Match.player2_id == player1_id),
            )
        )

        if match_date:
            query = query.filter(Match.date == match_date)

        return query.order_by(Match.date.desc()).all()


    def _trigger_h2h_losing_streak(self, player, matches, opponent):
        """
        Игрок проиграл 3+ матча ПОДРЯД этому конкретному сопернику.
        """
        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id) or
            (m.player1_id == opponent.id and m.player2_id == player.id)
        ]


        # Если нет очных матчей — выходим
        if not h2h_matches:
            return []

        # 2. Сортировка по дате и времени
        h2h_matches = sorted(
        h2h_matches,
        key=lambda m: (m.date, m.time if hasattr(m, "time") else m.id)
    )


        # 3. Подсчёт поражений подряд
        current_streak = []
        best_streak = []

        for match in h2h_matches:
            if match.winner_id != player.id:
                current_streak.append(match)

                if len(current_streak) > len(best_streak):
                    best_streak = current_streak.copy()
            else:
                current_streak = []

        max_streak = len(best_streak)


        # 4. Если серия ≥ 3 — создаём триггер
        if max_streak >= 3:
            trig = PlayerTrigger(
                player_id=player.id,
                match_id=best_streak[-1].id,  # последний матч серии
                trigger_type="h2h_losing_streak",
                trigger_subtype=f"Противник: {opponent.full_name}",
                trigger_value=f"Серия поражений: {max_streak} подряд",
                period_start=best_streak[0].date,
                period_end=best_streak[-1].date,
                is_pair=True
            )

            sev = calculate_severity_level(
                player,
                opponent,
                h2h_matches,
                "h2h_losing_streak",
                best_streak
            )
            trig.severity_level = sev

            trig.set_metadata(
                build_trigger_metadata(
                    opponent=opponent,
                    matches=best_streak,   # 🔥 ВОТ ТУТ ТЕПЕРЬ ВСЁ ПРАВИЛЬНО
                    pattern=max_streak
                )
            )

            self.db.add(trig)
            return [trig]


        return []


    def _trigger_h2h_close_score_losses(self, player, matches, opponent):
        """
        Игрок часто проигрывает этому сопернику в плотных концовках:
        - проигрыш с разницей <= 1 сет
        - или много поражений 2:3 / 1:2
        """
        # Берем только очные матчи
        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id) or
            (m.player1_id == opponent.id and m.player2_id == player.id)
        ]

        if not h2h_matches:
            return []

        h2h_matches = sorted(h2h_matches, key=lambda m: m.date)

        close_losses_matches = []
        total_losses = 0

        for m in h2h_matches:
            if m.winner_id == player.id:
                continue  # победа
            total_losses += 1

            # подсчет сетов для player
            p_sets = m.sets_player1 if m.player1_id == player.id else m.sets_player2
            o_sets = m.sets_player2 if m.player1_id == player.id else m.sets_player1

            if abs(p_sets - o_sets) == 1:
                close_losses_matches.append(m)

        # проверяем условие: >=3 поражений и >=50% в плотных концовках
        if total_losses >= 3 and len(close_losses_matches) / total_losses >= 0.5:
            trig = PlayerTrigger(
                player_id=player.id,
                trigger_type="h2h_close_score_losses",
                trigger_subtype=f"Противник: {opponent.full_name}",
                trigger_value=(
                    f"Частые поражения в плотных концовках: "
                    f"{len(close_losses_matches)} из {total_losses}"
                ),
                period_start=h2h_matches[0].date,
                period_end=h2h_matches[-1].date,
                is_pair=True
            )

            # рассчитываем severity
            sev = calculate_severity_level(
                player,
                opponent,
                h2h_matches,
                "h2h_close_score_losses",
                close_losses_matches
            )
            trig.severity_level = sev

            # metadata
            trig.set_metadata(
                build_trigger_metadata(
                    opponent=opponent,
                    matches=close_losses_matches,
                    pattern=f"{len(close_losses_matches)}/{total_losses}"
                )
            )

            self.db.add(trig)
            return [trig]

        return []


    

    def _trigger_h2h_score_patterns(self, player, matches, opponent):
        """
        Анализ: какие счета побед/поражений чаще всего встречаются
        между player и opponent.
        """

        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id) or
            (m.player1_id == opponent.id and m.player2_id == player.id)
        ]

        if not h2h_matches:
            return []

        win_counts = {}
        loss_counts = {}

        for m in h2h_matches:
            if m.player1_id == player.id:
                p_sets, o_sets = m.sets_player1 or 0, m.sets_player2 or 0
            else:
                p_sets, o_sets = m.sets_player2 or 0, m.sets_player1 or 0

            score_key = f"{p_sets}:{o_sets}"

            if p_sets > o_sets:
                win_counts[score_key] = win_counts.get(score_key, 0) + 1
            else:
                loss_counts[score_key] = loss_counts.get(score_key, 0) + 1

        triggers = []

        def make_trigger(title, top_score, freq):
            matches_sorted = sorted(h2h_matches, key=lambda x: x.date)

            pattern_matches = [
                m for m in h2h_matches
                if ((m.player1_id == player.id and f"{m.sets_player1}:{m.sets_player2}" == top_score) or
                    (m.player1_id != player.id and f"{m.sets_player2}:{m.sets_player1}" == top_score))
            ]

            trig = PlayerTrigger(
                player_id=player.id,
                trigger_type="h2h_score_pattern",
                trigger_subtype=f"Противник: {opponent.full_name}",
                trigger_value=f"{title}: {top_score} повторяется {freq} раз",
                # severity_level=sev,
                period_start=matches_sorted[0].date,
                period_end=matches_sorted[-1].date,
                is_pair=True
            )
            sev = calculate_severity_level(player, opponent, h2h_matches, "h2h_score_pattern", pattern_matches)
            trig.severity_level = sev

            trig.set_metadata(build_trigger_metadata(
                opponent=opponent,
                matches=pattern_matches,
                pattern=top_score
            ))

            self.db.add(trig)
            triggers.append(trig)

                # --- анализ поражений ---
        defeat_score = None
        defeat_freq = 0
        if loss_counts:
            defeat_score, defeat_freq = max(loss_counts.items(), key=lambda x: x[1])

        # --- анализ побед ---
        win_score = None
        win_freq = 0
        if win_counts:
            win_score, win_freq = max(win_counts.items(), key=lambda x: x[1])

        # --- выбор только одного ---
        # оба должны быть ≥ 2, иначе триггер не нужен
        if defeat_freq < 2 and win_freq < 2:
            return []

        # Если частота поражений больше — берем поражения
        if defeat_freq > win_freq:
            make_trigger("Чаще всего проигрывает", defeat_score, defeat_freq)
            return triggers

        # Если частота побед больше — берем победы
        if win_freq > defeat_freq:
            make_trigger("Чаще всего выигрывает", win_score, win_freq)
            return triggers

        # Если равны → выбери что-то одно
        # например: приоритет поражений
        make_trigger("Чаще всего проигрывает", defeat_score, defeat_freq)
        return triggers


    def _trigger_h2h_set_anomalies(self, player, matches, opponent):
        """
        Анализ аномальных сетов:
        - крупные проигрыши (0–11, 1–11, 2–11)
        - крупные победы   (11–0..11–3)
        - и проверка, бывают ли такие случаи ТОЛЬКО против этого соперника
        """

        # Функция для сбора сетов из матча
        def extract_sets(m, player):
            sets = []
            for i in range(1, 6):
                p = getattr(m, f"set{i}_player1", None)
                o = getattr(m, f"set{i}_player2", None)
                if p is None or o is None:
                    continue
                if m.player1_id != player.id:
                    p, o = o, p
                sets.append((p, o))
            return sets

        # Очные матчи
        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id)
            or (m.player1_id == opponent.id and m.player2_id == player.id)
        ]

        if not h2h_matches:
            return []

        # Сбор аномалий
        big_losses = []   # список матчей
        big_wins = []

        # Подсчёты конкретных счетов
        big_loss_counts = {"0:11": 0, "1:11": 0, "2:11": 0}
        big_win_counts = {}

        for m in h2h_matches:
            for ps, os in extract_sets(m, player):

                # крупные провалы
                if ps <= 3 and os >= 11:
                    score = f"{ps}:{os}"
                    if score in big_loss_counts:
                        big_loss_counts[score] += 1
                    big_losses.append(m)

                # крупные победы
                if ps >= 11 and os <= 3:
                    score = f"{ps}:{os}"
                    big_win_counts[score] = big_win_counts.get(score, 0) + 1
                    big_wins.append(m)

        if not big_losses and not big_wins:
            return []

        # Проверяем: бывают ли такие аномалии против других соперников
        all_player_matches = self.db.query(Match).filter(
            (Match.player1_id == player.id) | (Match.player2_id == player.id)
        ).all()

        big_losses_other = False
        big_wins_other = False

        for m in all_player_matches:
            if m in h2h_matches:
                continue
            for ps, os in extract_sets(m, player):
                if ps <= 3 and os >= 11:
                    big_losses_other = True
                if ps >= 11 and os <= 3:
                    big_wins_other = True

        triggers = []

        # ===============================================================
        #           ТРИГГЕР: КРУПНЫЕ ПРОВАЛЫ ТОЛЬКО ЗДЕСЬ
        # ===============================================================
        filtered_loss_counts = {k: v for k, v in big_loss_counts.items() if v > 0}
        total_losses = sum(filtered_loss_counts.values())

        if total_losses > 0 and not big_losses_other:

            details = ", ".join([f"{score} — {count} раз"
                                for score, count in filtered_loss_counts.items()])

            trig = PlayerTrigger(
                player_id=player.id,
                trigger_type="h2h_set_anomalies",
                trigger_subtype=f"Противник: {opponent.full_name}",
                trigger_value=f"Крупные провалы: {total_losses} раз ({details})",
                period_start=min(m.date for m in h2h_matches),
                period_end=max(m.date for m in h2h_matches),
                is_pair=True
            )

            sev = calculate_severity_level(
                player, opponent, h2h_matches,
                "h2h_set_anomalies", big_losses
            )
            trig.severity_level = sev

            trig.set_metadata(build_trigger_metadata(
                opponent=opponent,
                matches=big_losses,
                pattern="big_losses_only_vs_opponent"
            ))

            self.db.add(trig)
            triggers.append(trig)

        # ===============================================================
        #           ТРИГГЕР: КРУПНЫЕ ПОБЕДЫ ТОЛЬКО ЗДЕСЬ
        # ===============================================================
        if big_win_counts and not big_wins_other:

            total_wins = sum(big_win_counts.values())
            details_w = ", ".join([f"{score} — {count} раз"
                                for score, count in big_win_counts.items()])

            trig = PlayerTrigger(
                player_id=player.id,
                trigger_type="h2h_set_anomalies",
                trigger_subtype=f"Противник: {opponent.full_name}",
                trigger_value=f"Крупные победы: {total_wins} раз ({details_w})",
                period_start=min(m.date for m in h2h_matches),
                period_end=max(m.date for m in h2h_matches),
                is_pair=True
            )

            sev = calculate_severity_level(
                player, opponent, h2h_matches,
                "h2h_set_anomalies", big_wins
            )
            trig.severity_level = sev

            trig.set_metadata(build_trigger_metadata(
                opponent=opponent,
                matches=big_wins,
                pattern="big_wins_only_vs_opponent"
            ))

            self.db.add(trig)
            triggers.append(trig)

        return triggers

    def _trigger_h2h_first_set_win_effect(self, player, matches, opponent):
        """
        Если игрок выигрывает первый сет — выигрывает ли он матч?
        Считаем только очные матчи против конкретного соперника.
        Условие триггера: % побед при счёте 1:0 > 50%.
        """
        # Берем только очные матчи
        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id)
            or (m.player1_id == opponent.id and m.player2_id == player.id)
        ]

        if not h2h_matches:
            return []

        first_set_taken = []
        wins_after_1_0 = []

        for m in h2h_matches:
            # Получаем первый сет из таблицы MatchSet
            first_set = (
                self.db.query(MatchSet)
                .filter(MatchSet.match_id == m.id, MatchSet.set_number == 1)
                .first()
            )
            if not first_set:
                continue

            # Определяем очки игрока и соперника в первом сете
            if m.player1_id == player.id:
                p_first, o_first = first_set.player1_points, first_set.player2_points
            else:
                p_first, o_first = first_set.player2_points, first_set.player1_points

            # Игрок выиграл первый сет
            if p_first > o_first:
                first_set_taken.append(m)

                # Победил ли он весь матч?
                if m.winner_id == player.id:
                    wins_after_1_0.append(m)

        if not first_set_taken:
            return []

        total = len(first_set_taken)
        wins = len(wins_after_1_0)
        pct = (wins / total) * 100

        if pct <= 50:
            return []

        value_text = f"Победы при 1:0 — {pct:.0f}% ({wins}/{total})"

        trig = PlayerTrigger(
            player_id=player.id,
            trigger_type="h2h_first_set_win",
            trigger_subtype=f"Противник: {opponent.full_name}",
            trigger_value=value_text,
            period_start=min(m.date for m in h2h_matches),
            period_end=max(m.date for m in h2h_matches),
            is_pair=True
        )

        # Severity
        sev = calculate_severity_level(
            player, opponent, h2h_matches, "h2h_first_set_win", wins_after_1_0
        )
        trig.severity_level = sev

        trig.set_metadata(
            build_trigger_metadata(
                opponent=opponent,
                matches=wins_after_1_0,
                pattern=f"{wins}/{total}"
            )
        )

        self.db.add(trig)
        return [trig]
    
    
    
    def _trigger_h2h_seasonal_pattern(self, player, matches, opponent):
        """
        Сезонная стабильность по годам (ТОЛЬКО player vs opponent)
        """

        # 1️⃣ Только очные матчи
        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id)
            or (m.player1_id == opponent.id and m.player2_id == player.id)
        ]

        if not h2h_matches:
            return []

        # 2️⃣ Группировка по годам → сезонам
        yearly = defaultdict(lambda: defaultdict(list))

        for m in h2h_matches:
            year = m.date.year
            season = get_season(m.date)
            yearly[year][season].append(m)

        if len(yearly) < 2:
            return []  # важно: минимум 3 года

        best_seasons = []
        worst_seasons = []
        season_match_map = defaultdict(list)

        # 3️⃣ Анализ каждого года
        for year, seasons in yearly.items():
            season_stats = {}

            for season, season_matches in seasons.items():
                if len(season_matches) < 2:
                    continue

                wins = sum(1 for m in season_matches if m.winner_id == player.id)
                total = len(season_matches)
                winrate = wins / total

                season_stats[season] = {
                    "wins": wins,
                    "total": total,
                    "winrate": winrate
                }

                season_match_map[season].extend(season_matches)

            if not season_stats:
                continue

            best = max(season_stats.items(), key=lambda x: x[1]["winrate"])[0]
            worst = min(season_stats.items(), key=lambda x: x[1]["winrate"])[0]

            best_seasons.append(best)
            worst_seasons.append(worst)

        if len(best_seasons) < 3:
            return []

        triggers = []

        # 4️⃣ Проверка паттернов
        best_counter = Counter(best_seasons)
        worst_counter = Counter(worst_seasons)

        years_count = len(best_seasons)

        def make_trigger(season, count, label):
            used_matches = season_match_map[season]

            trig = PlayerTrigger(
                player_id=player.id,
                trigger_type="h2h_seasonal_pattern",
                trigger_subtype=f"Противник: {opponent.full_name}",
                trigger_value=(
                    f"{label}: {season} "
                    f"(повторяется в {count} из {years_count} лет)"
                ),
                period_start=min(m.date for m in used_matches),
                period_end=max(m.date for m in used_matches),
                is_pair=True
            )

            sev = calculate_severity_level(
                player,
                opponent,
                h2h_matches,
                "h2h_seasonal_pattern",
                used_matches
            )
            trig.severity_level = sev

            trig.set_metadata(
                build_trigger_metadata(
                    opponent=opponent,
                    matches=used_matches,
                    pattern=season,
                    years_with_pattern=count,
                    total_years=years_count
                )
            )

            self.db.add(trig)
            triggers.append(trig)

        # Лучший сезон
        season, count = best_counter.most_common(1)[0]
        if count / years_count >= 0.6:
            make_trigger(season, count, "Лучший сезон")

        # Худший сезон
        season, count = worst_counter.most_common(1)[0]
        if count / years_count >= 0.6:
            make_trigger(season, count, "Худший сезон")

        return triggers
    
    def _trigger_h2h_deciding_set_behavior(self, player, matches, opponent):
        """
        Поведение игрока при счёте 1–1:
        - берет ли он третий сет
        - или часто ломается
        """

        # 1️⃣ Только очные матчи
        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id)
            or (m.player1_id == opponent.id and m.player2_id == player.id)
        ]

        if not h2h_matches:
            return []

        deciding_matches = []
        cases = {
            "lose3_win_match": [],
            "lose3_lose_match": [],
            "win3_win_match": [],
            "win3_lose_match": []
        }


        for m in h2h_matches:

            # 2️⃣ Берём все сеты матча
            sets = (
                self.db.query(MatchSet)
                .filter(MatchSet.match_id == m.id)
                .order_by(MatchSet.set_number)
                .all()
            )

            if len(sets) < 3:
                continue  # матч не дошёл до 3 сетов

            # 3️⃣ Определяем победителей первых двух сетов
            first_two_winners = []

            for s in sets[:2]:
                if s.player1_points > s.player2_points:
                    winner = m.player1_id
                else:
                    winner = m.player2_id
                first_two_winners.append(winner)

            # должно быть 1–1
            if first_two_winners.count(player.id) != 1:
                continue

            # 4️⃣ Победитель третьего сета
            third_set = sets[2]

            if third_set.player1_points > third_set.player2_points:
                third_winner = m.player1_id
            else:
                third_winner = m.player2_id

            deciding_matches.append(m)

            won_third = (third_winner == player.id)
            won_match = (m.winner_id == player.id)

            if not won_third and won_match:
                cases["lose3_win_match"].append(m)

            elif not won_third and not won_match:
                cases["lose3_lose_match"].append(m)

            elif won_third and won_match:
                cases["win3_win_match"].append(m)

            else:
                cases["win3_lose_match"].append(m)

        total = len(deciding_matches)

        if total < 3:
            return []  # слишком мало данных
        
        THRESHOLD = 0.7

        stats = {
            key: len(matches) / total
            for key, matches in cases.items()
        }

        dominant_case = None

        for key, pct in stats.items():
            if pct >= THRESHOLD:
                dominant_case = key
                break

        if not dominant_case:
            return []
        
        LABELS = {
            "lose3_win_match": "Проигрывает 3-й сет при 1–1, но чаще всего выигрывает матч",
            "lose3_lose_match": "Проигрывает 3-й сет при 1–1 и чаще всего проигрывает матч",
            "win3_win_match": "Берёт 3-й сет при 1–1 и чаще всего выигрывает матч",
            "win3_lose_match": "Берёт 3-й сет при 1–1, но чаще всего проигрывает матч"
        }
        used_matches = cases[dominant_case]

        # 6️⃣ Создание триггера
        trig = PlayerTrigger(
            player_id=player.id,
            trigger_type="h2h_deciding_set_behavior",
            trigger_subtype=f"Противник: {opponent.full_name}",
            trigger_value=f"{LABELS[dominant_case]} — {len(used_matches)}/{total}",
            period_start=min(m.date for m in deciding_matches),
            period_end=max(m.date for m in deciding_matches),
            is_pair=True
        )

        sev = calculate_severity_level(
            player,
            opponent,
            h2h_matches,
            "h2h_deciding_set_behavior",
            used_matches
        )
        trig.severity_level = sev

        trig.set_metadata(
            build_trigger_metadata(
                opponent=opponent,
                matches=used_matches,
                pattern="1-1_deciding_set",
                total=total
            )
        )

        self.db.add(trig)
        return [trig]
    

    def _trigger_h2h_lead_2_0_behavior(self, player, matches, opponent):
        """
        Поведение игрока при счёте 2–0:
        - дожимает 3:0
        - дожимает 3:1
        - или сливает 2:3
        """

        # 1️⃣ Только очные матчи
        h2h_matches = [
            m for m in matches
            if (m.player1_id == player.id and m.player2_id == opponent.id)
            or (m.player1_id == opponent.id and m.player2_id == player.id)
        ]

        if not h2h_matches:
            return []

        cases = {
            "win_3_0": [],
            "win_3_1": [],
            "lose_2_3": []
        }

        relevant_matches = []

        for m in h2h_matches:
            # 2️⃣ Получаем сеты матча
            sets = (
                self.db.query(MatchSet)
                .filter(MatchSet.match_id == m.id)
                .order_by(MatchSet.set_number)
                .all()
            )

            if len(sets) < 3:
                continue  # матч не BO5

            # 3️⃣ Определяем победителей первых двух сетов
            first_two_winners = []

            for s in sets[:2]:
                if s.player1_points > s.player2_points:
                    winner = m.player1_id
                else:
                    winner = m.player2_id
                first_two_winners.append(winner)

            # игрок должен вести 2–0
            if first_two_winners.count(player.id) != 2:
                continue

            relevant_matches.append(m)

            # 4️⃣ Финальный счёт матча
            p_sets = m.sets_player1 if m.player1_id == player.id else m.sets_player2
            o_sets = m.sets_player2 if m.player1_id == player.id else m.sets_player1

            if p_sets == 3 and o_sets == 0:
                cases["win_3_0"].append(m)

            elif p_sets == 3 and o_sets == 1:
                cases["win_3_1"].append(m)

            elif p_sets == 2 and o_sets == 3:
                cases["lose_2_3"].append(m)

        total = len(relevant_matches)

        if total < 3:
            return []  # мало данных

        # 5️⃣ Анализ доминирующего сценария
        THRESHOLD = 0.6

        dominant_case = None
        dominant_matches = []

        for key, ms in cases.items():
            if len(ms) / total >= THRESHOLD:
                dominant_case = key
                dominant_matches = ms
                break

        if not dominant_case:
            return []

        # 6️⃣ Человекочитаемый текст
        LABELS = {
            "win_3_0": "При счёте 2–0 чаще всего выигрывает матч 3:0",
            "win_3_1": "При счёте 2–0 чаще всего доводит матч до 3:1",
            "lose_2_3": "Ведя 2–0, часто упускает матч (2:3)"
        }

        trig = PlayerTrigger(
            player_id=player.id,
            trigger_type="h2h_lead_2_0_behavior",
            trigger_subtype=f"Противник: {opponent.full_name}",
            trigger_value=f"{LABELS[dominant_case]} — {len(dominant_matches)}/{total}",
            period_start=min(m.date for m in relevant_matches),
            period_end=max(m.date for m in relevant_matches),
            is_pair=True
        )

        sev = calculate_severity_level(
            player,
            opponent,
            relevant_matches,
            "h2h_lead_2_0_behavior",
            dominant_matches
        )
        trig.severity_level = sev

        trig.set_metadata(
            build_trigger_metadata(
                opponent=opponent,
                matches=dominant_matches,
                pattern=dominant_case,
                breakdown={k: len(v) for k, v in cases.items()},
                total=total
            )
        )

        self.db.add(trig)
        return [trig]







    def analyze_h2h(self, player1_id: str, player2_id: str, match_date=None):
        try:
            player1 = self.db.query(Player).filter(Player.id == player1_id).first()
            player2 = self.db.query(Player).filter(Player.id == player2_id).first()

            if not player1 or not player2:
                return None, None, []

            matches = self.get_h2h_matches(player1_id, player2_id, match_date)

            # очищаем старые триггеры H2H
            self.db.query(PlayerTrigger).filter(
                PlayerTrigger.trigger_type.in_(["h2h_losing_streak", "h2h_close_score_losses", "h2h_score_pattern", "h2h_deciding_set_behavior", "h2h_set_anomalies", "h2h_first_set_win", "h2h_seasonal_pattern", "h2h_lead_2_0_behavior"
]),
                PlayerTrigger.player_id.in_([player1.id, player2.id])
            ).delete(synchronize_session=False)

            trig_p1 = []
            trig_p2 = []

            trig_p1 += self._trigger_h2h_losing_streak(player1, matches, player2)
            trig_p1 += self._trigger_h2h_close_score_losses(player1, matches, player2)
            trig_p1 += self._trigger_h2h_score_patterns(player1, matches, player2)
            trig_p1 += self._trigger_h2h_set_anomalies(player1, matches, player2) #???  не могу провеить, нет матчей с такими аномалиями
            trig_p1 += self._trigger_h2h_first_set_win_effect(player1, matches, player2)
            trig_p1 += self._trigger_h2h_seasonal_pattern(player1, matches, player2) #??? не могу провеить, недостаточно матчей с разными сезонами
            trig_p1 += self._trigger_h2h_deciding_set_behavior(player1, matches, player2)
            trig_p1 += self._trigger_h2h_lead_2_0_behavior(player1, matches, player2)




            trig_p2 += self._trigger_h2h_losing_streak(player2, matches, player1)
            trig_p2 += self._trigger_h2h_close_score_losses(player2, matches, player1)
            trig_p2 += self._trigger_h2h_score_patterns(player2, matches, player1)
            trig_p2 += self._trigger_h2h_set_anomalies(player2, matches, player1)
            trig_p2 += self._trigger_h2h_first_set_win_effect(player2, matches, player1)
            trig_p2 += self._trigger_h2h_seasonal_pattern(player2, matches, player1)
            trig_p2 += self._trigger_h2h_deciding_set_behavior(player2, matches, player1)
            trig_p2 += self._trigger_h2h_lead_2_0_behavior(player2, matches, player1)

            self.db.commit()

            return trig_p1, trig_p2, matches

        except Exception as e:
            import traceback
            print("❌ ERROR in analyze_h2h:")
            traceback.print_exc()
            raise e

        



    
