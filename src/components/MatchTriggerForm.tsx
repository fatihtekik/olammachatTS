import React, { useState } from 'react';
import './MatchTriggerForm.css';
import { MatchData, TriggerResponse, ModelType } from '../types/chat';
import { authAPI } from '../services/backendApi';

interface MatchTriggerFormProps {  
  onSubmit?: (data: MatchData, response: TriggerResponse) => void;  
  onClose: () => void;
  selectedModel: ModelType;
}

const API_BASE_URL = 'http://localhost:8000/api/v1';

const MatchTriggerForm: React.FC<MatchTriggerFormProps> = ({ onSubmit, onClose, selectedModel }) => {
  const [form, setForm] = useState<MatchData>({
    игрок_1: '',
    игрок_2: '',
    рейтинг_1: 0,
    рейтинг_2: 0,
    счёт: '',
    этап: '',
    турнир: '',
    лига: ''
  });  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TriggerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: name.includes('рейтинг') ? parseFloat(value) : value }));
  };  
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); // Предотвращаем поведение по умолчанию
    setLoading(true);
    setError(null);
    setResult(null);
    
    console.log('🔍 MatchTriggerForm - Отправка данных формы:', form);
    console.log('🔍 MatchTriggerForm - Выбранная модель:', selectedModel);
    console.log('🔍 MatchTriggerForm - API URL:', `${API_BASE_URL}/ollama/check-trigger`);    
    try {
      // Получаем токен авторизации
      const authToken = localStorage.getItem('ollamaChat_authToken');
      console.log('Текущий URL страницы:', window.location.href);
      console.log('Origin:', window.location.origin);
      
      // Добавляем заголовок авторизации
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Origin': window.location.origin
      };
      
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
        console.log('Используем токен для авторизации');
      } else {
        console.warn('Токен авторизации отсутствует!');
      }
      
      // Формируем полный URL запроса
      const url = `${API_BASE_URL}/ollama/check-trigger`;
      console.log('🔍 MatchTriggerForm - Полный URL запроса:', url);
      
      const requestData = {
        ...form,
        model: selectedModel // Добавляем выбранную модель в запрос
      };
      console.log('🔍 MatchTriggerForm - Данные для отправки:', requestData);
      
      const response = await fetch(url, {
        method: 'POST',
        headers,
        credentials: 'include', // Включаем куки авторизации
        body: JSON.stringify(requestData)
      });
      
      console.log('Получен ответ:', response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Не удалось прочитать текст ошибки');
        console.error('Ошибка ответа:', response.status, response.statusText, errorText);
        throw new Error(`Ошибка запроса: ${response.status} ${response.statusText}. ${errorText}`);
      }
      
      // Проверяем, что ответ содержит данные
      const text = await response.text();
      console.log('Текст ответа:', text);
      
      if (!text) {
        throw new Error('Получен пустой ответ от сервера');
      }
        // Пробуем распарсить JSON
      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        throw new Error(`Ошибка парсинга ответа: ${e}. Текст ответа: ${text.substring(0, 100)}...`);
      }
      
      console.log('Успешно получены данные:', data);      // Извлекаем только analysis из ответа для отправки в чат
      let analysisText = '';
      console.log('=== MatchTriggerForm DEBUG ===');
      console.log('1. Full data object:', data);
      console.log('2. data.analysis exists?', !!data.analysis);
      console.log('3. data.ollama_response exists?', !!data.ollama_response);
      console.log('4. data.ollama_response content:', data.ollama_response);
      
      if (data.analysis) {
        // Если есть поле analysis - используем его
        analysisText = data.analysis;
        console.log('5. Using direct analysis field:', analysisText);      } else if (data.ollama_response) {
        // Если есть ollama_response, пытаемся извлечь analysis из JSON
        console.log('6. Processing ollama_response...');
        console.log('7. ollama_response type:', typeof data.ollama_response);
        console.log('8. ollama_response content:', data.ollama_response);
        
        try {
          const ollamaData = JSON.parse(data.ollama_response);
          console.log('9. Successfully parsed ollama_response:', ollamaData);
          console.log('10. ollamaData.analysis exists?', !!ollamaData.analysis);
          
          analysisText = ollamaData.analysis || data.ollama_response;
          console.log('11. Final analysisText:', analysisText);        } catch (parseError) {
          console.log('12. JSON parsing failed:', parseError);
          console.log('13. Trying regex extraction...');
          
          // Попытка извлечь анализ из поврежденного JSON с помощью регулярного выражения
          const analysisMatch = data.ollama_response.match(/"analysis"\s*:\s*"([^"]*(?:\\.[^"]*)*)"?/);
          if (analysisMatch && analysisMatch[1]) {
            analysisText = analysisMatch[1].replace(/\\"/g, '"').replace(/\\n/g, '\n').replace(/\\\\/g, '\\');
            console.log('14. Extracted analysis via regex:', analysisText);
          } else {
            // Если не JSON, используем как есть
            analysisText = data.ollama_response;
            console.log('15. Using ollama_response as is:', analysisText);
          }
        }
      } else {
        analysisText = 'Анализ не найден в ответе сервера';
        console.log('16. No analysis found in server response');
      }
      
      console.log('=== MatchTriggerForm END DEBUG ===');

      const finalResponse: TriggerResponse = {
        context: data.context || '',
        ollama_response: analysisText
      };
      
      setResult(data); // Показываем полный результат в форме
      if (onSubmit) {
        console.log('Вызываем callback onSubmit');
        onSubmit(form, finalResponse); // Но отправляем в чат только анализ
      }
    } catch (err: any) {
      console.error('Полная ошибка при отправке триггера:', err);
      setError(err.message || 'Ошибка');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="match-trigger-form-modal" onClick={(e) => {
      // Закрываем модальное окно при клике на фон
      if (e.target === e.currentTarget) onClose();
    }}>
      <div className="match-trigger-form">
        <button type="button" className="close-btn" onClick={onClose}>×</button>
        <h3>Данные матча</h3>
        <form onSubmit={handleSubmit}>
          <input name="игрок_1" placeholder="Игрок 1" value={form.игрок_1} onChange={handleChange} required />
          <input name="игрок_2" placeholder="Игрок 2" value={form.игрок_2} onChange={handleChange} required />
          <input name="рейтинг_1" type="number" placeholder="Рейтинг 1" value={form.рейтинг_1 || ''} onChange={handleChange} required />
          <input name="рейтинг_2" type="number" placeholder="Рейтинг 2" value={form.рейтинг_2 || ''} onChange={handleChange} required />
          <input name="счёт" placeholder="Счёт" value={form.счёт} onChange={handleChange} required />
          <input name="этап" placeholder="Этап" value={form.этап} onChange={handleChange} required />
          <input name="турнир" placeholder="Турнир" value={form.турнир} onChange={handleChange} required />
          <input name="лига" placeholder="Лига" value={form.лига} onChange={handleChange} required />
          <button type="submit" disabled={loading}>
            {loading ? "Загрузка..." : "Проверить триггер"}
          </button>
        </form>
        {loading && <div className="loading">Проверка...</div>}
        
        {result && (
          <div className="trigger-result">
            <div className="result-section">
              <h4>Контекст:</h4>
              <div className="context-box">{result.context}</div>
            </div>
            <div className="result-section">
              <h4>Ответ от Ollama:</h4>
              <div className="ollama-response">{result.ollama_response}</div>
            </div>
          </div>
        )}
        
        {error && <div className="error-message">Ошибка: {error}</div>}
      </div>
    </div>
  );
};

export default MatchTriggerForm;
