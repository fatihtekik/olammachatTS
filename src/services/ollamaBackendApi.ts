import { ModelType, Message, LMStudioSettings } from '../types/chat';
import { authAPI } from './backendApi';

// Backend API URL (прокси через бэкенд к Ollama)
const API_BASE_URL = 'http://localhost:8000/api/v1';

// List of large models that need special handling
const LARGE_MODELS: string[] = ['deepseek', 'llama3-70b', 'mixtral-8x7b', 'qwen', 'solar-10b'];

// Helper function to check if a model is considered "large" and needs special handling
export function isLargeModel(modelName: string): boolean {
  return LARGE_MODELS.some((name: string) => 
    modelName.toLowerCase().includes(name.toLowerCase())
  );
}

// Получение настроек LM Studio из localStorage
export function getLMStudioSettings(): LMStudioSettings | null {
  try {
    const saved = localStorage.getItem('lmstudio_settings');
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    console.error('Error loading LM Studio settings:', e);
  }
  return null;
}

// Заголовки для запросов
const getHeaders = () => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  const authToken = localStorage.getItem('ollamaChat_authToken');
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
    console.log('Using auth token for request:', authToken.substring(0, 10) + '...');
  } else {
    console.warn('No auth token found in localStorage');
  }

  return headers;
};

