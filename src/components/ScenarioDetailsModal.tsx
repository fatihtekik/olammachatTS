import React, { useState, useEffect } from 'react';
import { ScenarioStats, ScenarioMatchDetail, ScenarioCode } from '../types/scenario';
import { scenarioAPI, scenarioUtils } from '../services/scenarioApi';
import './ScenarioDetailsModal.css';

interface ScenarioDetailsModalProps {
  scenario: ScenarioStats;
  playerId: string;
  playerName: string;
  onClose: () => void;
}

const ScenarioDetailsModal: React.FC<ScenarioDetailsModalProps> = ({
  scenario,
  playerId,
  playerName,
  onClose,
}) => {
  const [matches, setMatches] = useState<ScenarioMatchDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadMatches();
  }, [playerId, scenario.scenario_code]);

  const loadMatches = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await scenarioAPI.getScenarioMatches(
        playerId,
        scenario.scenario_code as ScenarioCode
      );
      setMatches(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки матчей');
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="scenario-modal-backdrop" onClick={handleBackdropClick}>
      <div className="scenario-modal">
        {/* Заголовок */}
        <div className="modal-header">
          <div>
            <h2>{playerName}</h2>
            <p className="modal-subtitle">
              {scenario.scenario_code}: {scenario.scenario_name}
            </p>
          </div>
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Статический блок с метриками */}
        <div className="modal-stats">
          <div className="stat-card">
            <div className="stat-label">Всего матчей</div>
            <div className="stat-value">{scenario.matches_total}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Побед</div>
            <div className="stat-value text-success">{scenario.wins}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Поражений</div>
            <div className="stat-value text-danger">{scenario.losses}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">% побед</div>
            <div 
              className="stat-value stat-badge"
              style={{ 
                backgroundColor: scenarioUtils.getWinRateColor(scenario.win_rate) 
              }}
            >
              {scenario.win_rate}%
            </div>
          </div>
          {scenario.fight_score !== null && (
            <div className="stat-card">
              <div className="stat-label">Fight Score</div>
              <div 
                className="stat-value stat-badge"
                style={{ 
                  backgroundColor: scenarioUtils.getFightScoreColor(scenario.fight_score) 
                }}
              >
                {scenario.fight_score.toFixed(3)}
              </div>
            </div>
          )}
        </div>

        {/* Интерпретация и поведение */}
        <div className="modal-interpretation">
          <div className="interpretation-item">
            <span className="interpretation-label">Интерпретация Fight Score:</span>
            <span className="interpretation-value">{scenario.fight_score_interpretation}</span>
          </div>
          <div className="interpretation-item">
            <span className="interpretation-label">Поведение игрока:</span>
            <span 
              className="interpretation-badge"
              style={{ 
                backgroundColor: scenarioUtils.getBehaviorBadgeColor(scenario.behavior_label) 
              }}
            >
              {scenario.behavior_label}
            </span>
          </div>
        </div>

        {/* Блок с доказательствами (матчи) */}
        <div className="modal-body">
          <h3>Доказательства (матчи)</h3>
          
          {loading ? (
            <div className="matches-loading">
              <div className="loading-spinner"></div>
              <p>Загрузка матчей...</p>
            </div>
          ) : error ? (
            <div className="matches-error">
              <p>{error}</p>
            </div>
          ) : matches.length === 0 ? (
            <div className="no-matches">
              <p>Нет матчей в этом сценарии</p>
            </div>
          ) : (
            <div className="matches-list">
              {matches.map((match) => (
                <div key={match.match_id} className="match-card">
                  <div className="match-header-row">
                    <div className="match-date">
                      {scenarioUtils.formatDate(match.date)}
                    </div>
                    <div 
                      className={`match-result ${match.is_win ? 'win' : 'loss'}`}
                    >
                      {match.is_win ? 'Победа' : 'Поражение'}
                    </div>
                  </div>

                  <div className="match-players">
                    <div className="player-name">{match.player1_name}</div>
                    <div className="match-score">{match.score}</div>
                    <div className="player-name">{match.player2_name}</div>
                  </div>

                  {match.fight_score !== null && (
                    <div className="match-fight-score">
                      Fight Score: 
                      <span 
                        className="fight-score-value"
                        style={{ 
                          color: scenarioUtils.getFightScoreColor(match.fight_score) 
                        }}
                      >
                        {match.fight_score.toFixed(3)}
                      </span>
                    </div>
                  )}

                  <div className="match-sets">
                    {match.sets.map((set, idx) => (
                      <div key={idx} className="set-detail">
                        <span className="set-number">Сет {set.set_number}:</span>
                        <span className="set-score">
                          {set.player1_points} - {set.player2_points}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScenarioDetailsModal;
