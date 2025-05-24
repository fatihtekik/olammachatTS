import React from 'react';
import { ModelType } from '../types/chat';
import './ModelSelector.css';

interface ModelSelectorProps {
  selectedModel: ModelType;
  onSelectModel: (model: ModelType) => void;
  models: { id: string, name: string }[];
  disabled?: boolean;
}

const ModelSelector: React.FC<ModelSelectorProps> = ({ 
  selectedModel, 
  onSelectModel,
  models,
  disabled = false
}) => {
  return (
    <div className="model-selector">
      <label htmlFor="model">Model:</label>
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
    </div>
  );
};

export default ModelSelector;
