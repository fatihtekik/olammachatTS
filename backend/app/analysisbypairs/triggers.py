from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.match import Match, Player, PlayerTrigger


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
        Игрок проиграл 3+ матча подряд этому конкретному сопернику.
        """
        streak = 0
        max_streak = 0

        for match in sorted(matches, key=lambda m: m.date):
            if match.winner_id != player.id:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

        if max_streak >= 3:
            trig = PlayerTrigger(
                player_id=player.id,
                trigger_type="h2h_losing_streak",
                trigger_value=f"Серия поражений от {opponent.full_name}: {max_streak} подряд",
                severity_level=2,
                period_start=date(1900,1,1),  # В H2H можно ставить технические даты
                period_end=date(2100,1,1),
                is_active=True
            )
            self.db.add(trig)
            return [trig]

        return []

    def _trigger_h2h_close_score_losses(self, player, matches, opponent):
        """
        Игрок часто проигрывает этому сопернику в плотных концовках:
        - проигрыш с разницей <= 2 очков в финальном сете
        - или много проигрышей 2:3 / 1:2
        """

        close_losses = 0
        total_losses = 0

        for m in matches:
            if m.winner_id == player.id:
                continue  # это победа

            total_losses += 1

            # работаем по основному счету
            p_sets = m.sets_player1 if m.player1_id == player.id else m.sets_player2
            o_sets = m.sets_player2 if m.player1_id == player.id else m.sets_player1

            # критерии плотного поражения:
            # - 2:3 или 1:2
            if abs(p_sets - o_sets) == 1:
                close_losses += 1

        if total_losses >= 3 and close_losses / total_losses >= 0.5:
            trig = PlayerTrigger(
                player_id=player.id,
                trigger_type="h2h_close_score_losses",
                trigger_value=(
                    f"Частые плотные поражения от {opponent.full_name}: "
                    f"{close_losses} из {total_losses}"
                ),
                severity_level=1,
                period_start=date(1900,1,1),
                period_end=date(2100,1,1),
                is_active=True
            )
            self.db.add(trig)
            return [trig]

        return []



    def analyze_h2h(self, player1_id: str, player2_id: str, match_date=None):

        player1 = self.db.query(Player).filter(Player.id == player1_id).first()
        player2 = self.db.query(Player).filter(Player.id == player2_id).first()

        if not player1 or not player2:
            return None, None, []

        matches = self.get_h2h_matches(player1_id, player2_id, match_date)

        # очищаем старые триггеры H2H, чтобы не накапливались
        self.db.query(PlayerTrigger).filter(
            PlayerTrigger.trigger_type.in_(["h2h_losing_streak", "h2h_close_score_losses"]),
            PlayerTrigger.player_id.in_([player1.id, player2.id])
        ).delete()

        trig_p1 = []
        trig_p2 = []

        trig_p1 += self._trigger_h2h_losing_streak(player1, matches, player2)
        trig_p1 += self._trigger_h2h_close_score_losses(player1, matches, player2)

        trig_p2 += self._trigger_h2h_losing_streak(player2, matches, player1)
        trig_p2 += self._trigger_h2h_close_score_losses(player2, matches, player1)

        self.db.commit()

        return trig_p1, trig_p2, matches
