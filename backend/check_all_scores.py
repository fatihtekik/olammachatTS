from app.database.db import SessionLocal
from app.models.match import Match, MatchSet
from sqlalchemy import func

db = SessionLocal()

# Статистика по счетам
score_stats = db.query(
    Match.sets_player1,
    Match.sets_player2,
    func.count(Match.id).label('count')
).group_by(Match.sets_player1, Match.sets_player2).all()

print("=== Статистика счетов в БД ===")
for p1, p2, count in sorted(score_stats, key=lambda x: -x[2]):
    print(f"{p1}:{p2} - {count} матчей")

# Проверяем сколько сетов записано для каждого типа счета
print("\n=== Проверка MatchSet для разных счетов ===")
for p1_sets, p2_sets, _ in score_stats:
    match = db.query(Match).filter(
        Match.sets_player1 == p1_sets,
        Match.sets_player2 == p2_sets
    ).first()
    
    if match:
        sets_count = db.query(MatchSet).filter(MatchSet.match_id == match.id).count()
        expected = p1_sets + p2_sets
        status = "✅" if sets_count == expected else "❌"
        print(f"{status} Счет {p1_sets}:{p2_sets} - MatchSets: {sets_count}/{expected}")

db.close()
