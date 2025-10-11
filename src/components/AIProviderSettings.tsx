import React, { useState, useEffect } from 'react';
import './AIProviderSettings.css';

export type AIProvider = 'ollama' | 'lmstudio';

interface AIProviderSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  currentProvider: AIProvider;
  onProviderChange: (provider: AIProvider) => void;
  onRefreshModels: () => void;
}

interface ProviderStatus {
  ollama: 'connected' | 'disconnected' | 'checking';
  lmstudio: 'connected' | 'disconnected' | 'checking';
}

interface ProviderModels {
  ollama: { id: string; name: string }[];
  lmstudio: { id: string; name: string }[];
}

const AIProviderSettings: React.FC<AIProviderSettingsProps> = ({
  isOpen,
  onClose,
  currentProvider,
  onProviderChange,
  onRefreshModels
}) => {
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>({
    ollama: 'checking',
    lmstudio: 'checking'
  });
  
  const [providerModels, setProviderModels] = useState<ProviderModels>({
    ollama: [],
    lmstudio: []
  });

  const [isChecking, setIsChecking] = useState(false);

  // Проверка статуса провайдеров при открытии
  useEffect(() => {
    if (isOpen) {
      checkAllProviders();
    }
  }, [isOpen]);

  const checkAllProviders = async () => {
    setIsChecking(true);
    await Promise.all([
      checkOllamaStatus(),
      checkLMStudioStatus()
    ]);
    setIsChecking(false);
  };

  const checkOllamaStatus = async () => {
    setProviderStatus(prev => ({ ...prev, ollama: 'checking' }));
    try {
      const response = await fetch('http://localhost:8000/api/v1/ollama/status');
      const data = await response.json();
      setProviderStatus(prev => ({ 
        ...prev, 
        ollama: data.status === 'connected' ? 'connected' : 'disconnected' 
      }));
      
      // Если подключено, получаем модели
      if (data.status === 'connected') {
        await fetchOllamaModels();
      }
    } catch (error) {
      console.error('Error checking Ollama status:', error);
      setProviderStatus(prev => ({ ...prev, ollama: 'disconnected' }));
    }
  };

  const checkLMStudioStatus = async () => {
    setProviderStatus(prev => ({ ...prev, lmstudio: 'checking' }));
    try {
      const response = await fetch('http://localhost:8000/api/v1/ollama/lmstudio/status');
      const data = await response.json();
      setProviderStatus(prev => ({ 
        ...prev, 
        lmstudio: data.status === 'connected' ? 'connected' : 'disconnected' 
      }));
      
      // Если подключено, получаем модели
      if (data.status === 'connected') {
        await fetchLMStudioModels();
      }
    } catch (error) {
      console.error('Error checking LM Studio status:', error);
      setProviderStatus(prev => ({ ...prev, lmstudio: 'disconnected' }));
    }
  };

  const fetchOllamaModels = async () => {
    try {
      const token = localStorage.getItem('ollamaChat_authToken');
      const response = await fetch('http://localhost:8000/api/v1/ollama/models', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const models = await response.json();
        setProviderModels(prev => ({ ...prev, ollama: models }));
      }
    } catch (error) {
      console.error('Error fetching Ollama models:', error);
    }
  };

  const fetchLMStudioModels = async () => {
    try {
      const token = localStorage.getItem('ollamaChat_authToken');
      const response = await fetch('http://localhost:8000/api/v1/ollama/lmstudio/models', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const models = await response.json();
        setProviderModels(prev => ({ ...prev, lmstudio: models }));
      }
    } catch (error) {
      console.error('Error fetching LM Studio models:', error);
    }
  };

  const handleProviderSelect = (provider: AIProvider) => {
    if (providerStatus[provider] === 'connected') {
      onProviderChange(provider);
      onRefreshModels();
      onClose();
    } else {
      alert(`${provider === 'ollama' ? 'Ollama' : 'LM Studio'} не подключен. Пожалуйста, запустите его и проверьте подключение.`);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="ai-provider-modal-overlay" onClick={onClose}>
      <div className="ai-provider-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Настройки AI Провайдера</h2>
          <button className="close-button" onClick={onClose}>✕</button>
        </div>

        <div className="modal-content">
          <div className="provider-info">
            <p>Выберите источник AI моделей для чата:</p>
          </div>

          {/* Ollama Provider */}
          <div className={`provider-card ${currentProvider === 'ollama' ? 'active' : ''}`}>
            <div className="provider-header">
              <div className="provider-title">
                <h3>Ollama</h3>
                <span className={`status-badge ${providerStatus.ollama}`}>
                  {providerStatus.ollama === 'connected' ? 'Подключено' : 
                   providerStatus.ollama === 'checking' ? 'Проверка...' : 
                   'Не подключено'}
                </span>
              </div>
              <button 
                className="check-button"
                onClick={checkOllamaStatus}
                disabled={isChecking}
              >
                Проверить
              </button>
            </div>
            
            {providerStatus.ollama === 'connected' && (
              <div className="provider-details">
                <p className="models-count">
                  Доступно моделей: {providerModels.ollama.length}
                </p>
                {providerModels.ollama.length > 0 && (
                  <div className="models-list">
                    {providerModels.ollama.slice(0, 5).map(model => (
                      <span key={model.id} className="model-badge">{model.name}</span>
                    ))}
                    {providerModels.ollama.length > 5 && (
                      <span className="model-badge">+{providerModels.ollama.length - 5} ещё</span>
                    )}
                  </div>
                )}
              </div>
            )}
            
            <button 
              className={`select-provider-button ${currentProvider === 'ollama' ? 'active' : ''}`}
              onClick={() => handleProviderSelect('ollama')}
              disabled={providerStatus.ollama !== 'connected'}
            >
              {currentProvider === 'ollama' ? 'Активно' : 'Выбрать Ollama'}
            </button>
          </div>

          {/* LM Studio Provider */}
          <div className={`provider-card ${currentProvider === 'lmstudio' ? 'active' : ''}`}>
            <div className="provider-header">
              <div className="provider-title">
                <h3>LM Studio</h3>
                <span className={`status-badge ${providerStatus.lmstudio}`}>
                  {providerStatus.lmstudio === 'connected' ? 'Подключено' : 
                   providerStatus.lmstudio === 'checking' ? 'Проверка...' : 
                   'Не подключено'}
                </span>
              </div>
              <button 
                className="check-button"
                onClick={checkLMStudioStatus}
                disabled={isChecking}
              >
                Проверить
              </button>
            </div>
            
            {providerStatus.lmstudio === 'connected' && (
              <div className="provider-details">
                <p className="models-count">
                  Доступно моделей: {providerModels.lmstudio.length}
                </p>
                {providerModels.lmstudio.length > 0 && (
                  <div className="models-list">
                    {providerModels.lmstudio.slice(0, 5).map(model => (
                      <span key={model.id} className="model-badge">{model.name}</span>
                    ))}
                    {providerModels.lmstudio.length > 5 && (
                      <span className="model-badge">+{providerModels.lmstudio.length - 5} ещё</span>
                    )}
                  </div>
                )}
              </div>
            )}
            
            <button 
              className={`select-provider-button ${currentProvider === 'lmstudio' ? 'active' : ''}`}
              onClick={() => handleProviderSelect('lmstudio')}
              disabled={providerStatus.lmstudio !== 'connected'}
            >
              {currentProvider === 'lmstudio' ? 'Активно' : 'Выбрать LM Studio'}
            </button>
          </div>

          <div className="help-section">
            <h4>Подсказки:</h4>
            <ul>
              <li><strong>Ollama:</strong> По умолчанию работает на порту 11434</li>
              <li><strong>LM Studio:</strong> Запустите локальный сервер на порту 1234 (Server tab → Start Server)</li>
              <li>Убедитесь, что выбранный провайдер запущен перед использованием</li>
              <li>В LM Studio загрузите модель перед запуском сервера</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIProviderSettings;
