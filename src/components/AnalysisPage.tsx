import React, { useState, useEffect } from 'react';
import './AnalysisPage.css';

// === ТИПЫ ДАННЫХ ===
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
  ai_analysis?: string;
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

interface UploadResult {
  created_matches?: number;
  skipped_duplicates?: number;
  total_processed?: number;
  created_players?: number;
  file_player_ids?: string[];
  errors?: string[];
}

// === ОСНОВНОЙ КОМПОНЕНТ ===
const AnalysisPage: React.FC = () => {
  // === СОСТОЯНИЯ ===
  const [analysisMode, setAnalysisMode] = useState<'upload' | 'database'>('upload');
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [selectedTrigger, setSelectedTrigger] = useState<Trigger | null>(null);
  const [singleTriggerAnalysis, setSingleTriggerAnalysis] = useState<string>('');
  const [singleTriggerLoading, setSingleTriggerLoading] = useState<boolean>(false);
  const SINGLE_TRIGGER_WORD_LIMIT = 60;
  
  // Состояния для фильтрации и анализа базы данных
  const [periodStart, setPeriodStart] = useState<string>('');
  const [periodEnd, setPeriodEnd] = useState<string>('');
  const [triggerFilter, setTriggerFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<'name' | 'rating' | 'triggers' | 'severity'>('name');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [aiProvider, setAiProvider] = useState<'ollama' | 'lmstudio'>('lmstudio'); // AI провайдер (по умолчанию LM Studio)
  
  // Состояния для панели настроек
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [matchesLimit, setMatchesLimit] = useState<number>(10); // Лимит матчей для анализа

  // === КОНСТАНТЫ ===
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

  // === ИНИЦИАЛИЗАЦИЯ ===
  useEffect(() => {
    initializePeriod();
    // Загружаем сохранённые настройки из localStorage
    const savedProvider = localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio';
    const savedMatchesLimit = localStorage.getItem('matchesLimit');
    
    if (savedProvider) {
      setAiProvider(savedProvider);
    }
    if (savedMatchesLimit) {
      setMatchesLimit(parseInt(savedMatchesLimit));
    }
  }, []);

  // === ОСНОВНЫЕ ФУНКЦИИ ===
  const initializePeriod = () => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(startDate.getMonth() - 3);
    
    setPeriodEnd(endDate.toISOString().split('T')[0]);
    setPeriodStart(startDate.toISOString().split('T')[0]);
  };
  
  // Сохранение настроек
  const saveSettings = () => {
    localStorage.setItem('aiProvider', aiProvider);
    localStorage.setItem('matchesLimit', matchesLimit.toString());
    setSettingsOpen(false);
    alert('✅ Настройки сохранены!');
  };

  // Загрузка Excel файла
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedFile(e.target.files?.[0] || null);
  };
  
  const uploadExcel = async () => {
    if (!selectedFile) {
      alert('Пожалуйста, выберите файл');
      return;
    }
    
    setLoading(true);
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
      console.log('📁 Результат загрузки файла:', result);
      console.log('🎯 Игроков в файле:', result.file_player_ids?.length || 0);
    } catch (error) {
  console.error('Error uploading Excel!!:', error);
  alert('Ошибка при загрузке файла: ' + (error as Error).message);
}
 finally {
      setLoading(false);
    }
  };

  // Анализ базы данных - ОСНОВНАЯ ФУНКЦИЯ
  const analyzeDatabase = async () => {
    if (!periodStart || !periodEnd) {
      alert('Пожалуйста, выберите период анализа');
      return;
    }

    // Собираем player_ids из результата загрузки если есть
    const playerIds = uploadResult?.file_player_ids && uploadResult.file_player_ids.length > 0
      ? uploadResult.file_player_ids
      : undefined;

    setLoading(true);
    try {
      const requestBody = {
        period_start: periodStart,
        period_end: periodEnd,
        analyze_recent_upload_only: !playerIds, // если явно не передали список
        player_ids: playerIds,
        ai_provider: aiProvider  // Добавляем выбранный провайдер
      };

      console.log('🚀 Отправка запроса на анализ:', {
        ...requestBody,
        ai_provider: aiProvider
      });

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
        console.log('🎯 Результат анализа:', result);
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

  // После загрузки Excel, переходим к анализу
  const handleAnalyzeAfterUpload = async () => {
    setAnalysisMode('database');
    await analyzeDatabase();
  };

  // === ФУНКЦИИ ДЛЯ РАБОТЫ С ТРИГГЕРАМИ ===
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

  // Функции для модального окна
  const openTriggerModal = (trigger: Trigger) => {
    setSelectedTrigger(trigger);
    setModalOpen(true);
  // Инициируем загрузку ИИ-анализа только для этого триггера (сжатый)
  fetchSingleTriggerAnalysis(trigger.id);
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedTrigger(null);
    setSingleTriggerAnalysis('');
  };

  const fetchSingleTriggerAnalysis = async (triggerId: string) => {
    try {
      setSingleTriggerLoading(true);
      setSingleTriggerAnalysis('');
      const response = await fetch(`http://localhost:8000/api/v1/match-analysis/triggers/${triggerId}/ai-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ word_limit: SINGLE_TRIGGER_WORD_LIMIT })
      });
      if (response.ok) {
        const data = await response.json();
        setSingleTriggerAnalysis(data.ai_analysis);
      } else {
        const err = await response.json();
        setSingleTriggerAnalysis(`Ошибка анализа: ${err.detail || 'неизвестно'}`);
      }
    } catch (e) {
      setSingleTriggerAnalysis('Ошибка сети при запросе анализа');
    } finally {
      setSingleTriggerLoading(false);
    }
  };

  return (
    <div className="analysis-page">
      <div className="analysis-header">
        <h1>Игроков анализ</h1>
        <div className="header-controls">
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
          <button 
            className="settings-btn"
            onClick={() => setSettingsOpen(true)}
            title="Настройки анализа"
          >
            <i className="bi bi-gear-fill"></i>
          </button>
        </div>
      </div>

      {analysisMode === 'upload' ? (
        <div className="upload-section">
          <div className="upload-card">
            <i className="bi bi-file-earmark-excel"></i>
            <h3>Загрузить Excel файл</h3>
            <p>Загрузите файл с матчами для анализа триггеров</p>
            <div className="format-guide">
              <h4>📋 Формат файла:</h4>
              <p><strong>Обязательные столбцы:</strong> Дата, Игрок 1, Счёт, Игрок 2</p>
              <p><strong>Для корректных рейтингов добавьте:</strong> Рейтинг игрок 1, Рейтинг игрок 2</p>
              <p><strong>Дополнительно:</strong> Время, Стадия, Турнир</p>
              <details>
                <summary>Подробная инструкция</summary>
                <div className="detailed-format">
                  <p>Пример заполнения:</p>
                  <table className="format-table">
                    <thead>
                      <tr>
                        <th>Дата</th>
                        <th>Игрок 1</th>
                        <th>Счёт</th>
                        <th>Игрок 2</th>
                        <th>Рейтинг игрок 1</th>
                        <th>Рейтинг игрок 2</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>2024-01-15</td>
                        <td>Иванов Иван</td>
                        <td>3:1</td>
                        <td>Петров Петр</td>
                        <td>1250</td>
                        <td>1180</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </details>
            </div>
            <input type="file" accept=".xlsx,.xls" onChange={handleFileChange} />
            <button className="upload-btn" onClick={uploadExcel} disabled={!selectedFile || loading}>
              <i className="bi bi-upload"></i>
              {loading ? 'Загружаем...' : 'Загрузить'}
            </button>
            {uploadResult && (
              <div className="upload-result">
                <h4>📊 Результат загрузки:</h4>
                <p>Всего строк: {uploadResult.total_processed}</p>
                <p>Создано матчей: {uploadResult.created_matches}</p>
                <p>Создано новых игроков: {uploadResult.created_players}</p>
                <p>Пропущено дубликатов: {uploadResult.skipped_duplicates}</p>
                {uploadResult.file_player_ids && (
                  <p>🎯 Игроков в файле для анализа: <strong>{uploadResult.file_player_ids.length}</strong></p>
                )}
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
                  Анализировать загруженных игроков
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
              <label>Анализ игроков:</label>
              <p className="analysis-note">
                ✅ Будут проанализированы <strong>ТОЛЬКО игроки из загруженного Excel файла</strong> за указанный период.
                <br />
                Игроки из базы данных, которых нет в файле, анализироваться не будут.
              </p>
            </div>

            <div className="control-group">
              <label>AI провайдер:</label>
              <div className="provider-selector">
                <button
                  className={`provider-btn ${aiProvider === 'ollama' ? 'active' : ''}`}
                  onClick={() => setAiProvider('ollama')}
                  type="button"
                >
                  🟢 Ollama
                </button>
                <button
                  className={`provider-btn ${aiProvider === 'lmstudio' ? 'active' : ''}`}
                  onClick={() => setAiProvider('lmstudio')}
                  type="button"
                >
                  🔷 LM Studio
                </button>
              </div>
              <p className="provider-note">
                Выбранный провайдер: <strong>{aiProvider === 'ollama' ? 'Ollama' : 'LM Studio'}</strong>
              </p>
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
                            <h3 className="player-name">{mainTrigger.player_name}</h3>
                            
                            <div className="stats-grid">
                              <div className="stat-item">
                                <span className="stat-label">Рейтинг:</span>
                                <span className="stat-value">{mainTrigger.player_rating || 'н/д'}</span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">Побед:</span>
                                <span className="stat-value">
                                  {mainTrigger.player_stats ? 
                                    `${mainTrigger.player_stats.wins}/${mainTrigger.player_stats.matches_played} (${mainTrigger.player_stats.win_rate.toFixed(1)}%)` : 
                                    'н/д'
                                  }
                                </span>
                              </div>
                              <div className="stat-item">
                                <span className="stat-label">Сеты:</span>
                                <span className="stat-value">
                                  {mainTrigger.player_stats ? 
                                    `${mainTrigger.player_stats.sets_won}:${mainTrigger.player_stats.sets_lost}` : 
                                    'н/д'
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
                                    // Заглушка если нет данных
                                    <span className="no-data">н/д</span>
                                  }
                                </div>
                              </div>
                            </div>

                            {/* Анализ конкретного триггера игрока */}
                            <div className="player-triggers">
                              <h4>Найденные проблемы:</h4>
                              <div className="triggers-tags">
                                {playerTriggers.map((playerTrigger, index) => {
                                  const triggerInfo = triggerTypes.find(t => t.id === playerTrigger.trigger_type);
                                  return (
                                    <button
                                      key={index}
                                      className={`trigger-tag ${playerTrigger.trigger_type === 'top_performers' ? 'trigger-tag-positive' : 'trigger-tag-negative'}`}
                                      onClick={() => openTriggerModal(playerTrigger)}
                                      title={triggerInfo?.description}
                                    >
                                      {triggerInfo?.name || playerTrigger.trigger_type}
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                          </div>

                          <div className="analysis-text-section">
                            <div className="analysis-text">
                              {/* Анализ основного триггера */}
                              <div className="main-trigger-analysis">
                                <h5>Основная проблема: {triggerTypes.find(t => t.id === mainTrigger.trigger_type)?.name}</h5>
                                <p className="trigger-description">
                                  {mainTrigger.trigger_value}
                                </p>
                                {mainTrigger.ai_analysis && (
                                  <div className="ai-analysis">
                                    <p><strong>Анализ ИИ:</strong></p>
                                    <p>{mainTrigger.ai_analysis}</p>
                                  </div>
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
                <div className="modal-ai-analysis">
                  <h5>Краткий анализ этого триггера:</h5>
                  {singleTriggerLoading ? (
                    <p>Генерируем краткий анализ...</p>
                  ) : (
                    <p>{singleTriggerAnalysis || 'Нет данных'}</p>
                  )}
                  <small>Лимит слов: {SINGLE_TRIGGER_WORD_LIMIT}</small>
                </div>

                <div className="trigger-period">
                  <p><strong>Период:</strong> {formatDate(selectedTrigger.period_start)} - {formatDate(selectedTrigger.period_end)}</p>
                  <p><strong>Создано:</strong> {formatDate(selectedTrigger.created_at)}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Модальное окно настроек */}
      {settingsOpen && (
        <div className="modal-overlay" onClick={() => setSettingsOpen(false)}>
          <div className="modal-content settings-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3><i className="bi bi-gear-fill"></i> Настройки анализа</h3>
              <button className="modal-close" onClick={() => setSettingsOpen(false)}>×</button>
            </div>
            
            <div className="modal-body settings-body">
              {/* AI Провайдер */}
              <div className="setting-group">
                <label className="setting-label">
                  <i className="bi bi-robot"></i> AI Провайдер
                </label>
                <div className="provider-selector">
                  <button
                    className={`provider-btn ${aiProvider === 'lmstudio' ? 'active' : ''}`}
                    onClick={() => setAiProvider('lmstudio')}
                  >
                    <i className="bi bi-server"></i>
                    <span>LM Studio</span>
                    {aiProvider === 'lmstudio' && <i className="bi bi-check-circle-fill"></i>}
                  </button>
                  <button
                    className={`provider-btn ${aiProvider === 'ollama' ? 'active' : ''}`}
                    onClick={() => setAiProvider('ollama')}
                  >
                    <i className="bi bi-terminal"></i>
                    <span>Ollama</span>
                    {aiProvider === 'ollama' && <i className="bi bi-check-circle-fill"></i>}
                  </button>
                </div>
                <p className="setting-hint">
                  {aiProvider === 'lmstudio' 
                    ? '🔷 Использует LM Studio (localhost:1234)' 
                    : '🟢 Использует Ollama (localhost:11434)'}
                </p>
              </div>

              {/* Лимит матчей */}
              <div className="setting-group">
                <label className="setting-label">
                  <i className="bi bi-list-ol"></i> Количество матчей для анализа
                </label>
                <div className="matches-limit-control">
                  <input
                    type="range"
                    min="5"
                    max="50"
                    step="5"
                    value={matchesLimit}
                    onChange={(e) => setMatchesLimit(parseInt(e.target.value))}
                    className="matches-slider"
                  />
                  <div className="matches-value">
                    <input
                      type="number"
                      min="5"
                      max="50"
                      value={matchesLimit}
                      onChange={(e) => setMatchesLimit(Math.min(50, Math.max(5, parseInt(e.target.value) || 5)))}
                      className="matches-input"
                    />
                    <span>матчей</span>
                  </div>
                </div>
                <p className="setting-hint">
                  📊 AI будет анализировать последние {matchesLimit} матчей каждого игрока
                </p>
              </div>

              {/* Информация */}
              <div className="setting-info">
                <i className="bi bi-info-circle"></i>
                <p>
                  Настройки сохраняются автоматически и будут использоваться для всех последующих анализов.
                  Рекомендуется использовать LM Studio с 10-20 матчами для оптимального результата.
                </p>
              </div>
            </div>

            <div className="modal-footer">
              <button className="btn-cancel" onClick={() => setSettingsOpen(false)}>
                Отмена
              </button>
              <button className="btn-save" onClick={saveSettings}>
                <i className="bi bi-check-lg"></i> Сохранить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
