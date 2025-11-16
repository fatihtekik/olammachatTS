import React, { useState, useEffect } from 'react';
import { ScenarioStats, ScenarioCode } from '../types/scenario';
import { scenarioAPI, scenarioUtils } from '../services/scenarioApi';
import ScenarioDetailsModal from './ScenarioDetailsModal';
import './ScenarioAnalysisTab.css';

interface ScenarioAnalysisTabProps {
  playerId: string;
  playerName: string;
}

const ScenarioAnalysisTab: React.FC<ScenarioAnalysisTabProps> = ({ playerId, playerName }) => {
  const [scenarios, setScenarios] = useState<ScenarioStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<ScenarioStats | null>(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    loadScenarios();
  }, [playerId]);

  const loadScenarios = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await scenarioAPI.getPlayerScenarios(playerId);
      setScenarios(response.scenarios);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    try {
      setAnalyzing(true);
      await scenarioAPI.analyzePlayer(playerId);
      await loadScenarios();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка анализа');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleScenarioClick = (scenario: ScenarioStats) => {
    setSelectedScenario(scenario);
  };

  if (loading) {
    return (
      <div className="scenario-analysis-loading">
        <div className="loading-spinner"></div>
        <p>Загрузка данных...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="scenario-analysis-error">
        <p>{error}</p>
        <button onClick={loadScenarios}>Повторить</button>
      </div>
    );
  }

  return (
    <div className="scenario-analysis-tab">
      <div className="scenario-header">
        <h2>Статистический анализ сценариев</h2>
        <button 
          className="analyze-button" 
          onClick={handleAnalyze}
          disabled={analyzing}
        >
          {analyzing ? 'Анализируем...' : 'Обновить анализ'}
        </button>
      </div>

      {scenarios.length === 0 ? (
        <div className="no-scenarios">
          <p>Нет данных для анализа</p>
          <p className="hint">Нажмите "Обновить анализ" для расчёта сценариев</p>
        </div>
      ) : (
        <table className="scenarios-table">
          <thead>
            <tr>
              <th>Сценарий</th>
              <th>Матчей</th>
              <th>Побед</th>
              <th>Поражений</th>
              <th>% побед</th>
              <th>Fight Score</th>
              <th>Поведение</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario) => (
              <tr key={scenario.scenario_code}>
                <td>
                  <div className="scenario-name">
                    <span className="scenario-code">{scenario.scenario_code}</span>
                    <span className="scenario-description">{scenario.scenario_name}</span>
                  </div>
                </td>
                <td className="text-center">{scenario.matches_total}</td>
                <td className="text-center text-success">{scenario.wins}</td>
                <td className="text-center text-danger">{scenario.losses}</td>
                <td className="text-center">
                  <span 
                    className="win-rate-badge"
                    style={{ 
                      backgroundColor: scenarioUtils.getWinRateColor(scenario.win_rate) 
                    }}
                  >
                    {scenario.win_rate}%
                  </span>
                </td>
                <td className="text-center">
                  {scenario.fight_score !== null ? (
                    <span 
                      className="fight-score-badge"
                      style={{ 
                        backgroundColor: scenarioUtils.getFightScoreColor(scenario.fight_score) 
                      }}
                    >
                      {scenario.fight_score.toFixed(3)}
                    </span>
                  ) : (
                    <span className="no-data">—</span>
                  )}
                </td>
                <td>
                  <span 
                    className="behavior-badge"
                    style={{ 
                      backgroundColor: scenarioUtils.getBehaviorBadgeColor(scenario.behavior_label) 
                    }}
                  >
                    {scenario.behavior_label}
                  </span>
                </td>
                <td>
                  <button 
                    className="details-button"
                    onClick={() => handleScenarioClick(scenario)}
                  >
                    Подробнее
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedScenario && (
        <ScenarioDetailsModal
          scenario={selectedScenario}
          playerId={playerId}
          playerName={playerName}
          onClose={() => setSelectedScenario(null)}
        />
      )}
    </div>
  );
};

export default ScenarioAnalysisTab;
