import React, { useState, useRef } from 'react';
import { MatchData, TriggerResponse, ModelType } from '../types/chat';
import MatchTriggerForm from './MatchTriggerForm';
import { parseExcelFile, ExcelMatchData } from '../utils/excelParser';
import { downloadExampleExcelFile } from '../utils/excelHelpers';
import './MatchDataInput.css';

interface MatchDataInputProps {
  onClose: () => void;
  onSubmit: (data: MatchData, response: TriggerResponse) => void;
  selectedModel: ModelType;
}

const MatchDataInput: React.FC<MatchDataInputProps> = ({ onClose, onSubmit, selectedModel }) => {
  const [inputMode, setInputMode] = useState<'manual' | 'excel' | null>(null);
  const [excelData, setExcelData] = useState<ExcelMatchData[]>([]);
  const [selectedMatch, setSelectedMatch] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingProgress, setLoadingProgress] = useState<string>('');
  const excelInputRef = useRef<HTMLInputElement>(null);  const handleExcelFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    // Проверяем, что это Excel файл
    const isExcel = file.type.includes('sheet') || 
                   file.type.includes('excel') || 
                   file.name.endsWith('.xlsx') || 
                   file.name.endsWith('.xls');
    
    if (!isExcel) {
      setError('Пожалуйста, выберите Excel файл (.xlsx или .xls)');
      return;
    }

    // Переключаемся в режим Excel и показываем индикатор загрузки
    setInputMode('excel');
    setIsLoadingFile(true);
    setIsProcessing(false);
    setError(null);
    setLoadingProgress('Читаем файл...');

    try {
      // Показываем размер файла для больших файлов
      const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
      if (file.size > 1024 * 1024) { // Больше 1MB
        setLoadingProgress(`Обрабатываем большой файл (${fileSizeMB} MB)...`);
      }

      // Небольшая задержка для отображения UI
      await new Promise(resolve => setTimeout(resolve, 100));
      
      setLoadingProgress('Парсим данные Excel...');
      const parsedData = await parseExcelFile(file);
      
      setLoadingProgress('Проверяем данные...');
      await new Promise(resolve => setTimeout(resolve, 200));
      
      if (parsedData.length === 0) {
        setError('Excel файл не содержит данных о матчах');
        return;
      }

      setLoadingProgress(`Загружено ${parsedData.length} матчей. Готово!`);
      await new Promise(resolve => setTimeout(resolve, 500));

      setExcelData(parsedData);
      setSelectedMatch(0);
      
      console.log(`Загружено ${parsedData.length} матчей из Excel файла`);
      
    } catch (error: any) {
      console.error('Ошибка при обработке Excel файла:', error);
      setError(`Ошибка при обработке Excel файла: ${error.message}`);
    } finally {
      setIsLoadingFile(false);
      setLoadingProgress('');
      
      // Сброс input для возможности повторного выбора
      if (excelInputRef.current) {
        excelInputRef.current.value = '';
      }
    }
  };

  const handleAnalyzeExcelMatch = async (matchData: ExcelMatchData) => {
    setIsProcessing(true);
    setError(null);

    try {
      // Конвертируем ExcelMatchData в MatchData
      const formattedMatchData: MatchData = {
        игрок_1: matchData.игрок_1,
        игрок_2: matchData.игрок_2,
        рейтинг_1: matchData.рейтинг_1,
        рейтинг_2: matchData.рейтинг_2,
        счёт: matchData.счёт,
        этап: matchData.этап,
        турнир: matchData.турнир,
        лига: matchData.лига
      };

      // Отправляем запрос на анализ (используем тот же API что и для ручного ввода)
      const authToken = localStorage.getItem('ollamaChat_authToken');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': window.location.origin
      };
      
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const requestData = {
        ...formattedMatchData,
        model: selectedModel // Добавляем выбранную модель
      };
      console.log('🔍 MatchDataInput - Excel данные для отправки:', requestData);
      console.log('🔍 MatchDataInput - Выбранная модель:', selectedModel);

      const response = await fetch('http://localhost:8000/api/v1/ollama/check-trigger', {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Не удалось прочитать текст ошибки');
        throw new Error(`Ошибка запроса: ${response.status} ${response.statusText}. ${errorText}`);
      }      const responseText = await response.text();
      console.log('Raw response from server:', responseText); // Debug
      const responseData = JSON.parse(responseText);
      console.log('Parsed response data:', responseData); // Debug

      // Пытаемся извлечь только analysis из ответа
      let analysisText = '';
      console.log('MatchDataInput - responseData:', responseData); // Debug
      
      if (responseData.analysis) {
        // Если есть поле analysis - используем его
        analysisText = responseData.analysis;
        console.log('MatchDataInput - Found direct analysis field:', analysisText); // Debug
      } else if (responseData.ollama_response) {
        // Если есть ollama_response, пытаемся извлечь analysis из JSON
        console.log('MatchDataInput - ollama_response:', responseData.ollama_response); // Debug
        try {
          const ollamaData = JSON.parse(responseData.ollama_response);
          console.log('MatchDataInput - Parsed ollama_response:', ollamaData); // Debug
          analysisText = ollamaData.analysis || responseData.ollama_response;
          console.log('MatchDataInput - Extracted analysis:', analysisText); // Debug
        } catch (parseError) {
          console.log('MatchDataInput - JSON parsing failed, trying regex extraction...'); // Debug
          // Попытка извлечь анализ из поврежденного JSON с помощью регулярного выражения
          const analysisMatch = responseData.ollama_response.match(/"analysis"\s*:\s*"([^"]*(?:\\.[^"]*)*)"?/);
          if (analysisMatch && analysisMatch[1]) {
            analysisText = analysisMatch[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').replace(/\\\\/g, '\\');
            console.log('MatchDataInput - Extracted analysis via regex:', analysisText); // Debug
          } else {
            // Если не JSON, используем как есть
            analysisText = responseData.ollama_response;
            console.log('MatchDataInput - Using ollama_response as is:', analysisText); // Debug
          }
        }
      } else {
        analysisText = 'Анализ не найден в ответе сервера';
        console.log('MatchDataInput - No analysis found'); // Debug
      }

      const finalResponse: TriggerResponse = {
        context: responseData.context || '',
        ollama_response: analysisText
      };

      // Вызываем callback с результатами
      onSubmit(formattedMatchData, finalResponse);

    } catch (error: any) {
      console.error('Ошибка при анализе матча:', error);
      setError(`Ошибка при анализе матча: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="match-data-input-modal" onClick={(e) => {
      if (e.target === e.currentTarget) onClose();
    }}>
      <div className="match-data-input">
        <button type="button" className="close-btn" onClick={onClose}>×</button>
        
        {!inputMode && (
          <div className="input-mode-selection">
            <h3>Выберите способ ввода данных матча</h3>
            <div className="mode-buttons">              <button 
                type="button"
                className="mode-button manual-mode"
                onClick={() => setInputMode('manual')}
              >
                <i className="bi bi-keyboard"></i>
                <span>Ручной ввод</span>
                <small>Введите данные матча вручную</small>
              </button>              <button 
                type="button"
                className="mode-button excel-mode"
                onClick={() => {
                  console.log('Excel button clicked'); // Debug
                  console.log('ExcelInputRef:', excelInputRef.current); // Debug
                  // Сразу открываем диалог выбора файла
                  if (excelInputRef.current) {
                    excelInputRef.current.click();
                  } else {
                    console.error('ExcelInputRef is null');
                  }
                }}
                disabled={isProcessing}
              >
                <i className="bi bi-table"></i>
                <span>Excel файл</span>
                <small>Загрузите данные из Excel файла</small>
              </button>
            </div>
            
            {/* Скрытый input для выбора Excel файлов */}
            <input 
              type="file"
              ref={excelInputRef}
              style={{ display: 'none' }}
              onChange={handleExcelFileSelect}
              accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
            />
          </div>
        )}
        
        {inputMode === 'manual' && (
          <div className="manual-input-container">
            <button 
              type="button" 
              className="back-button"
              onClick={() => setInputMode(null)}
            >
              ← Назад
            </button>
            <MatchTriggerForm 
              onClose={onClose}
              onSubmit={onSubmit}
              selectedModel={selectedModel}
            />
          </div>
        )}
          {inputMode === 'excel' && isLoadingFile && (
          <div className="file-loading-container">
            <button 
              type="button" 
              className="back-button"
              onClick={() => {
                setInputMode(null);
                setIsLoadingFile(false);
                setLoadingProgress('');
                setError(null);
              }}
            >
              ← Отменить
            </button>            <div className="file-loading-content">
              <div className="file-loading-icon">
                <i className="bi bi-cloud-upload loading-pulse"></i>
              </div>
              <h3>Обрабатываем Excel файл</h3>
              <div className="loading-progress">
                <div className="progress-bar">
                  <div className="progress-bar-fill"></div>
                </div>
                <p className="progress-text">{loadingProgress}</p>
              </div>
              <div className="loading-tips">
                <p><strong>Совет:</strong> Большие файлы могут занять несколько секунд для обработки.</p>
                <p>Пожалуйста, подождите...</p>
              </div>
            </div>
          </div>
        )}
        
        {inputMode === 'excel' && excelData.length > 0 && !isLoadingFile && (
          <div className="excel-input-container">            <button 
              type="button" 
              className="back-button"
              onClick={() => {
                setInputMode(null);
                setExcelData([]);
                setIsLoadingFile(false);
                setLoadingProgress('');
                setError(null);
              }}
            >
              ← Назад
            </button>
            <h3>Данные из Excel файла</h3>
            <p>Найдено матчей: {excelData.length}</p>
            
            {excelData.length > 1 && (
              <div className="match-selector">
                <label>Выберите матч для анализа:</label>
                <select 
                  value={selectedMatch} 
                  onChange={(e) => setSelectedMatch(Number(e.target.value))}
                  disabled={isProcessing}
                >
                  {excelData.map((match, index) => (
                    <option key={index} value={index}>
                      {match.игрок_1} vs {match.игрок_2} ({match.счёт})
                    </option>
                  ))}
                </select>
              </div>
            )}
              {excelData[selectedMatch] && (
              <div className="match-preview">
                <h4>Предпросмотр матча:</h4>
                <div className="match-details">
                  <p><strong>Игроки:</strong> {excelData[selectedMatch].игрок_1} vs {excelData[selectedMatch].игрок_2}</p>
                  <p><strong>Счёт:</strong> {excelData[selectedMatch].счёт}</p>
                  <p><strong>Стадия:</strong> {excelData[selectedMatch].этап}</p>
                  <p><strong>Турнир:</strong> {excelData[selectedMatch].турнир}</p>
                  <p><small><em>Рейтинги: {excelData[selectedMatch].рейтинг_1} / {excelData[selectedMatch].рейтинг_2} (по умолчанию)</em></small></p>
                </div>
                
                <button 
                  type="button"
                  className="analyze-button"
                  onClick={() => handleAnalyzeExcelMatch(excelData[selectedMatch])}
                  disabled={isProcessing}
                >
                  {isProcessing ? 'Анализируем...' : 'Анализировать матч'}
                </button>
              </div>
            )}
            
            <button 
              type="button"
              className="select-file-button"
              onClick={() => excelInputRef.current?.click()}
              disabled={isProcessing}
            >
              Выбрать другой файл
            </button>
          </div>
        )}
          {inputMode === 'excel' && excelData.length === 0 && !isLoadingFile && (
          <div className="excel-input-container">
            <button 
              type="button" 
              className="back-button"
              onClick={() => setInputMode(null)}
            >
              ← Назад
            </button>
            <h3>Обработка Excel файла</h3>
            <p>Выберите Excel файл с данными о матчах.</p>            <div className="file-format-info">
              <h4>Формат файла:</h4>
              <p>Excel файл должен содержать колонки с названиями:</p>
              <ul>
                <li><strong>Игрок 1</strong> - Полное имя и рейтинг первого игрока<br/>
                    <small><em>Пример: "Лбов Юрий Вячеславович rating: 476.81"</em></small></li>
                <li><strong>Счёт</strong> - Результат матча с детализацией<br/>
                    <small><em>Пример: "2-3 (4-11 11-6 11-4 8-11 6-11)"</em></small></li>
                <li><strong>Игрок 2</strong> - Полное имя и рейтинг второго игрока<br/>
                    <small><em>Пример: "Малиновский Роман Александрович rating: 464.68"</em></small></li>
                <li><strong>Стадия</strong> - Этап турнира<br/>
                    <small><em>Пример: "Группа"</em></small></li>
                <li><strong>Турнир</strong> - Название турнира и лига<br/>
                    <small><em>Пример: "Турнир А5. Лига 450-500"</em></small></li>
              </ul>
              <p><small>Система автоматически извлечет имена игроков, их рейтинги, название турнира и лигу из этого формата.</small></p>
            </div>
            
            <div className="file-actions">
              <button 
                type="button"
                className="download-example-button"
                onClick={downloadExampleExcelFile}
              >
                📥 Скачать пример файла
              </button>
              
              <button 
                type="button"
                className="select-file-button"
                onClick={() => excelInputRef.current?.click()}
              >
                📁 Выбрать свой файл
              </button>
            </div>
          </div>
        )}
          {isProcessing && !isLoadingFile && (
          <div className="processing-overlay">
            <div className="loading-spinner"></div>
            <p>Анализируем матч...</p>
          </div>
        )}
        
        {error && (
          <div className="error-message">
            <strong>Ошибка:</strong> {error}
            <button 
              type="button" 
              className="dismiss-error"
              onClick={() => setError(null)}
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MatchDataInput;
