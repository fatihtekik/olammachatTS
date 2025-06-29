import React, { useState, useRef, useEffect } from 'react';
import { MatchData, TriggerResponse, ModelType } from '../types/chat';
import MatchDataInput from './MatchDataInput';
import './ChatInput.css';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  onMatchAnalysis?: (matchData: MatchData, response: TriggerResponse) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  selectedModel: ModelType;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage,
  onMatchAnalysis,
  isLoading, 
  disabled = false,
  placeholder = "Введите сообщение...",
  selectedModel
}) => {  
  const [input, setInput] = useState<string>('');
  const [showMatchDataInput, setShowMatchDataInput] = useState<boolean>(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Авто-увеличение высоты textarea при вводе текста
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading && !disabled) {
      onSendMessage(input);
      setInput('');
      
      // Сбросить высоту текстового поля
      if (textareaRef.current) {
        setTimeout(() => {
          textareaRef.current!.style.height = 'auto';
        }, 0);
      }
    }
  };
  
  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit}>
        <div className="input-row">
          {/* Кнопка для анализа данных матча */}          <button 
            type="button"
            className="match-analysis-button"
            onClick={() => setShowMatchDataInput(true)}
            disabled={isLoading || disabled}
            title="Анализ матча"
          >
            <i className="bi bi-trophy"></i>
          </button>
          
          {/* Текстовое поле для ввода сообщения */}
          <textarea
            ref={textareaRef}
            className={`chat-textarea ${disabled ? 'disabled' : ''}`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={placeholder}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            disabled={isLoading || disabled}
            rows={1}
          />
          
          {/* Кнопка отправки */}
          <button 
            type="submit" 
            className="send-button"
            disabled={input.trim() === '' || isLoading || disabled}
          >
            {isLoading ? (
              <span className="loading-spinner-small"></span>
            ) : (
              <>
                <i className="bi bi-send"></i>
                Отправить
              </>
            )}
          </button>
        </div>
        {input.length > 0 && (
          <div className="input-hints">
            Enter — отправить, Shift+Enter — новая строка
          </div>
        )}
      </form>
      
      {/* Модальное окно для ввода данных матча */}
      {showMatchDataInput && (
        <MatchDataInput 
          onClose={() => setShowMatchDataInput(false)}
          selectedModel={selectedModel}
          onSubmit={(data, response) => {
            // Используем новую функцию для анализа матча
            if (onMatchAnalysis) {
              onMatchAnalysis(data, response);
            }
            
            // Закрываем форму
            setShowMatchDataInput(false);
          }}
        />
      )}
    </div>
  );
};

export default ChatInput;
