import { ChatSession } from '../types/chat';

// Имя базы данных
const DB_NAME = 'ollamaChat';
const STORE_NAME = 'chatSessions';
const DB_VERSION = 1;

// Открытие соединения с базой данных
const openDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = (event) => {
      console.error('IndexedDB error:', event);
      reject(new Error('Could not open IndexedDB'));
    };
    
    request.onsuccess = (event) => {
      resolve((event.target as IDBOpenDBRequest).result);
    };
    
    // Создание структуры базы при первом открытии
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      // Создание хранилища для сессий чата
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        // Создание индексов для быстрого поиска
        store.createIndex('createdAt', 'createdAt', { unique: false });
        store.createIndex('updatedAt', 'updatedAt', { unique: false });
      }
    };
  });
};

// Максимальный размер для localStorage
const MAX_LOCAL_STORAGE_SIZE = 100 * 1024 * 1024; // 5MB

// Сохранение всех сессий
export const saveSessions = async (sessions: ChatSession[], activeSessionId: string | null): Promise<void> => {
  try {
    // Кодирование больших вложений для хранения
    const preparedSessions = sessions.map(session => {
      // Глубокое клонирование сессии для безопасного изменения
      const clonedSession = JSON.parse(JSON.stringify(session));
      
      // Обработка вложений в сообщениях для оптимизации размера
      if (clonedSession.messages) {
        clonedSession.messages = clonedSession.messages.map((msg: any) => {
          if (msg.attachments && msg.attachments.length > 0) {
            // Для больших файлов сохраняем только метаданные в localStorage
            msg.attachments = msg.attachments.map((att: any) => {
              // Если размер dataUrl больше 500KB, переносим в IndexedDB
              if (att.dataUrl && att.dataUrl.length > 500 * 1024) {
                // Сохраняем информацию, что файл большой и его нужно загрузить из IndexedDB
                const shortAtt = { ...att };
                delete shortAtt.dataUrl;
                shortAtt.largeFile = true;
                return shortAtt;
              }
              return att;
            });
          }
          return msg;
        });
      }
      
      return clonedSession;
    });

    const db = await openDB();
    const transaction = db.transaction(STORE_NAME, 'readwrite');
    const store = transaction.objectStore(STORE_NAME);
    
    // Сначала очистим хранилище
    await new Promise<void>((resolve, reject) => {
      const clearRequest = store.clear();
      clearRequest.onsuccess = () => resolve();
      clearRequest.onerror = () => reject(new Error('Failed to clear sessions store'));
    });
    
    // Сохраним сессии с полными данными в IndexedDB
    for (const session of sessions) {
      store.put(session);
    }
    
    // Сохраняем активную сессию в localStorage
    localStorage.setItem('ollamaChat_activeSessionId', activeSessionId || '');
    
    // Пытаемся сохранить оптимизированные сессии в localStorage в качестве резервной копии
    try {
      const json = JSON.stringify(preparedSessions);
      // Проверяем, не превышает ли размер лимит localStorage
      if (json.length < MAX_LOCAL_STORAGE_SIZE) {
        localStorage.setItem('ollamaChat_sessions', json);
      }
    } catch (e) {
      console.warn('Failed to save backup to localStorage, data may be too large:', e);
    }
    
    return new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => {
        console.log('Sessions saved to IndexedDB');
        resolve();
      };
      transaction.onerror = (event) => {
        console.error('Error saving sessions to IndexedDB:', event);
        reject(new Error('Failed to save sessions'));
      };
    });
  } catch (error) {
    console.error('Error saving to IndexedDB:', error);
    throw error;
  }
};

// Загрузка всех сессий
export const loadSessions = async (): Promise<{ sessions: ChatSession[], activeSessionId: string | null }> => {
  try {
    const db = await openDB();
    const transaction = db.transaction(STORE_NAME, 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    
    return new Promise((resolve, reject) => {
      const request = store.getAll();
      
      request.onsuccess = () => {
        const sessions = request.result;
        // Преобразование дат из строк в объекты Date
        const processedSessions = sessions.map((session: any) => ({
          ...session,
          createdAt: new Date(session.createdAt),
          updatedAt: new Date(session.updatedAt),
          messages: session.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
        
        // Получение activeSessionId из localStorage
        const activeSessionId = localStorage.getItem('ollamaChat_activeSessionId') || null;
        
        resolve({
          sessions: processedSessions,
          activeSessionId
        });
      };
      
      request.onerror = (event) => {
        console.error('Error loading sessions from IndexedDB:', event);
        reject(new Error('Failed to load sessions'));
      };
    });
  } catch (error) {
    console.error('Error accessing IndexedDB:', error);
    
    // Резервный вариант - загрузка из localStorage
    const sessionsJson = localStorage.getItem('ollamaChat_sessions');
    const activeSessionId = localStorage.getItem('ollamaChat_activeSessionId') || null;
    
    if (sessionsJson) {
      try {
        const sessions = JSON.parse(sessionsJson);
        // Преобразование дат из строк в объекты Date
        const processedSessions = sessions.map((session: any) => ({
          ...session,
          createdAt: new Date(session.createdAt),
          updatedAt: new Date(session.updatedAt),
          messages: session.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
        
        return { sessions: processedSessions, activeSessionId };
      } catch (e) {
        console.error('Error parsing sessions from localStorage:', e);
      }
    }
    
    // Если всё пошло не так, возвращаем пустой массив
    return { sessions: [], activeSessionId: null };
  }
};

// Автоматический экспорт истории чата в файл
export const exportSessionsToFile = (sessions: ChatSession[]): void => {
  try {
    if (sessions.length === 0) return;
    
    const dataStr = JSON.stringify(sessions, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `ollama-chat-backup-${new Date().toISOString().slice(0, 10)}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.style.display = 'none';
    document.body.appendChild(linkElement);
    linkElement.click();
    document.body.removeChild(linkElement);
    
    console.log('Chat history exported to file:', exportFileDefaultName);
  } catch (error) {
    console.error('Error exporting sessions to file:', error);
  }
};

// Загрузка истории чата из файла
export const importSessionsFromFile = (file: File): Promise<ChatSession[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string;
        const sessions = JSON.parse(content);
        
        // Валидация и преобразование дат
        const processedSessions = sessions.map((session: any) => ({
          ...session,
          createdAt: new Date(session.createdAt),
          updatedAt: new Date(session.updatedAt),
          messages: session.messages.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }))
        }));
        
        resolve(processedSessions);
      } catch (error) {
        console.error('Error parsing imported file:', error);
        reject(new Error('Invalid file format'));
      }
    };
    
    reader.onerror = () => {
      reject(new Error('Error reading file'));
    };
    
    reader.readAsText(file);
  });
};
