import React, { useState, useEffect } from 'react';
import './H2HAnalysisPage.css';

interface Player {
  id: string;
  full_name: string;
  current_rating: number;
}

interface H2HStats {
  player1: {
    id: string;
    full_name: string;
    current_rating: number;
    triggers: Array<{
      type: string;
      severity: number;
    }>;
  };
  player2: {
    id: string;
    full_name: string;
    current_rating: number;
    triggers: Array<{
      type: string;
      severity: number;
    }>;
  };
  matches: Array<{
    id: string;
    date: string;
    score: string;
    stage: string | null;
    league_id: string | null;
    winner_id: string;
    sets: Array<{
      set_number: number;
      player1_points: number;
      player2_points: number;
    }>;
    player1_triggers: Array<{
      type: string;
      severity: number;
    }>;
    player2_triggers: Array<{
      type: string;
      severity: number;
    }>;
    serve_efficiency_p1: number | null;
    receive_efficiency_p1: number | null;
    serve_efficiency_p2: number | null;
    receive_efficiency_p2: number | null;
  }>;
  ai_analysis: string;
}

interface DateAnalysisResult {
  date: string;
  pairs: Array<{
    player1: {
      id: string;
      full_name: string;
      current_rating: number;
    };
    player2: {
      id: string;
      full_name: string;
      current_rating: number;
    };
    matches: Array<{
      id: string;
      score: string;
      stage: string | null;
      winner_id: string;
      sets: Array<{
        set_number: number;
        player1_points: number;
        player2_points: number;
      }>;
      player1_triggers: Array<{
        type: string;
        severity: number;
      }>;
      player2_triggers: Array<{
        type: string;
        severity: number;
      }>;
    }>;
    player1_wins: number;
    player2_wins: number;
    total_matches: number;
  }>;
  total_matches: number;
}

