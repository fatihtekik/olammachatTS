import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { parseExcelFile, ExcelMatchData } from '../utils/excelParser';
import { downloadExampleExcelFile } from '../utils/excelHelpers';
import { useInvalidateStats } from '../hooks/useDashboardStats';
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
  const navigate = useNavigate();
  const invalidateStats = useInvalidateStats();
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
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState('');
  const [uploadSpeed, setUploadSpeed] = useState<string>('');
  const [uploadedSize, setUploadedSize] = useState<string>('');
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisStage, setAnalysisStage] = useState('');
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
    setUploadProgress(0);
    setUploadStage('Подготовка файла...');
    setUploadSpeed('');
    setUploadedSize('');
    
    let smoothProgressInterval: NodeJS.Timeout | null = null;
    
    try {
      const formData = new FormData();
      formData.append('file', file);

      console.log('🚀 Начинаем загрузку файла:', file.name, `(${(file.size / 1024 / 1024).toFixed(2)} MB)`);
      
      // Показываем начальный прогресс
      await new Promise(resolve => setTimeout(resolve, 300));
      setUploadProgress(5);
      setUploadStage('Подготовка данных...');
      
      const startTime = Date.now();
      let lastLoaded = 0;
      let lastTime = startTime;
      let uploadStarted = false;
      
      // Используем XMLHttpRequest для отслеживания прогресса загрузки
      const xhr = new XMLHttpRequest();
      
      let smoothProgress = 5; // Начинаем с 5%
      let actualProgress = 0;
      
      // Плавное обновление прогресса
      smoothProgressInterval = setInterval(() => {
        if (smoothProgress < actualProgress) {
          smoothProgress = Math.min(smoothProgress + 2, actualProgress);
          setUploadProgress(smoothProgress);
        }
      }, 50); // Обновляем каждые 50мс
      
      // Обработчик прогресса загрузки
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          actualProgress = Math.round((event.loaded / event.total) * 95); // Оставляем 5% для обработки
          
          if (!uploadStarted) {
            uploadStarted = true;
            setUploadStage('Отправка файла на сервер...');
          }
          
          // Расчет скорости загрузки
          const currentTime = Date.now();
          const timeDiff = (currentTime - lastTime) / 1000; // в секундах
          const bytesDiff = event.loaded - lastLoaded;
          
          if (timeDiff > 0.3) { // Обновляем скорость каждые 0.3 сек
            const speedBps = bytesDiff / timeDiff;
            const speedKbps = speedBps / 1024;
            const speedMbps = speedKbps / 1024;
            
            let speedText = '';
            if (speedMbps >= 1) {
              speedText = `${speedMbps.toFixed(2)} MB/s`;
            } else if (speedKbps >= 1) {
              speedText = `${speedKbps.toFixed(2)} KB/s`;
            } else {
              speedText = `${speedBps.toFixed(0)} B/s`;
            }
            
            setUploadSpeed(speedText);
            lastLoaded = event.loaded;
            lastTime = currentTime;
          }
          
          // Размер загруженных данных
          const loadedMB = (event.loaded / 1024 / 1024).toFixed(2);
          const totalMB = (event.total / 1024 / 1024).toFixed(2);
          setUploadedSize(`${loadedMB} / ${totalMB} MB`);
        }
      });

      // Обработчик завершения загрузки
      const uploadPromise = new Promise<any>((resolve, reject) => {
        xhr.onload = async () => {
          console.log('📡 Получен ответ сервера:', xhr.status, xhr.statusText);
          
          if (xhr.status >= 200 && xhr.status < 300) {
            // Плавно доводим до 95%
            actualProgress = 95;
            setUploadStage('Обработка данных на сервере...');
            
            // Ждем пока догонит плавная анимация
            await new Promise(resolve => setTimeout(resolve, 500));
            
            try {
              const result = JSON.parse(xhr.responseText);
              console.log('✅ Результат загрузки:', result);
              resolve(result);
            } catch (parseError) {
              reject(new Error('Ошибка парсинга ответа сервера'));
            }
          } else {
            try {
              const err = JSON.parse(xhr.responseText);
              reject(new Error(err.detail || xhr.statusText));
            } catch {
              reject(new Error(xhr.statusText || 'Ошибка загрузки'));
            }
          }
        };

        xhr.onerror = () => {
          reject(new Error('Ошибка сети при загрузке файла'));
        };

        xhr.ontimeout = () => {
          reject(new Error('Превышено время ожидания'));
        };
      });

      // Настройка и отправка запроса
      xhr.open('POST', 'http://localhost:8000/api/v1/match-analysis/upload-excel', true);
      xhr.timeout = 300000; // 5 минут таймаут
      xhr.send(formData);

      // Ожидаем завершения загрузки
      const result = await uploadPromise;
      
      // Останавливаем плавную анимацию
      clearInterval(smoothProgressInterval);
      
      // Плавно доводим до 100%
      actualProgress = 100;
      for (let i = smoothProgress; i <= 100; i++) {
        setUploadProgress(i);
        await new Promise(resolve => setTimeout(resolve, 20));
      }
      
      setUploadStage('Загрузка завершена!');
      setUploadResult(result);
      
      // Инвалидируем кеш статистики дашборда после успешной загрузки
      if (result.success !== false) {
        console.log('🔄 Инвалидация кеша статистики после загрузки файла');
        invalidateStats();
      }
      
    } catch (err: any) {
      console.error('❌ Ошибка загрузки:', err);
      
      // Очищаем интервал при ошибке
      if (smoothProgressInterval) {
        clearInterval(smoothProgressInterval);
      }
      
      setError(err.message || 'Ошибка при загрузке файла');
      setUploadResult({
        success: false,
        error: err.message || 'Неизвестная ошибка'
      });
      setUploadProgress(0);
      setUploadStage('');
      setUploadSpeed('');
      setUploadedSize('');
    } finally {
      // Очищаем интервал в любом случае
      if (smoothProgressInterval) {
        clearInterval(smoothProgressInterval);
      }
      
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setUploadStage('');
        setUploadSpeed('');
        setUploadedSize('');
      }, 1500); // Увеличил время для отображения 100%
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
    setAnalysisProgress(0);
    setAnalysisStage('Подготовка анализа...');
    
    try {
      setAnalysisProgress(10);
      setAnalysisStage('Отправка запроса на анализ...');
      
      // Имитация прогресса во время ожидания ответа
      const progressInterval = setInterval(() => {
        setAnalysisProgress(prev => {
          if (prev < 85) {
            return prev + 1;
          }
          return prev;
        });
      }, 300); // Обновляем каждые 300мс
      
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
      
      clearInterval(progressInterval);
      setAnalysisProgress(90);
      setAnalysisStage('Получение результатов...');

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

      setAnalysisProgress(95);
      setAnalysisStage('Обработка результатов...');
      
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

      setAnalysisProgress(100);
      setAnalysisStage('Анализ завершён!');
      setAnalysisResult(result);
    } catch (error) {
      console.error('💥 Ошибка при анализе:', error);
      alert('Ошибка при анализе: ' + (error instanceof Error ? error.message : 'Неизвестная ошибка'));
      setAnalysisProgress(0);
      setAnalysisStage('');
    } finally {
      setTimeout(() => {
        setIsAnalyzing(false);
        setAnalysisProgress(0);
        setAnalysisStage('');
      }, 1500);
    }
  };

  const handleTriggerToggle = (triggerType: string) => {
    setSelectedTriggers(prev => 
      prev.includes(triggerType) 
        ? prev.filter(t => t !== triggerType)
        : [...prev, triggerType]
    );
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
      {/* Основной контент */}
      <div className="analysis-content">

      {!uploadResult ? (
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
                <p>Обработка данных...</p>
              </div>
            ) : (
              <>
                <i className="bi bi-file-earmark-excel upload-icon"></i>
                <h3>Загрузить Excel файл</h3>
                <p>Загрузите файл с матчами для анализа триггеров</p>
                <div className="supported-formats">
                  Форматы: .xlsx, .xls
                </div>
              </>
            )}
          </div>

          <div className="format-info">
            <i className="bi bi-info-circle"></i>
            <div>
              <strong>Формат файла:</strong>
              <p><strong>Обязательные столбцы:</strong> Дата, Игрок 1, Счёт, Игрок 2</p>
              <p><strong>Для корректных рейтингов:</strong> Рейтинг игрок 1, Рейтинг игрок 2</p>
              <p><strong>Дополнительно:</strong> Время, Стадия, Турнир</p>
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
      
      {/* Loading Overlay для загрузки */}
      {isUploading && (
        <div className="upload-overlay">
          <div className="upload-overlay-content">
            <div className="upload-spinner">
              <div className="spinner-ring"></div>
              <div className="spinner-ring"></div>
              <div className="spinner-ring"></div>
            </div>
            <h2>Загрузка данных</h2>
            <p className="upload-stage">{uploadStage}</p>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <span className="progress-text">{uploadProgress}%</span>
            {uploadSpeed && (
              <div className="upload-info">
                <span className="upload-speed">⚡ {uploadSpeed}</span>
                {uploadedSize && <span className="upload-size">📦 {uploadedSize}</span>}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Loading Overlay для анализа */}
      {isAnalyzing && (
        <div className="upload-overlay">
          <div className="upload-overlay-content">
            <div className="upload-spinner">
              <div className="spinner-ring"></div>
              <div className="spinner-ring"></div>
              <div className="spinner-ring"></div>
            </div>
            <h2>Анализ данных</h2>
            <p className="upload-stage">{analysisStage}</p>
            <div className="progress-bar">
              <div 
                className="progress-fill" 
                style={{ width: `${analysisProgress}%` }}
              ></div>
            </div>
            <span className="progress-text">{analysisProgress}%</span>
          </div>
        </div>
      )}
      
      </div> {/* Закрываем analysis-content */}
    </div>
  );
};

export default ExcelUploadPage;
