/**
 * Типы для сценарного анализа игроков
 */

export interface SetDetail {
  set_number: number;
  player1_points: number;
  player2_points: number;
  winner_id: string;
}

export interface ScenarioMatchDetail {
  match_id: string;
  date: string | null;
  player1_name: string;
  player2_name: string;
  score: string;
  winner_id: string | null;
  is_win: boolean;
  fight_score: number | null;
  sets: SetDetail[];
}

export interface ScenarioStats {
  scenario_code: string;
  scenario_name: string;
  matches_total: number;
  wins: number;
  losses: number;
  win_rate: number;
  fight_score: number | null;
  fight_score_interpretation: string;
  behavior_label: string;
  updated_at: string | null;
}

export interface PlayerScenariosResponse {
  player_id: string;
  scenarios: ScenarioStats[];
}

export interface AnalyzePlayerResponse {
  player_id: string;
  scenarios_analyzed: number;
  total_matches: number;
  message: string;
}

export type ScenarioCode = 'S1' | 'S2' | 'S3' | 'S4' | 'S5' | 'S6';

export const SCENARIO_DESCRIPTIONS: Record<ScenarioCode, string> = {
  S1: 'Выиграл 1-й сет → проиграл матч 1-3',
  S2: 'Выиграл первые 2 сета → проиграл 2-3',
  S3: 'Матч был 1-1 по сетам',
  S4: 'Вёл по сетам 2-0',
  S5: 'Fight Score в проигранных сетах ≥ 0.3',
  S6: 'Fight Score < 0.3',
};
