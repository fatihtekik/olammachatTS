import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { analysisHistoryService, AnalysisHistory as AnalysisHistoryType } from '../services/analysisHistoryService';
import { h2hHistoryService, H2HAnalysisHistory } from '../services/h2hHistoryService';
import './AnalysisHistory.css';

const AnalysisHistory: React.FC = () => {
  const navigate = useNavigate();
  const [history, setHistory] = useState<AnalysisHistoryType[]>([]);
  const [h2hHistory, setH2hHistory] = useState<H2HAnalysisHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'ollama' | 'lmstudio'>('all');
  const [sortBy, setSortBy] = useState<'date' | 'players' | 'matches' | 'triggers'>('date');
  const [activeTab, setActiveTab] = useState<'general' | 'h2h'>('general');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Инициализируем и загружаем параллельно
      const [allHistory, allH2hHistory] = await Promise.all([
        analysisHistoryService.init().then(() => analysisHistoryService.getAllAnalyses()),
        h2hHistoryService.init().then(() => h2hHistoryService.getAllH2HAnalyses())
      ]);
      
      setHistory(allHistory);
      setH2hHistory(allH2hHistory);
    } catch (err: any) {
      console.error('❌ Ошибка загрузки истории:', err);
      setError(err.message || 'Ошибка загрузки истории');
    } finally {
      setLoading(false);
    }
  };

  const openAnalysis = (item: AnalysisHistoryType) => {
    console.log('📂 Открытие анализа:', item);
    navigate('/analysis', {
      state: { analysisHistory: item }
    });
  };

  const openH2HAnalysis = (item: H2HAnalysisHistory) => {
    console.log('📂 Открытие H2H анализа:', item);
    navigate('/h2h-analysis', {
      state: { h2hHistory: item }
    });
  };

  const deleteAnalysis = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Вы уверены, что хотите удалить этот анализ из истории?')) {
      return;
    }

    try {
      await analysisHistoryService.deleteAnalysis(id);
      await loadHistory();
    } catch (err: any) {
      console.error('❌ Ошибка удаления:', err);
      alert('Ошибка удаления анализа');
    }
  };

  const deleteH2HAnalysis = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Вы уверены, что хотите удалить этот H2H анализ из истории?')) {
      return;
    }

    try {
      await h2hHistoryService.deleteH2HAnalysis(id);
      await loadHistory();
    } catch (err: any) {
      console.error('❌ Ошибка удаления:', err);
      alert('Ошибка удаления H2H анализа');
    }
  };

  const clearAllHistory = async () => {
    if (!confirm('Вы уверены, что хотите очистить всю историю анализов?')) {
      return;
    }

    try {
      if (activeTab === 'general') {
        await analysisHistoryService.clearAll();
      } else {
        await h2hHistoryService.clearAll();
      }
      await loadHistory();
    } catch (err: any) {
      console.error('❌ Ошибка очистки:', err);
      alert('Ошибка очистки истории');
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp).toLocaleString('ru-RU', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatPeriod = (start: string, end: string) => {
    const startDate = new Date(start).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
    const endDate = new Date(end).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' });
    return `${startDate} - ${endDate}`;
  };

  // Фильтрация и сортировка
  const filteredHistory = history
    .filter(item => filter === 'all' || item.aiProvider === filter)
    .sort((a, b) => {
      switch (sortBy) {
        case 'date':
          return b.timestamp - a.timestamp;
        case 'players':
          return b.totalPlayers - a.totalPlayers;
        case 'matches':
          return b.totalMatches - a.totalMatches;
        case 'triggers':
          return b.triggersFound - a.triggersFound;
        default:
          return 0;
      }
    });

  if (loading) {
    return (
      <div className="analysis-history-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Загрузка истории...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analysis-history-page">
      <div className="history-header">
        <div className="header-top">
          <h2>История анализов</h2>
          {((activeTab === 'general' && history.length > 0) || (activeTab === 'h2h' && h2hHistory.length > 0)) && (
            <button 
              className="clear-all-btn"
              onClick={clearAllHistory}
              title="Очистить всю историю"
            >
              <i className="bi bi-trash"></i>
              Очистить все
            </button>
          )}
        </div>
        
        {/* Вкладки для переключения между типами истории */}
        <div className="history-tabs">
          <button 
            className={`tab-btn ${activeTab === 'general' ? 'active' : ''}`}
            onClick={() => setActiveTab('general')}
          >
            <i className="bi bi-graph-up-arrow"></i>
            Общий анализ ({history.length})
          </button>
          <button 
            className={`tab-btn ${activeTab === 'h2h' ? 'active' : ''}`}
            onClick={() => setActiveTab('h2h')}
          >
            <i className="bi bi-people-fill"></i>
            H2H анализ ({h2hHistory.length})
          </button>
        </div>
        
        {activeTab === 'general' && history.length > 0 && (
          <div className="history-controls">
            <div className="filter-group">
              <label>Провайдер:</label>
              <div className="filter-buttons">
                <button 
                  className={filter === 'all' ? 'active' : ''}
                  onClick={() => setFilter('all')}
                >
                  Все
                </button>
                <button 
                  className={filter === 'lmstudio' ? 'active' : ''}
                  onClick={() => setFilter('lmstudio')}
                >
                  LM Studio
                </button>
                <button 
                  className={filter === 'ollama' ? 'active' : ''}
                  onClick={() => setFilter('ollama')}
                >
                  Ollama
                </button>
              </div>
            </div>

            <div className="sort-group">
              <label>Сортировка:</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
                <option value="date">По дате</option>
                <option value="players">По игрокам</option>
                <option value="matches">По матчам</option>
                <option value="triggers">По триггерам</option>
              </select>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          <i className="bi bi-exclamation-triangle"></i>
          {error}
        </div>
      )}

      {/* Общий анализ */}
      {activeTab === 'general' && (
        <>
          {filteredHistory.length === 0 ? (
            <div className="empty-state">
              <i className="bi bi-inbox"></i>
              <h3>История пуста</h3>
              <p>Проведите анализ базы данных, чтобы увидеть результаты здесь</p>
              <button 
                className="go-to-analysis-btn"
                onClick={() => navigate('/analysis')}
              >
                Перейти к анализу
              </button>
            </div>
          ) : (
            <div className="history-grid">
              {filteredHistory.map((item) => (
                <div 
                  key={item.id}
                  className="history-card"
                  onClick={() => openAnalysis(item)}
                >
                  <div className="history-header">
                    <div className="history-icon">
                      <i className="bi bi-graph-up-arrow"></i>
                    </div>
                    <div className="history-info">
                      <h4>Анализ от {formatDate(item.timestamp)}</h4>
                      <p className="history-period">
                        Период: {formatPeriod(item.periodStart, item.periodEnd)}
                      </p>
                    </div>
                    <button 
                      className="delete-btn"
                      onClick={(e) => deleteAnalysis(item.id, e)}
                      title="Удалить"
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                  
                  <div className="history-stats">
                    <div className="history-stat">
                      <i className="bi bi-people-fill"></i>
                      <span>{item.totalPlayers} игроков</span>
                    </div>
                    <div className="history-stat">
                      <i className="bi bi-trophy-fill"></i>
                      <span>{item.totalMatches} матчей</span>
                    </div>
                    <div className="history-stat">
                      <i className="bi bi-exclamation-triangle-fill"></i>
                      <span>{item.triggersFound} триггеров</span>
                    </div>
                  </div>
                  
                  <div className="history-provider">
                    <i className="bi bi-cpu"></i>
                    <span>{item.aiProvider === 'lmstudio' ? 'LM Studio' : 'Ollama'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="history-info">
            <i className="bi bi-info-circle"></i>
            Показано {filteredHistory.length} из {history.length} записей. 
            Максимум хранится 50 записей.
          </div>
        </>
      )}

      {/* H2H анализ */}
      {activeTab === 'h2h' && (
        <>
          {h2hHistory.length === 0 ? (
            <div className="empty-state">
              <i className="bi bi-inbox"></i>
              <h3>История H2H пуста</h3>
              <p>Проведите H2H анализ, чтобы увидеть результаты здесь</p>
              <button 
                className="go-to-analysis-btn"
                onClick={() => navigate('/h2h-analysis')}
              >
                Перейти к H2H анализу
              </button>
            </div>
          ) : (
            <div className="history-grid">
              {h2hHistory.map((item) => (
                <div 
                  key={item.id}
                  className="history-card h2h-card"
                  onClick={() => openH2HAnalysis(item)}
                >
                  <div className="history-header">
                    <div className="history-icon h2h-icon">
                      <i className="bi bi-people-fill"></i>
                    </div>
                    <div className="history-info">
                      <h4>
                        {item.analysisType === 'players' 
                          ? `${item.player1?.full_name || 'Игрок 1'} vs ${item.player2?.full_name || 'Игрок 2'}`
                          : `Анализ по дате: ${item.dateForAnalysis}`
                        }
                      </h4>
                      <p className="history-period">
                        {formatDate(item.timestamp)}
                      </p>
                    </div>
                    <button 
                      className="delete-btn"
                      onClick={(e) => deleteH2HAnalysis(item.id, e)}
                      title="Удалить"
                    >
                      <i className="bi bi-trash"></i>
                    </button>
                  </div>
                  
                  <div className="history-stats">
                    {item.analysisType === 'players' ? (
                      <>
                        <div className="history-stat">
                          <i className="bi bi-trophy-fill"></i>
                          <span>{item.totalMatches} матчей</span>
                        </div>
                        <div className="history-stat">
                          <i className="bi bi-exclamation-triangle-fill"></i>
                          <span>{item.triggersFound} триггеров</span>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="history-stat">
                          <i className="bi bi-people-fill"></i>
                          <span>{item.totalPairs || 0} пар</span>
                        </div>
                        <div className="history-stat">
                          <i className="bi bi-trophy-fill"></i>
                          <span>{item.totalMatches} матчей</span>
                        </div>
                      </>
                    )}
                  </div>
                  
                  <div className="history-provider">
                    <i className="bi bi-cpu"></i>
                    <span>{item.aiProvider === 'lmstudio' ? 'LM Studio' : 'Ollama'}</span>
                    {item.analysisType === 'players' && (
                      <span className="h2h-type-badge">По игрокам</span>
                    )}
                    {item.analysisType === 'date' && (
                      <span className="h2h-type-badge date-badge">По дате</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="history-info">
            <i className="bi bi-info-circle"></i>
            Показано {h2hHistory.length} записей H2H анализов. 
            Максимум хранится 50 записей.
          </div>
        </>
      )}
    </div>
  );
};

export default AnalysisHistory;
