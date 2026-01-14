import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { analysisHistoryService } from '../services/analysisHistoryService';
import { useInvalidateStats } from '../hooks/useDashboardStats';
import PlayerCardModal from './PlayerCardModal';
import './AnalysisPage.css';

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
  const navigate = useNavigate();
  const location = useLocation();
  const invalidateStats = useInvalidateStats();
  
  // === СОСТОЯНИЯ ===
  const [loading, setLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [selectedTrigger, setSelectedTrigger] = useState<Trigger | null>(null);
  const [singleTriggerAnalysis, setSingleTriggerAnalysis] = useState<string>('');
  const [singleTriggerLoading, setSingleTriggerLoading] = useState<boolean>(false);
  const SINGLE_TRIGGER_WORD_LIMIT = 60;
  
  // Состояние для модального окна сценариев
  const [scenarioModalOpen, setScenarioModalOpen] = useState<boolean>(false);
  const [selectedPlayerForScenario, setSelectedPlayerForScenario] = useState<{ id: string; name: string; rating?: number } | null>(null);
  
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
  const [aiAnalysisEnabled, setAiAnalysisEnabled] = useState<boolean>(true); // Включение/выключение AI анализа
  const [selectedModel, setSelectedModel] = useState<string>(''); // Выбранная модель
  const [availableModels, setAvailableModels] = useState<string[]>([]); // Доступные модели
  const [isLoadingModels, setIsLoadingModels] = useState<boolean>(false); // Загрузка моделей
  const [maxTokens, setMaxTokens] = useState<number>(2000); // Ограничение токенов

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
    { id: 'pressure_situations', name: 'Игра под давлением', description: 'Слабые результаты в важных матчах', severity: 'high' },
    { id: 'time_performance', name: 'Слабая форма в ночное время', description: 'Проблемы по времени суток', severity: 'medium' },
    { id: 'losing_streaks', name: 'Проигрыши в ряд', description: 'Серии поражений подряд', severity: 'medium' },
    { id: 'post_holiday_problems', name: 'Проблемы после праздников', description: 'Слабая игра после перерывов', severity: 'medium' }
  ];

  // === ИНИЦИАЛИЗАЦИЯ ===
  useEffect(() => {
    initializePeriod();
    // Загружаем сохранённые настройки из localStorage
    const savedProvider = localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio';
    const savedMatchesLimit = localStorage.getItem('matchesLimit');
    const savedAiAnalysisEnabled = localStorage.getItem('aiAnalysisEnabled');
    const savedSelectedModel = localStorage.getItem('selectedModel');
    const savedMaxTokens = localStorage.getItem('maxTokens');
    
    if (savedProvider) {
      setAiProvider(savedProvider);
    }
    if (savedMatchesLimit) {
      setMatchesLimit(parseInt(savedMatchesLimit));
    }
    if (savedAiAnalysisEnabled !== null) {
      setAiAnalysisEnabled(savedAiAnalysisEnabled === 'true');
    }
    if (savedSelectedModel) {
      setSelectedModel(savedSelectedModel);
    }
    if (savedMaxTokens) {
      setMaxTokens(parseInt(savedMaxTokens));
    }
  }, []);

  // Загружаем историю анализа при переходе из Dashboard
  useEffect(() => {
    if (location.state?.analysisHistory) {
      const history = location.state.analysisHistory;
      console.log('📥 Загрузка истории анализа:', history);
      
      // Восстанавливаем результаты
      setAnalysisResult({
        period_start: history.periodStart,
        period_end: history.periodEnd,
        total_players: history.totalPlayers,
        total_matches: history.totalMatches,
        triggers_found: history.triggersFound,
        triggers: history.triggers,
        top_performers: [],
        problem_players: []
      });
      
      // Восстанавливаем настройки периода
      if (history.periodStart) setPeriodStart(history.periodStart);
      if (history.periodEnd) setPeriodEnd(history.periodEnd);
      
      // Восстанавливаем настройки AI
      if (history.analysisSettings) {
        if (history.analysisSettings.matchesLimit) {
          setMatchesLimit(history.analysisSettings.matchesLimit);
        }
        if (history.analysisSettings.aiAnalysisEnabled !== undefined) {
          setAiAnalysisEnabled(history.analysisSettings.aiAnalysisEnabled);
        }
        if (history.analysisSettings.selectedModel) {
          setSelectedModel(history.analysisSettings.selectedModel);
        }
      }
      
      // Восстанавливаем провайдера AI
      if (history.aiProvider) {
        setAiProvider(history.aiProvider);
      }
      
      setLoading(false);
      
      // Очищаем state после загрузки чтобы не загружать повторно
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // Загружаем модели при изменении провайдера
  useEffect(() => {
    if (settingsOpen) {
      loadAvailableModels(aiProvider);
    }
  }, [aiProvider, settingsOpen]);

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
    localStorage.setItem('aiAnalysisEnabled', aiAnalysisEnabled.toString());
    localStorage.setItem('selectedModel', selectedModel);
    localStorage.setItem('maxTokens', maxTokens.toString());
    setSettingsOpen(false);
    alert('✅ Настройки сохранены!');
  };

  // Загрузка доступных моделей
  const loadAvailableModels = async (provider: 'ollama' | 'lmstudio') => {
    setIsLoadingModels(true);
    try {
      let url = '';
      if (provider === 'ollama') {
        url = 'http://localhost:11434/api/tags';
      } else {
        url = 'http://localhost:1234/v1/models';
      }

      console.log(`🔍 Загрузка моделей для ${provider} с ${url}`);
      
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('📦 Получены модели:', data);

      let models: string[] = [];
      if (provider === 'ollama' && data.models) {
        models = data.models.map((m: any) => m.name);
      } else if (provider === 'lmstudio' && data.data) {
        models = data.data.map((m: any) => m.id);
      }

      setAvailableModels(models);
      
      // Автоматически выбираем первую модель, если ничего не выбрано
      if (models.length > 0 && !selectedModel) {
        setSelectedModel(models[0]);
      }
      
      console.log('✅ Загружено моделей:', models.length);
    } catch (error) {
      console.error('❌ Ошибка загрузки моделей:', error);
      alert(`Не удалось загрузить модели для ${provider}. Убедитесь, что сервер запущен.`);
      setAvailableModels([]);
    } finally {
      setIsLoadingModels(false);
    }
  };

  // Тестовый запрос к модели
  const testModel = async (provider: 'ollama' | 'lmstudio', model: string) => {
    try {
      let url = '';
      let body = {};
      
      if (provider === 'ollama') {
        url = 'http://localhost:11434/api/generate';
        body = {
          model: model,
          prompt: 'Test',
          stream: false
        };
      } else {
        url = 'http://localhost:1234/v1/chat/completions';
        body = {
          model: model,
          messages: [{ role: 'user', content: 'Test' }],
          max_tokens: 10
        };
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      return response.ok;
    } catch (error) {
      console.error('❌ Ошибка теста модели:', error);
      return false;
    }
  };

  // Анализ базы данных - ОСНОВНАЯ ФУНКЦИЯ
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
        analyze_recent_upload_only: false,
        ai_provider: aiProvider,  // Добавляем выбранный провайдер
        ai_analysis_enabled: aiAnalysisEnabled,  // Включение/выключение AI
        selected_model: selectedModel,  // Выбранная модель
        max_tokens: maxTokens  // Ограничение токенов
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

        // Сохраняем результат в IndexedDB
        try {
          await analysisHistoryService.init();
          await analysisHistoryService.saveAnalysis({
            periodStart,
            periodEnd,
            totalPlayers: result.total_players || 0,
            totalMatches: result.total_matches || 0,
            triggersFound: result.triggers_found || 0,
            triggers: result.triggers || [],
            aiProvider,
            analysisSettings: {
              matchesLimit,
              aiAnalysisEnabled,
              selectedModel
            }
          });
          console.log('✅ Analysis saved to IndexedDB');
        } catch (dbError) {
          console.error('❌ Failed to save to IndexedDB:', dbError);
        }

        // Инвалидируем кеш статистики дашборда
        invalidateStats();

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
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedTrigger(null);
  };

  const getEfficiencyClass = (value?: number): string => {
    if (!value) return 'medium';
    if (value < 40) return 'low';
    if (value < 60) return 'medium';
    return 'high';
  };

  // Краткая строка со счетом всех сетов, например: "5:11 · 7:11 · 9:11"
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

    return (
      <div className="modal-evidence-section">
        <h5>Доказательства из матчей ({trigger.evidence.length})</h5>
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

              {/* Под шапкой всегда показываем компактную строку сетов в стилизованном блоке */}
              {/* ТОЛЬКО если нет детальных сетов - показываем highlight */}
              {!(evidence.sets && evidence.sets.length > 0) && (
                <div className="evidence-highlight">
                  {evidence.highlight}
                </div>
              )}

              {/* Детализированные сеты (горизонтально), если нужны визуально */}
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
      </div>
    );
  };

  const fetchSingleTriggerAnalysis = async (triggerId: string) => {
    try {
      setSingleTriggerLoading(true);
      setSingleTriggerAnalysis('');
      const response = await fetch(`http://localhost:8000/api/v1/match-analysis/triggers/${triggerId}/ai-analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          word_limit: SINGLE_TRIGGER_WORD_LIMIT,
          provider: aiProvider || 'lmstudio'
        })
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
      {/* Основной контент */}
      <div className="analysis-content">
        <div className="analysis-header">
          <h2>Анализ базы данных</h2>
          <button 
            className="settings-btn"
            onClick={() => setSettingsOpen(true)}
            title="Настройки анализа"
          >
            <i className="bi bi-gear-fill"></i>
          </button>
        </div>

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
              <label>AI провайдер:</label>
              <div className="provider-selector">
                <button
                  className={`provider-btn ${aiProvider === 'ollama' ? 'active' : ''}`}
                  onClick={() => setAiProvider('ollama')}
                  type="button"
                >
                  <span className="provider-indicator"></span>
                  Ollama
                </button>
                <button
                  className={`provider-btn ${aiProvider === 'lmstudio' ? 'active' : ''}`}
                  onClick={() => setAiProvider('lmstudio')}
                  type="button"
                >
                  <span className="provider-indicator"></span>
                  LM Studio
                </button>
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
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                              <h3 className="player-name">{mainTrigger.player_name}</h3>
                              <button
                                className="scenario-analysis-button"
                                onClick={() => {
                                  setSelectedPlayerForScenario({
                                    id: playerId,
                                    name: mainTrigger.player_name,
                                    rating: mainTrigger.player_rating
                                  });
                                  setScenarioModalOpen(true);
                                }}
                                title="Открыть сценарный анализ"
                              >
                                Сценарии
                              </button>
                            </div>
                            
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
                                <div className="ai-analysis">
                                  <p><strong>Анализ ИИ:</strong></p>
                                  {!aiAnalysisEnabled ? (
                                    <p style={{ color: '#6b7280', fontStyle: 'italic' }}>Был отключен</p>
                                  ) : mainTrigger.ai_analysis ? (
                                    <p>{(() => {
                                      // Логируем полный ответ из бэкенда в консоль
                                      console.log('🤖 Полный AI ответ от бэкенда (с think):', mainTrigger.ai_analysis);
                                      const parsed = parseAIResponse(mainTrigger.ai_analysis);
                                      if (parsed.thinking) {
                                        console.log('💭 Think блок:', parsed.thinking);
                                      }
                                      console.log('📝 Чистый ответ:', parsed.response);
                                      return parsed.response;
                                    })()}</p>
                                  ) : (
                                    <p style={{ color: '#6b7280', fontStyle: 'italic' }}>Нет данных</p>
                                  )}
                                </div>
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

                {/* Доказательства из матчей */}
                {renderEvidence(selectedTrigger)}

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
              {/* Включение/выключение AI анализа */}
              <div className="setting-group">
                <label className="setting-label">
                  <i className="bi bi-lightbulb"></i> AI Анализ
                </label>
                <div className="toggle-container">
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={aiAnalysisEnabled}
                      onChange={(e) => setAiAnalysisEnabled(e.target.checked)}
                    />
                    <span className="toggle-slider"></span>
                  </label>
                  <span className="toggle-label">
                    {aiAnalysisEnabled ? 'Включен' : 'Выключен'}
                  </span>
                </div>
                {!aiAnalysisEnabled && (
                  <p className="setting-hint warning">
                    ⚠️ AI анализ отключен. В поле анализа будет отображаться: "Был отключен"
                  </p>
                )}
              </div>

              {/* AI Провайдер - показываем только если AI включен */}
              {aiAnalysisEnabled && (
                <>
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
                        {aiProvider === 'lmstudio' && <span className="provider-indicator"></span>}
                      </button>
                      <button
                        className={`provider-btn ${aiProvider === 'ollama' ? 'active' : ''}`}
                        onClick={() => setAiProvider('ollama')}
                      >
                        <i className="bi bi-terminal"></i>
                        <span>Ollama</span>
                        {aiProvider === 'ollama' && <span className="provider-indicator"></span>}
                      </button>
                    </div>
                    <p className="setting-hint">
                      {aiProvider === 'lmstudio' 
                        ? '🔷 Использует LM Studio (localhost:1234)' 
                        : '🟢 Использует Ollama (localhost:11434)'}
                    </p>
                  </div>

                  {/* Выбор модели */}
                  <div className="setting-group">
                    <label className="setting-label">
                      <i className="bi bi-cpu"></i> Модель анализа
                    </label>
                    {isLoadingModels ? (
                      <div className="loading-models">
                        <div className="spinner-small"></div>
                        <span>Загрузка доступных моделей...</span>
                      </div>
                    ) : availableModels.length > 0 ? (
                      <>
                        <select
                          value={selectedModel}
                          onChange={(e) => setSelectedModel(e.target.value)}
                          className="model-select"
                        >
                          {availableModels.map(model => (
                            <option key={model} value={model}>{model}</option>
                          ))}
                        </select>
                        <button
                          className="test-model-btn"
                          onClick={async () => {
                            const result = await testModel(aiProvider, selectedModel);
                            if (result) {
                              alert('✅ Модель работает корректно!');
                            } else {
                              alert('❌ Модель не отвечает. Проверьте, что она загружена в ' + aiProvider);
                            }
                          }}
                        >
                          <i className="bi bi-play-circle"></i> Проверить модель
                        </button>
                      </>
                    ) : (
                      <p className="setting-hint error">
                        ❌ Модели не найдены. Убедитесь, что {aiProvider === 'lmstudio' ? 'LM Studio' : 'Ollama'} запущен и модели загружены.
                      </p>
                    )}
                  </div>

                  {/* Ограничение токенов */}
                  <div className="setting-group">
                    <label className="setting-label">
                      <i className="bi bi-hash"></i> Ограничение токенов
                    </label>
                    <div className="tokens-control">
                      <input
                        type="range"
                        min="200"
                        max="8000"
                        step="100"
                        value={maxTokens}
                        onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                        className="tokens-slider"
                      />
                      <div className="tokens-value">
                        <input
                          type="number"
                          min="200"
                          max="8000"
                          value={maxTokens}
                          onChange={(e) => setMaxTokens(Math.min(8000, Math.max(200, parseInt(e.target.value) || 200)))}
                          className="tokens-input"
                        />
                        <span>токенов</span>
                      </div>
                    </div>
                    <p className="setting-hint">
                      📊 Макс. токенов для ответа AI (200-8000). <strong>По умолчанию: 2000</strong>
                    </p>
                  </div>
                </>
              )}
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
      
      {/* Модальное окно для сценарного анализа игрока */}
      {scenarioModalOpen && selectedPlayerForScenario && (
        <PlayerCardModal
          playerId={selectedPlayerForScenario.id}
          playerName={selectedPlayerForScenario.name}
          playerRating={selectedPlayerForScenario.rating}
          onClose={() => {
            setScenarioModalOpen(false);
            setSelectedPlayerForScenario(null);
          }}
        />
      )}
      
      </div> {/* Закрываем analysis-content */}
    </div>
  );
};

export default AnalysisPage;
