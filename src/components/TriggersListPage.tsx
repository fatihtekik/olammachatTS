import React, { useState, useEffect } from 'react';
import './TriggersListPage.css';

// Утилита для разделения think-блоков от основного ответа AI
const parseAIResponse = (text: string): { thinking: string | null; response: string } => {
  if (!text) return { thinking: null, response: '' };
  
  // Ищем <think>...</think> блоки (DeepSeek, и другие reasoning модели)
  const thinkMatch = text.match(/<think>([\s\S]*?)<\/think>/i);
  
  if (thinkMatch) {
    const thinking = thinkMatch[1].trim();
    const response = text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
    return { thinking, response };
  }
  
  return { thinking: null, response: text };
};

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
  // is_active: boolean;
  is_pair: boolean;
  trigger_metadata?: any;
  created_at: string;
  ai_analysis?: string;
  player_stats?: {
    matches_played: number;
    wins: number;
    losses: number;
    win_rate: number;
    recent_form: string;
    suspicion_score?: number;
    collapse_rate?: number;
    serve_efficiency_variance?: number;
  };
  evidence?: Array<{
    date: string;
    time?: string;
    opponent: string;
    opponent_rating?: number;
    score: string;
    sets?: Array<{
      set_number: number;
      player_points: number;
      opponent_points: number;
      won: boolean;
    }>;
    highlight: string;
    serve_efficiency?: number;
    receive_efficiency?: number;
    was_favorite: boolean;
    rating_diff: number;
    red_flags: string[];
  }>;
}

interface Player {
  id: string;
  full_name: string;
  current_rating: number;
}

