import React, { useState, useEffect } from 'react';
import './AnalysisPage.css';

interface AnalysisData {
  id: string;
  matchInfo: string;
  player1: string;
  player2: string;
  score: string;
  tournament: string;
  stage: string;
  createdAt: Date;
  analysisText: string;
}

const AnalysisPage: React.FC = () => {
  const [analyses, setAnalyses] = useState<AnalysisData[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadRecentAnalyses();
  }, []);

  const loadRecentAnalyses = async () => {
    setLoading(true);
    try {
      // TODO: Заменить на реальный API запрос к бэкенду
      // Пока используем mock данные
      const mockAnalyses: AnalysisData[] = [
        {
          id: '1',
          matchInfo: 'Анализ матча: Иванов И. (1850) vs Петров П. (1920)',
          player1: 'Иванов И.',
          player2: 'Петров П.',
          score: '2:1',
          tournament: 'Открытый турнир',
          stage: 'Полуфинал',
          createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 часа назад
          analysisText: 'Матч показал интересную динамику. Несмотря на более низкий рейтинг, Иванов смог одержать победу...'
        },
        {
          id: '2',
          matchInfo: 'Анализ матча: Сидоров С. (2100) vs Козлов К. (2050)',
          player1: 'Сидоров С.',
          player2: 'Козлов К.',
          score: '3:0',
          tournament: 'Чемпионат лиги',
          stage: 'Финал',
          createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000), // 5 часов назад
          analysisText: 'Убедительная победа фаворита. Сидоров продемонстрировал стабильную игру на всех этапах матча...'
        },
        {
          id: '3',
          matchInfo: 'Анализ матча: Новиков Н. (1750) vs Волков В. (1800)',
          player1: 'Новиков Н.',
          player2: 'Волков В.',
          score: '1:3',
          tournament: 'Кубок города',
          stage: 'Четвертьфинал',
          createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 день назад
          analysisText: 'Матч прошёл в соответствии с прогнозами. Волков использовал своё преимущество в рейтинге...'
        }
      ];
      
      setAnalyses(mockAnalyses);
    } catch (error) {
      console.error('Error loading analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      return 'Меньше часа назад';
    } else if (diffInHours < 24) {
      return `${diffInHours} ${diffInHours === 1 ? 'час' : diffInHours < 5 ? 'часа' : 'часов'} назад`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `${diffInDays} ${diffInDays === 1 ? 'день' : diffInDays < 5 ? 'дня' : 'дней'} назад`;
    }
  };

  return (
    <div className="analysis-page">
      <div className="analysis-header">
        <h1>Последние анализы матчей</h1>
        <p>Обзор недавно проанализированных игр</p>
      </div>

      {loading ? (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Загрузка анализов...</p>
        </div>
      ) : (
        <div className="analyses-grid">
          {analyses.length === 0 ? (
            <div className="empty-state">
              <i className="bi bi-clipboard-data"></i>
              <h3>Анализы не найдены</h3>
              <p>Перейдите в чат или загрузите Excel файл для создания первого анализа</p>
            </div>
          ) : (
            analyses.map((analysis) => (
              <div key={analysis.id} className="analysis-card">
                <div className="analysis-card-header">
                  <h3>{analysis.player1} vs {analysis.player2}</h3>
                  <span className="analysis-time">{formatTimeAgo(analysis.createdAt)}</span>
                </div>
                
                <div className="analysis-card-info">
                  <div className="match-details">
                    <span className="score">{analysis.score}</span>
                    <span className="tournament">{analysis.tournament}</span>
                    <span className="stage">{analysis.stage}</span>
                  </div>
                </div>
                
                <div className="analysis-preview">
                  {analysis.analysisText.length > 150 
                    ? analysis.analysisText.substring(0, 150) + '...'
                    : analysis.analysisText
                  }
                </div>
                
                <div className="analysis-card-footer">
                  <button className="view-details-btn">
                    <i className="bi bi-eye"></i>
                    Подробнее
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default AnalysisPage;
