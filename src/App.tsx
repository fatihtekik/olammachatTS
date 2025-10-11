import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import Sidebar from './components/Sidebar';
import AnalysisPage from './components/AnalysisPage';
import ChatPage from './components/ChatPage';
import ExcelUploadPage from './components/ExcelUploadPage';
import { Message, ModelType, ChatSession, FileAttachment, MatchData, TriggerResponse } from './types/chat';
import { sendMessage, sendMessageStreaming } from './services/ollamaBackendApi';
import { getAvailableModels, testConnection } from './services/aiProviderApi';
import { exportSessionsToFile, importSessionsFromFile } from './services/storageService';
import Auth from './components/Auth';
import { authAPI, chatAPI } from './services/backendApi';

function App() {
  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(authAPI.isAuthenticated());  const [currentUser, setCurrentUser] = useState<{id: string, username: string, email: string, full_name?: string} | null>(null);
  // Current session state
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
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
  useEffect(() => {
    const checkConnection = async () => {
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
                console.log('🎯 Selected Phi model:', phiModel.id);
                setModel(phiModel.id);
              } else if (llamaModel) {
                console.log('🎯 Selected Llama model:', llamaModel.id);
                setModel(llamaModel.id);
              } else if (gemmaModel) {
                console.log('🎯 Selected Gemma model:', gemmaModel.id);
                setModel(gemmaModel.id);
              } else if (smallModel) {
                console.log('🎯 Selected small model:', smallModel.id);
                setModel(smallModel.id);
              } else if (modelList.length > 0) {
                console.log('🎯 Selected first available model:', modelList[0].id);
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
      });    } catch (error) {
      console.error('Failed to rename session:', error);
    }
  };  // Handle match analysis results
  const handleMatchAnalysis = async (matchData: MatchData, response: TriggerResponse) => {
    // Create session if none active
    if (!activeSessionId) {
      await createNewSession();
    }
    
    // Format match data for display
    const matchInfo = `Анализ матча: ${matchData.игрок_1} (${matchData.рейтинг_1}) vs ${matchData.игрок_2} (${matchData.рейтинг_2})
Счёт: ${matchData.счёт}
Этап: ${matchData.этап}
Турнир: ${matchData.турнир}
Лига: ${matchData.лига}`;    // Extract ONLY analysis text from JSON response, no JSON structure
    let analysisText = response.ollama_response;
    console.log('=== DETAILED DEBUG ===');
    console.log('1. Original ollama_response:', response.ollama_response);
    console.log('2. Type of ollama_response:', typeof response.ollama_response);
    console.log('3. Length of ollama_response:', response.ollama_response.length);
    
    try {
      // Try to parse the response as JSON
      const parsedResponse = JSON.parse(response.ollama_response);
      console.log('4. Successfully parsed as JSON:', parsedResponse);
      console.log('5. Keys in parsed object:', Object.keys(parsedResponse));
      console.log('6. parsedResponse.analysis exists?', 'analysis' in parsedResponse);
      console.log('7. parsedResponse.analysis value:', parsedResponse.analysis);
      
      if (parsedResponse.analysis) {
        analysisText = parsedResponse.analysis; // Только текст анализа
        console.log('8. Using analysis field, length:', analysisText.length);
      } else {
        console.log('8. No analysis field found in parsed JSON');
      }
    } catch (error) {
      console.log('4. JSON parsing failed:', error);
      console.log('5. Trying to extract analysis from broken JSON...');
      
      // Попытка извлечь анализ из поврежденного JSON с помощью регулярного выражения
      const analysisMatch = response.ollama_response.match(/"analysis"\s*:\s*"([^"]*(?:\\.[^"]*)*)"?/);
      if (analysisMatch && analysisMatch[1]) {
        analysisText = analysisMatch[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').replace(/\\\\/g, '\\');
        console.log('6. Extracted analysis via regex:', analysisText);
      } else {
        console.log('6. Could not extract analysis via regex, using original response');
        analysisText = response.ollama_response;
      }
    }
    
    console.log('9. Final analysisText:', analysisText);
    console.log('10. Final analysisText type:', typeof analysisText);
    console.log('=== END DEBUG ===');
    
    // Add match info + pure analysis text (no JSON structure)
    const analysisMessage: Message = {
      id: uuidv4(),
      role: 'assistant',
      content: `${matchInfo}\n\n${analysisText}`,
      timestamp: new Date()
    };
    
    setMessages(messages => [...messages, analysisMessage]);
    
    // Generate title for new sessions based on match data
    if (sessions.find(s => s.id === activeSessionId)?.messages.length === 0) {
      const generatedTitle = `Анализ: ${matchData.игрок_1} vs ${matchData.игрок_2}`;
      renameSession(activeSessionId!, generatedTitle);
    }
  };
    // Handle message submission
  const handleSubmit = async (content: string) => {
    if (!content.trim()) return;
    
    // Create session if none active
    if (!activeSessionId) {
      await createNewSession();
    }
    
    // Получаем текущий провайдер и настройку стриминга
    const currentProvider = (localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio') || 'ollama';
    const streamingEnabled = JSON.parse(localStorage.getItem('streamingEnabled') || 'true');
    
    // Add user message
    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content,
      timestamp: new Date(),
      provider: currentProvider,
      model: model
    };
    
    setMessages(messages => [...messages, userMessage]);
    setIsLoading(true);
    
    try {
      let responseContent = '';
      
      if (streamingEnabled) {
        // Включаем режим стриминга
        setIsStreaming(true);
        
        // Создаем пустое сообщение ассистента, которое будем заполнять
        const assistantMessageId = uuidv4();
        const assistantMessage: Message = {
          id: assistantMessageId,
          role: 'assistant',
          content: '',
          timestamp: new Date(),
          provider: currentProvider,
          model: model
        };
        
        setMessages(msgs => [...msgs, assistantMessage]);
        setIsLoading(false); // Убираем LoadingIndicator при стриминге
        
        // Вызываем API со стримингом
        await sendMessageStreaming(
          model,
          [...messages, userMessage],
          (chunk: string) => {
            responseContent += chunk;
            // Обновляем сообщение с новым контентом
            setMessages(msgs => 
              msgs.map(msg => 
                msg.id === assistantMessageId 
                  ? { ...msg, content: responseContent }
                  : msg
              )
            );
          },
          currentProvider
        );
        
        setIsStreaming(false);
      } else {
        // Обычный режим без стриминга
        responseContent = await sendMessage(model, [...messages, userMessage], currentProvider);
        
        const assistantMessage: Message = {
          id: uuidv4(),
          role: 'assistant',
          content: responseContent,
          timestamp: new Date(),
          provider: currentProvider,
          model: model
        };
        
        setMessages(messages => [...messages, assistantMessage]);
      }
      
      // Generate title for new sessions based on first message
      if (sessions.find(s => s.id === activeSessionId)?.messages.length === 0) {
        const generatedTitle = content.length > 30 
          ? content.substring(0, 30) + '...'
          : content;
        renameSession(activeSessionId!, generatedTitle);
      }
    } catch (error: any) {
      console.error('Error sending message:', error);
      const currentProvider = (localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio') || 'ollama';
      let errorContent = `Error: ${error.message || 'Failed to get response'}`;
      
      // Специальная обработка для ошибки 404 или not found
      if (error.message && (error.message.includes('404') || error.message.includes('not found'))) {
        const providerName = currentProvider === 'lmstudio' ? 'LM Studio' : 'Ollama';
        errorContent = `Модель "${model}" не загружена в память ${providerName}.\n\n`;
        
        if (currentProvider === 'lmstudio') {
          errorContent += `Пожалуйста:\n1. Откройте LM Studio\n2. Загрузите модель "${model}" в память (кнопка "Load model")\n3. Убедитесь, что локальный сервер запущен (Server tab → Start Server)\n4. Попробуйте снова`;
        } else {
          errorContent += `Пожалуйста:\n1. Установите модель командой: ollama pull ${model}\n2. Или выберите другую модель из списка: ${models.map(m => m.id).join(', ')}`;
        }
      }
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: errorContent,
        timestamp: new Date(),
        error: true,
        provider: currentProvider,
        model: model
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
      </div>
    );
  }

  return (
    <Router>
      <div className="app-container">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<AnalysisPage />} />
            <Route 
              path="/chat" 
              element={
                <ChatPage
                  isAuthenticated={isAuthenticated}
                  currentUser={currentUser}
                  messages={messages}
                  isLoading={isLoading}
                  isStreaming={isStreaming}
                  model={model}
                  sessions={sessions}
                  activeSessionId={activeSessionId}
                  showSessions={showSessions}
                  models={models}
                  connectionStatus={connectionStatus}
                  chatHistoryRef={chatHistoryRef}
                  loadChatHistory={loadChatHistory}
                  setActiveSessionId={setActiveSessionId}
                  setMessages={setMessages}
                  setModel={setModel}
                  sendMessage={handleSubmit}
                  onMatchAnalysis={handleMatchAnalysis}
                  createNewSession={createNewSession}
                  selectSession={selectSession}
                  deleteSession={deleteSession}
                  renameSession={renameSession}
                  handleLogout={handleLogout}
                  handleExportSessions={handleExportSessions}
                  handleImportSessions={handleImportSessions}
                  setModels={setModels}
                  setConnectionStatus={setConnectionStatus}
                  setShowSessions={setShowSessions}
                />
              } 
            />
            <Route path="/analysis" element={<ExcelUploadPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
