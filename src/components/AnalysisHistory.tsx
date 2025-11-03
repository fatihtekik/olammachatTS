import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { analysisHistoryService, AnalysisHistory as AnalysisHistoryType } from '../services/analysisHistoryService';
import './AnalysisHistory.css';

const AnalysisHistory: React.FC = () => {
  const navigate = useNavigate();
  const [history, setHistory] = useState<AnalysisHistoryType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'ollama' | 'lmstudio'>('all');
  const [sortBy, setSortBy] = useState<'date' | 'players' | 'matches' | 'triggers'>('date');

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      await analysisHistoryService.init();
      const allHistory = await analysisHistoryService.getAllAnalyses();
      setHistory(allHistory);
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

  const clearAllHistory = async () => {
    if (!confirm('Вы уверены, что хотите очистить всю историю анализов?')) {
      return;
    }

    try {
      await analysisHistoryService.clearAll();
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
          {history.length > 0 && (
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
        
        {history.length > 0 && (
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
    </div>
  );
};

export default AnalysisHistory;
