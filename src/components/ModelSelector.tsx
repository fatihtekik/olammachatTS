import React from 'react';
import { ModelType } from '../types/chat';
import './ModelSelector.css';

interface ModelSelectorProps {
  selectedModel: ModelType;
  onSelectModel: (model: ModelType) => void;
  models: { id: string, name: string }[];
  disabled?: boolean;
  onRefreshModels?: () => void;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ 
  selectedModel, 
  onSelectModel,
  models,
  disabled = false,
  onRefreshModels
}) => {  return (
    <div className="model-selector">
      <label htmlFor="model">Модель:</label>
      {models.length > 0 ? (
        <>
          <select 
            id="model" 
            value={selectedModel}
            onChange={(e) => onSelectModel(e.target.value as ModelType)}
            disabled={disabled}
            className={disabled ? 'disabled' : ''}
          >
            {models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>          {onRefreshModels && (
            <button 
              type="button" 
              className="refresh-models-button" 
              onClick={onRefreshModels}
              title="Обновить доступные модели"
              disabled={disabled}
            >
              ↻
            </button>
          )}
        </>
      ) : (
        <>          <div className="no-models-message">
            {disabled ? 
              "Ollama не подключена - модели недоступны" : 
              "Модели не найдены в Ollama. Используйте 'ollama pull MODEL_NAME' для загрузки моделей."}
          </div>
          {onRefreshModels && (
            <button 
              type="button" 
              className="refresh-models-button" 
              onClick={onRefreshModels}
              title="Обновить доступные модели"
            >
              ↻
            </button>
          )}
        </>
      )}
    </div>
  );
};

export default ModelSelector;