export async function sendMessage(
  model: ModelType,
  messages: Message[],
  provider?: 'ollama' | 'lmstudio'
): Promise<string> {
  try {
    // Получаем текущий провайдер из localStorage, если не передан явно
    const currentProvider = provider || (localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio') || 'ollama';
    
    console.log(`Preparing to send message to model: ${model} via ${currentProvider}`);
    
    // Format messages for API
    const formattedMessages = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // Выбираем правильный эндпоинт в зависимости от провайдера
    const endpoint = currentProvider === 'lmstudio' ? '/ollama/lmstudio/chat' : '/ollama/chat';
    
    // Получаем настройки LM Studio если это lmstudio провайдер
    const lmstudioSettings = currentProvider === 'lmstudio' ? getLMStudioSettings() : null;
    
    console.log(`Sending chat request to ${endpoint} with headers:`, getHeaders());
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        model,
        messages: formattedMessages,
        ...(lmstudioSettings && { lmstudioSettings })
      }),
      credentials: 'include',  // Включаем куки для авторизации
    });

    console.log('Chat response status:', response.status);
    
    if (!response.ok) {
      let errorMessage = `Error: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        // Если ответ не может быть распарсен как JSON
        const errorText = await response.text();
        errorMessage = errorText || errorMessage;
      }
      
      console.error('Error response from backend:', errorMessage);
      throw new Error(errorMessage);
    }    // Логируем полный ответ для отладки
    const responseText = await response.text();
    console.log('Raw response from backend:', responseText);
    
    let data;
    try {
      // Пытаемся распарсить JSON
      data = JSON.parse(responseText);
      console.log('Parsed response data:', data);
    } catch (parseError) {
      console.error('Error parsing response as JSON:', parseError);
      // Если не удалось распарсить как JSON, возвращаем текст как есть
      return responseText || 'Не удалось получить ответ';
    }
    
    // Проверим наличие поля content в ответе
    if (!data || !data.content) {
      console.error('Incomplete response data:', data);
      return 'Неполные данные в ответе сервера';
    }
    
    return data.content;  } catch (error) {    
    // Получаем текущий провайдер для более точного сообщения об ошибке
    const currentProvider = provider || (localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio') || 'ollama';
    const providerName = currentProvider === 'lmstudio' ? 'LM Studio' : 'Ollama';
    
    console.error(`Error communicating with ${providerName} backend:`, error);
    
    // Создаем более информативное сообщение об ошибке
    let errorMessage = `Ошибка при общении с ${providerName}`;
    
    if (error instanceof Error) {
      errorMessage = error.message;
      
      // Для Ollama добавляем инструкции по установке моделей
      if (currentProvider === 'ollama') {
        if (errorMessage.includes("pull") || errorMessage.includes("not found")) {
          errorMessage += "\n\nВы можете установить модели с помощью команды: 'ollama pull модель' (например, 'ollama pull phi3')";
        }
        
        if (isLargeModel(model) && !errorMessage.includes("large model")) {
          errorMessage += "\n\nЭто большая модель, которая может загружаться несколько минут при первом запуске.";
        }
        
        errorMessage += "\n\nУбедитесь, что:\n1. Сервер Ollama запущен (команда 'ollama serve')\n2. Бэкенд приложения запущен\n3. Модель установлена и доступна";
      } else {
        // Для LM Studio другие инструкции
        errorMessage += "\n\nУбедитесь, что:\n1. LM Studio запущен\n2. Локальный сервер включен (Server tab → Start Server)\n3. Модель загружена в LM Studio\n4. Бэкенд приложения запущен";
      }
      
      const enhancedError = new Error(errorMessage);
      if (error.stack) {
        enhancedError.stack = error.stack;
      }
      throw enhancedError;
    }
    
    throw error;
  }
}

// Новая функция для отправки сообщения со стримингом
export async function sendMessageStreaming(
  model: ModelType,
  messages: Message[],
  onChunk: (chunk: string) => void,
  provider?: 'ollama' | 'lmstudio'
): Promise<void> {
  try {
    // Получаем текущий провайдер из localStorage, если не передан явно
    const currentProvider = provider || (localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio') || 'ollama';
    
    console.log(`Preparing to send streaming message to model: ${model} via ${currentProvider}`);
    
    // Format messages for API
    const formattedMessages = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // Выбираем правильный эндпоинт в зависимости от провайдера
    const endpoint = currentProvider === 'lmstudio' ? '/ollama/lmstudio/chat' : '/ollama/chat';
    
    // Получаем настройки LM Studio если это lmstudio провайдер
    const lmstudioSettings = currentProvider === 'lmstudio' ? getLMStudioSettings() : null;
    
    console.log(`Sending streaming chat request to ${endpoint}`);
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        model,
        messages: formattedMessages,
        stream: true,  // Включаем стриминг
        ...(lmstudioSettings && { lmstudioSettings })
      }),
      credentials: 'include',
    });

    console.log('Streaming response status:', response.status);
    
    if (!response.ok) {
      let errorMessage = `Error: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMessage = errorData.detail || errorMessage;
      } catch (e) {
        const errorText = await response.text();
        errorMessage = errorText || errorMessage;
      }
      
      console.error('Error response from backend:', errorMessage);
      throw new Error(errorMessage);
    }

    // Читаем поток данных
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }

      // Декодируем chunk
      buffer += decoder.decode(value, { stream: true });
      
      // Обрабатываем построчно (NDJSON формат)
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Сохраняем последнюю неполную строку

      for (const line of lines) {
        if (line.trim() === '') continue;
        
        try {
          const data = JSON.parse(line);
          
          // Проверяем наличие ошибки в ответе
          if (data.error) {
            console.error('Error from backend stream:', data.error);
            throw new Error(data.error);
          }
          
          // Для Ollama формат: {content: "text"}
          // Для LM Studio формат: {choices: [{delta: {content: "text"}}]}
          let content = '';
          
          if (data.content) {
            // Ollama формат
            content = data.content;
          } else if (data.choices && data.choices[0]?.delta?.content) {
            // LM Studio формат
            content = data.choices[0].delta.content;
          }
          
          if (content) {
            onChunk(content);
          }
        } catch (parseError) {
          console.error('Error parsing streaming chunk:', parseError, 'Line:', line);
          // Если это не ошибка парсинга, а реальная ошибка от сервера - пробрасываем дальше
          if (parseError instanceof Error && parseError.message !== 'Unexpected token') {
            throw parseError;
          }
        }
      }
    }

    // Обработаем остаток buffer
    if (buffer.trim()) {
      try {
        const data = JSON.parse(buffer);
        
        // Проверяем наличие ошибки
        if (data.error) {
          console.error('Error in final buffer:', data.error);
          throw new Error(data.error);
        }
        
        let content = '';
        
        if (data.content) {
          content = data.content;
        } else if (data.choices && data.choices[0]?.delta?.content) {
          content = data.choices[0].delta.content;
        }
        
        if (content) {
          onChunk(content);
        }
      } catch (parseError) {
        console.error('Error parsing final buffer:', parseError);
        // Пробрасываем реальные ошибки от сервера
        if (parseError instanceof Error && !parseError.message.includes('JSON')) {
          throw parseError;
        }
      }
    }

  } catch (error) {
    const currentProvider = provider || (localStorage.getItem('aiProvider') as 'ollama' | 'lmstudio') || 'ollama';
    const providerName = currentProvider === 'lmstudio' ? 'LM Studio' : 'Ollama';
    
    console.error(`Error communicating with ${providerName} backend:`, error);
    
    let errorMessage = `Ошибка при общении с ${providerName}`;
    
    if (error instanceof Error) {
      errorMessage = error.message;
      
      if (currentProvider === 'ollama') {
        if (errorMessage.includes("pull") || errorMessage.includes("not found")) {
          errorMessage += "\n\nВы можете установить модели с помощью команды: 'ollama pull модель' (например, 'ollama pull phi3')";
        }
        
        if (isLargeModel(model) && !errorMessage.includes("large model")) {
          errorMessage += "\n\nЭто большая модель, которая может загружаться несколько минут при первом запуске.";
        }
        
        errorMessage += "\n\nУбедитесь, что:\n1. Сервер Ollama запущен (команда 'ollama serve')\n2. Бэкенд приложения запущен\n3. Модель установлена и доступна";
      } else {
        errorMessage += "\n\nУбедитесь, что:\n1. LM Studio запущен\n2. Локальный сервер включен (Server tab → Start Server)\n3. Модель загружена в LM Studio\n4. Бэкенд приложения запущен";
      }
      
      const enhancedError = new Error(errorMessage);
      if (error.stack) {
        enhancedError.stack = error.stack;
      }
      throw enhancedError;
    }
    
    throw error;
  }
}

