import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import './App.css';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ModelSelector from './components/ModelSelector';
import ChatSessionList from './components/ChatSessionList';
import { Message, ModelType, ChatSession, FileAttachment } from './types/chat';
import { sendMessage, getAvailableModels, testConnection } from './services/ollamaApi';
import { saveSessions, loadSessions, exportSessionsToFile, importSessionsFromFile } from './services/storageService';

// Ключ для localStorage
const STORAGE_KEY = 'ollamaChat';

function App() {
  // Состояние для текущей сессии
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [model, setModel] = useState<ModelType>('phi3:3b');
  
  // Состояние для истории сессий
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showSessions, setShowSessions] = useState<boolean>(false);
  
  const [models, setModels] = useState<{id: string, name: string}[]>([
    { id: 'phi3:3b', name: 'Phi-3 (3B)' },
    { id: 'tinyllama', name: 'TinyLlama' },
    { id: 'gemma:2b', name: 'Gemma (2B)' }
  ]);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  // Загрузка истории чата при первом рендере
  useEffect(() => {
    const loadChatHistory = async () => {
      try {
        const { sessions: loadedSessions, activeSessionId: loadedActiveSessionId } = await loadSessions();
        
        if (loadedSessions && loadedSessions.length > 0) {
          setSessions(loadedSessions);
          
          // Установка активной сессии
          if (loadedActiveSessionId && loadedSessions.find(s => s.id === loadedActiveSessionId)) {
            setActiveSessionId(loadedActiveSessionId);
            const activeSession = loadedSessions.find(s => s.id === loadedActiveSessionId);
            if (activeSession) {
              setMessages(activeSession.messages);
              setModel(activeSession.model);
            }
          } else {
            // Если activeSessionId невалидный, используем последнюю сессию
            const lastSession = loadedSessions[loadedSessions.length - 1];
            setActiveSessionId(lastSession.id);
            setMessages(lastSession.messages);
            setModel(lastSession.model);
          }
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
      }
    };
    
    loadChatHistory();
    
    const checkConnection = async () => {
      setConnectionStatus('checking');
      const isConnected = await testConnection();
      setConnectionStatus(isConnected ? 'connected' : 'disconnected');
      
      if (isConnected) {
        // Load available models from local Ollama
        const modelList = await getAvailableModels();
        if (modelList.length > 0) {
          setModels(modelList);
          
          // Try to find a 3B model to set as default
          const smallModel = modelList.find(m => 
            m.id.toLowerCase().includes('3b') || 
            m.id.toLowerCase().includes('phi') ||
            m.id.toLowerCase().includes('tiny')
          );
          
          if (smallModel) {
            setModel(smallModel.id);
          } else if (modelList.length > 0) {
            setModel(modelList[0].id);
          }
        }
      }
    };
    
    checkConnection();
    
    // Предлагаем сделать резервную копию, если накопилось много чатов
    const askForBackup = () => {
      if (sessions.length > 5) {
        const lastBackup = localStorage.getItem('ollamaChat_lastBackup');
        const now = new Date();
        
        // Если прошло более 7 дней с последнего бэкапа или его не было
        if (!lastBackup || (now.getTime() - new Date(lastBackup).getTime()) > 7 * 24 * 60 * 60 * 1000) {
          if (window.confirm('Рекомендуется создать резервную копию ваших чатов. Сделать это сейчас?')) {
            exportSessionsToFile(sessions);
            localStorage.setItem('ollamaChat_lastBackup', now.toISOString());
          } else {
            // Напомним через неделю
            localStorage.setItem('ollamaChat_lastBackup', now.toISOString());
          }
        }
      }
    };
    
    // Запускаем проверку бэкапа через 5 секунд после загрузки
    const backupTimer = setTimeout(askForBackup, 5000);
    
    return () => clearTimeout(backupTimer);
  }, []);

  // Сохранение истории чатов при изменении
  useEffect(() => {
    // Пропускаем первичную инициализацию
    if (sessions.length === 0 && !activeSessionId) return;
    
    // Обновляем сессию только если есть activeSessionId
    if (activeSessionId && messages.length > 0) {
      updateActiveSession();
    }
    
    // Сохранение с небольшой задержкой для предотвращения слишком частых операций
    const saveTimer = setTimeout(() => {
      saveSessions(sessions, activeSessionId)
        .catch(error => console.error('Error saving sessions:', error));
    }, 500);
    
    return () => clearTimeout(saveTimer);
  }, [messages, sessions, activeSessionId, model]);

  // Обновление активной сессии при изменении сообщений
  const updateActiveSession = () => {
    if (!activeSessionId) return;
    
    setSessions(prevSessions => {
      return prevSessions.map(session => {
        if (session.id === activeSessionId) {
          return {
            ...session,
            messages: messages,
            model: model,
            updatedAt: new Date()
          };
        }
        return session;
      });
    });
  };

  // Создание новой сессии чата
  const createNewSession = () => {
    const newSessionId = uuidv4();
    const newSession: ChatSession = {
      id: newSessionId,
      title: `Чат ${sessions.length + 1}`,
      messages: [],
      model: model,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    setSessions([...sessions, newSession]);
    setActiveSessionId(newSessionId);
    setMessages([]);
    setShowSessions(false);
  };

  // Выбор существующей сессии
  const selectSession = (sessionId: string) => {
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      setActiveSessionId(sessionId);
      setMessages(session.messages);
      setModel(session.model);
      setShowSessions(false);
    }
  };

  // Удаление сессии
  const deleteSession = (sessionId: string) => {
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    
    // Если удаляем активную сессию, выберем другую или создадим новую
    if (sessionId === activeSessionId) {
      const remainingSessions = sessions.filter(s => s.id !== sessionId);
      if (remainingSessions.length > 0) {
        const lastSession = remainingSessions[remainingSessions.length - 1];
        setActiveSessionId(lastSession.id);
        setMessages(lastSession.messages);
        setModel(lastSession.model);
      } else {
        createNewSession();
      }
    }
  };

  const chatHistoryScrollToBottom = () => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  };

  // Check connection to Ollama and load models
  useEffect(() => {
    const checkConnection = async () => {
      setConnectionStatus('checking');
      const isConnected = await testConnection();
      setConnectionStatus(isConnected ? 'connected' : 'disconnected');
      
      if (isConnected) {
        // Load available models from local Ollama
        const modelList = await getAvailableModels();
        if (modelList.length > 0) {
          setModels(modelList);
          
          // Try to find a 3B model to set as default
          const smallModel = modelList.find(m => 
            m.id.toLowerCase().includes('3b') || 
            m.id.toLowerCase().includes('phi') ||
            m.id.toLowerCase().includes('tiny')
          );
          
          if (smallModel) {
            setModel(smallModel.id);
          } else if (modelList.length > 0) {
            setModel(modelList[0].id);
          }
        }
      }
    };
    
    checkConnection();

    // Load chat history from localStorage
    const savedMessages = localStorage.getItem('ollamaLocalChatHistory');
    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages).map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        setMessages(parsedMessages);
      } catch (error) {
        console.error('Failed to load chat history', error);
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('ollamaLocalChatHistory', JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    chatHistoryScrollToBottom();
  }, [messages]);

  // Обновим функцию handleSendMessage для поддержки вложений
  const handleSendMessage = async (content: string, attachments?: FileAttachment[]) => {
    // Не отправляем пустые сообщения без вложений
    if ((!content.trim() && (!attachments || attachments.length === 0)) || 
        isLoading || 
        connectionStatus !== 'connected') return;

    // Если нет активной сессии, создаем новую
    if (!activeSessionId || sessions.length === 0) {
      createNewSession();
    }

    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
      attachments
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Добавляем информацию о вложениях в контент сообщения для модели
      let enhancedContent = content;
      if (attachments && attachments.length > 0) {
        enhancedContent += "\n\n[Вложения: " + 
          attachments.map(a => `${a.name} (${a.type})`).join(", ") + "]";
      }

      const response = await sendMessage(model, [...messages, {
        ...userMessage,
        content: enhancedContent
      }]);
      
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      // Обновляем заголовок сессии, используя первое сообщение пользователя
      if (messages.length === 0) {
        const title = content.length > 30 
          ? content.substring(0, 30) + '...' 
          : content || 'Чат с вложениями';
          
        setSessions(prev => prev.map(session => {
          if (session.id === activeSessionId) {
            return { ...session, title };
          }
          return session;
        }));
      }
    } catch (error) {
      console.error('Failed to get response from Ollama:', error);
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'Error connecting to local Ollama instance. Please check that Ollama is running in your terminal.',
        timestamp: new Date(),
        error: true
      };

      setMessages(prev => [...prev, errorMessage]);
      
      // Check connection status again
      const isConnected = await testConnection();
      setConnectionStatus(isConnected ? 'connected' : 'disconnected');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear all chat history?')) {
      setMessages([]);
      localStorage.removeItem('ollamaLocalChatHistory');
    }
  };

  // Экспорт истории чата в JSON-файл
  const handleExportCurrentSession = () => {
    if (!activeSessionId || messages.length === 0) {
      alert('Нет активного чата для экспорта');
      return;
    }
    
    const session = sessions.find(s => s.id === activeSessionId);
    if (session) {
      exportSessionsToFile([session]);
    }
  };

  // Обработчик для экспорта всей истории чатов
  const handleExportAllSessions = () => {
    if (sessions.length === 0) {
      alert('Нет сохраненных чатов для экспорта');
      return;
    }
    
    exportSessionsToFile(sessions);
  };

  // Обработчик для импорта истории чатов
  const handleImportSessions = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    try {
      const importedSessions = await importSessionsFromFile(file);
      
      if (window.confirm(`Импортировать ${importedSessions.length} чатов? Текущие чаты будут объединены с импортированными.`)) {
        // Объединение с существующими сессиями, избегая дубликатов
        const existingIds = new Set(sessions.map(s => s.id));
        const newSessions = importedSessions.filter(s => !existingIds.has(s.id));
        
        setSessions(prev => [...prev, ...newSessions]);
        
        if (newSessions.length > 0 && window.confirm('Открыть первую импортированную сессию?')) {
          const firstNewSession = newSessions[0];
          setActiveSessionId(firstNewSession.id);
          setMessages(firstNewSession.messages);
          setModel(firstNewSession.model);
        }
      }
    } catch (error) {
      console.error('Error importing sessions:', error);
      alert('Не удалось импортировать чаты. Проверьте формат файла.');
    }
    
    // Сбросить input файла
    event.target.value = '';
  };

  const reconnectToOllama = async () => {
    setConnectionStatus('checking');
    const isConnected = await testConnection();
    setConnectionStatus(isConnected ? 'connected' : 'disconnected');
    
    if (isConnected) {
      // Reload models
      const modelList = await getAvailableModels();
      if (modelList.length > 0) {
        setModels(modelList);
      }
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-top">
          <h1>Ollama Local Chat</h1>
          <div className={`connection-status ${connectionStatus}`}>
            {connectionStatus === 'connected' && '✓ Connected to local Ollama'}
            {connectionStatus === 'disconnected' && (
              <>
                <span>⚠ Disconnected</span>
                <button className="reconnect-button" onClick={reconnectToOllama}>
                  Reconnect
                </button>
              </>
            )}
            {connectionStatus === 'checking' && 'Checking connection...'}
          </div>
        </div>
        
        <div className="header-controls">
          <div className="sessions-control">
            <button 
              className="toggle-sessions-button"
              onClick={() => setShowSessions(!showSessions)}
            >
              <i className={`bi ${showSessions ? 'bi-x-lg' : 'bi-clock-history'}`}></i>
              {showSessions ? 'Скрыть историю' : 'История чатов'}
            </button>
            
            <span className="active-session-name">
              {activeSessionId && sessions.find(s => s.id === activeSessionId)?.title}
            </span>
          </div>
          
          <ModelSelector 
            selectedModel={model} 
            onSelectModel={setModel} 
            models={models}
            disabled={connectionStatus !== 'connected'} 
          />
        </div>
      </header>

      <div className="chat-container">
        {showSessions && (
          <ChatSessionList 
            sessions={sessions}
            activeSessionId={activeSessionId}
            onSelectSession={selectSession}
            onCreateSession={createNewSession}
            onDeleteSession={deleteSession}
          />
        )}
      
        <div className="chat-history" ref={chatHistoryRef}>
          {connectionStatus === 'disconnected' && (
            <div className="connection-error">
              <h3>Cannot connect to local Ollama</h3>
              <p>Please make sure Ollama is running in your terminal. You can start it with:</p>
              <pre>ollama serve</pre>
              <button className="reconnect-button" onClick={reconnectToOllama}>
                Try Again
              </button>
            </div>
          )}
        
          {connectionStatus !== 'disconnected' && messages.length === 0 && (
            <div className="empty-state">
              <p>No messages yet. Start a conversation with your local Ollama model!</p>
              <p className="small">Your chat history is saved in your browser and never leaves your computer.</p>
            </div>
          )}
          
          {messages.map(message => (
            <ChatMessage key={message.id} message={message} />
          ))}
          
          {isLoading && (
            <div className="typing-indicator">
              <div className="typing-dots">
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
                <div className="typing-dot"></div>
              </div>
              <div className="text-muted small mt-2">
                Ollama is thinking... {model.includes('sport') ? "(New models may take time to load on first use)" : ""}
              </div>
            </div>
          )}
        </div>

        <ChatInput 
          onSendMessage={handleSendMessage} 
          isLoading={isLoading} 
          disabled={connectionStatus !== 'connected'} 
          placeholder={connectionStatus !== 'connected' 
            ? "Connect to Ollama to start chatting..." 
            : "Message your local Ollama model..."}
        />
        
        <div className="chat-actions">
          <div className="chat-buttons">
            <button
              className="new-chat-button"
              onClick={createNewSession}
              disabled={isLoading}
            >
              <i className="bi bi-plus-circle"></i> Новый чат
            </button>
            
            <button
              className="history-button"
              onClick={() => setShowSessions(!showSessions)}
            >
              <i className="bi bi-clock-history"></i> {showSessions ? 'Скрыть историю' : 'Показать историю'}
            </button>
            
            <div className="dropdown">
              <button className="backup-button dropdown-toggle" type="button" id="backupDropdown">
                <i className="bi bi-cloud-arrow-up"></i> Резервное копирование
              </button>
              <div className="dropdown-menu" aria-labelledby="backupDropdown">
                <input
                  type="file"
                  id="import-chat"
                  accept=".json"
                  onChange={handleImportSessions}
                  style={{ display: 'none' }}
                />
                <button 
                  className="dropdown-item"
                  onClick={() => document.getElementById('import-chat')?.click()}
                >
                  <i className="bi bi-upload"></i> Импортировать чаты
                </button>
                <button 
                  className="dropdown-item"
                  onClick={handleExportCurrentSession}
                  disabled={!activeSessionId || messages.length === 0}
                >
                  <i className="bi bi-download"></i> Экспортировать текущий чат
                </button>
                <button 
                  className="dropdown-item"
                  onClick={handleExportAllSessions}
                  disabled={sessions.length === 0}
                >
                  <i className="bi bi-archive"></i> Экспортировать все чаты
                </button>
              </div>
            </div>
          </div>
          
          {activeSessionId && (
            <button 
              className="clear-button" 
              onClick={() => {
                if (window.confirm('Are you sure you want to clear the current chat?')) {
                  setMessages([]);
                }
              }}
              disabled={messages.length === 0 || isLoading}
            >
              <i className="bi bi-trash"></i> Clear Chat
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
