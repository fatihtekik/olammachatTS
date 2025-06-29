from pydantic import BaseModel

class MatchData(BaseModel):
    игрок_1: str
    игрок_2: str
    рейтинг_1: float
    рейтинг_2: float
    счёт: str
    этап: str
    турнир: str
    лига: str
