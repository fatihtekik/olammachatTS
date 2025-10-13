import React, { useState, useRef } from 'react';
import './MatchAnalysisPage.css';

interface UploadResult {
  success: boolean;
  created_players?: number;
  created_matches?: number;
  errors?: string[];
  error?: string;
}

interface AnalysisResult {
  period_start: string;
  period_end: string;
  total_players: number;
  total_matches: number;
  triggers_found: number;
  top_performers: any[];
  problem_players: any[];
  triggers: any[];
}

const MatchAnalysisPage: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [triggerTypes, setTriggerTypes] = useState<string[]>([
    'top_performers',
    'losers_50_percent', 
    'endgame_problems',
    'lead_4_lost',
    'balance_problems'
  ]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setUploadResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      console.log('🚀 Начинаем загрузку файла:', file.name);

      const response = await fetch('http://localhost:8000/api/v1/match-analysis/upload-excel', {
        method: 'POST',
        body: formData,
      });

      console.log('📡 Получен ответ сервера:', response.status, response.statusText);

      if (!response.ok) {
        // Пытаемся получить текст ошибки
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorText = await response.text();
          console.log('📝 Текст ошибки от сервера:', errorText);
          
          // Пытаемся распарсить как JSON
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.detail || errorJson.message || errorMessage;
          } catch {
            // Если не JSON, используем как есть
            errorMessage = errorText || errorMessage;
          }
        } catch (textError) {
          console.error('❌ Не удалось получить текст ошибки:', textError);
        }
        
        throw new Error(errorMessage);
      }

      // Проверяем, что ответ не пустой
      const contentLength = response.headers.get('content-length');
      console.log('📏 Размер ответа:', contentLength);

      const responseText = await response.text();
      console.log('📄 Сырой ответ сервера:', responseText);

      if (!responseText || responseText.trim() === '') {
        throw new Error('Сервер вернул пустой ответ');
      }

      let result: UploadResult;
      try {
        result = JSON.parse(responseText);
        console.log('✅ Успешно распарсен JSON:', result);
      } catch (parseError) {
        console.error('❌ Ошибка парсинга JSON:', parseError);
        console.log('🔍 Проблемный текст:', responseText.substring(0, 200) + '...');
        throw new Error(`Некорректный ответ сервера: ${parseError}`);
      }

      setUploadResult(result);
      
      if (result.success) {
        console.log('🎉 Файл успешно загружен!');
        // Автоматически обновляем статистику после загрузки
        await updateStats();
      }
    } catch (error) {
      console.error('💥 Ошибка при загрузке:', error);
      setUploadResult({
        success: false,
        error: error instanceof Error ? error.message : 'Неизвестная ошибка'
      });
    } finally {
      setUploading(false);
    }
  };

  const updateStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/update-stats', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          force_recalculate: true
        }),
      });

      if (!response.ok) {
        throw new Error('Ошибка при обновлении статистики');
      }

      console.log('Статистика обновлена');
    } catch (error) {
      console.error('Ошибка при обновлении статистики:', error);
    }
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trigger_types: triggerTypes,
          period_start: null, // Последние 3 месяца по умолчанию
          period_end: null
        }),
      });

      console.log('📡 Получен ответ сервера:', response.status, response.statusText);

      if (!response.ok) {
        // Пытаемся получить текст ошибки
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorText = await response.text();
          console.log('📝 Текст ошибки от сервера:', errorText);
          
          // Пытаемся распарсить как JSON
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.detail || errorJson.message || errorMessage;
          } catch {
            // Если не JSON, используем как есть
            errorMessage = errorText || errorMessage;
          }
        } catch (textError) {
          console.error('❌ Не удалось получить текст ошибки:', textError);
        }
        
        throw new Error(errorMessage);
      }

      // Проверяем, что ответ не пустой
      const contentLength = response.headers.get('content-length');
      console.log('📏 Размер ответа:', contentLength);

      const responseText = await response.text();
      console.log('📄 Сырой ответ сервера:', responseText);

      if (!responseText || responseText.trim() === '') {
        throw new Error('Сервер вернул пустой ответ');
      }

      let result: AnalysisResult;
      try {
        result = JSON.parse(responseText);
        console.log('✅ Результат анализа:', result);
      } catch (parseError) {
        console.error('❌ Ошибка парсинга JSON:', parseError);
        throw new Error(`Не удалось распарсить ответ сервера: ${parseError}`);
      }

      setAnalysisResult(result);
    } catch (error) {
      console.error('💥 Ошибка при анализе:', error);
      alert('Ошибка при анализе: ' + (error instanceof Error ? error.message : 'Неизвестная ошибка'));
    } finally {
      setAnalyzing(false);
    }
  };

  const triggerTypeLabels: { [key: string]: string } = {
    'top_performers': 'Топ игроки по результативности',
    'losers_50_percent': 'Игроки с >50% поражений',
    'endgame_problems': 'Проблемы в концовках',
    'lead_4_lost': 'Вел 4+ и проиграл',
    'balance_problems': 'Проблемы в балансах',
    'led_2_sets_lost': 'Вел 2 сета но проиграл',
    'led_1_set_lost': 'Вел 1 сет и проиграл',
    'early_final_exit': 'Досрочный выход из финала',
    'league_promotion_failed': 'Не прошел в следующую лигу',
    'won_2_lost_3rd': 'Выиграл 2 сета но проиграл 3й',
    'close_score_losses': 'Поражения при равном счете',
    'post_holiday_problems': 'Проблемы после праздников',
    'time_performance': 'Проблемы по времени суток',
    'shutout_losses': 'Поражения 0:3',
    'losing_streaks': 'Серии поражений',
    'weaker_opponent_losses': 'Поражения от слабых соперников',
    'long_match_losses': 'Поражения в долгих матчах',
    'higher_league_struggles': 'Проблемы в высшей лиге',
    'reception_problems': 'Проблемы с приемом'
  };

  return (
    <div className="match-analysis-page">
      {/* Мини-навигация */}
      <div className="mini-navigation">
        <button className="nav-item" onClick={() => window.location.href = '/'}>
          <i className="bi bi-chat-dots"></i>
          <span>Чат</span>
        </button>
        <div className="nav-item active">
          <i className="bi bi-graph-up-arrow"></i>
          <span>Анализ данных</span>
        </div>
        <div className="nav-item disabled">
          <i className="bi bi-clock-history"></i>
          <span>История анализов</span>
        </div>
      </div>

      {/* Основной контент */}
      <div className="analysis-content">
        {/* Tabs для переключения */}
        <div className="analysis-tabs">
          <button className="tab-button active">
            <i className="bi bi-file-earmark-excel"></i>
            Загрузка Excel
          </button>
          <button className="tab-button">
            <i className="bi bi-database"></i>
            Анализ базы данных
          </button>
        </div>

      {/* Секция загрузки файла */}
      <div className="upload-section">
        <div className="section-header">
          <h2>Загрузить Excel файл</h2>
          <button className="settings-button" title="Настройки анализа">
            <i className="bi bi-gear"></i>
          </button>
        </div>
        
        <p className="section-description">
          Загрузите файл с данными матчей для автоматической обработки и выявления закономерностей
        </p>
        
        <div className="upload-area">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          
          <div 
            className={`file-drop-zone ${file ? 'has-file' : ''}`}
            onClick={() => fileInputRef.current?.click()}
          >
            {file ? (
              <div className="file-info">
                <i className="bi bi-file-earmark-excel"></i>
                <span>{file.name}</span>
                <small>({(file.size / 1024 / 1024).toFixed(2)} MB)</small>
              </div>
            ) : (
              <div className="drop-message">
                <i className="bi bi-file-earmark-excel"></i>
                <p>Загрузить Excel файл</p>
                <small>Загрузите файл с матчами для анализа триггеров</small>
              </div>
            )}
          </div>

          <div className="format-info">
            <i className="bi bi-info-circle"></i>
            <div>
              <strong>Формат файла:</strong>
              <p><strong>Обязательные столбцы:</strong> Дата, Игрок 1, Счёт, Игрок 2, Рейтинг игрок 1, Рейтинг игрок 2</p>
              <p><strong>Для корректных рейтингов добавьте:</strong> Рейтинг игрок 1, Рейтинг игрок 2</p>
              <p><strong>Дополнительно:</strong> Время, Стадия, Турнир</p>
              <a href="#" className="details-link">
                <i className="bi bi-arrow-right"></i>
                Подробная инструкция
              </a>
            </div>
          </div>

          <button 
            className="upload-btn"
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            {uploading ? (
              <>
                <i className="bi bi-hourglass-split rotating"></i>
                Обработка данных...
              </>
            ) : (
              <>
                <i className="bi bi-upload"></i>
                Загрузить
              </>
            )}
          </button>
        </div>

        {uploadResult && (
          <div className={`upload-result ${uploadResult.success ? 'success' : 'error'}`}>
            {uploadResult.success ? (
              <div>
                <i className="bi bi-check-circle"></i>
                <h3>Данные успешно загружены!</h3>
                <p>Создано игроков: {uploadResult.created_players}</p>
                <p>Создано матчей: {uploadResult.created_matches}</p>
                {uploadResult.errors && uploadResult.errors.length > 0 && (
                  <details>
                    <summary>Предупреждения ({uploadResult.errors.length})</summary>
                    <ul>
                      {uploadResult.errors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ) : (
              <div>
                <i className="bi bi-exclamation-triangle"></i>
                <h3>Ошибка при загрузке</h3>
                <p>{uploadResult.error}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Секция настройки анализа */}
      <div className="analysis-settings">
        <h2>
          <i className="bi bi-gear"></i>
          Настройки анализа
        </h2>
        
        <div className="trigger-types">
          <h3>Типы триггеров для анализа:</h3>
          <div className="trigger-checkboxes">
            {Object.entries(triggerTypeLabels).map(([key, label]) => (
              <label key={key} className="trigger-checkbox">
                <input
                  type="checkbox"
                  checked={triggerTypes.includes(key)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setTriggerTypes([...triggerTypes, key]);
                    } else {
                      setTriggerTypes(triggerTypes.filter(t => t !== key));
                    }
                  }}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </div>

        <button 
          className="analyze-btn"
          onClick={runAnalysis}
          disabled={analyzing || triggerTypes.length === 0}
        >
          {analyzing ? (
            <>
              <i className="bi bi-hourglass-split rotating"></i>
              Анализ...
            </>
          ) : (
            <>
              <i className="bi bi-search"></i>
              Запустить анализ
            </>
          )}
        </button>
      </div>

      {/* Результаты анализа */}
      {analysisResult && (
        <div className="analysis-results">
          <h2>
            <i className="bi bi-clipboard-data"></i>
            Результаты анализа
          </h2>
          
          <div className="stats-grid">
            <div className="stat-card">
              <i className="bi bi-people"></i>
              <div>
                <h3>{analysisResult.total_players}</h3>
                <p>Игроков проанализировано</p>
              </div>
            </div>
            
            <div className="stat-card">
              <i className="bi bi-trophy"></i>
              <div>
                <h3>{analysisResult.total_matches}</h3>
                <p>Матчей обработано</p>
              </div>
            </div>
            
            <div className="stat-card">
              <i className="bi bi-exclamation-triangle"></i>
              <div>
                <h3>{analysisResult.triggers_found}</h3>
                <p>Триггеров найдено</p>
              </div>
            </div>
          </div>

          <div className="analysis-period">
            <p>
              <i className="bi bi-calendar"></i>
              Период анализа: {analysisResult.period_start} — {analysisResult.period_end}
            </p>
          </div>

          {analysisResult.triggers.length > 0 && (
            <div className="triggers-list">
              <h3>Обнаруженные триггеры:</h3>
              <div className="triggers-grid">
                {analysisResult.triggers.map((trigger, index) => (
                  <div key={index} className={`trigger-card severity-${trigger.severity_level}`}>
                    <div className="trigger-header">
                      <h4>{triggerTypeLabels[trigger.trigger_type] || trigger.trigger_type}</h4>
                      <span className="severity-badge">
                        Уровень {trigger.severity_level}
                      </span>
                    </div>
                    <p>{trigger.trigger_value}</p>
                    {trigger.trigger_subtype && (
                      <small>Подтип: {trigger.trigger_subtype}</small>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      </div> {/* Закрываем analysis-content */}
    </div>
  );
};

export default MatchAnalysisPage;