const H2HAnalysisPage: React.FC = () => {
  const [analysisMode, setAnalysisMode] = useState<'players' | 'date'>('players');
  const [players, setPlayers] = useState<Player[]>([]);
  const [player1Id, setPlayer1Id] = useState<string>('');
  const [player2Id, setPlayer2Id] = useState<string>('');
  const [matchDate, setMatchDate] = useState<string>('');
  const [dateForAnalysis, setDateForAnalysis] = useState<string>('');
  const [h2hStats, setH2hStats] = useState<H2HStats | null>(null);
  const [dateAnalysis, setDateAnalysis] = useState<DateAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [selectedMatch, setSelectedMatch] = useState<any>(null);
  const [showModal, setShowModal] = useState(false);
  const [modalPlayers, setModalPlayers] = useState<{player1: any, player2: any} | null>(null);

  useEffect(() => {
    fetchPlayers();
  }, []);

  const fetchPlayers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/players');
      const data = await response.json();
      setPlayers(data);
    } catch (err) {
      console.error('Ошибка загрузки игроков:', err);
    }
  };

  const handleAnalyze = async () => {
    if (!player1Id || !player2Id) {
      setError('Выберите обоих игроков');
      return;
    }

    if (player1Id === player2Id) {
      setError('Выберите разных игроков');
      return;
    }

    setLoading(true);
    setError('');
    setDateAnalysis(null);

    try {
      let url = `http://localhost:8000/api/v1/match-analysis/h2h/${player1Id}/${player2Id}`;
      if (matchDate) {
        url += `?match_date=${matchDate}`;
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error('Ошибка анализа');
      }
      
      const data = await response.json();
      setH2hStats(data);
    } catch (err: any) {
      setError(err.message || 'Ошибка анализа');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeByDate = async () => {
    if (!dateForAnalysis) {
      setError('Выберите дату для анализа');
      return;
    }

    setLoading(true);
    setError('');
    setH2hStats(null);

    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/match-analysis/h2h-by-date/${dateForAnalysis}`
      );
      
      if (!response.ok) {
        throw new Error('Ошибка анализа');
      }
      
      const data = await response.json();
      setDateAnalysis(data);
    } catch (err: any) {
      setError(err.message || 'Ошибка анализа');
    } finally {
      setLoading(false);
    }
  };

  const getPlayer1Wins = () => {
    if (!h2hStats || h2hStats.matches.length === 0) return 0;
    return h2hStats.matches.filter(m => m.winner_id === h2hStats.player1.id).length;
  };

  const getPlayer2Wins = () => {
    if (!h2hStats || h2hStats.matches.length === 0) return 0;
    return h2hStats.matches.filter(m => m.winner_id === h2hStats.player2.id).length;
  };

  const getSeverityClass = (severity: number) => {
    if (severity >= 4) return 'high';
    if (severity >= 2) return 'medium';
    return 'low';
  };

  const openMatchModal = (match: any, player1: any, player2: any) => {
    setSelectedMatch(match);
    setModalPlayers({ player1, player2 });
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setSelectedMatch(null);
    setModalPlayers(null);
  };

  return (
    <div className="h2h-analysis-page">
      <div className="page-header">
        <h1>Анализ по парам</h1>
        <p>Статистика встреч между игроками</p>
      </div>

      <div className="mode-selector">
        <button 
          className={`mode-btn ${analysisMode === 'players' ? 'active' : ''}`}
          onClick={() => setAnalysisMode('players')}
        >
          Анализ по игрокам
        </button>
        <button 
          className={`mode-btn ${analysisMode === 'date' ? 'active' : ''}`}
          onClick={() => setAnalysisMode('date')}
        >
          Анализ по дате
        </button>
      </div>

      {analysisMode === 'players' ? (
        <div className="h2h-selection">
          <div className="player-selector">
            <label>Игрок 1</label>
            <select value={player1Id} onChange={(e) => setPlayer1Id(e.target.value)}>
              <option value="">Выберите игрока</option>
              {players.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.full_name} (Рейтинг: {player.current_rating})
                </option>
              ))}
            </select>
          </div>

          <div className="vs-divider">VS</div>

          <div className="player-selector">
            <label>Игрок 2</label>
            <select value={player2Id} onChange={(e) => setPlayer2Id(e.target.value)}>
              <option value="">Выберите игрока</option>
              {players.map((player) => (
                <option key={player.id} value={player.id}>
                  {player.full_name} (Рейтинг: {player.current_rating})
                </option>
              ))}
            </select>
          </div>

          <div className="player-selector">
            <label>Дата матча (опционально)</label>
            <input 
              type="date" 
              value={matchDate} 
              onChange={(e) => setMatchDate(e.target.value)}
              className="date-input"
            />
          </div>

          <button
            className="analyze-btn"
            onClick={handleAnalyze}
            disabled={loading || !player1Id || !player2Id}
          >
            {loading ? 'Анализ...' : 'Анализировать'}
          </button>
        </div>
      ) : (
        <div className="h2h-selection">
          <div className="player-selector">
            <label>Выберите дату</label>
            <input 
              type="date" 
              value={dateForAnalysis} 
              onChange={(e) => setDateForAnalysis(e.target.value)}
              className="date-input"
            />
          </div>

          <button
            className="analyze-btn"
            onClick={handleAnalyzeByDate}
            disabled={loading || !dateForAnalysis}
          >
            {loading ? 'Анализ...' : 'Анализировать'}
          </button>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {h2hStats && (
        <div className="h2h-results">
          <div className="h2h-summary">
            <div className="player-card">
              <h3>Игрок 1</h3>
              <p className="player-name">{h2hStats.player1.full_name}</p>
              <p className="player-rating">Рейтинг: {h2hStats.player1.current_rating}</p>
              <div className="triggers-section">
                <h4>Общие триггеры:</h4>
                {h2hStats.player1.triggers.length > 0 ? (
                  h2hStats.player1.triggers.map((trigger, idx) => (
                    <span 
                      key={idx} 
                      className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                    >
                      {trigger.type}
                    </span>
                  ))
                ) : (
                  <span className="no-triggers">Нет активных триггеров</span>
                )}
              </div>
            </div>

            <div className="match-score">
              <div className="score-display">
                <span className="score-number">{getPlayer1Wins()}</span>
                <span className="score-separator">:</span>
                <span className="score-number">{getPlayer2Wins()}</span>
              </div>
              <div className="sets-display">
                Всего матчей: {h2hStats.matches.length}
              </div>
            </div>

            <div className="player-card">
              <h3>Игрок 2</h3>
              <p className="player-name">{h2hStats.player2.full_name}</p>
              <p className="player-rating">Рейтинг: {h2hStats.player2.current_rating}</p>
              <div className="triggers-section">
                <h4>Общие триггеры:</h4>
                {h2hStats.player2.triggers.length > 0 ? (
                  h2hStats.player2.triggers.map((trigger, idx) => (
                    <span 
                      key={idx} 
                      className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                    >
                      {trigger.type}
                    </span>
                  ))
                ) : (
                  <span className="no-triggers">Нет активных триггеров</span>
                )}
              </div>
            </div>
          </div>

          <div className="matches-list">
            <h3>История матчей:</h3>
            {h2hStats.matches.map((match) => (
              <div 
                key={match.id} 
                className="match-card clickable"
                onClick={() => openMatchModal(match, h2hStats.player1, h2hStats.player2)}
              >
                <div className="match-header">
                  <span className="match-date">{new Date(match.date).toLocaleDateString('ru-RU')}</span>
                  <span className="match-score-badge">{match.score}</span>
                  {match.stage && <span className="match-stage">{match.stage}</span>}
                  <span className={`match-winner ${match.winner_id === h2hStats.player1.id ? 'winner-p1' : 'winner-p2'}`}>
                    Победитель: {match.winner_id === h2hStats.player1.id ? h2hStats.player1.full_name : h2hStats.player2.full_name}
                  </span>
                </div>
                
                <div className="match-sets">
                  <div className="sets-header">Сеты:</div>
                  {match.sets.map((set) => (
                    <span key={set.set_number} className="set-item">
                      Сет {set.set_number}: {set.player1_points}:{set.player2_points}
                    </span>
                  ))}
                </div>

                {(match.player1_triggers.length > 0 || match.player2_triggers.length > 0) && (
                  <div className="match-triggers">
                    {match.player1_triggers.length > 0 && (
                      <div className="match-trigger-group">
                        <strong>{h2hStats.player1.full_name}:</strong>
                        {match.player1_triggers.map((trigger, idx) => (
                          <span 
                            key={idx} 
                            className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                          >
                            {trigger.type}
                          </span>
                        ))}
                      </div>
                    )}
                    {match.player2_triggers.length > 0 && (
                      <div className="match-trigger-group">
                        <strong>{h2hStats.player2.full_name}:</strong>
                        {match.player2_triggers.map((trigger, idx) => (
                          <span 
                            key={idx} 
                            className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                          >
                            {trigger.type}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {(match.serve_efficiency_p1 || match.receive_efficiency_p1) && (
                  <div className="match-efficiency">
                    <div className="efficiency-row">
                      <span>{h2hStats.player1.full_name}:</span>
                      {match.serve_efficiency_p1 && <span>Подача: {match.serve_efficiency_p1}%</span>}
                      {match.receive_efficiency_p1 && <span>Приём: {match.receive_efficiency_p1}%</span>}
                    </div>
                    <div className="efficiency-row">
                      <span>{h2hStats.player2.full_name}:</span>
                      {match.serve_efficiency_p2 && <span>Подача: {match.serve_efficiency_p2}%</span>}
                      {match.receive_efficiency_p2 && <span>Приём: {match.receive_efficiency_p2}%</span>}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="h2h-ai-analysis">
            <h3>Анализ ИИ:</h3>
            <p className="ai-text">
              {h2hStats.ai_analysis}
            </p>
          </div>
        </div>
      )}

      {dateAnalysis && (
        <div className="date-analysis-results">
          <div className="date-header">
            <h2>Матчи на {new Date(dateAnalysis.date).toLocaleDateString('ru-RU')}</h2>
            <p>Всего матчей: {dateAnalysis.total_matches}</p>
          </div>

          {dateAnalysis.pairs.length === 0 ? (
            <div className="no-matches">Матчей на эту дату не найдено</div>
          ) : (
            <div className="pairs-grid">
              {dateAnalysis.pairs.map((pair, idx) => (
                <div key={idx} className="pair-card">
                  <div className="pair-header">
                    <div className="pair-players">
                      <span className="pair-player-name">{pair.player1.full_name}</span>
                      <span className="vs-separator">VS</span>
                      <span className="pair-player-name">{pair.player2.full_name}</span>
                    </div>
                    <div className="pair-score">
                      <span className="pair-wins">{pair.player1_wins}</span>
                      <span>:</span>
                      <span className="pair-wins">{pair.player2_wins}</span>
                    </div>
                  </div>

                  <div className="pair-stats">
                    <span>Матчей: {pair.total_matches}</span>
                    <span>Рейтинг: {pair.player1.current_rating} / {pair.player2.current_rating}</span>
                  </div>

                  <div className="pair-matches">
                    {pair.matches.map((match, mIdx) => (
                      <div 
                        key={mIdx} 
                        className="pair-match-item clickable"
                        onClick={() => openMatchModal(match, pair.player1, pair.player2)}
                      >
                        <div className="pair-match-header">
                          <span className="pair-match-score">{match.score}</span>
                          {match.stage && <span className="pair-match-stage">{match.stage}</span>}
                          <span className={`pair-match-winner ${match.winner_id === pair.player1.id ? 'winner-p1' : 'winner-p2'}`}>
                            {match.winner_id === pair.player1.id ? pair.player1.full_name : pair.player2.full_name}
                          </span>
                        </div>

                        <div className="pair-match-sets">
                          {match.sets.map((set) => (
                            <span key={set.set_number} className="pair-set">
                              {set.player1_points}:{set.player2_points}
                            </span>
                          ))}
                        </div>

                        {(match.player1_triggers.length > 0 || match.player2_triggers.length > 0) && (
                          <div className="pair-match-triggers">
                            {match.player1_triggers.length > 0 && (
                              <div className="pair-trigger-group">
                                <strong>{pair.player1.full_name}:</strong>
                                {match.player1_triggers.map((trigger, tIdx) => (
                                  <span 
                                    key={tIdx} 
                                    className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                                  >
                                    {trigger.type}
                                  </span>
                                ))}
                              </div>
                            )}
                            {match.player2_triggers.length > 0 && (
                              <div className="pair-trigger-group">
                                <strong>{pair.player2.full_name}:</strong>
                                {match.player2_triggers.map((trigger, tIdx) => (
                                  <span 
                                    key={tIdx} 
                                    className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                                  >
                                    {trigger.type}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {showModal && selectedMatch && modalPlayers && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={closeModal}>×</button>
            
            <div className="modal-body">
              <div className="modal-match-layout">
                <div className="modal-player-section">
                  <div className="modal-player-header">Игрок 1</div>
                  <div className="modal-player-name-large">{modalPlayers.player1.full_name}</div>
                  <div className="modal-player-rating">Рейтинг: {modalPlayers.player1.current_rating}</div>
                  
                  <div className="modal-triggers-section">
                    <h4>Триггеры:</h4>
                    <div className="modal-triggers-badges">
                      {selectedMatch.player1_triggers.length > 0 ? (
                        selectedMatch.player1_triggers.map((trigger: any, idx: number) => (
                          <span 
                            key={idx} 
                            className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                          >
                            {trigger.type}
                          </span>
                        ))
                      ) : (
                        <span className="no-triggers">Нет активных триггеров</span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="modal-score-section">
                  <div className="modal-score-large">
                    <span className="score-big">{selectedMatch.score.split(':')[0]}</span>
                    <span className="score-separator">:</span>
                    <span className="score-big">{selectedMatch.score.split(':')[1]}</span>
                  </div>
                  
                  <div className="modal-sets-small">
                    Счет по сетам
                    <div className="sets-grid-small">
                      {selectedMatch.sets.map((set: any, idx: number) => (
                        <div key={idx} className="set-row-small">
                          <span>{set.player1_points}</span>
                          <span>|</span>
                          <span>{set.player2_points}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="modal-player-section">
                  <div className="modal-player-header">Игрок 2</div>
                  <div className="modal-player-name-large">{modalPlayers.player2.full_name}</div>
                  <div className="modal-player-rating">Рейтинг: {modalPlayers.player2.current_rating}</div>
                  
                  <div className="modal-triggers-section">
                    <h4>Триггеры:</h4>
                    <div className="modal-triggers-badges">
                      {selectedMatch.player2_triggers.length > 0 ? (
                        selectedMatch.player2_triggers.map((trigger: any, idx: number) => (
                          <span 
                            key={idx} 
                            className={`trigger-badge trigger-${getSeverityClass(trigger.severity)}`}
                          >
                            {trigger.type}
                          </span>
                        ))
                      ) : (
                        <span className="no-triggers">Нет активных триггеров</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="modal-section ai-analysis-section">
                <h3>AI Анализ</h3>
                <div className="ai-analysis-placeholder">
                  <p>Готово для AI анализа матча между {modalPlayers.player1.full_name} и {modalPlayers.player2.full_name}</p>
                  <button className="ai-analyze-btn">Получить AI анализ</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default H2HAnalysisPage;
