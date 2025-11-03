from app.database.db import SessionLocal
from app.models.match import Match

db = SessionLocal()

# Найдем матчи где score и sets_player не совпадают
mismatches = []
for match in db.query(Match).limit(100).all():
    if match.score and ':' in match.score:
        try:
            score_parts = match.score.split(':')
            expected_p1 = int(score_parts[0])
            expected_p2 = int(score_parts[1])
            
            if expected_p1 != match.sets_player1 or expected_p2 != match.sets_player2:
                mismatches.append({
                    'id': match.id,
                    'date': match.date,
                    'score': match.score,
                    'expected': f"{expected_p1}:{expected_p2}",
                    'actual': f"{match.sets_player1}:{match.sets_player2}"
                })
        except:
            pass

print(f"=== Найдено несоответствий: {len(mismatches)} ===")
for m in mismatches[:10]:
    print(f"{m['date']}: score='{m['score']}' но sets={m['actual']} (ожидалось {m['expected']})")

db.close()
