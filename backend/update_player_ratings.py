from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from app.models.match import Player
from app.database import get_db_url
import logging

logger = logging.getLogger(__name__)

def update_existing_players_ratings():
    """Обновляет рейтинги существующих игроков на основе их имен"""
    engine = create_engine(get_db_url())
    session = Session(engine)
    
    try:
        players = session.query(Player).all()
        updated_count = 0
        
        for player in players:
            name_parts = player.full_name.split('rating:')
            if len(name_parts) > 1:
                try:
                    rating = int(name_parts[1].strip())
                    clean_name = name_parts[0].strip()
                    
                    # Обновляем имя и рейтинг
                    player.full_name = clean_name
                    player.current_rating = rating
                    updated_count += 1
                except ValueError:
                    logger.warning(f"Не удалось извлечь рейтинг из имени игрока: {player.full_name}")
        
        session.commit()
        print(f"Обновлено игроков: {updated_count}")
        
    except Exception as e:
        print(f"Произошла ошибка при обновлении рейтингов: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    update_existing_players_ratings()