const TriggersListPage: React.FC = () => {
  const [triggers, setTriggers] = useState<Trigger[]>([]);
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedEvidence, setExpandedEvidence] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState({
    player_id: '',
    trigger_type: '',
    severity_level: '',
    active_only: true
  });

  const triggerTypeLabels: { [key: string]: string } = {
    'top_performers': 'Топ игроки по результативности',
    'losers_50_percent': 'Игроки с >50% поражений',
    'defeat_0_3': 'Частые поражения 0:3',
    'won_2_lost_3rd_set': 'Проигрыш после лидерства 2:0 по сетам',
    'early_final_exit_advanced': 'Досрочный уход с корта в финалах',
    'led_1_set_lost_match': 'Проигрыш после лидерства в счёте',
    'led_2_sets_lost_match': 'Критический проигрыш после лидерства 2:0',
    'psychological_breakdown': 'Психологические срывы',
    'comeback_inability': 'Неспособность к камбекам',
    'pressure_situations': 'Проблемы в важных матчах',
    'endgame_problems': 'Проблемы в концовках',
    'lead_4_lost': 'Вел 4+ и проиграл',
    'balance_problems': 'Проблемы в балансах',
    'led_2_sets_lost': 'Вел 2 сета но проиграл',
    'led_1_set_lost': 'Вел 1 сет и проиграл',
    'early_final_exit': 'Досрочный выход из финала',
    'league_promotion_failed': 'Не прошел в следующую лигу',
    'won_2_lost_3rd': 'Выиграл 2 сета но проиграл 3й',
    'close_score_losses': 'Поражения при равном счете',
    'post_holiday_problems': 'Проблемы после праздников',
    'time_performance': 'Слабая форма в ночное время',
    'shutout_losses': 'Поражения 0:3',
    'losing_streaks': 'Проигрыши в ряд',
    'weaker_opponent_losses': 'Поражения от слабых соперников',
    'long_match_losses': 'Поражения в долгих матчах',
    'higher_league_struggles': 'Проблемы в высшей лиге',
    'reception_problems': 'Проблемы с приемом'
  };

  const triggerTypes = Object.keys(triggerTypeLabels);

  useEffect(() => {
    fetchData();
    
    // Добавляем автообновление каждые 30 секунд для получения новых триггеров
    const interval = setInterval(() => {
      fetchTriggers();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchTriggers();
  }, [filters]);

  const fetchData = async () => {
    try {
      await Promise.all([fetchPlayers(), fetchTriggers()]);
    } catch (err) {
      setError('Ошибка при загрузке данных');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlayers = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/players');
      if (!response.ok) throw new Error('Failed to fetch players');
      const data = await response.json();
      setPlayers(data);
    } catch (err) {
      console.error('Error fetching players:', err);
    }
  };

  const fetchTriggers = async () => {
    try {
      const params = new URLSearchParams();
      
      // Используем расширенный эндпоинт с ИИ-анализом
      if (filters.player_id) params.append('player_id', filters.player_id);
      if (filters.trigger_type) params.append('trigger_type', filters.trigger_type);
      if (filters.severity_level) params.append('severity_level', filters.severity_level);
      params.append('limit', '200');
      
      // Используем широкий диапазон дат для поиска всех возможных триггеров
      params.append('start_date', '2024-01-01');
      params.append('end_date', '2025-12-31');
      params.append('enable_ai_analysis', 'false'); // Отключаем ИИ для быстрой загрузки

      console.log('🔍 Запрос триггеров с параметрами:', params.toString());

      const response = await fetch(`http://localhost:8000/api/v1/match-analysis/triggers-enhanced?${params}`);
      if (!response.ok) {
        console.log('❌ Расширенный эндпоинт не работает, пробуем обычный');
        // Если расширенный эндпоинт не работает, используем обычный
        const fallbackParams = new URLSearchParams();
        if (filters.player_id) fallbackParams.append('player_id', filters.player_id);
        if (filters.trigger_type) fallbackParams.append('trigger_type', filters.trigger_type);
        if (filters.severity_level) fallbackParams.append('severity_level', filters.severity_level);
        fallbackParams.append('limit', '200');
        
        const fallbackResponse = await fetch(`http://localhost:8000/api/v1/match-analysis/triggers?${fallbackParams}`);
        if (!fallbackResponse.ok) throw new Error('Failed to fetch triggers');
        
        const fallbackData = await fallbackResponse.json();
        console.log('📄 Ответ от обычного эндпоинта:', fallbackData);
        // Если это объект с полем triggers, извлекаем массив
        const triggersArray = Array.isArray(fallbackData) ? fallbackData : fallbackData.triggers || [];
        setTriggers(triggersArray);
        return;
      }
      
      const data = await response.json();
      console.log('📄 Ответ от расширенного эндпоинта:', data);
      setTriggers(data);
    } catch (err) {
      setError('Ошибка при загрузке триггеров');
      console.error('Error fetching triggers:', err);
    }
  };

  const fetchTriggersWithAI = async () => {
    try {
      setLoading(true);
      setAiLoading(true);
      const params = new URLSearchParams();
      
      if (filters.player_id) params.append('player_id', filters.player_id);
      if (filters.trigger_type) params.append('trigger_type', filters.trigger_type);
      if (filters.severity_level) params.append('severity_level', filters.severity_level);
      params.append('limit', '50'); // Уменьшаем лимит для ИИ-анализа
      
      params.append('start_date', '2024-01-01');
      params.append('end_date', '2025-12-31');
      params.append('enable_ai_analysis', 'true'); // Включаем ИИ-анализ

      console.log('🤖 Запрос триггеров с ИИ-анализом:', params.toString());

      const response = await fetch(`http://localhost:8000/api/v1/match-analysis/triggers-enhanced?${params}`);
      if (!response.ok) throw new Error('Failed to fetch triggers with AI');
      
      const data = await response.json();
      console.log('📄 Ответ с ИИ-анализом:', data);
      setTriggers(data);
    } catch (err) {
      setError('Ошибка при загрузке триггеров с ИИ-анализом');
      console.error('Error fetching triggers with AI:', err);
    } finally {
      setLoading(false);
      setAiLoading(false);
    }
  };

  const getSeverityColor = (level: number): string => {
    switch (level) {
      case 3: return '#dc3545'; // красный
      case 2: return '#fd7e14'; // оранжевый
      case 1: return '#ffc107'; // желтый
      default: return '#6c757d'; // серый
    }
  };

  const getSeverityLabel = (level: number): string => {
    switch (level) {
      case 3: return 'Критический';
      case 2: return 'Высокий';
      case 1: return 'Средний';
      default: return 'Низкий';
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('ru-RU');
  };

  const getPlayerNameById = (playerId: string): string => {
    const player = players.find(p => p.id === playerId);
    return player?.full_name || 'Неизвестный игрок';
  };

  const getSuspicionLevel = (score: number): string => {
    if (score >= 0.7) return 'КРИТИЧЕСКИЙ';
    if (score >= 0.5) return 'ВЫСОКИЙ';
    if (score >= 0.3) return 'СРЕДНИЙ';
    return 'НИЗКИЙ';
  };

  const getSuspicionClass = (score: number): string => {
    if (score >= 0.7) return 'critical';
    if (score >= 0.5) return 'high';
    if (score >= 0.3) return 'medium';
    return 'low';
  };

  const getSuspicionIcon = (score: number): string => {
    if (score >= 0.7) return '🔴';
    if (score >= 0.5) return '🟠';
    if (score >= 0.3) return '🟡';
    return '🟢';
  };

  const renderAIAnalysis = (analysisText: string) => {
    // Отделяем think-блоки от основного ответа
    const { thinking, response } = parseAIResponse(analysisText);
    const cleanText = response || analysisText;
    
    // Парсим анализ и извлекаем структуру
    const riskMatch = cleanText.match(/🚨\s*УРОВЕНЬ РИСКА:\s*\[?([А-ЯЁ]+)\]?/i);
    const anomaliesMatch = cleanText.match(/📊\s*КЛЮЧЕВЫЕ АНОМАЛИИ:\s*([\s\S]+?)(?=🎯|✅|$)/);
    const schemeMatch = cleanText.match(/🎯\s*ВЕРОЯТНАЯ СХЕМА:\s*([\s\S]+?)(?=✅|$)/);
    const recommendationsMatch = cleanText.match(/✅\s*РЕКОМЕНДАЦИИ:\s*([\s\S]+?)$/);

    const riskLevel = riskMatch ? riskMatch[1].trim() : 'НЕИЗВЕСТНО';
    const anomalies = anomaliesMatch ? anomaliesMatch[1].trim() : '';
    const scheme = schemeMatch ? schemeMatch[1].trim() : '';
    const recommendations = recommendationsMatch ? recommendationsMatch[1].trim() : '';

    // Определяем цвет по уровню риска
    const getRiskColor = (level: string) => {
      switch(level.toUpperCase()) {
        case 'КРИТИЧЕСКИЙ': return '#dc3545';
        case 'ВЫСОКИЙ': return '#fd7e14';
        case 'СРЕДНИЙ': return '#ffc107';
        case 'НИЗКИЙ': return '#28a745';
        default: return '#6c757d';
      }
    };

    const getRiskIcon = (level: string) => {
      switch(level.toUpperCase()) {
        case 'КРИТИЧЕСКИЙ': return '🚨';
        case 'ВЫСОКИЙ': return '⚠️';
        case 'СРЕДНИЙ': return '⚡';
        case 'НИЗКИЙ': return '✅';
        default: return '❓';
      }
    };

    return (
      <div className="ai-analysis-parsed">
        <div className="risk-level-badge" style={{ backgroundColor: getRiskColor(riskLevel) }}>
          <span className="risk-icon">{getRiskIcon(riskLevel)}</span>
          <span className="risk-text">УРОВЕНЬ РИСКА: {riskLevel}</span>
        </div>

        {anomalies && (
          <div className="analysis-section">
            <div className="section-header">📊 Ключевые аномалии</div>
            <div className="section-content">{anomalies}</div>
          </div>
        )}

        {scheme && (
          <div className="analysis-section">
            <div className="section-header">🎯 Вероятная схема</div>
            <div className="section-content">{scheme}</div>
          </div>
        )}

        {recommendations && (
          <div className="analysis-section">
            <div className="section-header">✅ Рекомендации</div>
            <div className="section-content">{recommendations}</div>
          </div>
        )}

        {!riskMatch && (
          <div className="analysis-fallback">
            <p>{analysisText}</p>
          </div>
        )}
      </div>
    );
  };

  const toggleEvidence = (triggerId: string) => {
    setExpandedEvidence(prev => {
      const newSet = new Set(prev);
      if (newSet.has(triggerId)) {
        newSet.delete(triggerId);
      } else {
        newSet.add(triggerId);
      }
      return newSet;
    });
  };

  const getEfficiencyClass = (value?: number): string => {
    if (!value) return 'medium';
    if (value < 40) return 'low';
    if (value < 60) return 'medium';
    return 'high';
  };

  // Краткая строка со счётом всех сетов: "5:11 · 7:11 · 9:11"
  const formatSetsSummary = (sets?: Array<{ set_number: number; player_points: number; opponent_points: number; won: boolean; }>): string => {
    if (!sets || sets.length === 0) return '';
    return sets
      .sort((a, b) => a.set_number - b.set_number)
      .map(s => `${s.player_points}:${s.opponent_points}`)
      .join(' · ');
  };

  const renderEvidence = (trigger: Trigger) => {
    if (!trigger.evidence || trigger.evidence.length === 0) {
      return null;
    }

    const isExpanded = expandedEvidence.has(trigger.id);

    return (
      <div className="evidence-section">
        <div className="evidence-header" onClick={() => toggleEvidence(trigger.id)}>
          <div className="evidence-title">
            Доказательства из матчей
            <span className="evidence-count">{trigger.evidence.length} матчей</span>
          </div>
          <span className={`evidence-toggle ${isExpanded ? 'expanded' : ''}`}>▼</span>
        </div>

        {isExpanded && (
          <div className="evidence-list">
            {trigger.evidence.map((evidence, index) => (
              <div key={index} className="evidence-item">
                <div className="evidence-item-header">
                  <div className="evidence-match-info">
                    <div className="evidence-date-time">
                      {new Date(evidence.date).toLocaleDateString('ru-RU')}
                      {evidence.time && ` | ${evidence.time}`}
                    </div>
                    <div className="evidence-opponent">
                      {evidence.opponent}
                      {evidence.opponent_rating && (
                        <span className={`evidence-rating-diff ${evidence.was_favorite ? 'favorite' : 'underdog'}`}>
                          {evidence.was_favorite ? 'Фаворит' : 'Аутсайдер'} (±{Math.abs(evidence.rating_diff)})
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="evidence-score">{evidence.score}</div>
                </div>

                {/* Всегда показываем компактную строку сетов вместо текста названия триггера */}
                {/* ТОЛЬКО если нет детальных сетов - показываем highlight */}
                {!(evidence.sets && evidence.sets.length > 0) && (
                  <div className="evidence-highlight">
                    {evidence.highlight}
                  </div>
                )}

                {/* Детализированные сеты (горизонтально) */}
                {evidence.sets && evidence.sets.length > 0 && (
                  <div className="evidence-sets">
                    {evidence.sets.map((set, setIdx) => (
                      <div
                        key={setIdx}
                        className={`set-score ${set.won ? 'set-won' : 'set-lost'}`}
                      >
                        <span className="set-number">Сет {set.set_number}</span>
                        <span className="set-points">{set.player_points}:{set.opponent_points}</span>
                      </div>
                    ))}
                  </div>
                )}

                {(evidence.serve_efficiency !== undefined || evidence.receive_efficiency !== undefined) && (
                  <div className="evidence-stats">
                    {evidence.serve_efficiency !== undefined && (
                      <div className="evidence-stat">
                        <div className="evidence-stat-label">Подача</div>
                        <div className={`evidence-stat-value ${getEfficiencyClass(evidence.serve_efficiency)}`}>
                          {evidence.serve_efficiency.toFixed(1)}%
                        </div>
                      </div>
                    )}
                    {evidence.receive_efficiency !== undefined && (
                      <div className="evidence-stat">
                        <div className="evidence-stat-label">Прием</div>
                        <div className={`evidence-stat-value ${getEfficiencyClass(evidence.receive_efficiency)}`}>
                          {evidence.receive_efficiency.toFixed(1)}%
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {evidence.red_flags && evidence.red_flags.length > 0 && (
                  <div className="evidence-red-flags">
                    {evidence.red_flags.map((flag, idx) => (
                      <span key={idx} className="red-flag-badge">{flag}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="triggers-list-page">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Загрузка триггеров...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="triggers-list-page">
        <div className="error-container">
          <p>❌ {error}</p>
          <button onClick={() => window.location.reload()} className="retry-button">
            Попробовать снова
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="triggers-list-page">
      <div className="page-header">
        <h1>
          <i className="bi bi-exclamation-triangle"></i>
          Список триггеров
        </h1>
        <p>Все обнаруженные проблемы и достижения игроков</p>
        <button 
          className="refresh-button"
          onClick={fetchTriggers}
          disabled={loading}
        >
          <i className="bi bi-arrow-clockwise"></i>
          Обновить
        </button>
        
        <button 
          className="ai-analysis-button"
          onClick={() => fetchTriggersWithAI()}
          disabled={loading}
          title="Загрузить триггеры с ИИ-анализом (медленно)"
        >
          <i className="bi bi-robot"></i>
          ИИ-анализ
        </button>
      </div>

      {/* Фильтры */}
      <div className="filters-section">
        <div className="filters-grid">
          <div className="filter-group">
            <label>Игрок:</label>
            <select
              value={filters.player_id}
              onChange={(e) => setFilters({ ...filters, player_id: e.target.value })}
            >
              <option value="">Все игроки</option>
              {players.map(player => (
                <option key={player.id} value={player.id}>
                  {player.full_name} ({player.current_rating})
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Тип триггера:</label>
            <select
              value={filters.trigger_type}
              onChange={(e) => setFilters({ ...filters, trigger_type: e.target.value })}
            >
              <option value="">Все типы</option>
              {triggerTypes.map(type => (
                <option key={type} value={type}>
                  {triggerTypeLabels[type]}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label>Уровень серьезности:</label>
            <select
              value={filters.severity_level}
              onChange={(e) => setFilters({ ...filters, severity_level: e.target.value })}
            >
              <option value="">Все уровни</option>
              <option value="3">Критический</option>
              <option value="2">Высокий</option>
              <option value="1">Средний</option>
            </select>
          </div>
        </div>
      </div>

      {/* Статистика */}
      <div className="stats-section">
        <div className="stats-grid">
          <div className="stat-card">
            <h3>{triggers.length}</h3>
            <p>Всего триггеров</p>
          </div>
          <div className="stat-card critical">
            <h3>{triggers.filter(t => t.severity_level === 3).length}</h3>
            <p>Критические</p>
          </div>
          <div className="stat-card warning">
            <h3>{triggers.filter(t => t.severity_level === 2).length}</h3>
            <p>Высокие</p>
          </div>
          <div className="stat-card info">
            <h3>{triggers.filter(t => t.severity_level === 1).length}</h3>
            <p>Средние</p>
          </div>
        </div>
      </div>

      {/* Список триггеров */}
      <div className="triggers-section">
        {triggers.length === 0 ? (
          <div className="no-triggers">
            <p>Триггеры не найдены</p>
            <small>Попробуйте изменить фильтры или провести анализ матчей</small>
          </div>
        ) : (
          <div className="triggers-grid">
            {triggers.map(trigger => (
              <div key={trigger.id} className={`trigger-card severity-${trigger.severity_level}`}>
                <div className="trigger-header">
                  <div className="trigger-title">
                    <h4>{triggerTypeLabels[trigger.trigger_type] || trigger.trigger_type}</h4>
                    <span 
                      className="severity-badge"
                      style={{ backgroundColor: getSeverityColor(trigger.severity_level) }}
                    >
                      {getSeverityLabel(trigger.severity_level)}
                    </span>
                  </div>
                  <div className="trigger-meta">
                    <span className="player-name">{trigger.player_name}</span>
                    {trigger.player_rating && (
                      <span className="player-rating">Рейтинг: {trigger.player_rating}</span>
                    )}
                  </div>
                </div>

                <div className="trigger-content">
                  {/* Возвращаем техническое описание триггера */}
                  <p className="trigger-description">{trigger.trigger_value}</p>
                  
                  {trigger.trigger_subtype && (
                    <p className="trigger-subtype">
                      <strong>Подтип:</strong> {trigger.trigger_subtype}
                    </p>
                  )}

                  <div className="trigger-period">
                    <small>
                      Период: {formatDate(trigger.period_start)} — {formatDate(trigger.period_end)}
                    </small>
                  </div>

                  {trigger.player_stats && (
                    <div className="player-stats">
                      <h5>Статистика игрока:</h5>
                      <div className="stats-row">
                        <span>Матчей: {trigger.player_stats.matches_played}</span>
                        <span>Побед: {trigger.player_stats.wins}</span>
                        <span>Процент побед: {trigger.player_stats.win_rate.toFixed(1)}%</span>
                      </div>
                      {trigger.player_stats.recent_form && (
                        <div className="recent-form">
                          <span>Последние матчи: {trigger.player_stats.recent_form}</span>
                        </div>
                      )}
                      
                      {trigger.player_stats.suspicion_score !== undefined && (
                        <div className="suspicion-score-block">
                          <h5>📊 Автоматический скоринг подозрительности:</h5>
                          <div className={`suspicion-badge ${getSuspicionClass(trigger.player_stats.suspicion_score)}`}>
                            {getSuspicionIcon(trigger.player_stats.suspicion_score)} {(trigger.player_stats.suspicion_score * 100).toFixed(0)}% ({getSuspicionLevel(trigger.player_stats.suspicion_score)})
                          </div>
                          <div className="suspicion-details">
                            {trigger.player_stats.collapse_rate !== undefined && (
                              <span>• Коллапсы после 2:0: {trigger.player_stats.collapse_rate.toFixed(0)}%</span>
                            )}
                            {trigger.player_stats.serve_efficiency_variance !== undefined && (
                              <span>• Волатильность подачи: ±{(trigger.player_stats.serve_efficiency_variance * 100).toFixed(0)}%</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {aiLoading && (
                    <div className="ai-thinking">
                      🤖 ИИ анализирует данные
                      <div className="thinking-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  )}

                  {!aiLoading && trigger.ai_analysis && (
                    <div className="ai-analysis-block">
                      <div className="ai-analysis-header">
                        <div className="ai-icon">🤖</div>
                        <h5>Анализ детектора мошенничества</h5>
                      </div>
                      <div className="ai-analysis-content">
                        {renderAIAnalysis(trigger.ai_analysis)}
                      </div>
                    </div>
                  )}

                  {/* Доказательства показываем всегда, когда они есть */}
                  {renderEvidence(trigger)}
                </div>

                <div className="trigger-footer">
                  <span className="created-date">
                    Обнаружен: {formatDate(trigger.created_at)}
                  </span>
                  {/* <span className={`status ${trigger.is_active ? 'active' : 'inactive'}`}> */}
                  {/* {trigger.is_active ? 'Активный' : 'Неактивный'} */}
                  <span className={`status ${trigger.is_pair ? 'active' : 'inactive'}`}>
                    {trigger.is_pair ? 'Активный' : 'Неактивный'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TriggersListPage;
