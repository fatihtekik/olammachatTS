/**
 * Универсальный API для работы с AI провайдерами (Ollama и LM Studio)
 */

import { ModelType } from '../types/chat';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export type AIProvider = 'ollama' | 'lmstudio';

// Получение заголовков с токеном авторизации
const getHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const authToken = localStorage.getItem('ollamaChat_authToken');
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  return headers;
};

/**
 * Получить текущий провайдер из localStorage
 */
export function getCurrentProvider(): AIProvider {
  return (localStorage.getItem('aiProvider') as AIProvider) || 'ollama';
}

/**
 * Установить текущий провайдер в localStorage
 */
export function setCurrentProvider(provider: AIProvider): void {
  localStorage.setItem('aiProvider', provider);
}

/**
 * Проверка подключения к провайдеру
 */
export async function testProviderConnection(provider: AIProvider): Promise<boolean> {
  try {
    const endpoint = provider === 'ollama' ? '/ollama/status' : '/ollama/lmstudio/status';
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    const data = await response.json();
    return data.status === 'connected';
  } catch (error) {
    console.error(`Error testing ${provider} connection:`, error);
    return false;
  }
}

/**
 * Получить список доступных моделей для провайдера
 */
export async function getAvailableModelsForProvider(
  provider: AIProvider
): Promise<{ id: string; name: string }[]> {
  try {
    const endpoint = provider === 'ollama' ? '/ollama/models' : '/ollama/lmstudio/models';
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: getHeaders(),
    });

    if (!response.ok) {
      console.error(`Failed to fetch models for ${provider}:`, response.status);
      return [];
    }

    const models = await response.json();
    return models;
  } catch (error) {
    console.error(`Error fetching models for ${provider}:`, error);
    return [];
  }
}

/**
 * Получить список моделей для текущего активного провайдера
 */
export async function getAvailableModels(): Promise<{ id: string; name: string }[]> {
  const provider = getCurrentProvider();
  return getAvailableModelsForProvider(provider);
}

/**
 * Проверка подключения к текущему провайдеру
 */
export async function testConnection(): Promise<boolean> {
  const provider = getCurrentProvider();
  return testProviderConnection(provider);
}
