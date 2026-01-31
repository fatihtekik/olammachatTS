/**
 * Сервис для работы с историей анализов через IndexedDB
 */

export interface AnalysisHistory {
  id: string;
  timestamp: number;
  periodStart: string;
  periodEnd: string;
  totalPlayers: number;
  totalMatches: number;
  triggersFound: number;
  triggers: any[];
  aiProvider: string;
  analysisSettings: {
    matchesLimit?: number;
    aiAnalysisEnabled?: boolean;
    selectedModel?: string;
  };
}

const DB_NAME = 'SportAnalyticsDB';
const STORE_NAME = 'analysisHistory';
const DB_VERSION = 2; // Версия 2 для поддержки H2H store
const MAX_HISTORY_ITEMS = 50; // Максимум 50 записей истории

class AnalysisHistoryService {
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
        console.error('IndexedDB error:', request.error);
        reject(request.error);
      };

      request.onsuccess = () => {
        this.db = request.result;
        this.initPromise = null;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result;
        
        // Создаем хранилище если его нет
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const objectStore = db.createObjectStore(STORE_NAME, { keyPath: 'id' });
          objectStore.createIndex('timestamp', 'timestamp', { unique: false });
          objectStore.createIndex('periodStart', 'periodStart', { unique: false });
        }
        
        // H2H store для версии 2+
        if (!db.objectStoreNames.contains('h2hAnalysisHistory')) {
          const h2hStore = db.createObjectStore('h2hAnalysisHistory', { keyPath: 'id' });
          h2hStore.createIndex('timestamp', 'timestamp', { unique: false });
          h2hStore.createIndex('analysisType', 'analysisType', { unique: false });
        }
      };
    });
  }

  /**
   * Сохранить результат анализа
   */
  async saveAnalysis(analysis: Omit<AnalysisHistory, 'id' | 'timestamp'>): Promise<string> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);

      const newAnalysis: AnalysisHistory = {
        id: `analysis_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        timestamp: Date.now(),
        ...analysis
      };

      const request = store.add(newAnalysis);

      request.onsuccess = async () => {
        console.log('✅ Analysis saved to IndexedDB:', newAnalysis.id);
        
        // Очищаем старые записи
        await this.cleanOldRecords();
        
        resolve(newAnalysis.id);
      };

      request.onerror = () => {
        console.error('❌ Error saving analysis:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Получить все сохраненные анализы
   */
  async getAllAnalyses(): Promise<AnalysisHistory[]> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const index = store.index('timestamp');
      
      // Получаем все записи, отсортированные по времени (новые первыми)
      const request = index.openCursor(null, 'prev');
      const results: AnalysisHistory[] = [];

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
        console.error('❌ Error getting analyses:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Получить анализ по ID
   */
  async getAnalysisById(id: string): Promise<AnalysisHistory | null> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.get(id);

      request.onsuccess = () => {
        resolve(request.result || null);
      };

      request.onerror = () => {
        console.error('❌ Error getting analysis:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Удалить анализ по ID
   */
  async deleteAnalysis(id: string): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(id);

      request.onsuccess = () => {
        console.log('✅ Analysis deleted:', id);
        resolve();
      };

      request.onerror = () => {
        console.error('❌ Error deleting analysis:', request.error);
        reject(request.error);
      };
    });
  }

  /**
   * Очистить старые записи, оставить только MAX_HISTORY_ITEMS последних
   */
  private async cleanOldRecords(): Promise<void> {
    const allAnalyses = await this.getAllAnalyses();
    
    if (allAnalyses.length > MAX_HISTORY_ITEMS) {
      const toDelete = allAnalyses.slice(MAX_HISTORY_ITEMS);
      
      for (const analysis of toDelete) {
        await this.deleteAnalysis(analysis.id);
      }
      
      console.log(`🧹 Cleaned ${toDelete.length} old records`);
    }
  }

  /**
   * Получить последние N анализов
   */
  async getRecentAnalyses(limit: number = 10): Promise<AnalysisHistory[]> {
    const allAnalyses = await this.getAllAnalyses();
    return allAnalyses.slice(0, limit);
  }

  /**
   * Очистить всю историю
   */
  async clearAll(): Promise<void> {
    if (!this.db) await this.init();

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([STORE_NAME], 'readwrite');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.clear();

      request.onsuccess = () => {
        console.log('✅ All history cleared');
        resolve();
      };

      request.onerror = () => {
        console.error('❌ Error clearing history:', request.error);
        reject(request.error);
      };
    });
  }
}

// Экспортируем singleton
export const analysisHistoryService = new AnalysisHistoryService();
