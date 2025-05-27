import React, { useState, useRef, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { FileAttachment } from '../types/chat';
import FileAttachmentComponent from './FileAttachment';
import './ChatInput.css';

interface ChatInputProps {
  onSendMessage: (message: string, attachments?: FileAttachment[]) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  isLoading, 
  disabled = false,
  placeholder = "Введите сообщение..."
}) => {
  const [input, setInput] = useState<string>('');
  const [attachments, setAttachments] = useState<FileAttachment[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Авто-увеличение высоты textarea при вводе текста
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if ((input.trim() || attachments.length > 0) && !isLoading && !disabled) {
      onSendMessage(input, attachments.length > 0 ? attachments : undefined);
      setInput('');
      setAttachments([]);
      
      // Сбросить высоту текстового поля
      if (textareaRef.current) {
        setTimeout(() => {
          textareaRef.current!.style.height = 'auto';
        }, 0);
      }
    }
  };

  // Обработчик выбора файлов
  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const newAttachments: FileAttachment[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      // Чтение файла как DataURL для сохранения и отображения
      const dataUrl = await readFileAsDataURL(file);
      // Создание превью для изображений
      const preview = file.type.startsWith('image/') ? dataUrl : undefined;
      
      newAttachments.push({
        id: uuidv4(),
        name: file.name,
        type: file.type,
        size: file.size,
        dataUrl,
        preview
      });
    }
    
    setAttachments(prev => [...prev, ...newAttachments]);
    
    // Сброс input для возможности повторного выбора тех же файлов
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Функция для чтения файла как DataURL
  const readFileAsDataURL = (file: File): Promise<string> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        resolve(e.target!.result as string);
      };
      reader.readAsDataURL(file);
    });
  };

  // Удаление вложения
  const removeAttachment = (id: string) => {
    setAttachments(prev => prev.filter(attachment => attachment.id !== id));
  };

  return (
    <form className="chat-input-container" onSubmit={handleSubmit}>
      {/* Область для отображения вложений */}
      {attachments.length > 0 && (
        <div className="attachments-container">
          {attachments.map(attachment => (
            <FileAttachmentComponent 
              key={attachment.id} 
              file={attachment} 
              onRemove={() => removeAttachment(attachment.id)} 
            />
          ))}
        </div>
      )}
      
      <div className="input-row">
        {/* Кнопка для прикрепления файлов */}
        <button 
          type="button"
          className="attach-button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading || disabled}
        >
          <i className="bi bi-paperclip"></i>
        </button>
        
        {/* Скрытый input для выбора файлов */}
        <input 
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileSelect}
          multiple
          accept="image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        />
        
        {/* Текстовое поле для ввода сообщения */}
        <textarea
          ref={textareaRef}
          className={`chat-textarea ${disabled ? 'disabled' : ''}`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          disabled={isLoading || disabled}
          rows={1}
        />
        
        {/* Кнопка отправки */}
        <button 
          type="submit" 
          className="send-button"
          disabled={(input.trim() === '' && attachments.length === 0) || isLoading || disabled}
        >
          {isLoading ? (
            <span className="loading-spinner-small"></span>
          ) : (
            <>
              <i className="bi bi-send"></i>
              Отправить
            </>
          )}
        </button>
      </div>
      
      {input.length > 0 && (
        <div className="input-hints">
          Enter — отправить, Shift+Enter — новая строка
        </div>
      )}
    </form>
  );
};

export default ChatInput;
