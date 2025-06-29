import React, { useState, useEffect } from 'react';
import './LoadingIndicator.css';
import { isLargeModel } from '../services/ollamaApi';

interface LoadingIndicatorProps {
  model: string;
}

const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({ model }) => {
  const [dots, setDots] = useState(1);
  const [elapsedTime, setElapsedTime] = useState(0);
  
  // Check if this is a large model using our helper
  const isModelLarge = isLargeModel(model);
  
  // Animate dots (...)
  useEffect(() => {
    const dotInterval = setInterval(() => {
      setDots(prev => prev < 3 ? prev + 1 : 1);
    }, 500);
    
    return () => clearInterval(dotInterval);
  }, []);
  
  // Track elapsed time
  useEffect(() => {
    const timeInterval = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);
    
    return () => clearInterval(timeInterval);
  }, []);
    // Get appropriate message based on elapsed time and model size
  const getMessage = () => {    if (isModelLarge) {
      if (elapsedTime < 5) {
        return 'Думаю';
      } else if (elapsedTime < 15) {
        return 'Загружаю большую модель, это может занять время';
      } else if (elapsedTime < 30) {
        return 'Большие модели как deepseek могут загружаться 1-2 минуты';
      } else if (elapsedTime < 60) {
        return 'Модель обрабатывает ваш запрос, пожалуйста подождите';
      } else if (elapsedTime < 120) {
        return 'Большим моделям нужно время для загрузки и генерации ответов';
      } else {
        return 'Всё ещё работаю с этой большой моделью, пожалуйста потерпите';
      }
    } else {
      if (elapsedTime < 5) {
        return 'Думаю';
      } else if (elapsedTime < 15) {
        return 'Обрабатываю ваш запрос';
      } else if (elapsedTime < 30) {
        return 'Эта модель работает дольше обычного';
      } else if (elapsedTime < 60) {
        return 'Всё ещё обрабатываю, пожалуйста подождите';
      } else {
        return 'Всё ещё работаю над этим, пожалуйста потерпите';
      }
    }
  };
  
  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };  // Get additional tip based on model and time elapsed
  const getTip = () => {
    if (isModelLarge && elapsedTime > 40) {
      return "Совет: Большие модели как deepseek-r1 могут загружаться несколько минут, особенно при первом использовании.";
    }
    return null;
  };

  return (
    <div className="advanced-loading-indicator">
      <div className="thinking-text">
        {getMessage()}{'.'.repeat(dots)}
      </div>      <div className="thinking-detail">
        Используется модель: <strong>{model}</strong>
      </div>
      <div className="elapsed-time">
        Прошло времени: {formatTime(elapsedTime)}
      </div>
      {getTip() && (
        <div className="loading-tip">
          {getTip()}
        </div>
      )}
      <div className="loading-spinner-large"></div>
    </div>
  );
};

export default LoadingIndicator;
