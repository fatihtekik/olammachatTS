import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Спорт Аналитика</h2>
      </div>
      
      <nav className="sidebar-nav">
        <Link 
          to="/" 
          className={`nav-item ${isActive('/') ? 'active' : ''}`}
        >
          <i className="bi bi-house"></i>
          <span>Главная</span>
        </Link>
        
        <Link 
          to="/chat" 
          className={`nav-item ${isActive('/chat') ? 'active' : ''}`}
        >
          <i className="bi bi-chat-dots"></i>
          <span>Чат</span>
        </Link>
      </nav>
    </aside>
  );
};

export default Sidebar;
