"""
API роуты для анализа сценариев игроков
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.db import get_db
from app.schemas.scenario import (
    ScenarioStatsResponse,
    ScenarioMatchDetail,
    PlayerScenariosResponse,
    AnalyzePlayerResponse
)
from app.services.scenario_analysis_service import ScenarioAnalysisService
from app.models.match import Player

router = APIRouter()


@router.get("/player/{player_id}/scenarios", response_model=PlayerScenariosResponse)
async def get_player_scenarios(
    player_id: str,
    db: Session = Depends(get_db)
):
    """
    Получить статистику по всем сценариям для игрока
    """
    # Проверяем существование игрока
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Получаем сценарии
    scenarios = ScenarioAnalysisService.get_player_scenarios(db, player_id)
    
    return PlayerScenariosResponse(
        player_id=player_id,
        scenarios=scenarios
    )


@router.get("/player/{player_id}/scenarios/{scenario_code}/matches", response_model=List[ScenarioMatchDetail])
async def get_scenario_matches(
    player_id: str,
    scenario_code: str,
    db: Session = Depends(get_db)
):
    """
    Получить детальный список матчей для конкретного сценария
    """
    # Проверяем существование игрока
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Проверяем валидность кода сценария
    if scenario_code not in ScenarioAnalysisService.SCENARIOS:
        raise HTTPException(status_code=400, detail="Invalid scenario code")
    
    # Получаем матчи
    matches = ScenarioAnalysisService.get_scenario_matches(db, player_id, scenario_code)
    
    return matches


@router.post("/player/{player_id}/scenarios/analyze", response_model=AnalyzePlayerResponse)
async def analyze_player(
    player_id: str,
    db: Session = Depends(get_db)
):
    """
    Запустить анализ матчей игрока и обновить статистику по сценариям
    """
    # Проверяем существование игрока
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    
    # Анализируем матчи
    result = ScenarioAnalysisService.analyze_player_matches(db, player_id)
    
    return AnalyzePlayerResponse(
        player_id=result["player_id"],
        scenarios_analyzed=result["scenarios_analyzed"],
        total_matches=result["total_matches"],
        message=f"Successfully analyzed {result['total_matches']} matches, found {result['scenarios_analyzed']} scenarios"
    )


@router.post("/scenarios/analyze-all", response_model=dict)
async def analyze_all_players(
    db: Session = Depends(get_db)
):
    """
    Запустить анализ для всех игроков
    """
    players = db.query(Player).all()
    
    results = []
    for player in players:
        try:
            result = ScenarioAnalysisService.analyze_player_matches(db, player.id)
            results.append({
                "player_id": player.id,
                "player_name": player.full_name,
                "scenarios": result["scenarios_analyzed"],
                "matches": result["total_matches"]
            })
        except Exception as e:
            results.append({
                "player_id": player.id,
                "player_name": player.full_name,
                "error": str(e)
            })
    
    return {
        "total_players": len(players),
        "analyzed": len([r for r in results if "error" not in r]),
        "failed": len([r for r in results if "error" in r]),
        "results": results
    }
