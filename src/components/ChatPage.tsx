import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ModelSelector from './ModelSelector';
import ChatSessionList from './ChatSessionList';
import LoadingIndicator from './LoadingIndicator';
import UserProfile from './UserProfile';
import AIProviderSettings, { AIProvider } from './AIProviderSettings';
import { Message, ModelType, ChatSession, MatchData, TriggerResponse } from '../types/chat';
import { 
  getAvailableModels, 
  testConnection,
  getCurrentProvider,
  setCurrentProvider as setProviderInStorage 
} from '../services/aiProviderApi';
import './ChatPage.css';

interface ChatPageProps {
  isAuthenticated: boolean;
  currentUser: {id: string, username: string, email: string, full_name?: string} | null;
  messages: Message[];
  isLoading: boolean;
  model: ModelType;
  sessions: ChatSession[];
  activeSessionId: string | null;
  showSessions: boolean;
  models: {id: string, name: string}[];
  connectionStatus: 'connected' | 'disconnected' | 'checking';
  chatHistoryRef: React.RefObject<HTMLDivElement | null>;
  loadChatHistory: () => Promise<void>;
  setActiveSessionId: (id: string | null) => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setModel: React.Dispatch<React.SetStateAction<ModelType>>;
  sendMessage: (content: string) => Promise<void>;
  onMatchAnalysis: (matchData: MatchData, response: TriggerResponse) => Promise<void>;
  createNewSession: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, newTitle: string) => Promise<void>;
  handleLogout: () => void;
  handleExportSessions: () => void;
  handleImportSessions: (sessions: ChatSession[]) => Promise<void>;
  setModels: React.Dispatch<React.SetStateAction<{id: string, name: string}[]>>;
  setConnectionStatus: React.Dispatch<React.SetStateAction<'connected' | 'disconnected' | 'checking'>>;
  setShowSessions: React.Dispatch<React.SetStateAction<boolean>>;
}

const ChatPage: React.FC<ChatPageProps> = ({
  isAuthenticated,
  currentUser,
  messages,
  isLoading,
  model,
  sessions,
  activeSessionId,
  showSessions,
  models,
  connectionStatus,
  chatHistoryRef,
  loadChatHistory,
  setActiveSessionId,
  setMessages,
  setModel,
  sendMessage,
  onMatchAnalysis,
  createNewSession,
  selectSession,
  deleteSession,
  renameSession,
  handleLogout,
  handleExportSessions,
  handleImportSessions,
  setModels,
  setConnectionStatus,
  setShowSessions
}) => {
  const [showProviderSettings, setShowProviderSettings] = useState(false);
  const [currentProvider, setCurrentProvider] = useState<AIProvider>(getCurrentProvider);

  // Обновляем провайдера и перезагружаем модели
  const handleProviderChange = async (provider: AIProvider) => {
    setCurrentProvider(provider);
    setProviderInStorage(provider);
    await refreshModelsForProvider();
  };

  const refreshModelsForProvider = async () => {
    setConnectionStatus('checking');
    try {
      const isConnected = await testConnection();
      if (isConnected) {
        const freshModels = await getAvailableModels();
        setModels(freshModels);
        setConnectionStatus('connected');
        
        if (freshModels.length > 0) {
          // Если текущая модель не в списке, выбираем первую
          if (!freshModels.some(m => m.id === model)) {
            setModel(freshModels[0].id);
          }
        } else {
          const providerName = getCurrentProvider() === 'ollama' ? 'Ollama' : 'LM Studio';
          alert(`Модели не найдены в ${providerName}. Пожалуйста, загрузите модели.`);
        }
      } else {
        setConnectionStatus('disconnected');
        setModels([]);
      }
    } catch (error) {
      console.error('Error refreshing models:', error);
      setConnectionStatus('disconnected');
      setModels([]);
    }
  };

  return (
    <div className="chat-page">
      <header className="chat-header">
        <div className="brand">
          <h1>Чат с ИИ</h1>
          {connectionStatus === 'connected' ? (
            <span className="status connected">
              Подключено к {currentProvider === 'ollama' ? 'Ollama' : 'LM Studio'} ({models.length} {models.length === 1 ? 'модель' : models.length < 5 ? 'модели' : 'моделей'} доступно)
            </span>
          ) : connectionStatus === 'disconnected' ? (
            <span className="status disconnected">{currentProvider === 'ollama' ? 'Ollama' : 'LM Studio'} not available</span>
          ) : (
            <span className="status checking">Checking connection...</span>
          )}
        </div>
        
        <div className="actions">
          <button 
            onClick={() => setShowProviderSettings(true)} 
            className="settings-button"
            title="Настройки AI провайдера"
          >
            <i className="bi bi-gear"></i>
          </button>
          <button onClick={() => setShowSessions(!showSessions)} className="session-button">
            {showSessions ? 'Скрыть сессии' : 'Показать сессии'}
          </button>
          <button onClick={createNewSession} className="new-chat-button">
            Новый чат
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
      
      <AIProviderSettings
        isOpen={showProviderSettings}
        onClose={() => setShowProviderSettings(false)}
        currentProvider={currentProvider}
        onProviderChange={handleProviderChange}
        onRefreshModels={refreshModelsForProvider}
      />
      
      <div className="chat-content-wrapper">
        {showSessions && (
          <aside className="chat-sidebar">
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
        
        <main className="chat-container">
          <div className="model-selector-container">
            <ModelSelector 
              models={models}
              selectedModel={model} 
              onSelectModel={(newModel) => {
                console.log('Пользователь выбрал модель:', newModel);
                setModel(newModel);
              }}
              disabled={connectionStatus !== 'connected'}
              onRefreshModels={refreshModelsForProvider}
            />
          </div>
          
          <div className="chat-history" ref={chatHistoryRef}>
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isLoading && <LoadingIndicator model={model} />}
            {messages.length === 0 && (
              <div className="empty-chat">
                <h2>Start a new conversation</h2>
                <p>Send a message to begin chatting with the AI.</p>
              </div>
            )}
          </div>
          
          <ChatInput 
            onSendMessage={sendMessage}
            onMatchAnalysis={onMatchAnalysis}
            isLoading={isLoading}
            disabled={connectionStatus !== 'connected'}
            selectedModel={model}
          />
        </main>
      </div>
    </div>
  );
};

export default ChatPage;
