export interface FileAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  dataUrl?: string; // Для хранения содержимого файла в формате data URL
  url?: string;     // Для потенциального хранения в будущем на сервере
  preview?: string; // URL предпросмотра для изображений
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  error?: boolean;
  attachments?: FileAttachment[];
  provider?: 'ollama' | 'lmstudio'; // Добавляем информацию о провайдере
  model?: string; // Добавляем информацию о модели
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  model: string;
  createdAt: Date;
  updatedAt: Date;
}

export interface ChatHistory {
  sessions: ChatSession[];
  activeSessionId: string | null;
}

export interface OllamaModel {
  id: string;
  name: string;
}

export type ModelType = 'llama2' | 'mistral' | 'phi' | string;

export interface MatchData {
  игрок_1: string;
  игрок_2: string;
  рейтинг_1: number;
  рейтинг_2: number;
  счёт: string;
  этап: string;
  турнир: string;
  лига: string;
}

export interface TriggerResponse {
  context: string;
  ollama_response: string;
}

// LM Studio настройки модели
export interface LMStudioSettings {
  temperature: number;           // 0.0 - 2.0, по умолчанию 0.7
  maxCompletionTokens: number;   // Токены для ответа
  maxReasoningTokens: number;    // Токены для thinking/reasoning
  topP: number;                  // 0.0 - 1.0, по умолчанию 1.0
  topK: number;                  // 1 - 100, по умолчанию 40
  repeatPenalty: number;         // 1.0 - 2.0, по умолчанию 1.1
  reasoningEffort: 'low' | 'medium' | 'high';  // Усилие reasoning
  showReasoning: boolean;        // Показывать ли thinking в ответе
}

export const DEFAULT_LMSTUDIO_SETTINGS: LMStudioSettings = {
  temperature: 0.7,
  maxCompletionTokens: 4000,
  maxReasoningTokens: 5000,
  topP: 1.0,
  topK: 40,
  repeatPenalty: 1.1,
  reasoningEffort: 'medium',
  showReasoning: false
};
