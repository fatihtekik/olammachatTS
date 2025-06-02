import React, { useState } from 'react';
import { ChatSession } from '../types/chat';
import './ChatSessionList.css';

interface ChatSessionListProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  onRenameSession: (sessionId: string, newTitle: string) => void;
}

const ChatSessionList: React.FC<ChatSessionListProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession
}) => {
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState<string>('');

  // Форматирование даты в читаемый вид
  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('default', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const startRenaming = (sessionId: string, currentTitle: string) => {
    setEditingSessionId(sessionId);
    setNewTitle(currentTitle);
  };

  const handleRename = (sessionId: string) => {
    if (newTitle.trim()) {
      onRenameSession(sessionId, newTitle);
    }
    setEditingSessionId(null);
    setNewTitle('');
  };

  const handleKeyDown = (e: React.KeyboardEvent, sessionId: string) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleRename(sessionId);
    } else if (e.key === 'Escape') {
      setEditingSessionId(null);
      setNewTitle('');
    }
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
                className={`session-item ${activeSessionId === session.id ? 'active' : ''}`}
                onClick={() => activeSessionId !== session.id && onSelectSession(session.id)}
              >
                <div className="session-info">
                  {editingSessionId === session.id ? (
                    <input
                      type="text"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      onBlur={() => handleRename(session.id)}
                      onKeyDown={(e) => handleKeyDown(e, session.id)}
                      autoFocus
                      className="session-title-input"
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <div className="session-title" onClick={() => activeSessionId === session.id && startRenaming(session.id, session.title)}>
                      {session.title}
                    </div>
                  )}
                  <div className="session-meta">
                    <span className="session-model">{session.model}</span>
                    <span className="session-date">{formatDate(session.updatedAt)}</span>
                  </div>
                </div>
                
                <div className="session-actions">
                  <button 
                    className="rename-session-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      startRenaming(session.id, session.title);
                    }}
                    title="Переименовать"
                  >
                    <i className="bi bi-pencil"></i>
                  </button>
                  <button 
                    className="delete-session-button"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm('Вы уверены, что хотите удалить этот чат?')) {
                        onDeleteSession(session.id);
                      }
                    }}
                    title="Удалить"
                  >
                    <i className="bi bi-trash"></i>
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default ChatSessionList;
