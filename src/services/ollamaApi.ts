/**
 * DEPRECATED: Этот файл больше не используется в основном потоке приложения.
 * Вместо него используется ollamaBackendApi.ts, который обращается к Ollama через бэкенд.
 * Этот файл сохранен для обратной совместимости и в качестве примера прямых запросов к API Ollama.
 */

import { ModelType, Message } from '../types/chat';

// Local Ollama API URL (default port for Ollama)
const API_BASE_URL = 'http://localhost:11434';

// List of large models that need special handling
const LARGE_MODELS: string[] = ['deepseek', 'llama3-70b', 'mixtral-8x7b', 'qwen', 'solar-10b'];

// Helper function to check if a model is considered "large" and needs special handling
export function isLargeModel(modelName: string): boolean {
  return LARGE_MODELS.some((name: string) => 
    modelName.toLowerCase().includes(name.toLowerCase())
  );
}

export async function sendMessage(
  model: ModelType,
  messages: Message[]
): Promise<string> {
  try {
    console.log(`Preparing to send message to model: ${model}`);    // For deepseek or other large models, let's try to handle initial loading
    // by doing a quick check but not blocking on absence
    const isModelLarge = isLargeModel(model);
    
    // Only do the availability check for non-large models for better UX
    if (!isModelLarge) {
      // First check if the model exists
      const isAvailable = await isModelAvailable(model);
      if (!isAvailable) {
        throw new Error(`Model "${model}" not found. You need to download it first using the command: ollama pull ${model}`);
      }
    } else {
      console.log(`Skipping strict availability check for large model: ${model}`);
    }
    
    // Format messages for Ollama API
    const formattedMessages = messages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    // Always use streaming regardless of model size for consistent UX and to avoid timeouts
    return await sendStreamingMessage(model, formattedMessages);
  } catch (error) {
    if (typeof error === 'object' && error !== null && 'name' in error && (error as any).name === 'AbortError') {
      // This message should never be seen since AbortError handling is now in sendStreamingMessage
      return "Request timed out. The model might be still loading or the response is taking too long. You may need to restart Ollama. If it worked in the terminal, try increasing the timeout in the application settings.";
    }
    
    // If the error message contains guidance about pulling the model, add extra help
    if (error instanceof Error && error.message.includes("pull")) {
      error.message += "\n\nYou can install models using the Ollama command line. For example: 'ollama pull phi3'";
    }    // For large models, add additional guidance
    if (error instanceof Error && isLargeModel(model)) {
      if (!error.message.includes("large model")) {
        error.message += "\n\nThis is a large model that may take several minutes to load the first time. If it worked in your terminal, try waiting for a while and making the request again.";
      }
    }
    
    console.error('Error communicating with local Ollama instance:', error);
    throw error;
  }
}

// Use streaming to get response chunks as they're generated
// This helps with large models that might otherwise time out
async function sendStreamingMessage(
  model: string,
  messages: { role: string, content: string }[]
): Promise<string> {  // Add extended timeout for very large models (5 minutes)
  // Models like deepseek can take significantly longer to load and generate responses
  const isModelLarge = isLargeModel(model);  const timeoutDuration = isModelLarge ? 300000 : 180000; // 5 min for large models, 3 min for others
  
  console.log(`Setting ${isModelLarge ? 'extended' : 'standard'} timeout of ${timeoutDuration/1000}s for model: ${model}`);
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutDuration);
  
  try {
    console.log(`Sending streaming request to model: ${model}`);
    // Add more detailed logging to help with debugging
    const startTime = new Date();
    console.log(`Request started at: ${startTime.toISOString()}`);
    
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model,
        messages,
        stream: true,  // Enable streaming
        options: {
          num_ctx: 8192,  // Increased context window for better handling large models
          temperature: 0.7,
          top_k: 50,
        }
      }),
      signal: controller.signal
    });
      if (!response.ok || !response.body) {
      clearTimeout(timeoutId);
      const errorText = await response.text();
      console.error(`Error response from Ollama API: ${response.status} - ${errorText}`);
      
      // Handle specific error cases with more detailed explanations
      if (response.status === 404 && errorText.includes("model") && errorText.includes("not found")) {
        throw new Error(`Model "${model}" not found. You need to download it first using the command: ollama pull ${model}`);
      }
      
      // Handle timeout/loading errors with better explanation
      if (response.status === 500 || response.status === 502 || response.status === 504) {
        throw new Error(`Model "${model}" is having trouble loading or responding (Error ${response.status}). Large models like deepseek may take several minutes to load. Try restarting Ollama or checking the Ollama logs.`);
      }
      
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }

    let fullResponse = '';
    let hasStartedReceivingContent = false;
    let lastProgressUpdate = Date.now();
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    // Process stream chunks until done
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n').filter(line => line.trim() !== '');
      
      for (const line of lines) {
        try {
          const json = JSON.parse(line);
          if (json.message?.content) {
            if (!hasStartedReceivingContent) {
              hasStartedReceivingContent = true;
              console.log(`First content received after ${(Date.now() - startTime.getTime()) / 1000}s`);
            }
            fullResponse += json.message.content;
            lastProgressUpdate = Date.now();
          } else if (json.response) {
            if (!hasStartedReceivingContent) {
              hasStartedReceivingContent = true;
              console.log(`First content received after ${(Date.now() - startTime.getTime()) / 1000}s`);
            }
            fullResponse += json.response;
            lastProgressUpdate = Date.now();
          }
          
          // Log progress for very long responses
          if (Date.now() - lastProgressUpdate > 10000) {  // Log every 10 seconds of inactivity
            console.log(`Still receiving data from model ${model}, response length so far: ${fullResponse.length}`);
            lastProgressUpdate = Date.now();
          }
        } catch (e) {
          console.warn('Failed to parse streaming response chunk:', line);
        }
      }
    }
    
    clearTimeout(timeoutId);
    console.log(`Full response received after ${(Date.now() - startTime.getTime()) / 1000}s, length: ${fullResponse.length}`);
    return fullResponse;  } catch (error) {
    clearTimeout(timeoutId);
    console.error('Streaming error:', error);
      if (typeof error === 'object' && error !== null && 'name' in error && (error as any).name === 'AbortError') {
      const errorMessage = `Request to model "${model}" timed out after ${timeoutDuration/1000} seconds.\n\n`;
      
      if (isModelLarge) {
        throw new Error(errorMessage + 
          `This is a very large model that takes significant time to load. The model might still be loading in the background. You can try:\n` +
          `1. Wait a few minutes and try again\n` +
          `2. Check Ollama logs in the terminal\n` +
          `3. Restart the Ollama service\n` +
          `4. Consider using a smaller model if immediate responses are needed`);
      } else {
        throw new Error(errorMessage +
          `The model might be still loading or the response is taking too long. You may need to restart Ollama.`);
      }
    }
    
    throw error;
  }
}

