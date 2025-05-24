import React from 'react';
import { Message } from '../types/chat';
import './ChatMessage.css';

interface ChatMessageProps {
  message: Message;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  return (
    <div className={`chat-message ${message.role}`}>
      <div className="message-header">
        <span className="message-role">{message.role === 'user' ? 'You' : 'Ollama'}</span>
        <span className="message-time">
          {message.timestamp.toLocaleTimeString()}
        </span>
      </div>
      <div className="message-content">{message.content}</div>
    </div>
  );
};

export default ChatMessage;
