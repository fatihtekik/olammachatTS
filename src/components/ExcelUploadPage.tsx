import React, { useState, useRef } from 'react';
import { parseExcelFile, ExcelMatchData } from '../utils/excelParser';
import { downloadExampleExcelFile } from '../utils/excelHelpers';
import './ExcelUploadPage.css';

interface UploadResult {
  success: boolean;
  created_players?: number;
  created_matches?: number;
  skipped_duplicates?: number;
  total_processed?: number;
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

interface Match {
  id: string;
  date: string;
  time?: string;
  player1: string;
  player2: string;
  player1_id: string;
  player2_id: string;
  score: string;
  sets_player1: number;
  sets_player2: number;
  winner: string;
  winner_id?: string;
  tournament?: string;
  stage?: string;
  is_final?: boolean;
  is_semifinal?: boolean;
  created_at?: string;
}

const ExcelUploadPage: React.FC = () => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadedData, setUploadedData] = useState<ExcelMatchData[]>([]);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAnalysisModal, setShowAnalysisModal] = useState(false);
  const [selectedTriggers, setSelectedTriggers] = useState<string[]>([
    'top_performers',
    'losers_50_percent',
    'losing_streaks'
  ]);
  const [matchesData, setMatchesData] = useState<Match[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  const handleFileSelect = (file: File) => {
    if (file.type !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' && 
        file.type !== 'application/vnd.ms-excel') {
      setError('Пожалуйста, выберите файл Excel (.xlsx или .xls)');
      return;
    }

    uploadFileToServer(file);
  };

  const uploadFileToServer = async (file: File) => {
    setIsUploading(true);
    setError(null);
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
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorText = await response.text();
          console.log('📝 Текст ошибки от сервера:', errorText);
          
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.detail || errorJson.message || errorMessage;
          } catch {
            errorMessage = errorText || errorMessage;
          }
        } catch (textError) {
          console.error('❌ Не удалось получить текст ошибки:', textError);
        }
        
        throw new Error(errorMessage);
      }

      const responseText = await response.text();
      console.log('📄 Сырой ответ сервера:', responseText);

      if (!responseText || responseText.trim() === '') {
        throw new Error('Сервер вернул пустой ответ');
      }

      let result: UploadResult;
      try {
        result = JSON.parse(responseText);
        console.log('✅ Результат загрузки:', result);
      } catch (parseError) {
        console.error('❌ Ошибка парсинга JSON:', parseError);
        throw new Error(`Не удалось распарсить ответ сервера: ${parseError}`);
      }

      setUploadResult(result);
      
      // Сразу после успешной загрузки обновляем статистику
      if (result.success) {
        await updateStats();
        await loadMatches();
      }
      
    } catch (err: any) {
      setError(err.message || 'Ошибка при загрузке файла');
      setUploadResult({
        success: false,
        error: err.message || 'Неизвестная ошибка'
      });
    } finally {
      setIsUploading(false);
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

      console.log('✅ Статистика обновлена');
    } catch (error) {
      console.error('❌ Ошибка при обновлении статистики:', error);
    }
  };

  const loadMatches = async () => {
    try {
      console.log('📋 Загружаем матчи из базы данных...');
      
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/all-matches?limit=1000', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Ошибка при загрузке матчей: ${response.status}`);
      }

      const matches: Match[] = await response.json();
      console.log(`✅ Загружено матчей: ${matches.length}`);
      
      setMatchesData(matches);
    } catch (error) {
      console.error('❌ Ошибка при загрузке матчей:', error);
      // В случае ошибки показываем пустой массив
      setMatchesData([]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const runAnalysis = async () => {
    setIsAnalyzing(true);
    setShowAnalysisModal(false);
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          trigger_types: selectedTriggers,
          period_start: null,
          period_end: null
        }),
      });

      console.log('📡 Получен ответ сервера:', response.status, response.statusText);

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        
        try {
          const errorText = await response.text();
          console.log('📝 Текст ошибки от сервера:', errorText);
          
          try {
            const errorJson = JSON.parse(errorText);
            errorMessage = errorJson.detail || errorJson.message || errorMessage;
          } catch {
            errorMessage = errorText || errorMessage;
          }
        } catch (textError) {
          console.error('❌ Не удалось получить текст ошибки:', textError);
        }
        
        throw new Error(errorMessage);
      }

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
      setIsAnalyzing(false);
    }
  };

  const handleTriggerToggle = (triggerType: string) => {
    setSelectedTriggers(prev => 
      prev.includes(triggerType) 
        ? prev.filter(t => t !== triggerType)
        : [...prev, triggerType]
    );
  };

  const getMatchRowClass = (match: Match, analysisResult: AnalysisResult | null) => {
    // Проверяем, есть ли триггеры для игроков этого матча
    let hasPlayerTriggers = false;
    if (analysisResult && analysisResult.triggers) {
      hasPlayerTriggers = analysisResult.triggers.some(trigger => 
        trigger.player_id === match.player1_id || trigger.player_id === match.player2_id
      );
    }
    
    // Определяем, кто выиграл (по winner_id или по счету)
    let isPlayer1Winner = false;
    if (match.winner_id) {
      isPlayer1Winner = match.winner_id === match.player1_id;
    } else {
      // Если нет winner_id, определяем по сетам
      isPlayer1Winner = match.sets_player1 > match.sets_player2;
    }
    
    // Возвращаем класс в зависимости от наличия триггеров и результата
    if (hasPlayerTriggers) {
      return isPlayer1Winner ? 'match-row-win-trigger' : 'match-row-loss-trigger';
    } else {
      return isPlayer1Winner ? 'match-row-win-normal' : 'match-row-loss-normal';
    }
  };

  const handleReset = () => {
    setUploadedData([]);
    setUploadResult(null);
    setAnalysisResult(null);
    setMatchesData([]);
    setError(null);
    setShowAnalysisModal(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Загружаем матчи при первом рендере компонента
  React.useEffect(() => {
    loadMatches();
  }, []);

  return (
    <div className="excel-upload-page">
      <div className="upload-header">
        <h1>Анализ матчей</h1>
        <p>Загрузите файл Excel с данными матчей и проведите анализ триггеров для выявления проблем игроков</p>
      </div>

      {!uploadResult ? (
        <div className="upload-section">
          <div 
            className={`drop-zone ${isDragOver ? 'drag-over' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileInputChange}
              className="file-input"
            />
            
            {isProcessing ? (
              <div className="processing">
                <div className="spinner"></div>
                <p>Обработка файла...</p>
              </div>
            ) : (
              <>
                <i className="bi bi-file-earmark-excel upload-icon"></i>
                <h3>Загрузите Excel файл</h3>
                <p>или кликните для выбора файла</p>
                <div className="supported-formats">
                  Поддерживаемые форматы: .xlsx, .xls
                </div>
              </>
            )}
          </div>

          <div className="help-section">
            <h3>Как подготовить файл Excel?</h3>
            <div className="help-content">
              <div className="help-item">
                <i className="bi bi-download"></i>
                <div>
                  <h4>Скачайте пример</h4>
                  <p>Используйте наш шаблон для правильного форматирования данных</p>
                  <button 
                    onClick={downloadExampleExcelFile}
                    className="download-example-btn"
                  >
                    <i className="bi bi-download"></i>
                    Скачать пример
                  </button>
                </div>
              </div>
              
              <div className="help-item">
                <i className="bi bi-table"></i>
                <div>
                  <h4>Структура данных</h4>
                  <p>Файл должен содержать колонки: Игрок 1, Игрок 2, Рейтинг 1, Рейтинг 2, Счёт, Турнир, Этап, Лига</p>
                </div>
              </div>
              
              <div className="help-item">
                <i className="bi bi-check-circle"></i>
                <div>
                  <h4>Проверка данных</h4>
                  <p>Убедитесь, что все обязательные поля заполнены и рейтинги указаны числами</p>
                </div>
              </div>
            </div>
          </div>

          {error && (
            <div className="error-message">
              <i className="bi bi-exclamation-triangle"></i>
              {error}
            </div>
          )}
        </div>
      ) : (
        <div className="results-section">
          {/* Результаты загрузки */}
          <div className="upload-results">
            <h2>
              <i className="bi bi-check-circle-fill text-success"></i>
              Данные загружены успешно
            </h2>
            <div className="results-stats">
              <div className="stat-item">
                <span className="stat-label">Всего строк:</span>
                <span className="stat-value">{uploadResult?.total_processed || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Создано игроков:</span>
                <span className="stat-value">{uploadResult?.created_players || 0}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Загружено матчей:</span>
                <span className="stat-value text-success">{uploadResult?.created_matches || 0}</span>
              </div>
              {uploadResult?.skipped_duplicates && uploadResult.skipped_duplicates > 0 && (
                <div className="stat-item">
                  <span className="stat-label">Пропущено дубликатов:</span>
                  <span className="stat-value text-warning">{uploadResult.skipped_duplicates}</span>
                </div>
              )}
              {uploadResult?.errors && uploadResult.errors.length > 0 && (
                <div className="stat-item">
                  <span className="stat-label">Ошибок:</span>
                  <span className="stat-value text-error">{uploadResult.errors.length}</span>
                </div>
              )}
            </div>
          </div>

          {/* Детали обработки */}
          {uploadResult && ((uploadResult.skipped_duplicates && uploadResult.skipped_duplicates > 0) || (uploadResult.errors && uploadResult.errors.length > 0)) && (
            <div className="processing-details">
              {uploadResult.skipped_duplicates && uploadResult.skipped_duplicates > 0 && (
                <div className="duplicates-info">
                  <h4>
                    <i className="bi bi-info-circle"></i>
                    Пропущенные дубликаты
                  </h4>
                  <p>
                    Найдено {uploadResult.skipped_duplicates} дублирующихся матчей. 
                    Проверка на дубликаты учитывает дату, игроков и счёт матча.
                  </p>
                </div>
              )}
              
              {uploadResult.errors && uploadResult.errors.length > 0 && (
                <div className="errors-info">
                  <h4>
                    <i className="bi bi-exclamation-triangle"></i>
                    Ошибки при обработке
                  </h4>
                  <div className="errors-list">
                    {uploadResult.errors.slice(0, 10).map((error, index) => (
                      <div key={index} className="error-item">{error}</div>
                    ))}
                    {uploadResult.errors.length > 10 && (
                      <div className="error-item more-errors">
                        ... и ещё {uploadResult.errors.length - 10} ошибок
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Кнопки действий */}
          <div className="action-buttons">
            <button 
              onClick={() => setShowAnalysisModal(true)} 
              className="analyze-btn"
              disabled={isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <div className="spinner-small"></div>
                  Анализируем...
                </>
              ) : (
                <>
                  <i className="bi bi-search"></i>
                  Анализировать триггеры
                </>
              )}
            </button>
            <button onClick={handleReset} className="reset-btn">
              <i className="bi bi-arrow-clockwise"></i>
              Загрузить другой файл
            </button>
          </div>

          {/* Результаты анализа */}
          {analysisResult && (
            <div className="analysis-results">
              <h3>Результаты анализа</h3>
              <div className="analysis-stats">
                <div className="stat-card">
                  <h4>{analysisResult.total_players}</h4>
                  <p>Игроков проанализировано</p>
                </div>
                <div className="stat-card">
                  <h4>{analysisResult.total_matches}</h4>
                  <p>Матчей за период</p>
                </div>
                <div className="stat-card">
                  <h4>{analysisResult.triggers_found}</h4>
                  <p>Триггеров найдено</p>
                </div>
              </div>

              {/* Топ игроки */}
              {analysisResult.top_performers.length > 0 && (
                <div className="top-performers">
                  <h4>
                    <i className="bi bi-trophy"></i>
                    Топ игроки ({analysisResult.top_performers.length})
                  </h4>
                  <div className="players-list">
                    {analysisResult.top_performers.map((player) => (
                      <div key={player.id} className="player-card top-performer">
                        <div className="player-header">
                          <span className="player-rank">#{player.rank || 'N/A'}</span>
                          <span className="player-name">{player.full_name}</span>
                        </div>
                        <div className="player-stats">
                          <div className="stat-row">
                            <span className="stat-label">Рейтинг:</span>
                            <span className="stat-value">{player.current_rating || 'N/A'}</span>
                          </div>
                          <div className="stat-row">
                            <span className="stat-label">Побед:</span>
                            <span className="stat-value">{player.wins || 0}/{player.matches_played || 0} ({player.win_rate || 0}%)</span>
                          </div>
                          <div className="stat-row">
                            <span className="stat-label">Сеты:</span>
                            <span className="stat-value">{player.sets_won || 0}:{player.sets_lost || 0} ({player.sets_ratio || 0})</span>
                          </div>
                          <div className="stat-row">
                            <span className="stat-label">Форма:</span>
                            <span className="form-indicator">{player.recent_form || 'N/A'}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Проблемные игроки */}
              {analysisResult.problem_players.length > 0 && (
                <div className="problem-players">
                  <h4>
                    <i className="bi bi-exclamation-triangle"></i>
                    Игроки с проблемами ({analysisResult.problem_players.length})
                  </h4>
                  <div className="players-list">
                    {analysisResult.problem_players.map((player) => (
                      <div key={player.id} className="player-card problem-player">
                        <div className="player-header">
                          <span className="player-rank">#{player.rank || 'N/A'}</span>
                          <span className="player-name">{player.full_name}</span>
                        </div>
                        <div className="player-stats">
                          <div className="stat-row">
                            <span className="stat-label">Рейтинг:</span>
                            <span className="stat-value">{player.current_rating || 'N/A'}</span>
                          </div>
                          <div className="stat-row">
                            <span className="stat-label">Поражений:</span>
                            <span className="stat-value">{player.losses || 0}/{player.matches_played || 0} ({player.loss_rate || 0}%)</span>
                          </div>
                          <div className="stat-row">
                            <span className="stat-label">Сеты:</span>
                            <span className="stat-value">{player.sets_won || 0}:{player.sets_lost || 0} ({player.sets_ratio || 0})</span>
                          </div>
                          <div className="stat-row">
                            <span className="stat-label">Форма:</span>
                            <span className="form-indicator">{player.recent_form || 'N/A'}</span>
                          </div>
                          {player.current_losing_streak > 0 && (
                            <div className="stat-row warning">
                              <span className="stat-label">Серия поражений:</span>
                              <span className="stat-value">{player.current_losing_streak}</span>
                            </div>
                          )}
                          {player.triggers_count > 0 && (
                            <div className="stat-row warning">
                              <span className="stat-label">Триггеров:</span>
                              <span className="stat-value">{player.triggers_count}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Список триггеров */}
              {analysisResult.triggers.length > 0 && (
                <div className="triggers-list">
                  <h4>
                    <i className="bi bi-list-check"></i>
                    Найденные триггеры ({analysisResult.triggers.length})
                  </h4>
                  <div className="triggers-grid">
                    {analysisResult.triggers.map((trigger) => (
                      <div key={trigger.id} className={`trigger-card severity-${trigger.severity_level}`}>
                        <div className="trigger-header">
                          <span className="trigger-type">{triggerTypeLabels[trigger.trigger_type] || trigger.trigger_type}</span>
                          <span className="severity-badge">Уровень {trigger.severity_level}</span>
                        </div>
                        <div className="trigger-value">{trigger.trigger_value}</div>
                        <div className="trigger-meta">
                          <div className="trigger-player">
                            <i className="bi bi-person"></i>
                            <strong>{trigger.player_name || 'Неизвестный игрок'}</strong>
                            {trigger.player_rating && (
                              <span className="player-rating-small"> (рейтинг: {trigger.player_rating})</span>
                            )}
                          </div>
                          {trigger.trigger_subtype && (
                            <div className="trigger-subtype">
                              <i className="bi bi-arrow-right"></i>
                              {trigger.trigger_subtype}
                            </div>
                          )}
                          <div className="trigger-date">
                            <i className="bi bi-calendar"></i>
                            {new Date(trigger.created_at).toLocaleDateString('ru-RU')}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Список матчей с подсветкой */}
          {matchesData.length > 0 && (
            <div className="matches-section">
              <h3>
                <i className="bi bi-table"></i>
                Матчи ({matchesData.length})
              </h3>
              <div className="matches-table-container">
                <table className="matches-table">
                  <thead>
                    <tr>
                      <th>Дата/Время</th>
                      <th>Игрок 1</th>
                      <th>Игрок 2</th>
                      <th>Счёт</th>
                      <th>Победитель</th>
                      <th>Турнир</th>
                      <th>Стадия</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchesData.map((match) => {
                      const isPlayer1Winner = match.winner_id ? 
                        match.winner_id === match.player1_id : 
                        match.sets_player1 > match.sets_player2;
                      
                      return (
                        <tr key={match.id} className={getMatchRowClass(match, analysisResult)}>
                          <td>
                            <div className="match-datetime">
                              <div className="match-date">{match.date}</div>
                              {match.time && <div className="match-time">{match.time}</div>}
                            </div>
                          </td>
                          <td className={isPlayer1Winner ? 'winner' : 'loser'}>
                            {match.player1}
                          </td>
                          <td className={!isPlayer1Winner ? 'winner' : 'loser'}>
                            {match.player2}
                          </td>
                          <td className="score">{match.score}</td>
                          <td className="winner-cell">{match.winner}</td>
                          <td>{match.tournament}</td>
                          <td>{match.stage}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Модальное окно выбора триггеров */}
      {showAnalysisModal && (
        <div className="modal-overlay" onClick={() => setShowAnalysisModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Выбор триггеров для анализа</h3>
              <button 
                className="modal-close"
                onClick={() => setShowAnalysisModal(false)}
              >
                <i className="bi bi-x"></i>
              </button>
            </div>
            
            <div className="modal-body">
              <p>Выберите типы триггеров, которые вы хотите проанализировать:</p>
              
              <div className="triggers-selection">
                {Object.entries(triggerTypeLabels).map(([key, label]) => (
                  <div key={key} className="trigger-option">
                    <input
                      type="checkbox"
                      id={key}
                      checked={selectedTriggers.includes(key)}
                      onChange={() => handleTriggerToggle(key)}
                    />
                    <label htmlFor={key}>{label}</label>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                className="btn-secondary"
                onClick={() => setShowAnalysisModal(false)}
              >
                Отмена
              </button>
              <button 
                className="btn-primary"
                onClick={runAnalysis}
                disabled={selectedTriggers.length === 0}
              >
                <i className="bi bi-play"></i>
                Запустить анализ ({selectedTriggers.length} триггеров)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExcelUploadPage;
