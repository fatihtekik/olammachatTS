
# from backend.app.analysisbypairs.dop_functions import ai_generate_match
# from fastapi import APIRouter, Depends, HTTPException, Body, Request
# from app.models.match import Player, Match, PlayerTrigger, PlayerStats
# from sqlalchemy.orm import Session
# from app.database.db import get_db

# router = APIRouter(prefix="/match-analysis", tags=["Match Analysis"])

# @router.post("/match-ai")
# async def match_ai_analysis(payload: dict, db: Session = Depends(get_db)):
#     match_id = payload["match_id"]
#     player1_id = payload["player1_id"]
#     player2_id = payload["player2_id"]

#     match = db.query(Match).filter(Match.id == match_id).first()
#     player1 = db.query(Player).filter(Player.id == player1_id).first()
#     player2 = db.query(Player).filter(Player.id == player2_id).first()

#     if not match or not player1 or not player2:
#         raise HTTPException(status_code=404, detail="Match or players not found")

#     ai_text = ai_generate_match(
#         match=match,
#         player1=player1,
#         player2=player2,
#         db=db
#     )

#     return {
#         "ai_text": ai_text  # ❗ ПОЛНЫЙ ТЕКСТ, С think
#     }
