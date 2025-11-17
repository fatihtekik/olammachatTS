import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Sidebar.css';

const Sidebar: React.FC = () => {
  const location = useLocation();
  const [analysisOpen, setAnalysisOpen] = useState(false);

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

        <Link 
          to="/upload" 
          className={`nav-item ${isActive('/upload') ? 'active' : ''}`}
        >
          <i className="bi bi-file-earmark-excel"></i>
          <span>Загрузка</span>
        </Link>

        <div className="nav-group">
          <div 
            className={`nav-item ${isActive('/analysis') || isActive('/h2h-analysis') ? 'active' : ''}`}
            onClick={() => setAnalysisOpen(!analysisOpen)}
          >
            <i className="bi bi-graph-up-arrow"></i>
            <span>Анализ</span>
            <i className={`bi bi-chevron-${analysisOpen ? 'down' : 'right'} chevron-icon`}></i>
          </div>
          
          {analysisOpen && (
            <div className="nav-submenu">
              <Link 
                to="/analysis" 
                className={`nav-subitem ${isActive('/analysis') ? 'active' : ''}`}
              >
                <span>Анализ по игрокам</span>
              </Link>
              <Link 
                to="/h2h-analysis" 
                className={`nav-subitem ${isActive('/h2h-analysis') ? 'active' : ''}`}
              >
                <span>Анализ по парам</span>
              </Link>
            </div>
          )}
        </div>

        <Link 
          to="/history" 
          className={`nav-item ${isActive('/history') ? 'active' : ''}`}
        >
          <i className="bi bi-clock-history"></i>
          <span>История</span>
        </Link>
      </nav>
    </aside>
  );
};

export default Sidebar;