export async function getAvailableModels(): Promise<{ id: string, name: string }[]> {
  try {
    // Получаем модели через бэкенд
    console.log('Fetching available models from backend');
    const response = await fetch(`${API_BASE_URL}/ollama/models`, {
      headers: getHeaders(),
      credentials: 'include',  // Включаем куки для авторизации
    });
    
    console.log('Models response status:', response.status);
    
    if (!response.ok) {
      if (response.status === 401) {
        // If unauthorized, clear token and throw specific error
        localStorage.removeItem('ollamaChat_authToken');
        console.error('Authentication failed when fetching models');
        throw new Error('Unauthorized. Please login again.');
      }
      const errorText = await response.text();
      console.error('Error response text:', errorText);
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }
    
    const models = await response.json();
    console.log('Received models from backend:', models);
    return models;
  } catch (error) {
    console.error('Error fetching models from backend:', error);
    return [];
  }
}

// Test connection to Ollama instance via backend
export async function testConnection(): Promise<boolean> {
  try {
    console.log('Testing connection to Ollama via backend...');
    // Using the direct endpoint from main.py that's available without authentication
    const response = await fetch(`${API_BASE_URL}/ollama/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Add cache control to prevent browser caching
      cache: 'no-store'
    });
    
    console.log('Status response code:', response.status);
    
    // Even if response is not OK, try to parse it
    let data;
    try {
      data = await response.json();
      console.log('Status response data:', data);
    } catch (parseError) {
      console.error('Error parsing status response:', parseError);
      return false;
    }
    
    if (!response.ok) {
      console.error(`Status check failed with code: ${response.status}`);
      // Even with error status, we might get useful data
      if (data && data.status) {
        return data.status === 'connected';
      }
      return false;
    }
    
    return data && data.status === 'connected';
  } catch (error) {
    console.error('Cannot connect to Ollama instance via backend:', error);
    return false;
  }
}

// Check if a specific model is available
export async function isModelAvailable(modelName: string): Promise<boolean> {
  try {
    const models = await getAvailableModels();
    return models.some(model => model.id === modelName);
  } catch (error) {
    console.error('Error checking model availability:', error);
    return false;
  }
}
