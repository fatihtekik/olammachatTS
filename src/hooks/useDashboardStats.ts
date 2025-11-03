/**
 * Хуки для работы с данными дашборда и статистикой
 */

import { useState, useEffect, useCallback } from 'react';

interface DashboardStats {
  total_players: number;
  total_matches: number;
  active_triggers: number;
  recent_uploads: number;
  last_upload_date?: string;
  last_analysis_date?: string;
}

const CACHE_KEY = 'dashboard_stats_cache';
const CACHE_DURATION = 5 * 60 * 1000; // 5 минут

interface CachedData {
  data: DashboardStats;
  timestamp: number;
}

/**
 * Хук для получения статистики дашборда
 */
export function useDashboardStats() {
  const [stats, setStats] = useState<DashboardStats>({
    total_players: 0,
    total_matches: 0,
    active_triggers: 0,
    recent_uploads: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async (forceRefresh: boolean = false) => {
    try {
      setLoading(true);
      setError(null);

      // Проверяем кеш
      if (!forceRefresh) {
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          const { data, timestamp }: CachedData = JSON.parse(cached);
          const age = Date.now() - timestamp;
          
          if (age < CACHE_DURATION) {
            console.log('📦 Using cached dashboard stats');
            setStats(data);
            setLoading(false);
            return;
          }
        }
      }

      // Загружаем свежие данные
      console.log('🔄 Fetching fresh dashboard stats');
      const response = await fetch('http://localhost:8000/api/v1/match-analysis/dashboard-stats');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setStats(data);

      // Сохраняем в кеш
      const cacheData: CachedData = {
        data,
        timestamp: Date.now()
      };
      localStorage.setItem(CACHE_KEY, JSON.stringify(cacheData));
      
    } catch (err) {
      console.error('❌ Failed to load dashboard stats:', err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return {
    stats,
    loading,
    error,
    refresh: () => loadStats(true)
  };
}

/**
 * Хук для инвалидации кеша статистики
 * Вызывать после загрузки файла или нового анализа
 */
export function useInvalidateStats() {
  return useCallback(() => {
    console.log('🗑️ Invalidating stats cache');
    localStorage.removeItem(CACHE_KEY);
  }, []);
}
