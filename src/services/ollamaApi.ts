import { ModelType, Message } from '../types/chat';

// Local Ollama API URL (default port for Ollama)
const API_BASE_URL = 'http://localhost:11434';

export async function sendMessage(
  model: ModelType,
  messages: Message[]
): Promise<string> {
  try {
    // Format messages for Ollama API
    const formattedMessages = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // For Ollama 3B models, we use the /api/generate endpoint
    // or /api/chat depending on the model capabilities
    const endpoint = '/api/chat';

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages: formattedMessages,
        stream: false,
      }),
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    return data.message?.content || data.response || '';
  } catch (error) {
    console.error('Error communicating with local Ollama instance:', error);
    throw error;
  }
}

export async function getAvailableModels(): Promise<{ id: string, name: string }[]> {
  try {
    // Fetch available models from local Ollama
    const response = await fetch(`${API_BASE_URL}/api/tags`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Convert Ollama model list format to our app format
    return data.models?.map((model: any) => ({
      id: model.name,
      name: model.name
    })) || [];
  } catch (error) {
    console.error('Error fetching models from local Ollama:', error);
    // Default models that are common for Ollama, including 3B models
    return [
      { id: 'phi3:3b', name: 'Phi-3 (3B)' },
      { id: 'tinyllama', name: 'TinyLlama' },
      { id: 'gemma:2b', name: 'Gemma (2B)' },
      { id: 'mistral:7b', name: 'Mistral (7B)' }
    ];
  }
}

// Test connection to local Ollama instance
export async function testConnection(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/version`);
    return response.ok;
  } catch (error) {
    console.error('Cannot connect to local Ollama instance:', error);
    return false;
  }
}
