import React, { useState, useEffect } from 'react';
import './AnalysisPage.css';

interface TriggerType {
  id: string;
  name: string;
  description: string;
  severity: 'positive' | 'low' | 'medium' | 'high' | 'critical';
}

interface Trigger {
  id: string;
  player_id: string;
  player_name: string;
  player_rating?: number;
  trigger_type: string;
  trigger_subtype?: string;
  trigger_value: string;
  severity_level: number;
  period_start: string;
  period_end: string;
  is_active: boolean;
  trigger_metadata?: any;
  created_at: string;
  ai_analysis?: string; // ← Добавляем поле для ИИ-анализа
  player_stats?: {
    matches_played: number;
    wins: number;
    losses: number;
    win_rate: number;
    sets_won: number;
    sets_lost: number;
    recent_form: string | string[];
    recent_matches?: Array<{
      date: string;
      opponent: string;
      result: 'W' | 'L';
      score: string;
      time?: string;
    }>;
  };
}

interface Player {
  id: string;
  full_name: string;
  current_rating?: number;
  stats?: {
    matches_played: number;
    wins: number;
    losses: number;
    win_percentage: number;
    sets_won: number;
    sets_lost: number;
  };
}

interface AnalysisResult {
  period_start: string;
  period_end: string;
  total_players: number;
  total_matches: number;
  triggers_found: number;
  top_performers: any[];
  problem_players: any[];
  triggers: Trigger[];
}

