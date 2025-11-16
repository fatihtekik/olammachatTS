import React, { useState } from 'react';
import ScenarioAnalysisTab from './ScenarioAnalysisTab';
import './PlayerCardModal.css';

interface PlayerCardModalProps {
  playerId: string;
  playerName: string;
  playerRating?: number;
  onClose: () => void;
  // Дополнительная информация о триггере (опционально)
  triggerInfo?: {
    trigger_type: string;
    trigger_value: string;
    severity_level: number;
    period_start: string;
    period_end: string;
    created_at: string;
    evidence?: any[];
  };
}

type TabType = 'triggers' | 'scenarios';

const PlayerCardModal: React.FC<PlayerCardModalProps> = ({
  playerId,
  playerName,
  playerRating,
  onClose,
  triggerInfo,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('triggers');

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="player-card-modal-backdrop" onClick={handleBackdropClick}>
      <div className="player-card-modal">
        {/* Заголовок */}
        <div className="player-card-header">
          <div>
            <h2>{playerName}</h2>
            {playerRating && (
              <p className="player-rating">Рейтинг: {playerRating}</p>
            )}
          </div>
          <button className="close-button" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Вкладки */}
        <div className="player-card-tabs">
          <button
            className={`tab-button ${activeTab === 'triggers' ? 'active' : ''}`}
            onClick={() => setActiveTab('triggers')}
          >
            Карточки
          </button>
          <button
            className={`tab-button ${activeTab === 'scenarios' ? 'active' : ''}`}
            onClick={() => setActiveTab('scenarios')}
          >
            СТАТИСТИЧЕСКИЙ АНАЛИЗ
          </button>
        </div>

        {/* Контент вкладок */}
        <div className="player-card-content">
          {activeTab === 'triggers' && triggerInfo && (
            <div className="triggers-tab">
              <div className="trigger-details">
                <h3>Информация о триггере</h3>
                
                <div className="trigger-info-grid">
                  <div className="info-item">
                    <span className="info-label">Тип:</span>
                    <span className="info-value">{triggerInfo.trigger_type}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Описание:</span>
                    <span className="info-value">{triggerInfo.trigger_value}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Период:</span>
                    <span className="info-value">
                      {new Date(triggerInfo.period_start).toLocaleDateString('ru-RU')} - 
                      {new Date(triggerInfo.period_end).toLocaleDateString('ru-RU')}
                    </span>
                  </div>
                </div>

                {triggerInfo.evidence && triggerInfo.evidence.length > 0 && (
                  <div className="evidence-section">
                    <h4>Доказательства</h4>
                    <div className="evidence-list">
                      {triggerInfo.evidence.map((ev, idx) => (
                        <div key={idx} className="evidence-item">
                          <p><strong>Дата:</strong> {new Date(ev.date).toLocaleDateString('ru-RU')}</p>
                          <p><strong>Оппонент:</strong> {ev.opponent}</p>
                          <p><strong>Счёт:</strong> {ev.score}</p>
                          {ev.highlight && <p><strong>Детали:</strong> {ev.highlight}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'triggers' && !triggerInfo && (
            <div className="no-trigger-info">
              <p>Информация о триггере отсутствует</p>
            </div>
          )}

          {activeTab === 'scenarios' && (
            <ScenarioAnalysisTab 
              playerId={playerId}
              playerName={playerName}
            />
          )}
        </div>
      </div>
    </div>
  );
};

export default PlayerCardModal;
