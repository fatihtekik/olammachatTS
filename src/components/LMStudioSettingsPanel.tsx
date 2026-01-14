import React, { useState, useEffect, useCallback } from 'react';
import { LMStudioSettings, DEFAULT_LMSTUDIO_SETTINGS } from '../types/chat';
import './LMStudioSettingsPanel.css';

interface LMStudioSettingsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSettingsChange: (settings: LMStudioSettings) => void;
}

const LMStudioSettingsPanel: React.FC<LMStudioSettingsPanelProps> = ({
  isOpen,
  onClose,
  onSettingsChange
}) => {
  const [settings, setSettings] = useState<LMStudioSettings>(DEFAULT_LMSTUDIO_SETTINGS);
  const [activeTab, setActiveTab] = useState<'generation' | 'reasoning' | 'advanced'>('generation');

  // Загрузка настроек из localStorage
  useEffect(() => {
    const saved = localStorage.getItem('lmstudio_settings');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setSettings({ ...DEFAULT_LMSTUDIO_SETTINGS, ...parsed });
      } catch (e) {
        console.error('Error parsing LM Studio settings:', e);
      }
    }
  }, []);

  // Сохранение настроек
  const saveSettings = useCallback((newSettings: LMStudioSettings) => {
    localStorage.setItem('lmstudio_settings', JSON.stringify(newSettings));
    onSettingsChange(newSettings);
  }, [onSettingsChange]);

  const handleSettingChange = <K extends keyof LMStudioSettings>(
    key: K,
    value: LMStudioSettings[K]
  ) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    saveSettings(newSettings);
  };

  const resetToDefaults = () => {
    setSettings(DEFAULT_LMSTUDIO_SETTINGS);
    saveSettings(DEFAULT_LMSTUDIO_SETTINGS);
  };

  if (!isOpen) return null;

  return (
    <div className="lmstudio-settings-overlay" onClick={onClose}>
      <div className="lmstudio-settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <div className="settings-title">
            <h2>Параметры LM Studio</h2>
          </div>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {/* Tabs */}
        <div className="settings-tabs">
          <button 
            className={`tab-btn ${activeTab === 'generation' ? 'active' : ''}`}
            onClick={() => setActiveTab('generation')}
          >
            Генерация
          </button>
          <button 
            className={`tab-btn ${activeTab === 'reasoning' ? 'active' : ''}`}
            onClick={() => setActiveTab('reasoning')}
          >
            Reasoning
          </button>
          <button 
            className={`tab-btn ${activeTab === 'advanced' ? 'active' : ''}`}
            onClick={() => setActiveTab('advanced')}
          >
            Дополнительно
          </button>
        </div>

        <div className="settings-content">
          {/* Generation Tab */}
          {activeTab === 'generation' && (
            <div className="settings-section">
              {/* Temperature */}
              <div className="setting-item">
                <div className="setting-label">
                  <span className="label-text">Температура</span>
                  <span className="label-value">{settings.temperature.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.05"
                  value={settings.temperature}
                  onChange={(e) => handleSettingChange('temperature', parseFloat(e.target.value))}
                  className="setting-slider"
                />
                <div className="slider-labels">
                  <span>Точный (0)</span>
                  <span>Креативный (2)</span>
                </div>
                <p className="setting-description">
                  Низкое значение — более предсказуемые ответы. Высокое — более творческие.
                </p>
              </div>

              {/* Max Completion Tokens */}
              <div className="setting-item">
                <div className="setting-label">
                  <span className="label-text">Макс. токенов ответа</span>
                  <span className="label-value">{settings.maxCompletionTokens}</span>
                </div>
                <input
                  type="range"
                  min="256"
                  max="16384"
                  step="256"
                  value={settings.maxCompletionTokens}
                  onChange={(e) => handleSettingChange('maxCompletionTokens', parseInt(e.target.value))}
                  className="setting-slider"
                />
                <div className="slider-labels">
                  <span>Короткие (256)</span>
                  <span>Длинные (16K)</span>
                </div>
                <p className="setting-description">
                  Максимальная длина ответа модели в токенах.
                </p>
              </div>
            </div>
          )}

          {/* Reasoning Tab */}
          {activeTab === 'reasoning' && (
            <div className="settings-section">
              {/* Max Reasoning Tokens */}
              <div className="setting-item">
                <div className="setting-label">
                  <span className="label-text">Токены для мышления</span>
                  <span className="label-value">{settings.maxReasoningTokens}</span>
                </div>
                <input
                  type="range"
                  min="512"
                  max="16384"
                  step="512"
                  value={settings.maxReasoningTokens}
                  onChange={(e) => handleSettingChange('maxReasoningTokens', parseInt(e.target.value))}
                  className="setting-slider"
                />
                <div className="slider-labels">
                  <span>Мало (512)</span>
                  <span>Много (16K)</span>
                </div>
                <p className="setting-description">
                  Количество токенов для внутренних рассуждений модели (thinking).
                </p>
              </div>

              {/* Reasoning Effort */}
              <div className="setting-item">
                <div className="setting-label">
                  <span className="label-text">Интенсивность reasoning</span>
                </div>
                <div className="button-group">
                  {(['low', 'medium', 'high'] as const).map((effort) => (
                    <button
                      key={effort}
                      className={`effort-btn ${settings.reasoningEffort === effort ? 'active' : ''}`}
                      onClick={() => handleSettingChange('reasoningEffort', effort)}
                    >
                      {effort === 'low' ? 'Низкая' : effort === 'medium' ? 'Средняя' : 'Высокая'}
                    </button>
                  ))}
                </div>
                <p className="setting-description">
                  Низкая — быстрее, меньше анализа. Высокая — медленнее, глубже анализирует.
                </p>
              </div>

              {/* Show Reasoning */}
              <div className="setting-item">
                <div className="setting-toggle-row">
                  <span className="label-text">Показывать мысли модели</span>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={settings.showReasoning}
                      onChange={(e) => handleSettingChange('showReasoning', e.target.checked)}
                    />
                    <span className="toggle-slider-round"></span>
                  </label>
                </div>
                <p className="setting-description">
                  {settings.showReasoning 
                    ? 'Thinking-блоки будут отображаться в ответах'
                    : 'Thinking-блоки скрыты, виден только финальный ответ'}
                </p>
              </div>
            </div>
          )}

          {/* Advanced Tab */}
          {activeTab === 'advanced' && (
            <div className="settings-section">
              {/* Top P */}
              <div className="setting-item">
                <div className="setting-label">
                  <span className="label-text">Top P (nucleus sampling)</span>
                  <span className="label-value">{settings.topP.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="0.1"
                  max="1"
                  step="0.05"
                  value={settings.topP}
                  onChange={(e) => handleSettingChange('topP', parseFloat(e.target.value))}
                  className="setting-slider"
                />
                <div className="slider-labels">
                  <span>Узкий (0.1)</span>
                  <span>Широкий (1.0)</span>
                </div>
              </div>

              {/* Top K */}
              <div className="setting-item">
                <div className="setting-label">
                  <span className="label-text">Top K</span>
                  <span className="label-value">{settings.topK}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="100"
                  step="1"
                  value={settings.topK}
                  onChange={(e) => handleSettingChange('topK', parseInt(e.target.value))}
                  className="setting-slider"
                />
                <div className="slider-labels">
                  <span>Мало (1)</span>
                  <span>Много (100)</span>
                </div>
              </div>

              {/* Repeat Penalty */}
              <div className="setting-item">
                <div className="setting-label">
                  <span className="label-text">Штраф за повторы</span>
                  <span className="label-value">{settings.repeatPenalty.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="2"
                  step="0.05"
                  value={settings.repeatPenalty}
                  onChange={(e) => handleSettingChange('repeatPenalty', parseFloat(e.target.value))}
                  className="setting-slider"
                />
                <div className="slider-labels">
                  <span>Без штрафа (1.0)</span>
                  <span>Сильный (2.0)</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="settings-footer">
          <button className="reset-btn" onClick={resetToDefaults}>
            Сбросить
          </button>
          <div className="footer-info">
            <span className="info-text">Автосохранение</span>
          </div>
          <button className="done-btn" onClick={onClose}>
            Готово
          </button>
        </div>
      </div>
    </div>
  );
};

export default LMStudioSettingsPanel;
