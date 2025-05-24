export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatHistory {
  messages: Message[];
}

export interface OllamaModel {
  id: string;
  name: string;
}

export type ModelType = 'llama2' | 'mistral' | 'phi' | string;
