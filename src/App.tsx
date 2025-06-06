import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import './App.css';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ModelSelector from './components/ModelSelector';
import ChatSessionList from './components/ChatSessionList';
import LoadingIndicator from './components/LoadingIndicator';
import ConnectionStatus from './components/ConnectionStatus';
import { Message, ModelType, ChatSession, FileAttachment } from './types/chat';
// Импортируем функции из нового сервиса, использующего бэкенд
import { sendMessage, getAvailableModels, testConnection } from './services/ollamaBackendApi';
import { exportSessionsToFile, importSessionsFromFile } from './services/storageService';
import Auth from './components/Auth';
import UserProfile from './components/UserProfile';
import { authAPI, chatAPI } from './services/backendApi';

function App() {
  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(authAPI.isAuthenticated());
  const [currentUser, setCurrentUser] = useState<{id: string, username: string, email: string, full_name?: string} | null>(null);
    // Current session state
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [model, setModel] = useState<ModelType>('phi3');
  
  // Session history state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [showSessions, setShowSessions] = useState<boolean>(false);
  // Изначально пустой список моделей, который будет заполнен из Ollama
  const [models, setModels] = useState<{id: string, name: string}[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const chatHistoryRef = useRef<HTMLDivElement>(null);

  // Load user profile on authentication
  useEffect(() => {
    const loadUserProfile = async () => {
      if (isAuthenticated) {
        try {
          const userProfile = await authAPI.getProfile();
          setCurrentUser({
            id: userProfile.id,
            username: userProfile.username,
            email: userProfile.email,
            full_name: userProfile.full_name
          });
          loadChatHistory();
        } catch (error) {
          console.error('Failed to load user profile:', error);
          handleLogout();
        }
      }
    };
    
    loadUserProfile();
  }, [isAuthenticated]);

  // Load chat history from backend
  const loadChatHistory = async () => {
    if (!isAuthenticated) return;
    
    try {
      const backendSessions = await chatAPI.getSessions();
      
      if (backendSessions && backendSessions.length > 0) {
        // Convert backend format to frontend format
        const convertedSessions: ChatSession[] = backendSessions.map((session: any) => ({
          id: session.id,
          title: session.title,
          messages: session.messages.map((msg: any) => ({
            id: msg.id || uuidv4(),
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.timestamp),
            attachments: msg.attachments || []
          })),
          model: session.model,
          createdAt: new Date(session.created_at),
          updatedAt: new Date(session.updated_at)
        }));
        
        setSessions(convertedSessions);
        
        // Set active session to the most recently updated one
        const mostRecentSession = convertedSessions.sort(
          (a, b) => b.updatedAt.getTime() - a.updatedAt.getTime()
        )[0];
        
        if (mostRecentSession) {
          setActiveSessionId(mostRecentSession.id);
          setMessages(mostRecentSession.messages);
          setModel(mostRecentSession.model);
        }
      } else {
        createNewSession();
      }
    } catch (error) {
      console.error('Failed to load chat history:', error);
    }
  };

  // Check Ollama connection
  useEffect(() => {    const checkConnection = async () => {
      setConnectionStatus('checking');
      const isConnected = await testConnection();
      
      if (isConnected) {
        try {
          // Загружаем доступные модели из локального Ollama
          const modelList = await getAvailableModels();
          
          if (modelList.length > 0) {
            console.log('Found models in Ollama:', modelList);
            setModels(modelList);
            
            // Пытаемся найти подходящую модель по умолчанию в следующем порядке предпочтения:
            // 1. Текущая выбранная модель (если она существует в списке)
            // 2. phi (модели Phi)
            // 3. llama (модели Llama)
            // 4. gemma (модели Gemma)
            // 5. Любая небольшая модель с "3b" или "tiny" в названии
            // 6. Первая доступная модель
            
            // Сначала проверим, существует ли текущая модель в списке
            const currentModelExists = modelList.some(m => m.id === model);
            
            if (currentModelExists) {
              // Оставляем текущую модель
              console.log('Current model exists in Ollama:', model);
            } else {
              // Ищем другие подходящие модели
              const phiModel = modelList.find(m => 
                m.id.toLowerCase().includes('phi')
              );
              
              const llamaModel = modelList.find(m => 
                m.id.toLowerCase().includes('llama')
              );
              
              const gemmaModel = modelList.find(m => 
                m.id.toLowerCase().includes('gemma')
              );
              
              const smallModel = modelList.find(m => 
                m.id.toLowerCase().includes('3b') || 
                m.id.toLowerCase().includes('tiny')
              );
              
              if (phiModel) {
                console.log('Selected Phi model:', phiModel.id);
                setModel(phiModel.id);
              } else if (llamaModel) {
                console.log('Selected Llama model:', llamaModel.id);
                setModel(llamaModel.id);
              } else if (gemmaModel) {
                console.log('Selected Gemma model:', gemmaModel.id);
                setModel(gemmaModel.id);
              } else if (smallModel) {
                console.log('Selected small model:', smallModel.id);
                setModel(smallModel.id);
              } else if (modelList.length > 0) {
                console.log('Selected first available model:', modelList[0].id);
                setModel(modelList[0].id);
              }
            }
            
            setConnectionStatus('connected');
          } else {
            console.warn("No models found in Ollama.");
            setConnectionStatus('disconnected');
          }
        } catch (error) {
          console.error("Failed to fetch models from Ollama:", error);
          setConnectionStatus('disconnected');
        }
      } else {
        setConnectionStatus('disconnected');
      }
    };
    
    checkConnection();
  }, []);

  // Update active session in backend whenever messages change
  useEffect(() => {
    if (!isAuthenticated || !activeSessionId || messages.length === 0) return;
    
    const updateSessionInBackend = async () => {
      try {
        const activeSession = sessions.find(s => s.id === activeSessionId);
        if (activeSession) {
          await chatAPI.updateSession(activeSessionId, activeSession.title, model);
          
          // Update messages for this session
          await chatAPI.updateSessionMessages(activeSessionId, messages);
        }
      } catch (error) {
        console.error('Error updating session in backend:', error);
      }
    };
    
    // Use debounce to prevent too many API calls
    const updateTimer = setTimeout(updateSessionInBackend, 1000);
    
    return () => clearTimeout(updateTimer);
  }, [messages, activeSessionId, model, isAuthenticated]);

  // Update active session in local state
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

  // Create new session
  const createNewSession = async () => {
    if (!isAuthenticated) return;
    
    try {
      const newTitle = `Chat ${sessions.length + 1}`;
      const response = await chatAPI.createSession(newTitle, model);
      
      const newSession: ChatSession = {
        id: response.id,
        title: newTitle,
        messages: [],
        model: model,
        createdAt: new Date(response.created_at),
        updatedAt: new Date(response.updated_at)
      };
      
      setSessions(prev => [...prev, newSession]);
      setActiveSessionId(newSession.id);
      setMessages([]);
      setShowSessions(false);
    } catch (error) {
      console.error('Failed to create new session:', error);
    }
  };

  // Select existing session
  const selectSession = async (sessionId: string) => {
    try {
      const session = sessions.find(s => s.id === sessionId);
      
      if (session) {
        // If we already have the session data locally
        setActiveSessionId(sessionId);
        setMessages(session.messages);
        setModel(session.model);
        setShowSessions(false);
      } else {
        // Fetch session data from backend
        const sessionData = await chatAPI.getSessionById(sessionId);
        
        const convertedMessages = sessionData.messages.map((msg: any) => ({
          id: msg.id || uuidv4(),
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          attachments: msg.attachments || []
        }));
        
        setActiveSessionId(sessionId);
        setMessages(convertedMessages);
        setModel(sessionData.model);
        setShowSessions(false);
      }
    } catch (error) {
      console.error('Error selecting session:', error);
    }
  };

  // Delete session
  const deleteSession = async (sessionId: string) => {
    try {
      await chatAPI.deleteSession(sessionId);
      
      setSessions(prev => prev.filter(s => s.id !== sessionId));
      
      // If deleting active session, select another one or create new
      if (sessionId === activeSessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId);
        if (remainingSessions.length > 0) {
          const lastSession = remainingSessions[remainingSessions.length - 1];
          selectSession(lastSession.id);
        } else {
          createNewSession();
        }
      }
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  // Rename session
  const renameSession = async (sessionId: string, newTitle: string) => {
    try {
      await chatAPI.updateSession(sessionId, newTitle);
      
      setSessions(prevSessions => {
        return prevSessions.map(session => {
          if (session.id === sessionId) {
            return { ...session, title: newTitle };
          }
          return session;
        });
      });
    } catch (error) {
      console.error('Failed to rename session:', error);
    }
  };  // Handle message submission
  const handleSubmit = async (content: string, attachments: FileAttachment[] = []) => {
    if (!content.trim() && attachments.length === 0) return;
    
    // Create session if none active
    if (!activeSessionId) {
      await createNewSession();
    }
    
    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content,
      timestamp: new Date(),
      attachments: attachments.length > 0 ? attachments : undefined
    };
    
    setMessages(messages => [...messages, userMessage]);
    setIsLoading(true);
    
    try {
      // Call Ollama API through backend
      const response = await sendMessage(model, [...messages, userMessage]);
      
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response,
        timestamp: new Date()
      };
      
      setMessages(messages => [...messages, assistantMessage]);
      
      // Generate title for new sessions based on first message
      if (sessions.find(s => s.id === activeSessionId)?.messages.length === 0) {
        const generatedTitle = content.length > 30 
          ? content.substring(0, 30) + '...'
          : content;
        renameSession(activeSessionId!, generatedTitle);
      }
    } catch (error: any) {
      console.error('Error sending message:', error);
      let errorContent = `Error: ${error.message || 'Failed to get response'}`;
      
      // Add helpful instructions if the model was not found
      if (error.message && error.message.includes('not found')) {
        errorContent += `\n\nPlease make sure the model "${model}" is installed on your Ollama instance.\n\nYou can install it by running this command in your terminal:\n\nollama pull ${model}\n\nAfter installation is complete, click the refresh button (↻) next to the model selector to update the available models list or try sending your message again.\n\nAvailable models: ${models.map(m => m.id).join(', ')}`;
      }
      
      // Обработка ошибок авторизации
      if (error.message && error.message.includes('Unauthorized')) {
        errorContent += `\n\nYou have been logged out. Please login again.`;
        setTimeout(() => {
          handleLogout();
        }, 2000);
      }
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: errorContent,
        timestamp: new Date(),
        error: true
      };
      
      setMessages(messages => [...messages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle successful authentication
  const handleAuthSuccess = () => {
    setIsAuthenticated(true);
  };

  // Handle logout
  const handleLogout = () => {
    authAPI.logout();
    setIsAuthenticated(false);
    setCurrentUser(null);
    setSessions([]);
    setMessages([]);
    setActiveSessionId(null);
  };

  // Export chat sessions to file
  const handleExportSessions = () => {
    exportSessionsToFile(sessions);
  };

  // Import chat sessions from file
  const handleImportSessions = async (importedSessions: ChatSession[]) => {
    try {
      // For each imported session, create in backend
      const backendSessions = await Promise.all(
        importedSessions.map(async session => {
          try {
            const created = await chatAPI.createSession(session.title, session.model);
            
            // Update messages for this session
            if (session.messages.length > 0) {
              await chatAPI.updateSessionMessages(created.id, session.messages);
            }
            
            return {
              ...session,
              id: created.id,
              createdAt: new Date(created.created_at),
              updatedAt: new Date(created.updated_at)
            };
          } catch (error) {
            console.error('Failed to import session:', error);
            return null;
          }
        })
      );
      
      // Filter out failed imports
      const validSessions = backendSessions.filter(s => s !== null) as ChatSession[];
      
      // Update local state with new sessions
      setSessions(prev => [...prev, ...validSessions]);
      
      // Set active session to first imported one
      if (validSessions.length > 0) {
        setActiveSessionId(validSessions[0].id);
        setMessages(validSessions[0].messages);
        setModel(validSessions[0].model);
      }
    } catch (error) {
      console.error('Failed to import sessions:', error);
    }
  };

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);
  // If not authenticated, show login/register form
  if (!isAuthenticated) {
    return (
      <div className="App">
        <Auth onAuthSuccess={handleAuthSuccess} />
        <div style={{ maxWidth: '500px', margin: '20px auto' }}>
          <ConnectionStatus backendUrl="http://localhost:8000" />
        </div>
      </div>
    );
  }

  return (
    <div className="App">      <header className="App-header">
        <div className="brand">
          <h1>OllamaChat</h1>
          {connectionStatus === 'connected' ? (
            <span className="status connected">
              Connected to Ollama ({models.length} {models.length === 1 ? 'model' : 'models'} available)
            </span>
          ) : connectionStatus === 'disconnected' ? (
            <span className="status disconnected">Ollama not available</span>
          ) : (
            <span className="status checking">Checking connection...</span>
          )}
        </div>
        
        <div className="actions">
          <button onClick={() => setShowSessions(!showSessions)} className="session-button">
            {showSessions ? 'Hide Sessions' : 'Show Sessions'}
          </button>
          
          <button onClick={createNewSession} className="new-chat-button">
            New Chat
          </button>
          
          <div className="user-menu">
            <UserProfile 
              username={currentUser?.username || ''}
              email={currentUser?.email}
              fullName={currentUser?.full_name}
              onLogout={handleLogout} 
              onExportSessions={handleExportSessions}
              onImportSessions={handleImportSessions}
            />
          </div>
        </div>
      </header>
      
      <div className="content-wrapper">
        {showSessions && (
          <aside className="sidebar">
            <ChatSessionList
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelectSession={selectSession}
              onCreateSession={createNewSession}
              onDeleteSession={deleteSession}
              onRenameSession={renameSession}
            />
          </aside>
        )}
        
        <main className="chat-container">          <div className="model-selector-container">
            <ModelSelector 
              models={models}
              selectedModel={model} 
              onSelectModel={(newModel) => setModel(newModel)}
              disabled={connectionStatus !== 'connected'}
              onRefreshModels={async () => {
                setConnectionStatus('checking');
                try {
                  const isConnected = await testConnection();
                  if (isConnected) {
                    const freshModels = await getAvailableModels();
                    setModels(freshModels);
                    setConnectionStatus('connected');
                    if (freshModels.length === 0) {
                      alert('No models found. Please run "ollama pull MODEL_NAME" to download models.');
                    } else {
                      // Check if current model exists in the new model list
                      const currentModelExists = freshModels.some(m => m.id === model);
                      if (!currentModelExists && freshModels.length > 0) {
                        setModel(freshModels[0].id);
                      }
                    }
                  } else {
                    setConnectionStatus('disconnected');
                  }
                } catch (error) {
                  console.error('Error refreshing models:', error);
                  setConnectionStatus('disconnected');
                }
              }}
            />
          </div>
          
          <div className="chat-history" ref={chatHistoryRef}>
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}            {isLoading && <LoadingIndicator model={model} />}
            {messages.length === 0 && (
              <div className="empty-chat">
                <h2>Start a new conversation</h2>
                <p>Send a message to begin chatting with the AI.</p>
              </div>
            )}
          </div>
          
          <ChatInput 
            onSendMessage={handleSubmit} 
            isLoading={isLoading}
            disabled={connectionStatus !== 'connected'}
          />
        </main>
      </div>
    </div>
  );
}

export default App;
