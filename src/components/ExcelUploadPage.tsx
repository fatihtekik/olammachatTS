import React, { useState, useRef } from 'react';
import { parseExcelFile, ExcelMatchData } from '../utils/excelParser';
import { downloadExampleExcelFile } from '../utils/excelHelpers';
import './ExcelUploadPage.css';

const ExcelUploadPage: React.FC = () => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedData, setUploadedData] = useState<ExcelMatchData[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    if (file.type !== 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' && 
        file.type !== 'application/vnd.ms-excel') {
      setError('Пожалуйста, выберите файл Excel (.xlsx или .xls)');
      return;
    }

    processFile(file);
  };

  const processFile = async (file: File) => {
    setIsProcessing(true);
    setError(null);
    
    try {
      const data = await parseExcelFile(file);
      setUploadedData(data);
      
      if (data.length === 0) {
        setError('Файл не содержит данных для анализа');
      }
    } catch (err: any) {
      setError(err.message || 'Ошибка при обработке файла');
    } finally {
      setIsProcessing(false);
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

  const handleAnalyzeAll = () => {
    // TODO: Реализовать массовый анализ всех матчей
    console.log('Analyzing all matches:', uploadedData);
    alert('Функция массового анализа будет реализована в следующих версиях');
  };

  const handleReset = () => {
    setUploadedData([]);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="excel-upload-page">
      <div className="upload-header">
        <h1>Загрузка данных из Excel</h1>
        <p>Загрузите файл Excel с данными матчей для массового анализа</p>
      </div>

      {uploadedData.length === 0 ? (
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
                <h3>Перетащите файл Excel сюда</h3>
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
        <div className="data-preview-section">
          <div className="preview-header">
            <h2>Загружено {uploadedData.length} матчей</h2>
            <div className="preview-actions">
              <button onClick={handleAnalyzeAll} className="analyze-all-btn">
                <i className="bi bi-play-circle"></i>
                Анализировать все
              </button>
              <button onClick={handleReset} className="reset-btn">
                <i className="bi bi-arrow-clockwise"></i>
                Загрузить другой файл
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>№</th>
                  <th>Игрок 1</th>
                  <th>Рейтинг 1</th>
                  <th>Игрок 2</th>
                  <th>Рейтинг 2</th>
                  <th>Счёт</th>
                  <th>Турнир</th>
                  <th>Этап</th>
                  <th>Лига</th>
                </tr>
              </thead>
              <tbody>
                {uploadedData.map((match, index) => (
                  <tr key={index}>
                    <td>{index + 1}</td>
                    <td>{match.игрок_1}</td>
                    <td>{match.рейтинг_1}</td>
                    <td>{match.игрок_2}</td>
                    <td>{match.рейтинг_2}</td>
                    <td>{match.счёт}</td>
                    <td>{match.турнир}</td>
                    <td>{match.этап}</td>
                    <td>{match.лига}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExcelUploadPage;
