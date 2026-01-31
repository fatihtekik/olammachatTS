/**
 * Сервис для работы с историей H2H анализов через IndexedDB
 */

export interface H2HAnalysisHistory {
  id: string;
  timestamp: number;
  analysisType: 'players' | 'date';
  // Для анализа по игрокам
  player1?: {
    id: string;
    full_name: string;
    current_rating: number;
  };
  player2?: {
    id: string;
    full_name: string;
    current_rating: number;
  };
  matchDate?: string;
  // Для анализа по дате
  dateForAnalysis?: string;
  totalPairs?: number;
  // Общие данные
  totalMatches: number;
  triggersFound: number;
  aiProvider: string;
  aiAnalysis?: string;
  // Сохраняем полные данные для восстановления
  fullData: any;
}

const DB_NAME = 'SportAnalyticsDB';
const H2H_STORE_NAME = 'h2hAnalysisHistory';
const DB_VERSION = 2;
const MAX_HISTORY_ITEMS = 50;

class H2HHistoryService {
  private db: IDBDatabase | null = null;
  private initPromise: Promise<void> | null = null;

  /**
   * Инициализация базы данных (с кэшированием промиса)
   */
  async init(): Promise<void> {
    // Если уже инициализирована
    if (this.db) return;
    
    // Если инициализация уже запущена - ждём её
    if (this.initPromise) return this.initPromise;
    
    this.initPromise = new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => {
        this.initPromise = null;
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        this.initPromise = null;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        
        // Создаем хранилище для H2H истории если его нет
        if (!db.objectStoreNames.contains(H2H_STORE_NAME)) {
          const objectStore = db.createObjectStore(H2H_STORE_NAME, { keyPath: 'id' });
          objectStore.createIndex('timestamp', 'timestamp', { unique: false });
          objectStore.createIndex('analysisType', 'analysisType', { unique: false });
        }
        
        // Также убедимся что основной store существует
        if (!db.objectStoreNames.contains('analysisHistory')) {
          const mainStore = db.createObjectStore('analysisHistory', { keyPath: 'id' });
          mainStore.createIndex('timestamp', 'timestamp', { unique: false });
          mainStore.createIndex('periodStart', 'periodStart', { unique: false });
        }
      };
    });
    
    return this.initPromise;
  }

  /**
   * Сохранить результат H2H анализа
   */
  async saveH2HAnalysis(analysis: Omit<H2HAnalysisHistory, 'id' | 'timestamp'>): Promise<string> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([H2H_STORE_NAME], 'readwrite');
      const store = transaction.objectStore(H2H_STORE_NAME);

      const newAnalysis: H2HAnalysisHistory = {
        id: `h2h_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now(),
        ...analysis
      };

      const request = store.add(newAnalysis);

      request.onsuccess = async () => {
        console.log('✅ H2H Analysis saved to IndexedDB:', newAnalysis.id);
        
        // Очищаем старые записи
        await this.cleanOldRecords();
        
        resolve(newAnalysis.id);
      };

      request.onerror = () => {
        console.error('❌ Error saving H2H analysis:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Получить все сохраненные H2H анализы
   */
  async getAllH2HAnalyses(): Promise<H2HAnalysisHistory[]> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([H2H_STORE_NAME], 'readonly');
      const store = transaction.objectStore(H2H_STORE_NAME);
      const index = store.index('timestamp');
      
      const request = index.openCursor(null, 'prev');
      const results: H2HAnalysisHistory[] = [];

      request.onsuccess = (event) => {
        const cursor = (event.target as IDBRequest).result;
        if (cursor) {
          results.push(cursor.value);
          cursor.continue();
        } else {
          resolve(results);
        }
      };

      request.onerror = () => {
        console.error('❌ Error getting H2H analyses:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Получить H2H анализ по ID
   */
  async getH2HAnalysisById(id: string): Promise<H2HAnalysisHistory | null> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([H2H_STORE_NAME], 'readonly');
      const store = transaction.objectStore(H2H_STORE_NAME);
      const request = store.get(id);

      request.onsuccess = () => {
        resolve(request.result || null);
      };

      request.onerror = () => {
        console.error('❌ Error getting H2H analysis:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Удалить H2H анализ по ID
   */
  async deleteH2HAnalysis(id: string): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([H2H_STORE_NAME], 'readwrite');
      const store = transaction.objectStore(H2H_STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = () => {
        console.log('✅ H2H Analysis deleted:', id);
        resolve();
      };

      request.onerror = () => {
        console.error('❌ Error deleting H2H analysis:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Очистить старые записи
   */
  private async cleanOldRecords(): Promise<void> {
    const allAnalyses = await this.getAllH2HAnalyses();
    
    if (allAnalyses.length > MAX_HISTORY_ITEMS) {
      const toDelete = allAnalyses.slice(MAX_HISTORY_ITEMS);
      
      for (const analysis of toDelete) {
        await this.deleteH2HAnalysis(analysis.id);
      }
      
      console.log(`🧹 Cleaned ${toDelete.length} old H2H records`);
    }
  }

  /**
   * Очистить всю H2H историю
   */
  async clearAll(): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([H2H_STORE_NAME], 'readwrite');
      const store = transaction.objectStore(H2H_STORE_NAME);
      const request = store.clear();

      request.onsuccess = () => {
        console.log('✅ All H2H history cleared');
        resolve();
      };

      request.onerror = () => {
        console.error('❌ Error clearing H2H history:', request.error);
        reject(request.error);
      };
    });
  }
}

// Экспортируем singleton
export const h2hHistoryService = new H2HHistoryService();
