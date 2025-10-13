import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDashboardStats } from '../hooks/useDashboardStats';
import { analysisHistoryService, AnalysisHistory } from '../services/analysisHistoryService';
import './Dashboard.css';

interface DashboardStats {
  total_players: number;
  total_matches: number;
  active_triggers: number;
  recent_uploads: number;
  last_upload_date?: string;
  last_analysis_date?: string;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { stats, loading, error, refresh } = useDashboardStats();
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisHistory[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    loadRecentAnalyses();
  }, []);

  const loadRecentAnalyses = async () => {
    try {
      await analysisHistoryService.init();
      const analyses = await analysisHistoryService.getRecentAnalyses(5);
      setRecentAnalyses(analyses);
    } catch (error) {
      console.error('Failed to load analysis history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const navigateTo = (path: string) => {
    navigate(path);
  };

  const openAnalysisHistory = async (analysis: AnalysisHistory) => {
    // Переходим на страницу анализа с загруженными данными
    navigate('/analysis', { state: { analysisHistory: analysis } });
  };

  const formatDate = (date: Date) => {
    return new Date(date).toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="dashboard-page">
      {/* Основной контент */}
      <div className="dashboard-content">
        <div className="dashboard-header">
          <h1>Обзор системы</h1>
          <p>Актуальная информация о данных и анализе</p>
        </div>

        {/* Статистика в карточках */}
        <div className="stats-grid">
          <div className="stat-card" onClick={() => navigateTo('/analysis')}>
            <div className="stat-icon players">
              <i className="bi bi-people-fill"></i>
            </div>
            <div className="stat-content">
              <h3>{loading ? '...' : stats.total_players}</h3>
              <p>Игроков в базе</p>
            </div>
            <i className="bi bi-arrow-right stat-arrow"></i>
          </div>

          <div className="stat-card" onClick={() => navigateTo('/analysis')}>
            <div className="stat-icon matches">
              <i className="bi bi-trophy-fill"></i>
            </div>
            <div className="stat-content">
              <h3>{loading ? '...' : stats.total_matches}</h3>
              <p>Матчей обработано</p>
            </div>
            <i className="bi bi-arrow-right stat-arrow"></i>
          </div>

          <div className="stat-card" onClick={() => navigateTo('/analysis')}>
            <div className="stat-icon triggers">
              <i className="bi bi-exclamation-triangle-fill"></i>
            </div>
            <div className="stat-content">
              <h3>{loading ? '...' : stats.active_triggers}</h3>
              <p>Активных триггеров</p>
            </div>
            <i className="bi bi-arrow-right stat-arrow"></i>
          </div>

          <div className="stat-card" onClick={() => navigateTo('/upload')}>
            <div className="stat-icon uploads">
              <i className="bi bi-cloud-upload-fill"></i>
            </div>
            <div className="stat-content">
              <h3>{loading ? '...' : stats.recent_uploads}</h3>
              <p>Загрузок за неделю</p>
            </div>
            <i className="bi bi-arrow-right stat-arrow"></i>
          </div>
        </div>

        {/* Быстрые действия */}
        <div className="quick-actions">
          <h2>Быстрые действия</h2>
          <div className="actions-grid">
            <button className="action-card" onClick={() => navigateTo('/upload')}>
              <i className="bi bi-file-earmark-excel"></i>
              <h3>Загрузить Excel</h3>
              <p>Добавить новые данные матчей</p>
            </button>

            <button className="action-card" onClick={() => navigateTo('/analysis')}>
              <i className="bi bi-search"></i>
              <h3>Запустить анализ</h3>
              <p>Проанализировать базу данных</p>
            </button>

            <button className="action-card" onClick={() => navigateTo('/chat')}>
              <i className="bi bi-chat-dots"></i>
              <h3>Открыть чат</h3>
              <p>Задать вопрос AI помощнику</p>
            </button>
          </div>
        </div>

        {/* История анализов */}
        {recentAnalyses.length > 0 && (
          <div className="analysis-history">
            <div className="section-header">
              <h2>История анализов</h2>
              <button className="view-all-btn" onClick={() => navigateTo('/analysis')}>
                Смотреть все
              </button>
            </div>
            <div className="history-list">
              {recentAnalyses.map((analysis) => (
                <div 
                  key={analysis.id} 
                  className="history-card"
                  onClick={() => openAnalysisHistory(analysis)}
                >
                  <div className="history-header">
                    <div className="history-icon">
                      <i className="bi bi-graph-up-arrow"></i>
                    </div>
                    <div className="history-info">
                      <h4>Анализ от {formatDate(analysis.timestamp)}</h4>
                      <p className="history-period">
                        Период: {new Date(analysis.periodStart).toLocaleDateString('ru-RU')} - {new Date(analysis.periodEnd).toLocaleDateString('ru-RU')}
                      </p>
                    </div>
                  </div>
                  <div className="history-stats">
                    <div className="history-stat">
                      <i className="bi bi-people-fill"></i>
                      <span>{analysis.totalPlayers} игроков</span>
                    </div>
                    <div className="history-stat">
                      <i className="bi bi-trophy-fill"></i>
                      <span>{analysis.totalMatches} матчей</span>
                    </div>
                    <div className="history-stat">
                      <i className="bi bi-exclamation-triangle-fill"></i>
                      <span>{analysis.triggersFound} триггеров</span>
                    </div>
                  </div>
                  <div className="history-provider">
                    <i className="bi bi-cpu"></i>
                    <span>{analysis.aiProvider === 'lmstudio' ? 'LM Studio' : 'Ollama'}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Последняя активность */}
        <div className="recent-activity">
          <h2>Последняя активность</h2>
          <div className="activity-list">
            {stats.last_upload_date && (
              <div className="activity-item">
                <i className="bi bi-cloud-upload"></i>
                <div>
                  <p className="activity-title">Последняя загрузка данных</p>
                  <p className="activity-time">{new Date(stats.last_upload_date).toLocaleString('ru-RU')}</p>
                </div>
              </div>
            )}
            {stats.last_analysis_date && (
              <div className="activity-item">
                <i className="bi bi-graph-up"></i>
                <div>
                  <p className="activity-title">Последний анализ</p>
                  <p className="activity-time">{new Date(stats.last_analysis_date).toLocaleString('ru-RU')}</p>
                </div>
              </div>
            )}
            {!stats.last_upload_date && !stats.last_analysis_date && (
              <div className="activity-empty">
                <i className="bi bi-inbox"></i>
                <p>Активность отсутствует</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
