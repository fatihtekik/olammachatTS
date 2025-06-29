import React, { useState, useEffect } from 'react';

interface ConnectionStatusProps {
  backendUrl: string;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ backendUrl }) => {
  const [status, setStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');
  const [message, setMessage] = useState<string>('');
  const [models, setModels] = useState<{id: string, name: string}[]>([]);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        setStatus('checking');
          // Проверяем базовое соединение с бэкендом 
        console.log('Проверяем соединение с бэкендом...');
        const backendCheck = await fetch(`${backendUrl}/`);
        
        if (!backendCheck.ok) {
          setStatus('disconnected');
          setMessage(`Бэкенд сервер не отвечает: ${backendCheck.status} ${backendCheck.statusText}`);
          return;
        }
          // Проверяем соединение с Ollama через бэкенд
        console.log('Проверяем соединение с Ollama...');
        const response = await fetch(`${backendUrl}/api/v1/ollama/status`, {
          headers: {'Content-Type': 'application/json'}
        });
        
        console.log('Backend status response:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Status data:', data);
          
          if (data.status === 'connected') {
            setStatus('connected');
            setMessage('Успешно подключён к бэкенду и Ollama');
            
            // Пробуем получить список моделей (без авторизации - просто для проверки)
            try {
              console.log('Проверяем доступные модели...');
              const modelsResponse = await fetch(`${backendUrl}/api/v1/ollama/models`, {
                headers: {
                  'Content-Type': 'application/json',
                  // Добавляем временный заголовок для теста без авторизации
                  'X-CheckOnly': 'true'
                }
              });
              
              console.log('Models status:', modelsResponse.status);
              
              if (modelsResponse.ok) {
                const modelsList = await modelsResponse.json();
                console.log('Available models:', modelsList);
                setModels(modelsList);
                  if (modelsList.length === 0) {
                  setMessage('Подключён к Ollama, но модели не найдены. Используйте "ollama pull MODEL_NAME" для загрузки моделей.');
                } else {
                  setMessage(`Успешно подключён к бэкенду и Ollama. Найдено ${modelsList.length} моделей.`);
                }
              } else {
                console.log('Could not get models list (may require authentication)');
              }
            } catch (modelError) {
              console.error('Error checking models:', modelError);
            }
          } else {
            setStatus('disconnected');            setMessage(`Бэкенд доступен, но Ollama отключена: ${data.error || 'Неизвестная ошибка. Убедитесь, что Ollama запущена командой "ollama serve".'}`);
          }
        } else {
          setStatus('disconnected');
          setMessage(`API бэкенда не отвечает: ${response.status} ${response.statusText}`);
        }
      } catch (error) {
        setStatus('disconnected');
        setMessage(`Не удалось подключиться к бэкенду: ${error}`);
        console.error('Connection check error:', error);
      }
    };
    
    checkConnection();
  }, [backendUrl]);

  return (
    <div className="connection-status" style={{ padding: '10px', borderRadius: '4px', margin: '10px 0' }}>
      {status === 'checking' && (
        <div style={{ backgroundColor: '#f8f9fa', padding: '10px' }}>
          <span style={{ marginRight: '10px' }}>⏳</span>
          Проверяем соединение с бэкендом...
        </div>
      )}
      
      {status === 'connected' && (
        <div style={{ backgroundColor: '#d4edda', color: '#155724', padding: '10px' }}>
          <span style={{ marginRight: '10px' }}>✅</span>
          {message}
        </div>
      )}
      
      {status === 'disconnected' && (
        <div style={{ backgroundColor: '#f8d7da', color: '#721c24', padding: '10px' }}>
          <span style={{ marginRight: '10px' }}>❌</span>
          {message}
        </div>
      )}
    </div>
  );
};

export default ConnectionStatus;
