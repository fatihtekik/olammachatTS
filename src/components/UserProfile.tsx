import React, { useState, useRef } from 'react';
import { authAPI } from '../services/backendApi';
import { ChatSession } from '../types/chat';
import { importSessionsFromFile } from '../services/storageService';
import './UserProfile.css';

interface UserProfileProps {
  username: string;
  email?: string;
  fullName?: string;
  onLogout: () => void;
  onExportSessions: () => void;
  onImportSessions: (sessions: ChatSession[]) => void;
}

const UserProfile: React.FC<UserProfileProps> = ({ 
  username, 
  email, 
  fullName,
  onLogout,
  onExportSessions,
  onImportSessions
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const importFileInputRef = useRef<HTMLInputElement>(null);

  const handleLogout = () => {
    authAPI.logout();
    onLogout();
  };

  const handleToggleDropdown = () => {
    setShowDropdown(!showDropdown);
  };

  const handleImportClick = () => {
    // Click the hidden file input
    if (importFileInputRef.current) {
      importFileInputRef.current.click();
    }
    setShowDropdown(false);
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      try {
        const importedSessions = await importSessionsFromFile(file);
        onImportSessions(importedSessions);
      } catch (error) {
        console.error('Failed to import sessions:', error);
        alert('Failed to import sessions. Make sure the file format is correct.');
      }
    }
  };

  return (
    <div className="user-profile">
      <div className="user-info" onClick={handleToggleDropdown}>
        <div className="user-avatar">
          {username.charAt(0).toUpperCase()}
        </div>
        <span className="username">{username}</span>
      </div>

      {showDropdown && (
        <div className="user-dropdown">
          <div className="user-details">
            <div className="detail-item">
              <strong>Username:</strong> {username}
            </div>
            {email && (
              <div className="detail-item">
                <strong>Email:</strong> {email}
              </div>
            )}
            {fullName && (
              <div className="detail-item">
                <strong>Name:</strong> {fullName}
              </div>
            )}
          </div>
          
          <div className="dropdown-actions">
            <button className="dropdown-button" onClick={onExportSessions}>
              Export Sessions
            </button>
            <button className="dropdown-button" onClick={handleImportClick}>
              Import Sessions
            </button>
            <button className="dropdown-button logout" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      )}
      
      <input
        type="file"
        ref={importFileInputRef}
        accept=".json"
        style={{ display: 'none' }}
        onChange={handleFileChange}
      />
    </div>
  );
};

export default UserProfile;
