import React, { useState, useEffect } from 'react';
import { OllamaModel } from '../types/chat';
import { backendOllamaAPI } from '../services/backendOllamaApi';
import './ModelSelector.css';

const ModelSelectorExample: React.FC = () => {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<boolean | null>(null);

  const loadModels = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Сначала проверяем соединение с Ollama через бэкенд
      const isConnected = await backendOllamaAPI.testConnection();
      setConnectionStatus(isConnected);
      
      if (!isConnected) {
        setError("Не удалось подключиться к Ollama API через бэкенд");
        setLoading(false);
        return;
      }
      
      // Получаем доступные модели
      const availableModels = await backendOllamaAPI.getAvailableModels();
      setModels(availableModels);
      
      // Устанавливаем первую модель как выбранную по умолчанию, если есть доступные модели
      if (availableModels.length > 0 && !selectedModel) {
        setSelectedModel(availableModels[0].id);
      }
    } catch (err) {
      console.error("Error loading models:", err);
      setError("Ошибка при загрузке списка моделей");
    } finally {
      setLoading(false);
    }
  };

  // Загружаем модели при первой загрузке компонента
  useEffect(() => {
    loadModels();
  }, []);

  // Функция для отправки тестового сообщения выбранной модели
  const sendTestMessage = async () => {
    if (!selectedModel) {
      setError("Пожалуйста, выберите модель");
      return;
    }
    
    try {
      setLoading(true);
      
      // Проверяем доступность модели
      const isAvailable = await backendOllamaAPI.isModelAvailable(selectedModel);
      if (!isAvailable) {
        setError(`Модель ${selectedModel} недоступна. Возможно, её нужно загрузить.`);
        setLoading(false);
        return;
      }
      
      // Отправляем тестовое сообщение
      const response = await backendOllamaAPI.sendMessage(
        selectedModel, 
        [
          { id: '1', role: 'assistant', content: 'You are a helpful assistant.', timestamp: new Date() },
          { id: '2', role: 'user', content: 'Say hello and tell me your name', timestamp: new Date() }
        ]
      );
      
      // Показываем ответ
      alert(`Ответ от модели ${selectedModel}:\n\n${response}`);
      
    } catch (err) {
      console.error("Error sending test message:", err);
      setError(`Ошибка при отправке тестового сообщения: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="model-selector-example">
      <h2>Пример использования Ollama API через бэкенд</h2>
      
      {/* Статус подключения */}
      <div className="connection-status">
        <strong>Статус подключения к Ollama:</strong> 
        {connectionStatus === null ? (
          'Проверка...'
        ) : connectionStatus ? (
          <span className="status-connected">Подключено</span>
        ) : (
          <span className="status-disconnected">Не подключено</span>
        )}
      </div>
      
      {/* Селектор моделей */}
      <div className="model-selector">
        <label htmlFor="model-select">Выберите модель:</label>
        <div className="select-wrapper">
          <select 
            id="model-select" 
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            disabled={loading || models.length === 0}
          >
            {models.length > 0 ? (
              models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))
            ) : (
              <option value="">Нет доступных моделей</option>
            )}
          </select>
          
          <button 
            className="refresh-button" 
            onClick={loadModels} 
            disabled={loading}
          >
            {loading ? 'Загрузка...' : 'Обновить'}
          </button>
        </div>
      </div>
      
      {/* Кнопка тестового сообщения */}
      <div className="test-message-section">
        <button 
          className="test-button"
          onClick={sendTestMessage}
          disabled={loading || !selectedModel}
        >
          Отправить тестовое сообщение
        </button>
      </div>
      
      {/* Сообщение об ошибке */}
      {error && (
        <div className="error-message">
          {error}
        </div>
      )}
      
    </div>
  );
};

export default ModelSelectorExample;
