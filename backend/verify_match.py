from app.database.db import SessionLocal
from app.models.match import Match, MatchSet

db = SessionLocal()

match_id = 'd99bf607-62d6-483c-a359-949096936c75'
match = db.query(Match).filter(Match.id == match_id).first()

if match:
    print(f"=== MATCH DATA ===")
    print(f"ID: {match.id}")
    print(f"Date: {match.date}")
    print(f"Player 1: {match.player1_id}")
    print(f"Player 2: {match.player2_id}")
    print(f"Winner: {match.winner_id}")
    print(f"\n=== SCORE ===")
    print(f"Sets Player 1: {match.sets_player1}")
    print(f"Sets Player 2: {match.sets_player2}")
    print(f"Score (raw): {match.score}")
    
    # Проверяем MatchSet
    sets = db.query(MatchSet).filter(
        MatchSet.match_id == match_id
    ).order_by(MatchSet.set_number).all()
    
    print(f"\n=== MATCH SETS ({len(sets)} total) ===")
    for s in sets:
        print(f"Set {s.set_number}: P1={s.player1_points}, P2={s.player2_points}, Winner={s.winner_id}")
    
    # Подсчитываем победы в сетах
    p1_wins = sum(1 for s in sets if s.winner_id == match.player1_id)
    p2_wins = sum(1 for s in sets if s.winner_id == match.player2_id)
    
    print(f"\n=== CALCULATED FROM SETS ===")
    print(f"P1 won sets: {p1_wins}")
    print(f"P2 won sets: {p2_wins}")
    print(f"\n⚠️ MISMATCH: Match.sets_player1={match.sets_player1} vs calculated={p1_wins}")
    print(f"⚠️ MISMATCH: Match.sets_player2={match.sets_player2} vs calculated={p2_wins}")
    
db.close()