export async function getAvailableModels(): Promise<{ id: string, name: string }[]> {
  try {
    // Получаем все доступные модели из локального Ollama
    const response = await fetch(`${API_BASE_URL}/api/tags`);
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Если моделей нет или список пуст
    if (!data.models || data.models.length === 0) {
      console.warn('No models found in Ollama');
      return [];
    }
    
    console.log('Available models from Ollama:', data.models);
    
    // Преобразуем формат списка моделей Ollama в формат нашего приложения
    // Добавляем более описательные имена для распространенных моделей
    return data.models.map((model: any) => {
      const modelName = model.name.toLowerCase();
      let displayName = model.name;
      
      // Улучшенное именование моделей
      if (modelName.includes('phi3')) {
        displayName = `Phi-3 ${modelName.includes('mini') ? 'Mini' : ''}`;
      } else if (modelName.includes('llama3')) {
        displayName = `Llama 3 ${modelName.includes('8b') ? '8B' : modelName.includes('70b') ? '70B' : ''}`;
      } else if (modelName.includes('llama2')) {
        displayName = `Llama 2 ${modelName.includes('7b') ? '7B' : modelName.includes('13b') ? '13B' : ''}`;
      } else if (modelName.includes('gemma')) {
        displayName = `Gemma ${modelName.includes('2b') ? '2B' : modelName.includes('7b') ? '7B' : ''}`;
      } else if (modelName.includes('mistral')) {
        displayName = `Mistral ${modelName.includes('7b') ? '7B' : ''}`;
      }
      
      return {
        id: model.name,
        name: displayName
      };
    });
  } catch (error) {
    console.error('Error fetching models from local Ollama:', error);
    
    // Если не удалось получить модели из Ollama, возвращаем пустой массив, чтобы показать, что модели недоступны
    // Пользователь увидит сообщение об отсутствии подключения к Ollama
    return [];
  }
}

// Test connection to local Ollama instance
export async function testConnection(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000); // 5-second timeout for quick check
    
    const response = await fetch(`${API_BASE_URL}/api/version`, {
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    return response.ok;
  } catch (error) {
    console.error('Cannot connect to local Ollama instance:', error);
    return false;
  }
}

// Check if a specific model is available
export async function isModelAvailable(modelName: string): Promise<boolean> {
  try {
    const models = await getAvailableModels();
    const modelExists = models.some(model => model.id === modelName);
    
    // If model doesn't exist in the list, do a direct probe to verify
    // (Sometimes model list doesn't update immediately)
    if (!modelExists) {
      try {
        // Quick probe with a simple prompt to check model availability
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);
        
        const probeResponse = await fetch(`${API_BASE_URL}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: modelName,
            messages: [{ role: 'system', content: 'Hello' }],
            stream: false,
            options: { num_predict: 1 } // Minimum token prediction to check model exists
          }),
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        return probeResponse.ok;
      } catch (probeError) {
        console.log('Direct model probe failed:', probeError);
        return false;
      }
    }
    
    return modelExists;
  } catch (error) {
    console.error('Error checking model availability:', error);
    return false;
  }
}
