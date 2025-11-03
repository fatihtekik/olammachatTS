from app.database.db import SessionLocal
from app.models.match import MatchSet, Match, Player

db = SessionLocal()

match_id = 'd99bf607-62d6-483c-a359-949096936c75'

# Находим матч
match = db.query(Match).filter(Match.id == match_id).first()

if match:
    print(f"Матч найден: {match.id}")
    print(f"Дата: {match.date}")
    print(f"Счет: {match.sets_player1}:{match.sets_player2}")
    
    # Получаем игроков
    p1 = db.query(Player).filter(Player.id == match.player1_id).first()
    p2 = db.query(Player).filter(Player.id == match.player2_id).first()
    
    print(f"Игрок 1: {p1.full_name if p1 else 'Unknown'}")
    print(f"Игрок 2: {p2.full_name if p2 else 'Unknown'}")
    print(f"Победитель ID: {match.winner_id}")
    
    # Получаем все сеты
    sets = db.query(MatchSet).filter(
        MatchSet.match_id == match_id
    ).order_by(MatchSet.set_number).all()
    
    print(f"\nВсего сетов в БД: {len(sets)}")
    for s in sets:
        winner_name = "P1" if s.winner_id == match.player1_id else "P2"
        print(f"  Сет {s.set_number}: {s.player1_points}:{s.player2_points} (Победитель: {winner_name})")
else:
    print(f"Матч {match_id} не найден!")

db.close()
