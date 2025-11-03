from app.database.db import SessionLocal
from app.models.match import Match, MatchSet

db = SessionLocal()

matches_3_1 = db.query(Match).filter(((Match.sets_player1 == 3) & (Match.sets_player2 == 1)) | ((Match.sets_player1 == 1) & (Match.sets_player2 == 3))).limit(5).all()

print("=== Матчи со счетом 3:1 ===")
for match in matches_3_1:
    sets_count = db.query(MatchSet).filter(MatchSet.match_id == match.id).count()
    print(f"Match {match.date}: {match.sets_player1}:{match.sets_player2} - MatchSets: {sets_count}")
    
db.close()
