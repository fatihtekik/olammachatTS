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
        console.log('Checking connection to backend...');
        const backendCheck = await fetch(`${backendUrl}/`);
        
        if (!backendCheck.ok) {
          setStatus('disconnected');
          setMessage(`Backend server is not responding: ${backendCheck.status} ${backendCheck.statusText}`);
          return;
        }
        
        // Проверяем соединение с Ollama через бэкенд
        console.log('Checking connection to Ollama...');
        const response = await fetch(`${backendUrl}/api/v1/ollama/status`, {
          headers: {'Content-Type': 'application/json'}
        });
        
        console.log('Backend status response:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Status data:', data);
          
          if (data.status === 'connected') {
            setStatus('connected');
            setMessage('Successfully connected to backend and Ollama');
            
            // Пробуем получить список моделей (без авторизации - просто для проверки)
            try {
              console.log('Checking available models...');
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
                  setMessage('Connected to Ollama, but no models found. Use "ollama pull MODEL_NAME" to download models.');
                } else {
                  setMessage(`Successfully connected to backend and Ollama. Found ${modelsList.length} models.`);
                }
              } else {
                console.log('Could not get models list (may require authentication)');
              }
            } catch (modelError) {
              console.error('Error checking models:', modelError);
            }
          } else {
            setStatus('disconnected');
            setMessage(`Backend is available but Ollama is disconnected: ${data.error || 'Unknown error. Make sure Ollama is running with "ollama serve" command.'}`);
          }
        } else {
          setStatus('disconnected');
          setMessage(`Backend API is not responding: ${response.status} ${response.statusText}`);
        }
      } catch (error) {
        setStatus('disconnected');
        setMessage(`Failed to connect to backend: ${error}`);
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
          Checking connection to backend...
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
