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
  attachments?: FileAttachment[]; // Добавляем поддержку вложений
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
