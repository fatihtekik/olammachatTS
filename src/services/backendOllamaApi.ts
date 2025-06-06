import { Message, OllamaModel } from '../types/chat';
import { authAPI } from './backendApi';

// Базовый URL для API
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Вспомогательная функция для получения заголовков с авторизацией
const getHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const authToken = localStorage.getItem('ollamaChat_authToken');
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  return headers;
};

// Сервис для работы с Ollama API через бэкенд
export const backendOllamaAPI = {
  // Отправляет сообщение в модель Ollama
  async sendMessage(model: string, messages: Message[]): Promise<string> {
    try {
      // Проверка аутентификации
      if (!localStorage.getItem('ollamaChat_authToken')) {
        throw new Error('Authentication required to use the API');
      }

      console.log(`Preparing to send message to model: ${model}`);

      // Форматируем сообщения для API
      const formattedMessages = messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      // Отправляем запрос к API
      const response = await fetch(`${API_BASE_URL}/ollama/chat`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          model,
          messages: formattedMessages
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error(`Error response from API: ${response.status} - ${errorText}`);
        
        // Обрабатываем ошибки авторизации
        if (response.status === 401) {
          authAPI.logout();
          throw new Error('Сессия истекла. Пожалуйста, войдите снова.');
        }
        
        throw new Error(`API error: ${errorText}`);
      }

      const data = await response.json();
      return data.response;
    } catch (error) {
      console.error('Error communicating with API:', error);
      throw error;
    }
  },

  // Получает список доступных моделей из бэкенда
  async getAvailableModels(): Promise<OllamaModel[]> {
    try {
      // Проверка аутентификации
      if (!localStorage.getItem('ollamaChat_authToken')) {
        return [];
      }
      
      // Получаем модели из API
      const response = await fetch(`${API_BASE_URL}/ollama/models`, {
        headers: getHeaders()
      });
      
      if (!response.ok) {
        console.error(`API error: ${response.status}`);
        return [];
      }
      
      const models = await response.json();
      console.log('Available models from backend:', models);
      
      return models;
    } catch (error) {
      console.error('Error fetching models from API:', error);
      return [];
    }
  },

  // Проверяет соединение с Ollama через бэкенд
  async testConnection(): Promise<boolean> {
    try {
      // Проверка аутентификации
      if (!localStorage.getItem('ollamaChat_authToken')) {
        return false;
      }
      
      const response = await fetch(`${API_BASE_URL}/ollama/status`, {
        headers: getHeaders()
      });
      
      if (!response.ok) {
        return false;
      }
      
      const data = await response.json();
      return data.connected;
    } catch (error) {
      console.error('Cannot connect to Ollama through backend:', error);
      return false;
    }
  },

  // Проверяет, доступна ли указанная модель
  async isModelAvailable(modelName: string): Promise<boolean> {
    try {
      // Проверка аутентификации
      if (!localStorage.getItem('ollamaChat_authToken')) {
        return false;
      }
      
      const response = await fetch(`${API_BASE_URL}/ollama/model/${modelName}/status`, {
        headers: getHeaders()
      });
      
      if (!response.ok) {
        return false;
      }
      
      const data = await response.json();
      return data.available;
    } catch (error) {
      console.error('Error checking model availability:', error);
      return false;
    }
  }
};
