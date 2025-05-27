import React from 'react';
import { Message } from '../types/chat';
import FileAttachment from './FileAttachment';
import './ChatMessage.css';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  // Форматирование времени более читаемым образом
  const formattedTime = () => {
    const time = message.timestamp;
    return time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Проверка есть ли свойство error в сообщении
  const hasError = 'error' in message && message.error;
  
  // Проверка на наличие вложений
  const hasAttachments = message.attachments && message.attachments.length > 0;

  return (
    <div className={`chat-message ${message.role} ${hasError ? 'error-message' : ''}`}>
      <div className="message-header">
        <span className="message-role">
          {message.role === 'user' ? 'Вы' : 'Ollama'}
        </span>
        <span className="message-time">
          {formattedTime()}
        </span>
      </div>
      
      {/* Текстовое сообщение */}
      <div className="message-content">{message.content}</div>
      
      {/* Вложения файлов */}
      {hasAttachments && (
        <div className="message-attachments">
          {message.attachments!.map(attachment => (
            <FileAttachment key={attachment.id} file={attachment} />
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatMessage;
