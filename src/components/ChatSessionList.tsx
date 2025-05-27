import React from 'react';
import { ChatSession } from '../types/chat';
import './ChatSessionList.css';

interface ChatSessionListProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
}

const ChatSessionList: React.FC<ChatSessionListProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession
}) => {
  // Форматирование даты в читаемый вид
  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('default', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <div className="chat-sessions-list">
      <div className="sessions-header">
        <h3>История чатов</h3>
        <button 
          className="new-session-button"
          onClick={onCreateSession}
        >
          <i className="bi bi-plus-circle"></i> Новый чат
        </button>
      </div>
      
      <div className="sessions-container">
        {sessions.length === 0 ? (
          <div className="no-sessions">
            <p>Нет сохраненных чатов</p>
          </div>
        ) : (
          <ul className="sessions-list">
            {sessions.map(session => (
              <li 
                key={session.id}
                className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
                onClick={() => onSelectSession(session.id)}
              >
                <div className="session-info">
                  <div className="session-title">
                    <i className="bi bi-chat-left-text"></i>
                    {session.title || `Чат от ${formatDate(session.createdAt)}`}
                  </div>
                  <div className="session-meta">
                    <span className="session-model">{session.model}</span>
                    <span className="session-date">{formatDate(session.updatedAt)}</span>
                    <span className="session-count">{session.messages.length} сообщений</span>
                  </div>
                </div>
                <button
                  className="delete-session"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm('Удалить этот чат из истории?')) {
                      onDeleteSession(session.id);
                    }
                  }}
                >
                  <i className="bi bi-trash"></i>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ChatSessionList;
