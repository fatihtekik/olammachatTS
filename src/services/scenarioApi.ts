/**
 * API сервис для работы со сценарным анализом
 */
import {
  PlayerScenariosResponse,
  ScenarioMatchDetail,
  AnalyzePlayerResponse,
  ScenarioCode,
} from '../types/scenario';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Получение токена авторизации
const getAuthToken = () => localStorage.getItem('ollamaChat_authToken');

// Заголовки для запросов
const getHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

/**
 * API для работы со сценариями
 */
export const scenarioAPI = {
  /**
   * Получить статистику по всем сценариям для игрока
   */
  async getPlayerScenarios(playerId: string): Promise<PlayerScenariosResponse> {
    const response = await fetch(`${API_BASE_URL}/player/${playerId}/scenarios`, {
      method: 'GET',
      headers: getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch player scenarios: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Получить детальный список матчей для конкретного сценария
   */
  async getScenarioMatches(
    playerId: string,
    scenarioCode: ScenarioCode
  ): Promise<ScenarioMatchDetail[]> {
    const response = await fetch(
      `${API_BASE_URL}/player/${playerId}/scenarios/${scenarioCode}/matches`,
      {
        method: 'GET',
        headers: getHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch scenario matches: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Запустить анализ матчей игрока
   */
  async analyzePlayer(playerId: string): Promise<AnalyzePlayerResponse> {
    const response = await fetch(`${API_BASE_URL}/player/${playerId}/scenarios/analyze`, {
      method: 'POST',
      headers: getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to analyze player: ${response.statusText}`);
    }

    return response.json();
  },

  /**
   * Запустить анализ для всех игроков
   */
  async analyzeAllPlayers(): Promise<any> {
    const response = await fetch(`${API_BASE_URL}/scenarios/analyze-all`, {
      method: 'POST',
      headers: getHeaders(),
    });

    if (!response.ok) {
      throw new Error(`Failed to analyze all players: ${response.statusText}`);
    }

    return response.json();
  },
};

/**
 * Утилиты для работы со сценариями
 */
export const scenarioUtils = {
  /**
   * Получить цвет для Fight Score
   */
  getFightScoreColor(fightScore: number | null): string {
    if (fightScore === null) return '#999';
    if (fightScore >= 0.7) return '#22c55e'; // green
    if (fightScore >= 0.5) return '#eab308'; // yellow
    if (fightScore >= 0.3) return '#f97316'; // orange
    return '#ef4444'; // red
  },

  /**
   * Получить цвет для процента побед
   */
  getWinRateColor(winRate: number): string {
    if (winRate >= 60) return '#22c55e'; // green
    if (winRate >= 40) return '#eab308'; // yellow
    return '#ef4444'; // red
  },

  /**
   * Получить короткое описание поведения
   */
  getBehaviorBadgeColor(label: string): string {
    if (label.includes('Сыпется')) return '#ef4444';
    if (label.includes('Проблемы')) return '#f97316';
    if (label.includes('Слабая')) return '#f97316';
    if (label.includes('Не держит')) return '#f97316';
    if (label.includes('борьбу')) return '#eab308';
    if (label.includes('Равный')) return '#22c55e';
    return '#6b7280';
  },

  /**
   * Форматировать дату
   */
  formatDate(dateString: string | null): string {
    if (!dateString) return 'Н/Д';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  },
};
