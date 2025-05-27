import React from 'react';
import { FileAttachment as FileAttachmentType } from '../types/chat';
import './FileAttachment.css';

interface FileAttachmentProps {
  file: FileAttachmentType;
  onRemove?: () => void; // Опциональный обработчик удаления
}

const FileAttachment: React.FC<FileAttachmentProps> = ({ file, onRemove }) => {
  // Форматирование размера файла
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    else if (bytes < 1073741824) return (bytes / 1048576).toFixed(1) + ' MB';
    else return (bytes / 1073741824).toFixed(1) + ' GB';
  };

  // Определение иконки на основе типа файла
  const getFileIcon = (type: string): string => {
    if (type.startsWith('image/')) return 'bi-file-image';
    if (type === 'application/pdf') return 'bi-file-pdf';
    if (type.includes('word')) return 'bi-file-word';
    if (type.includes('excel') || type.includes('spreadsheet')) return 'bi-file-excel';
    if (type.includes('presentation') || type.includes('powerpoint')) return 'bi-file-ppt';
    if (type.includes('text/')) return 'bi-file-text';
    if (type.includes('zip') || type.includes('compressed')) return 'bi-file-zip';
    return 'bi-file';
  };

  // Обработчик открытия файла
  const handleOpen = () => {
    if (file.dataUrl) {
      window.open(file.dataUrl, '_blank');
    } else if (file.url) {
      window.open(file.url, '_blank');
    }
  };

  return (
    <div className="file-attachment">
      {/* Предпросмотр для изображений */}
      {file.type.startsWith('image/') && file.dataUrl && (
        <div className="file-preview" onClick={handleOpen}>
          <img src={file.dataUrl} alt={file.name} />
        </div>
      )}
      
      {/* Информация о файле */}
      <div className="file-info" onClick={handleOpen}>
        <i className={`bi ${getFileIcon(file.type)}`}></i>
        <div className="file-details">
          <div className="file-name">{file.name}</div>
          <div className="file-size">{formatFileSize(file.size)}</div>
        </div>
      </div>
      
      {/* Кнопка удаления, если предоставлен обработчик */}
      {onRemove && (
        <button className="file-remove" onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}>
          <i className="bi bi-x"></i>
        </button>
      )}
    </div>
  );
};

export default FileAttachment;