const AnalysisPage: React.FC = () => {
  const [analysisMode, setAnalysisMode] = useState<'upload' | 'database'>('upload');
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [players, setPlayers] = useState<Player[]>([]);
  const [selectedPlayers, setSelectedPlayers] = useState<string[]>([]);
  const [periodStart, setPeriodStart] = useState<string>('');
  const [periodEnd, setPeriodEnd] = useState<string>('');
  const [triggerFilter, setTriggerFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<'name' | 'rating' | 'triggers' | 'severity'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  // Состояние для загрузки Excel
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<{
    created_matches?: number;
    skipped_duplicates?: number;
    total_processed?: number;
    errors?: string[];
  } | null>(null);
  // Состояние для модального окна
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [selectedTrigger, setSelectedTrigger] = useState<Trigger | null>(null);

  const triggerTypes: TriggerType[] = [
    { id: 'top_performers', name: 'Топ игроки', description: 'Высокие результаты', severity: 'positive' },
    { id: 'losers_50_percent', name: 'Слабые результаты', description: 'Процент побед менее 50%', severity: 'medium' },
    { id: 'defeat_0_3', name: 'Поражения 0:3', description: 'Поражения в сухую', severity: 'high' },
    { id: 'won_2_lost_3rd_set', name: 'Проигрыш после 2:0', description: 'Потеря преимущества в матче', severity: 'high' },
    { id: 'early_final_exit_advanced', name: 'Досрочный уход', description: 'Незавершенные финальные матчи', severity: 'high' },
    { id: 'led_1_set_lost_match', name: 'Потеря лидерства', description: 'Проигрыш после преимущества', severity: 'medium' },
    { id: 'led_2_sets_lost_match', name: 'Критический проигрыш', description: 'Проигрыш после лидерства 2:0', severity: 'critical' },
    { id: 'psychological_breakdown', name: 'Психологические проблемы', description: 'Нестабильная игра', severity: 'high' },
    { id: 'comeback_inability', name: 'Проблемы с камбеками', description: 'Неспособность отыграться', severity: 'medium' },
    { id: 'pressure_situations', name: 'Игра под давлением', description: 'Слабые результаты в важных матчах', severity: 'high' }
  ];

  useEffect(() => {
    loadPlayers();
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 3);
    
    setPeriodEnd(endDate.toISOString().split('T')[0]);
    setPeriodStart(startDate.toISOString().split('T')[0]);
  }, []);

  const loadPlayers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/players');
      if (response.ok) {
        const data = await response.json();
        setPlayers(data.players || []);
      }
    } catch (error) {
      console.error('Error loading players:', error);
    }
  };

  const analyzeDatabase = async () => {
    if (!periodStart || !periodEnd) {
      alert('Пожалуйста, выберите период анализа');
      return;
    }

    setLoading(true);
    try {
      const requestBody = {
        period_start: periodStart,
        period_end: periodEnd,
        player_ids: selectedPlayers.length > 0 ? selectedPlayers : undefined
      };

      const response = await fetch('http://localhost:8000/api/v1/match-analysis/analyze-database', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const result = await response.json();
        setAnalysisResult(result);
      } else {
        const error = await response.json();
        alert(`Ошибка анализа: ${error.detail}`);
      }
    } catch (error) {
      console.error('Error analyzing database:', error);
      alert('Ошибка при анализе базы данных');
    } finally {
      setLoading(false);
    }
  };

  // Обработчик выбора файла
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(e.target.files?.[0] || null);
  };
  
  // Функция загрузки Excel на сервер
  const uploadExcel = async () => {
    if (!selectedFile) {
      alert('Пожалуйста, выберите файл');
      return;
    }
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/upload-excel', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        const err = await response.json();
        alert(`Ошибка загрузки: ${err.detail || response.statusText}`);
        return;
      }
      const result = await response.json();
      setUploadResult(result);
    } catch (error) {
      console.error('Error uploading Excel:', error);
      alert('Ошибка при загрузке файла');
    }
  };
  
  // После загрузки, перейти к анализу базы данных и выполнить анализ
  const handleAnalyzeAfterUpload = async () => {
    setAnalysisMode('database');
    await analyzeDatabase();
  };

  const handlePlayerToggle = (playerId: string) => {
    setSelectedPlayers(prev => 
      prev.includes(playerId) 
        ? prev.filter(id => id !== playerId)
        : [...prev, playerId]
    );
  };

  const getSeverityColor = (severity: number) => {
    switch (severity) {
      case 1: return '#28a745'; // green - low
      case 2: return '#ffc107'; // yellow - medium  
      case 3: return '#dc3545'; // red - high
      default: return '#6c757d'; // gray - unknown
    }
  };

  const getSeverityText = (severity: number) => {
    switch (severity) {
      case 1: return 'Низкая';
      case 2: return 'Средняя';
      case 3: return 'Высокая';
      default: return 'Неизвестно';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU');
  };

  // Функция для получения всех триггеров игрока
  const getPlayerTriggers = (playerId: string): Trigger[] => {
    return analysisResult?.triggers.filter(t => t.player_id === playerId) || [];
  };

  // Функция для группировки триггеров по игрокам
  const getGroupedTriggers = (): Record<string, Trigger[]> => {
    if (!analysisResult?.triggers) return {};
    
    const grouped: Record<string, Trigger[]> = {};
    const filteredTriggers = analysisResult.triggers.filter(trigger => 
      !triggerFilter || trigger.trigger_type === triggerFilter
    );
    
    filteredTriggers.forEach(trigger => {
      if (!grouped[trigger.player_id]) {
        grouped[trigger.player_id] = [];
      }
      grouped[trigger.player_id].push(trigger);
    });
    
    return grouped;
  };

  // Функция для получения основного триггера игрока (с наивысшим severity)
  const getMainTrigger = (playerTriggers: Trigger[]): Trigger => {
    return playerTriggers.reduce((main, current) => 
      (current.severity_level || 0) > (main.severity_level || 0) ? current : main
    );
  };

  // Функция для сортировки игроков
  const getSortedPlayers = (): [string, Trigger[]][] => {
    const grouped = getGroupedTriggers();
    const entries = Object.entries(grouped);
    
    return entries.sort(([playerIdA, triggersA], [playerIdB, triggersB]) => {
      const mainTriggerA = getMainTrigger(triggersA);
      const mainTriggerB = getMainTrigger(triggersB);
      
      let comparison = 0;
      
      switch (sortBy) {
        case 'name':
          comparison = mainTriggerA.player_name.localeCompare(mainTriggerB.player_name);
          break;
        case 'rating':
          const ratingA = mainTriggerA.player_rating || 1000;
          const ratingB = mainTriggerB.player_rating || 1000;
          comparison = ratingB - ratingA; // По умолчанию высокий рейтинг выше
          break;
        case 'triggers':
          comparison = triggersA.length - triggersB.length;
          break;
        case 'severity':
          const severityA = Math.max(...triggersA.map(t => t.severity_level || 0));
          const severityB = Math.max(...triggersB.map(t => t.severity_level || 0));
          comparison = severityB - severityA; // По умолчанию высокая опасность выше
          break;
      }
      
      // Применяем порядок сортировки
      return sortOrder === 'desc' ? -comparison : comparison;
    });
  };

  // Функция для открытия модального окна с деталями триггера
  const openTriggerModal = (trigger: Trigger) => {
    setSelectedTrigger(trigger);
    setModalOpen(true);
  };

  // Функция для закрытия модального окна
  const closeModal = () => {
    setModalOpen(false);
    setSelectedTrigger(null);
  };

  return (
    <div className="analysis-page">
      <div className="analysis-header">
        <h1>Игроков анализ</h1>
        <div className="mode-selector">
          <button 
            className={`mode-btn ${analysisMode === 'upload' ? 'active' : ''}`}
            onClick={() => setAnalysisMode('upload')}
          >
            Загрузка Excel
          </button>
          <button 
            className={`mode-btn ${analysisMode === 'database' ? 'active' : ''}`}
            onClick={() => setAnalysisMode('database')}
          >
            Анализ базы данных
          </button>
        </div>
      </div>

      {analysisMode === 'upload' ? (
        <div className="upload-section">
          <div className="upload-card">
            <i className="bi bi-file-earmark-excel"></i>
            <h3>Загрузить Excel файл</h3>
            <p>Загрузите файл с матчами для анализа триггеров</p>
            <input type="file" accept=".xlsx,.xls" onChange={handleFileChange} />
            <button className="upload-btn" onClick={uploadExcel} disabled={!selectedFile}>
              <i className="bi bi-upload"></i>
              Загрузить
            </button>
            {uploadResult && (
              <div className="upload-result">
                <p>Всего строк: {uploadResult.total_processed}</p>
                <p>Создано матчей: {uploadResult.created_matches}</p>
                <p>Пропущено дубликатов: {uploadResult.skipped_duplicates}</p>
                {uploadResult.errors && uploadResult.errors.length > 0 && (
                  <div>
                    <p>Ошибки при загрузке:</p>
                    <ul>
                      {uploadResult.errors.map((err, idx) => (
                        <li key={idx}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <button className="analyze-btn" onClick={handleAnalyzeAfterUpload}>
                  <i className="bi bi-search"></i>
                  Анализировать
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="database-analysis-section">
          <div className="analysis-controls">
            <div className="control-group">
              <label>Период анализа:</label>
              <div className="date-range">
                <input
                  type="date"
                  value={periodStart}
                  onChange={(e) => setPeriodStart(e.target.value)}
                />
                <span>до</span>
                <input
                  type="date"
                  value={periodEnd}
                  onChange={(e) => setPeriodEnd(e.target.value)}
                />
              </div>
            </div>

            <div className="control-group">
              <label>Игроки (оставьте пустым для анализа всех):</label>
              <div className="players-selection">
                {players.slice(0, 10).map(player => (
                  <label key={player.id} className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedPlayers.includes(player.id)}
                      onChange={() => handlePlayerToggle(player.id)}
                    />
                    {player.full_name} {player.current_rating && `(${player.current_rating})`}
                  </label>
                ))}
                {players.length > 10 && (
                  <p className="players-note">Показаны первые 10 игроков. Всего в базе: {players.length}</p>
                )}
              </div>
            </div>

            <button 
              className="analyze-btn"
              onClick={analyzeDatabase}
              disabled={loading}
            >
              {loading ? (
                <>
                  <div className="spinner-small"></div>
                  Анализируем...
                </>
              ) : (
                <>
                  <i className="bi bi-search"></i>
                  Анализировать
                </>
              )}
            </button>
          </div>

          {analysisResult && (
            <div className="analysis-results">
              <div className="results-summary">
                <h3>Результаты анализа</h3>
                <div className="summary-stats">
                  <div className="stat-card">
                    <span className="stat-number">{analysisResult.total_players}</span>
                    <span className="stat-label">Игроков проанализировано</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-number">{analysisResult.total_matches}</span>
                    <span className="stat-label">Матчей за период</span>
                  </div>
                  <div className="stat-card">
                    <span className="stat-number">{analysisResult.triggers_found}</span>
                    <span className="stat-label">Триггеров найдено</span>
                  </div>
                </div>
                <p className="period-info">
                  Период: {formatDate(analysisResult.period_start)} - {formatDate(analysisResult.period_end)}
                </p>
              </div>

              {/* Фильтр и сортировка */}
              {analysisResult.triggers && analysisResult.triggers.length > 0 && (
                <div className="controls-section">
                  <div className="triggers-filter">
                    <label htmlFor="trigger-filter">Фильтр по типу подозрительной активности:</label>
                    <select 
                      id="trigger-filter"
                      value={triggerFilter} 
                      onChange={(e) => setTriggerFilter(e.target.value)}
                      className="filter-select"
                    >
                      <option value="">Все типы активности</option>
                      {triggerTypes.map(trigger => (
                        <option key={trigger.id} value={trigger.id}>
                          {trigger.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div className="sort-controls">
                    <label htmlFor="sort-select">Сортировать по:</label>
                    <div className="sort-group">
                      <select 
                        id="sort-select"
                        value={sortBy} 
                        onChange={(e) => setSortBy(e.target.value as 'name' | 'rating' | 'triggers' | 'severity')}
                        className="filter-select"
                      >
                        <option value="name">Имени игрока</option>
                        <option value="rating">Рейтингу</option>
                        <option value="triggers">Количеству триггеров</option>
                        <option value="severity">Уровню опасности</option>
                      </select>
                      <button 
                        onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                        className="sort-order-btn"
                        title={sortOrder === 'asc' ? 'По возрастанию' : 'По убыванию'}
                      >
                        {sortOrder === 'asc' ? '▲' : '▼'}
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {analysisResult.triggers && analysisResult.triggers.length > 0 && (
                <div className="triggers-section">
                  <h4>Подозрительные игроки</h4>
                  <div className="triggers-list">
                    {getSortedPlayers().map(([playerId, playerTriggers]) => {
                      const mainTrigger = getMainTrigger(playerTriggers);
                      const hasPositiveTriggers = playerTriggers.some(t => t.trigger_type === 'top_performers');
                      
                      return (
                        <div key={playerId} className={`trigger-card ${hasPositiveTriggers ? 'trigger-card-green' : 'trigger-card-red'}`}>
                          <div className="player-badge">
                            <span className="player-number">#{Math.floor(Math.random() * 99) + 1}</span>
                          </div>
                          
                          <div className="player-info-section">
                            <h3 className="player-name">{mainTrigger.player_name} рейтинг: {mainTrigger.player_rating || 'н/д'}</h3>
                            
                            <div className="stats-grid">
                              <div className="stat-item">
                                <span className="stat-label">Рейтинг:</span>
                                <span className="stat-value">{mainTrigger.player_rating || 1000}</span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">Побед:</span>
                                <span className="stat-value">
                                  {mainTrigger.player_stats ? 
                                    `${mainTrigger.player_stats.wins}/${mainTrigger.player_stats.matches_played} (${mainTrigger.player_stats.win_rate.toFixed(1)}%)` : 
                                    '40/40 (100%)'
                                  }
                                </span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">Сеты:</span>
                                <span className="stat-value">
                                  {mainTrigger.player_stats ? 
                                    `${mainTrigger.player_stats.sets_won}:${mainTrigger.player_stats.sets_lost}` : 
                                    '15:5'
                                  }
                                </span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">Форма:</span>
                                <div className="form-indicator">
                                  {mainTrigger.player_stats && mainTrigger.player_stats.recent_form ? 
                                    // Проверяем, массив это или строка и приводим к массиву
                                    (Array.isArray(mainTrigger.player_stats.recent_form) ? 
                                      mainTrigger.player_stats.recent_form : 
                                      mainTrigger.player_stats.recent_form.split('')
                                    ).slice(0, 5).map((result: string, index: number) => (
                                      <span key={index} className={result === 'W' ? 'form-win' : 'form-loss'}>
                                        {result}
                                      </span>
                                    )) :
                                    // Fallback для статических данных
                                    ['W', 'W', 'W', 'W', 'W'].map((result, index) => (
                                      <span key={index} className="form-win">{result}</span>
                                    ))
                                  }
                                </div>
                              </div>
                            </div>

                            {/* Теги всех триггеров игрока */}
                            <div className="player-triggers">
                              <h4>Триггеры игрока:</h4>
                              <div className="triggers-tags">
                                {playerTriggers.map((playerTrigger, index) => (
                                  <button
                                    key={index}
                                    className={`trigger-tag ${playerTrigger.trigger_type === 'top_performers' ? 'trigger-tag-positive' : 'trigger-tag-negative'}`}
                                    onClick={() => openTriggerModal(playerTrigger)}
                                    title={triggerTypes.find(t => t.id === playerTrigger.trigger_type)?.description}
                                  >
                                    {triggerTypes.find(t => t.id === playerTrigger.trigger_type)?.name || playerTrigger.trigger_type}
                                  </button>
                                ))}
                              </div>
                            </div>
                          </div>

                          <div className="analysis-text-section">
                            <div className="analysis-text">
                              <div className="detailed-analysis">
                                {/* Комплексный ИИ-анализ всех триггеров игрока */}
                                {mainTrigger.ai_analysis ? (
                                  <div className="ai-analysis">
                                    <p><strong>Анализ ИИ</strong></p>
                                    <p>{mainTrigger.ai_analysis}</p>
                                  </div>
                                ) : (
                                  <p>
                                    Анализ выявленных паттернов поможет определить уровень подозрительности игрока 
                                    и возможные признаки договорных матчей или намеренных проигрышей.
                                  </p>
                                )}
                              </div>

                              {mainTrigger.trigger_metadata && (
                                <div className="metadata-info">
                                  <small>Последний анализ: {formatDate(mainTrigger.created_at)}</small>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Секция анализа ИИ теперь интегрирована в каждую карточку триггера */}
            </div>
          )}
        </div>
      )}

      {/* Модальное окно для детального просмотра триггера */}
      {modalOpen && selectedTrigger && (
        <div className="modal-overlay" onClick={closeModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Детали триггера</h3>
              <button className="modal-close" onClick={closeModal}>×</button>
            </div>
            
            <div className="modal-body">
              <div className="modal-player-info">
                <h4>{selectedTrigger.player_name}</h4>
                <p>Рейтинг: {selectedTrigger.player_rating || 'н/д'}</p>
              </div>

              <div className="modal-trigger-info">
                <div className="trigger-severity">
                  <span className="severity-label">Уровень серьезности:</span>
                  <span 
                    className="severity-indicator"
                    style={{ backgroundColor: getSeverityColor(selectedTrigger.severity_level) }}
                  >
                    {getSeverityText(selectedTrigger.severity_level)}
                  </span>
                </div>

                <div className="trigger-description">
                  <p>{triggerTypes.find(t => t.id === selectedTrigger.trigger_type)?.description || selectedTrigger.trigger_value}</p>
                  <p>{selectedTrigger.trigger_value}</p>
                </div>

                {selectedTrigger.ai_analysis && (
                  <div className="modal-ai-analysis">
                    <h5>Анализ ИИ:</h5>
                    <p>{selectedTrigger.ai_analysis}</p>
                  </div>
                )}

                <div className="trigger-period">
                  <p><strong>Период:</strong> {formatDate(selectedTrigger.period_start)} - {formatDate(selectedTrigger.period_end)}</p>
                  <p><strong>Создано:</strong> {formatDate(selectedTrigger.created_at)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
