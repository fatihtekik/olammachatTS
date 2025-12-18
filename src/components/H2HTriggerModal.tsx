import React, { useState, useEffect } from 'react';
import './H2HTriggerModal.css';

interface H2HTriggerModalProps {
  player1Id: string;
  player2Id: string;
  player1Name: string;
  player2Name: string;
  triggerType: string;
  triggerValue: string;
  severity: number;
  onClose: () => void;
}

interface MatchSet {
  set_number: number;
  player1_points: number;
  player2_points: number;
}

interface MatchData {
  id: string;
  date: string | null;
  score: string;
  winner_id: string;
  player1_id: string;
  player2_id: string;
  rating1: number;
  rating2: number;
  league1: string | null;
  league2: string | null;
  sets: MatchSet[];
}

interface TriggerDetails {
  ai_analysis: string;
  trigger: {
    trigger_type: string;
    trigger_subtype: string | null;
    trigger_value: string;
    severity_level: number;
  };
  matches: MatchData[];
}

const H2HTriggerModal: React.FC<H2HTriggerModalProps> = ({
  player1Id,
  player2Id,
  player1Name,
  player2Name,
  triggerType,
  triggerValue,
  severity,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggerDetails, setTriggerDetails] = useState<TriggerDetails | null>(null);

  useEffect(() => {
    fetchTriggerDetails();
  }, [player1Id, player2Id, triggerType]);

  const fetchTriggerDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `http://localhost:8000/api/v1/match-analysis/h2h/${player1Id}/${player2Id}/${triggerType}`
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка загрузки данных');
      }

      const data = await response.json();
      setTriggerDetails(data);
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки данных триггера');
    } finally {
      setLoading(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const getSeverityClass = (level: number) => {
    if (level >= 4) return 'high';
    if (level >= 2) return 'medium';
    return 'low';
  };

  const getSeverityLabel = (level: number) => {
    if (level >= 4) return 'Высокий';
    if (level >= 2) return 'Средний';
    return 'Низкий';
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return 'Дата неизвестна';
    return new Date(dateStr).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  const getLeagueName = (leagueId: string | null) => {
    if (!leagueId) return '';
    // Простое отображение лиги
    return `Лига ${leagueId}`;
  };

  return (
    <div className="h2h-trigger-modal-backdrop" onClick={handleBackdropClick}>
      <div className="h2h-trigger-modal">
        {/* Заголовок */}
        <div className="h2h-trigger-modal-header">
          <div className="header-content">
            <h2>{triggerValue} - {player2Name}</h2>
            <span className={`severity-badge severity-${getSeverityClass(severity)}`}>
              {getSeverityLabel(severity)}
            </span>
          </div>
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Контент */}
        <div className="h2h-trigger-modal-content">
          {loading && (
            <div className="loading-state">
              <div className="loading-spinner"></div>
              <p>Загрузка данных триггера...</p>
            </div>
          )}

          {error && (
            <div className="error-state">
              <p>⚠️ {error}</p>
              <button onClick={fetchTriggerDetails}>Повторить</button>
            </div>
          )}

          {!loading && !error && triggerDetails && (
            <>
              {/* Анализ ИИ */}
              <div className="ai-analysis-section">
                <h3>Анализ ИИ:</h3>
                <p className="ai-analysis-text">{triggerDetails.ai_analysis}</p>
              </div>

              {/* Информация о триггере */}
              <div className="trigger-info-section">
                <div className="trigger-info-grid">
                  <div className="info-item">
                    <span className="info-label">Тип триггера:</span>
                    <span className="info-value">{triggerDetails.trigger.trigger_type}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Значение:</span>
                    <span className="info-value">{triggerDetails.trigger.trigger_value}</span>
                  </div>
                </div>
              </div>

              {/* Список матчей-доказательств */}
              <div className="evidence-matches-section">
                <h3>Доказательства ({triggerDetails.matches.length} матчей):</h3>
                
                {triggerDetails.matches.length === 0 ? (
                  <div className="no-matches">
                    <p>Нет матчей для отображения</p>
                  </div>
                ) : (
                  <div className="matches-list">
                    {triggerDetails.matches.map((match) => {
                      // Используем player1_id из ответа матча для определения победителя
                      const isPlayer1Winner = match.winner_id === match.player1_id;
                      const isPlayer2Winner = match.winner_id === match.player2_id;
                      
                      return (
                      <div key={match.id} className="evidence-match-card">
                        {/* Игрок 1 */}
                        <div className={`match-player player-left ${isPlayer1Winner ? 'winner-side' : 'loser-side'}`}>
                          <div className="player-name">{player1Name}</div>
                          <div className="player-details">
                            <span className="player-rating">Рейтинг {match.rating1}</span>
                            {match.league1 && (
                              <span className="player-league">{getLeagueName(match.league1)}</span>
                            )}
                          </div>
                          {/* Очки по сетам слева */}
                          <div className="sets-points">
                            {match.sets.map((set) => (
                              <span 
                                key={set.set_number} 
                                className={`set-point ${set.player1_points > set.player2_points ? 'set-win' : 'set-lose'}`}
                              >
                                {set.player1_points}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Счёт в центре */}
                        <div className="match-center">
                          <div className="match-score-box">
                            <span className="main-score">{match.score}</span>
                          </div>
                          <div className="match-date">{formatDate(match.date)}</div>
                        </div>

                        {/* Игрок 2 */}
                        <div className={`match-player player-right ${isPlayer2Winner ? 'winner-side' : 'loser-side'}`}>
                          <div className="player-name">{player2Name}</div>
                          <div className="player-details">
                            <span className="player-rating">Рейтинг {match.rating2}</span>
                            {match.league2 && (
                              <span className="player-league">{getLeagueName(match.league2)}</span>
                            )}
                          </div>
                          {/* Очки по сетам справа */}
                          <div className="sets-points">
                            {match.sets.map((set) => (
                              <span 
                                key={set.set_number} 
                                className={`set-point ${set.player2_points > set.player1_points ? 'set-win' : 'set-lose'}`}
                              >
                                {set.player2_points}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default H2HTriggerModal;
