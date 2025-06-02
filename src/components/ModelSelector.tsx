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
      <label htmlFor="model">Model:</label>
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
          </select>
          {onRefreshModels && (
            <button 
              type="button" 
              className="refresh-models-button" 
              onClick={onRefreshModels}
              title="Refresh available models"
              disabled={disabled}
            >
              ↻
            </button>
          )}
        </>
      ) : (
        <>
          <div className="no-models-message">
            {disabled ? 
              "Ollama not connected - no models available" : 
              "No models found in Ollama. Use 'ollama pull MODEL_NAME' to download models."}
          </div>
          {onRefreshModels && (
            <button 
              type="button" 
              className="refresh-models-button" 
              onClick={onRefreshModels}
              title="Refresh available models"
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
