import { Message, ChatSession } from '../types/chat';

// Базовый URL для API
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Токен авторизации (будет устанавливаться после авторизации)
let authToken: string | null = localStorage.getItem('ollamaChat_authToken');

// Заголовки для запросов
const getHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  return headers;
};

// Тип для данных пользователя
export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

// Сервис аутентификации
export const authAPI = {
  // Регистрация нового пользователя
  async register(email: string, username: string, password: string, fullName?: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          username,
          password,
          full_name: fullName,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Ошибка при регистрации');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка регистрации:', error);
      throw error;
    }
  },
  // Авторизация пользователя
  async login(username: string, password: string) {
    try {
      console.log(`Авторизация пользователя: ${username}`);
      // Для OAuth2 схемы FastAPI требуется отправка данных в формате формы
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      console.log('Статус ответа на авторизацию:', response.status);
      
      if (!response.ok) {
        let errorMessage = 'Ошибка при авторизации';
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // Если ответ не может быть распарсен как JSON
          const errorText = await response.text();
          errorMessage = errorText || errorMessage;
        }
        console.error('Ошибка авторизации:', errorMessage);
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('Токен получен успешно');
      
      // Сохраняем токен в localStorage и переменной authToken
      localStorage.setItem('ollamaChat_authToken', data.access_token);
      authToken = data.access_token;

      return data;
    } catch (error) {
      console.error('Ошибка авторизации:', error);
      throw error;
    }
  },

  // Выход из системы
  logout() {
    localStorage.removeItem('ollamaChat_authToken');
    authToken = null;
  },

  // Проверка авторизован ли пользователь
  isAuthenticated() {
    return !!authToken;
  },

  // Получение профиля пользователя
  async getProfile() {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        headers: getHeaders(),
      });

      if (!response.ok) {
        throw new Error('Ошибка при получении профиля пользователя');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка получения профиля:', error);
      throw error;
    }
  },
};

// Сервис для работы с сессиями чата
export const chatAPI = {
  // Получение всех сессий пользователя
  async getSessions() {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/`, {
        headers: getHeaders(),
      });

      if (!response.ok) {
        if (response.status === 401) {
          authToken = null;
          localStorage.removeItem('ollamaChat_authToken');
        }
        throw new Error('Ошибка при получении сессий чата');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка получения сессий:', error);
      throw error;
    }
  },

  // Получение конкретной сессии по ID
  async getSessionById(sessionId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}/`, {
        headers: getHeaders(),
      });

      if (!response.ok) {
        throw new Error('Ошибка при получении сессии чата');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка получения сессии:', error);
      throw error;
    }
  },

  // Создание новой сессии
  async createSession(title: string, model: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          title,
          model,
          messages: []
        }),
      });

      if (!response.ok) {
        throw new Error('Ошибка при создании сессии чата');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка создания сессии:', error);
      throw error;
    }
  },
  // Обновление сессии
  async updateSession(sessionId: string, title?: string, model?: string) {
    try {
      const updateData: { title?: string; model?: string } = {};
      if (title) updateData.title = title;
      if (model) updateData.model = model;

      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}/`, {
        method: 'PUT', // Changed from PATCH to PUT to match backend
        headers: getHeaders(),
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        throw new Error('Ошибка при обновлении сессии чата');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка обновления сессии:', error);
      throw error;
    }
  },

  // Удаление сессии
  async deleteSession(sessionId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}/`, {
        method: 'DELETE',
        headers: getHeaders(),
      });

      if (!response.ok) {
        throw new Error('Ошибка при удалении сессии чата');
      }

      return true;
    } catch (error) {
      console.error('Ошибка удаления сессии:', error);
      throw error;
    }
  },

  // Получение сообщений для сессии
  async getMessages(sessionId: string) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}/messages/`, {
        headers: getHeaders(),
      });

      if (!response.ok) {
        throw new Error('Ошибка при получении сообщений');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка получения сообщений:', error);
      throw error;
    }
  },

  // Обновление сообщений сессии
  async updateSessionMessages(sessionId: string, messages: any[]) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}/messages/`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify({
          messages: messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            attachments: msg.attachments || []
          }))
        }),
      });

      if (!response.ok) {
        throw new Error('Ошибка при обновлении сообщений');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка обновления сообщений:', error);
      throw error;
    }
  },

  // Добавление нового сообщения в сессию
  async addMessage(sessionId: string, message: any) {
    try {
      const response = await fetch(`${API_BASE_URL}/chat-sessions/${sessionId}/messages/`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({
          role: message.role,
          content: message.content,
          attachments: message.attachments || []
        }),
      });

      if (!response.ok) {
        throw new Error('Ошибка при добавлении сообщения');
      }

      return await response.json();
    } catch (error) {
      console.error('Ошибка добавления сообщения:', error);
      throw error;
    }
  },
};
