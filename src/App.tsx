import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import './App.css';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ModelSelector from './components/ModelSelector';
import { Message, ModelType } from './types/chat';
import { sendMessage, getAvailableModels, testConnection } from './services/ollamaApi';

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [model, setModel] = useState<ModelType>('phi3:3b'); // Default to phi3:3b as an example
  const [models, setModels] = useState<{id: string, name: string}[]>([
    { id: 'phi3:3b', name: 'Phi-3 (3B)' },
    { id: 'tinyllama', name: 'TinyLlama' },
    { id: 'gemma:2b', name: 'Gemma (2B)' }
  ]);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');
  const chatHistoryRef = useRef<HTMLDivElement>(null);

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
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || isLoading || connectionStatus !== 'connected') return;

    const userMessage: Message = {
      id: uuidv4(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await sendMessage(model, [...messages, userMessage]);
      
      const assistantMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Failed to get response from Ollama:', error);
      
      const errorMessage: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: 'Error connecting to local Ollama instance. Please check that Ollama is running in your terminal.',
        timestamp: new Date()
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
          <ModelSelector 
            selectedModel={model} 
            onSelectModel={setModel} 
            models={models}
            disabled={connectionStatus !== 'connected'} 
          />
          <div className="model-info">
            <span>Local model running on <code>localhost:11434</code></span>
          </div>
        </div>
      </header>

      <div className="chat-container">
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
            <div className="loading-indicator">
              <p>Ollama is thinking... {isLoading && model.includes('sport') ? 
      "(New models may take time to load on first use)" : ""}</p>
              <div className="loading-spinner"></div>
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
          <div className="chat-tips">
            <span>Developer Tools:</span>
            <button 
              className="dev-button"
              onClick={() => handleSendMessage("Generate a React component for a file upload form")}
              disabled={connectionStatus !== 'connected' || isLoading}
            >
              React Component
            </button>
            <button 
              className="dev-button"
              onClick={() => handleSendMessage("Explain how to optimize a Node.js service")}
              disabled={connectionStatus !== 'connected' || isLoading}
            >
              Node.js Tips
            </button>
          </div>
          
          <button 
            className="clear-button" 
            onClick={handleClearHistory}
            disabled={messages.length === 0 || isLoading}
          >
            Clear History
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
