"""
Инструменты для аналитики и статистики матчей.
Проверка счетов, сетов, поиск несоответствий.
"""
import sys
from pathlib import Path

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func
from app.database.db import SessionLocal
from app.models.match import Match, MatchSet, Player


def print_header(title: str):
    """Красивый заголовок"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_score_statistics():
    """Выводит статистику по счетам матчей"""
    print_header("СТАТИСТИКА СЧЕТОВ МАТЧЕЙ")
    
    db = SessionLocal()
    
    try:
        # Группируем по счетам
        score_stats = db.query(
            Match.sets_player1,
            Match.sets_player2,
            func.count(Match.id).label('count')
        ).group_by(Match.sets_player1, Match.sets_player2).all()
        
        if not score_stats:
            print("ℹ️ Матчей в БД нет")
            return
        
        print("\n📊 Распределение счетов:")
        print("-" * 40)
        total = 0
        for p1, p2, count in sorted(score_stats, key=lambda x: -x[2]):
            total += count
            bar = "█" * min(count // 5, 30)
            print(f"  {p1}:{p2}  │ {count:5d} │ {bar}")
        
        print("-" * 40)
        print(f"  ВСЕГО: {total} матчей")
        
    finally:
        db.close()


def check_match_sets_integrity():
    """Проверяет соответствие количества сетов счёту матча"""
    print_header("ПРОВЕРКА ЦЕЛОСТНОСТИ СЕТОВ")
    
    db = SessionLocal()
    
    try:
        # Получаем уникальные счета
        score_stats = db.query(
            Match.sets_player1,
            Match.sets_player2,
        ).distinct().all()
        
        errors = 0
        checked = 0
        
        print("\n🔍 Проверка соответствия сетов для каждого типа счёта:")
        print("-" * 60)
        
        for p1_sets, p2_sets in score_stats:
            # Берём первый матч с таким счётом
            match = db.query(Match).filter(
                Match.sets_player1 == p1_sets,
                Match.sets_player2 == p2_sets
            ).first()
            
            if match:
                sets_count = db.query(MatchSet).filter(MatchSet.match_id == match.id).count()
                expected = (p1_sets or 0) + (p2_sets or 0)
                
                if sets_count == expected:
                    status = "✅"
                else:
                    status = "❌"
                    errors += 1
                
                checked += 1
                print(f"  {status} Счёт {p1_sets}:{p2_sets} │ Сетов: {sets_count}/{expected}")
        
        print("-" * 60)
        print(f"\n📊 Проверено: {checked} типов счетов")
        if errors > 0:
            print(f"⚠️ Найдено проблем: {errors}")
        else:
            print("✅ Все сеты соответствуют счетам!")
            
    finally:
        db.close()


def check_specific_match(match_id: str):
    """Детальная проверка конкретного матча"""
    print_header(f"ДЕТАЛИ МАТЧА: {match_id[:8]}...")
    
    db = SessionLocal()
    
    try:
        match = db.query(Match).filter(Match.id == match_id).first()
        
        if not match:
            print(f"❌ Матч {match_id} не найден!")
            return
        
        print(f"\n📋 Основная информация:")
        print(f"  └─ ID: {match.id}")
        print(f"  └─ Дата: {match.date}")
        print(f"  └─ Время: {match.time}")
        print(f"  └─ Счёт: {match.sets_player1}:{match.sets_player2}")
        print(f"  └─ SL ID: {match.match_sl_id}")
        
        # Игроки
        p1 = db.query(Player).filter(Player.id == match.player1_id).first()
        p2 = db.query(Player).filter(Player.id == match.player2_id).first()
        winner = db.query(Player).filter(Player.id == match.winner_id).first() if match.winner_id else None
        
        print(f"\n👤 Игроки:")
        print(f"  └─ Игрок 1: {p1.full_name if p1 else 'Unknown'}")
        print(f"  └─ Игрок 2: {p2.full_name if p2 else 'Unknown'}")
        print(f"  └─ Победитель: {winner.full_name if winner else 'Не определён'}")
        
        # Сеты
        sets = db.query(MatchSet).filter(
            MatchSet.match_id == match_id
        ).order_by(MatchSet.set_number).all()
        
        print(f"\n🏓 Сеты ({len(sets)}):")
        for s in sets:
            winner_name = "P1" if s.winner_id == match.player1_id else "P2"
            print(f"  └─ Сет {s.set_number}: {s.player1_points}:{s.player2_points} (Победитель: {winner_name})")
        
        # Проверка целостности
        expected_sets = (match.sets_player1 or 0) + (match.sets_player2 or 0)
        if len(sets) == expected_sets:
            print(f"\n✅ Целостность: OK (сетов: {len(sets)}/{expected_sets})")
        else:
            print(f"\n❌ Целостность: ОШИБКА (сетов: {len(sets)}/{expected_sets})")
            
    finally:
        db.close()


def find_matches_with_issues():
    """Ищет матчи с проблемами в данных"""
    print_header("ПОИСК ПРОБЛЕМНЫХ МАТЧЕЙ")
    
    db = SessionLocal()
    
    try:
        issues = []
        
        # Получаем все матчи
        matches = db.query(Match).all()
        
        print(f"\n🔍 Проверка {len(matches)} матчей...")
        
        for match in matches:
            problems = []
            
            # Проверка количества сетов
            sets_count = db.query(MatchSet).filter(MatchSet.match_id == match.id).count()
            expected = (match.sets_player1 or 0) + (match.sets_player2 or 0)
            
            if sets_count != expected:
                problems.append(f"Сетов: {sets_count}/{expected}")
            
            # Проверка победителя
            if not match.winner_id:
                problems.append("Нет победителя")
            
            # Проверка счёта
            if match.sets_player1 is None or match.sets_player2 is None:
                problems.append("Нет счёта")
            
            if problems:
                issues.append({
                    'id': match.id,
                    'date': match.date,
                    'problems': problems
                })
        
        if not issues:
            print("\n✅ Проблемных матчей не найдено!")
        else:
            print(f"\n⚠️ Найдено {len(issues)} проблемных матчей:")
            print("-" * 60)
            for issue in issues[:20]:  # Показываем первые 20
                print(f"  {issue['id'][:8]}... │ {issue['date']} │ {', '.join(issue['problems'])}")
            if len(issues) > 20:
                print(f"  ... и ещё {len(issues) - 20} матчей")
                
    finally:
        db.close()


def main():
    """Точка входа CLI"""
    print_header("ИНСТРУМЕНТЫ АНАЛИТИКИ")
    
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        
        if action == 'scores':
            check_score_statistics()
        elif action == 'sets':
            check_match_sets_integrity()
        elif action == 'issues':
            find_matches_with_issues()
        elif action == 'match' and len(sys.argv) > 2:
            check_specific_match(sys.argv[2])
        else:
            print(f"❌ Неизвестная команда: {action}")
            print("\n📋 Доступные команды:")
            print("  python -m tools.stats scores       - статистика счетов")
            print("  python -m tools.stats sets         - проверка сетов")
            print("  python -m tools.stats issues       - поиск проблем")
            print("  python -m tools.stats match <id>   - детали матча")
    else:
        # Запускаем все проверки
        check_score_statistics()
        check_match_sets_integrity()
        find_matches_with_issues()


if __name__ == "__main__":
    main()
