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
  const getMessage = () => {
    if (isModelLarge) {
      if (elapsedTime < 5) {
        return 'Thinking';
      } else if (elapsedTime < 15) {
        return 'Loading large model, this may take time';
      } else if (elapsedTime < 30) {
        return 'Large models like deepseek can take 1-2 minutes to load';
      } else if (elapsedTime < 60) {
        return 'Model is processing your request, please wait';
      } else if (elapsedTime < 120) {
        return 'Large models need time to load and generate responses';
      } else {
        return 'Still working with this large model, please be patient';
      }
    } else {
      if (elapsedTime < 5) {
        return 'Thinking';
      } else if (elapsedTime < 15) {
        return 'Processing your request';
      } else if (elapsedTime < 30) {
        return 'This model is taking longer than usual';
      } else if (elapsedTime < 60) {
        return 'Still processing, please wait';
      } else {
        return 'Still working on it, please be patient';
      }
    }
  };
  
  // Format time as MM:SS
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };
  // Get additional tip based on model and time elapsed
  const getTip = () => {
    if (isModelLarge && elapsedTime > 40) {
      return "Tip: Large models like deepseek-r1 can take several minutes to load, especially on the first use.";
    }
    return null;
  };

  return (
    <div className="advanced-loading-indicator">
      <div className="thinking-text">
        {getMessage()}{'.'.repeat(dots)}
      </div>
      <div className="thinking-detail">
        Using model: <strong>{model}</strong>
      </div>
      <div className="elapsed-time">
        Elapsed time: {formatTime(elapsedTime)}
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
