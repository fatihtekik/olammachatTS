import * as XLSX from 'xlsx';

/**
 * Профессиональный экспорт H2H анализа в Excel
 * Версия 2.0 - с полной детализацией триггеров и доказательств
 */

// === ИНТЕРФЕЙСЫ ===

interface H2HTrigger {
  type: string;
  trigger_value: string;
  severity: number;
}

interface H2HSet {
  set_number: number;
  player1_points: number;
  player2_points: number;
}

interface H2HMatch {
  id: string;
  date: string;
  score: string;
  stage: string | null;
  league_id: string | null;
  winner_id: string;
  sets: H2HSet[];
  player1_triggers: Array<{ type: string; severity: number }>;
  player2_triggers: Array<{ type: string; severity: number }>;
  serve_efficiency_p1: number | null;
  receive_efficiency_p1: number | null;
  serve_efficiency_p2: number | null;
  receive_efficiency_p2: number | null;
}

interface H2HPlayer {
  id: string;
  full_name: string;
  current_rating: number;
  triggers: H2HTrigger[];
}

interface H2HStats {
  player1: H2HPlayer;
  player2: H2HPlayer;
  matches: H2HMatch[];
  ai_analysis: string;
}

interface DateAnalysisPair {
  player1: {
    id: string;
    full_name: string;
    current_rating: number;
  };
  player2: {
    id: string;
    full_name: string;
    current_rating: number;
  };
  matches: Array<{
    id: string;
    score: string;
    stage: string | null;
    winner_id: string;
    sets: H2HSet[];
    player1_triggers: Array<{ type: string; severity: number }>;
    player2_triggers: Array<{ type: string; severity: number }>;
  }>;
  player1_wins: number;
  player2_wins: number;
  total_matches: number;
}

interface DateAnalysisResult {
  date: string;
  pairs: DateAnalysisPair[];
  total_matches: number;
}

// === КОНСТАНТЫ ===

// Полные названия триггеров на русском с объяснениями
const TRIGGER_INFO: Record<string, { name: string; description: string }> = {
  'h2h_dominant': {
    name: 'Доминирование в паре',
    description: 'Игрок имеет значительный перевес в личных встречах против соперника'
  },
  'h2h_losing_streak': {
    name: 'Серия поражений',
    description: 'Игрок имеет серию последовательных поражений от конкретного соперника'
  },
  'h2h_first_set_win': {
    name: 'Реализация первого сета',
    description: 'Статистика побед/поражений при выигрыше первого сета'
  },
  'h2h_comeback': {
    name: 'Камбэки (отыгрыши)',
    description: 'Игрок способен отыгрываться с отставания 0:1 по сетам'
  },
  'h2h_close_games': {
    name: 'Тайтовые матчи',
    description: 'В матчах часто встречаются близкие счета (2:3, 3:2)'
  },
  'h2h_mental_weakness': {
    name: 'Ментальная слабость',
    description: 'Игрок склонен проигрывать решающие сеты или тайтовые моменты'
  },
  'h2h_close_score_losses': {
    name: 'Поражения в плотных концовках',
    description: 'Игрок часто проигрывает матчи с минимальной разницей'
  },
  'h2h_score_pattern': {
    name: 'Паттерн счёта',
    description: 'Матчи часто заканчиваются определёнными счетами'
  },
  'h2h_deciding_set_behavior': {
    name: 'Поведение в решающем сете',
    description: 'Анализ результатов в решающих сетах'
  },
  'h2h_set_anomalies': {
    name: 'Аномалии в сетах',
    description: 'Нетипичные счета или резкие изменения в ходе матча'
  },
  'h2h_seasonal_pattern': {
    name: 'Сезонные паттерны',
    description: 'Зависимость результатов от времени года или периода'
  },
  'h2h_lead_2_0_behavior': {
    name: 'Поведение при счёте 2:0',
    description: 'Способность удержать или отыграть преимущество 2:0 по сетам'
  },
  'comeback_inability': {
    name: 'Неспособность к камбэку',
    description: 'Игрок редко отыгрывается при отставании по сетам'
  },
  'momentum_shift': {
    name: 'Потеря импульса',
    description: 'Игрок склонен терять контроль после успешного старта'
  },
};

// Описания уровней серьёзности
const SEVERITY_INFO: Record<number, { level: string; description: string }> = {
  1: { level: 'Минимальный', description: 'Слабый сигнал, требует дополнительного подтверждения' },
  2: { level: 'Низкий', description: 'Заметный паттерн, но с малой выборкой' },
  3: { level: 'Средний', description: 'Устойчивый паттерн с достаточной статистикой' },
  4: { level: 'Высокий', description: 'Сильный паттерн с высокой вероятностью повторения' },
  5: { level: 'Критический', description: 'Очень сильный паттерн, почти гарантированный' },
};

// === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

/**
 * Форматирование даты в русском формате
 */
function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

/**
 * Получение информации о триггере
 */
function getTriggerInfo(type: string): { name: string; description: string } {
  return TRIGGER_INFO[type] || { name: type, description: 'Дополнительный паттерн поведения' };
}

/**
 * Анализ матчей для построения доказательств триггера
 */
function buildEvidenceForTrigger(
  trigger: H2HTrigger,
  matches: H2HMatch[],
  playerId: string
): string[] {
  const evidence: string[] = [];
  const sortedMatches = [...matches].sort((a, b) => 
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
  
  switch (trigger.type) {
    case 'h2h_losing_streak': {
      let currentStreak: H2HMatch[] = [];
      let maxStreak: H2HMatch[] = [];
      
      for (const match of [...matches].sort((a, b) => 
        new Date(a.date).getTime() - new Date(b.date).getTime()
      )) {
        if (match.winner_id !== playerId) {
          currentStreak.push(match);
          if (currentStreak.length > maxStreak.length) {
            maxStreak = [...currentStreak];
          }
        } else {
          currentStreak = [];
        }
      }
      
      if (maxStreak.length >= 2) {
        evidence.push(`Серия из ${maxStreak.length} последовательных поражений:`);
        for (const m of maxStreak) {
          evidence.push(`  ▸ ${formatDate(m.date)}: Поражение ${m.score}`);
        }
      }
      break;
    }
    
    case 'h2h_close_score_losses': {
      const closeLosses = matches.filter(m => {
        if (m.winner_id === playerId) return false;
        const parts = m.score.split(':').map(Number);
        return Math.abs(parts[0] - parts[1]) === 1;
      });
      
      if (closeLosses.length > 0) {
        evidence.push(`${closeLosses.length} тесных поражений (разница 1 сет):`);
        for (const m of closeLosses.slice(0, 5)) {
          const setsStr = m.sets.map(s => `${s.player1_points}:${s.player2_points}`).join(', ');
          evidence.push(`  ▸ ${formatDate(m.date)}: ${m.score} (сеты: ${setsStr})`);
        }
      }
      break;
    }
    
    case 'h2h_first_set_win': {
      const firstSetStats = { wonFirstWonMatch: 0, wonFirstLostMatch: 0 };
      const examples: string[] = [];
      
      for (const m of matches) {
        if (m.sets.length > 0) {
          const wonFirst = m.sets[0].player1_points > m.sets[0].player2_points;
          if (wonFirst) {
            if (m.winner_id === playerId) {
              firstSetStats.wonFirstWonMatch++;
            } else {
              firstSetStats.wonFirstLostMatch++;
              const setsStr = m.sets.map(s => `${s.player1_points}:${s.player2_points}`).join(', ');
              examples.push(`  ▸ ${formatDate(m.date)}: Выиграл 1й сет, но проиграл ${m.score} (${setsStr})`);
            }
          }
        }
      }
      
      const total = firstSetStats.wonFirstWonMatch + firstSetStats.wonFirstLostMatch;
      if (total > 0) {
        const convRate = ((firstSetStats.wonFirstWonMatch / total) * 100).toFixed(0);
        evidence.push(`Статистика при выигрыше 1-го сета: ${firstSetStats.wonFirstWonMatch}/${total} побед (${convRate}%)`);
        if (examples.length > 0) {
          evidence.push('Примеры проигранных матчей после выигрыша 1-го сета:');
          evidence.push(...examples.slice(0, 3));
        }
      }
      break;
    }
    
    case 'h2h_comeback': {
      const comebacks: string[] = [];
      
      for (const m of matches) {
        if (m.sets.length >= 2) {
          const lostFirst = m.sets[0].player1_points < m.sets[0].player2_points;
          if (lostFirst && m.winner_id === playerId) {
            const setsStr = m.sets.map(s => `${s.player1_points}:${s.player2_points}`).join(', ');
            comebacks.push(`  ▸ ${formatDate(m.date)}: Проиграл 1й сет, выиграл матч ${m.score} (${setsStr})`);
          }
        }
      }
      
      if (comebacks.length > 0) {
        evidence.push(`${comebacks.length} успешных камбэков (победа после проигрыша 1-го сета):`);
        evidence.push(...comebacks.slice(0, 4));
      }
      break;
    }
    
    case 'h2h_dominant': {
      const wins = matches.filter(m => m.winner_id === playerId).length;
      const winRate = ((wins / matches.length) * 100).toFixed(0);
      evidence.push(`Общий счёт: ${wins} побед из ${matches.length} матчей (${winRate}%)`);
      
      const recentMatches = sortedMatches.slice(0, 5);
      evidence.push('Последние 5 встреч:');
      for (const m of recentMatches) {
        const result = m.winner_id === playerId ? '✓ Победа' : '✗ Поражение';
        evidence.push(`  ▸ ${formatDate(m.date)}: ${result} ${m.score}`);
      }
      break;
    }
    
    default: {
      // Общий анализ для неизвестных триггеров
      evidence.push('Последние матчи как доказательство:');
      for (const m of sortedMatches.slice(0, 5)) {
        const result = m.winner_id === playerId ? 'Победа' : 'Поражение';
        evidence.push(`  ▸ ${formatDate(m.date)}: ${result} ${m.score}`);
      }
    }
  }
  
  return evidence;
}

/**
 * Анализ паттернов в матчах
 */
function analyzePatterns(matches: H2HMatch[], playerId: string): string[] {
  const patterns: string[] = [];
  if (matches.length === 0) return patterns;
  
  // 1. Общий баланс
  const wins = matches.filter(m => m.winner_id === playerId).length;
  const losses = matches.length - wins;
  const winRate = ((wins / matches.length) * 100).toFixed(1);
  patterns.push(`Общий баланс: ${wins}W-${losses}L (${winRate}% побед)`);
  
  // 2. Анализ счетов
  const scoreFreq: Record<string, number> = {};
  for (const m of matches) {
    scoreFreq[m.score] = (scoreFreq[m.score] || 0) + 1;
  }
  const topScores = Object.entries(scoreFreq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([score, count]) => `${score} (x${count})`);
  patterns.push(`Частые счета: ${topScores.join(', ')}`);
  
  // 3. Сеты
  let totalSetsWon = 0;
  let totalSetsLost = 0;
  let totalPointsWon = 0;
  let totalPointsLost = 0;
  
  for (const m of matches) {
    const parts = m.score.split(':').map(Number);
    totalSetsWon += parts[0];
    totalSetsLost += parts[1];
    
    for (const s of m.sets) {
      totalPointsWon += s.player1_points;
      totalPointsLost += s.player2_points;
    }
  }
  
  patterns.push(`Сеты: ${totalSetsWon}:${totalSetsLost} (разница: ${totalSetsWon - totalSetsLost > 0 ? '+' : ''}${totalSetsWon - totalSetsLost})`);
  patterns.push(`Очки: ${totalPointsWon}:${totalPointsLost} (разница: ${totalPointsWon - totalPointsLost > 0 ? '+' : ''}${totalPointsWon - totalPointsLost})`);
  
  // 4. Первый сет
  let wonFirstSetCount = 0;
  let wonMatchAfterFirstSet = 0;
  
  for (const m of matches) {
    if (m.sets.length > 0) {
      const wonFirst = m.sets[0].player1_points > m.sets[0].player2_points;
      if (wonFirst) {
        wonFirstSetCount++;
        if (m.winner_id === playerId) wonMatchAfterFirstSet++;
      }
    }
  }
  
  if (wonFirstSetCount > 0) {
    const convRate = ((wonMatchAfterFirstSet / wonFirstSetCount) * 100).toFixed(0);
    patterns.push(`Выиграно 1-х сетов: ${wonFirstSetCount}, из них побед: ${convRate}%`);
  }
  
  // 5. Тайтовые матчи
  const closeMatches = matches.filter(m => {
    const parts = m.score.split(':').map(Number);
    return Math.abs(parts[0] - parts[1]) === 1;
  });
  
  if (closeMatches.length > 0) {
    const closeWins = closeMatches.filter(m => m.winner_id === playerId).length;
    patterns.push(`Тайтовые матчи: ${closeWins}W-${closeMatches.length - closeWins}L`);
  }
  
  // 6. Тренд (последние 3 матча)
  const recentMatches = [...matches]
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    .slice(0, 3);
  
  const recentWins = recentMatches.filter(m => m.winner_id === playerId).length;
  let trend = recentWins === 3 ? 'Горячая форма' : 
              recentWins === 0 ? 'Холодная серия' : 
              'Смешанные результаты';
  patterns.push(`Последние 3 матча: ${recentWins}W-${3 - recentWins}L (${trend})`);
  
  return patterns;
}

/**
 * Установка ширины колонок
 */
function setColumnWidths(sheet: XLSX.WorkSheet, widths: number[]): void {
  sheet['!cols'] = widths.map(w => ({ wch: w }));
}

// === ОСНОВНЫЕ ФУНКЦИИ ЭКСПОРТА ===

/**
 * Профессиональный экспорт H2H анализа по игрокам в Excel
 */
export function exportH2HToExcel(h2hStats: H2HStats): void {
  const workbook = XLSX.utils.book_new();
  const p1 = h2hStats.player1;
  const p2 = h2hStats.player2;
  
  // === ЛИСТ 1: СВОДКА ===
  const summaryData: any[][] = [];
  
  summaryData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  summaryData.push(['                              H2H АНАЛИЗ - ПРОФЕССИОНАЛЬНЫЙ ОТЧЁТ                                          ']);
  summaryData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  summaryData.push(['']);
  summaryData.push(['Дата формирования:', new Date().toLocaleString('ru-RU')]);
  summaryData.push(['']);
  
  summaryData.push(['┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐']);
  summaryData.push(['│                                    УЧАСТНИКИ АНАЛИЗА                                                    │']);
  summaryData.push(['└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘']);
  summaryData.push(['']);
  
  summaryData.push(['', 'ИГРОК 1', 'ИГРОК 2', 'РАЗНИЦА']);
  summaryData.push(['Имя:', p1.full_name, p2.full_name, '']);
  summaryData.push(['Рейтинг:', p1.current_rating, p2.current_rating, p1.current_rating - p2.current_rating > 0 ? `+${p1.current_rating - p2.current_rating}` : p1.current_rating - p2.current_rating]);
  summaryData.push(['Триггеров:', p1.triggers.length, p2.triggers.length, '']);
  summaryData.push(['']);
  
  // Подсчёт статистики
  const p1Wins = h2hStats.matches.filter(m => m.winner_id === p1.id).length;
  const p2Wins = h2hStats.matches.filter(m => m.winner_id === p2.id).length;
  const p1WinRate = h2hStats.matches.length > 0 ? ((p1Wins / h2hStats.matches.length) * 100).toFixed(1) : '0';
  const p2WinRate = h2hStats.matches.length > 0 ? ((p2Wins / h2hStats.matches.length) * 100).toFixed(1) : '0';
  
  summaryData.push(['┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐']);
  summaryData.push(['│                                    СТАТИСТИКА ВСТРЕЧ                                                    │']);
  summaryData.push(['└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘']);
  summaryData.push(['']);
  summaryData.push(['Всего матчей:', h2hStats.matches.length]);
  summaryData.push(['']);
  summaryData.push(['', 'ИГРОК 1', 'ИГРОК 2']);
  summaryData.push(['Побед:', p1Wins, p2Wins]);
  summaryData.push(['Процент побед:', `${p1WinRate}%`, `${p2WinRate}%`]);
  summaryData.push(['']);
  
  // Анализ сетов
  let totalSetsP1 = 0;
  let totalSetsP2 = 0;
  let totalPointsP1 = 0;
  let totalPointsP2 = 0;
  
  for (const match of h2hStats.matches) {
    const scoreParts = match.score.split(':').map(Number);
    totalSetsP1 += scoreParts[0];
    totalSetsP2 += scoreParts[1];
    
    for (const set of match.sets) {
      totalPointsP1 += set.player1_points;
      totalPointsP2 += set.player2_points;
    }
  }
  
  summaryData.push(['Сетов выиграно:', totalSetsP1, totalSetsP2]);
  summaryData.push(['Очков набрано:', totalPointsP1, totalPointsP2]);
  summaryData.push(['']);
  
  // Эффективность
  const serveEffP1 = h2hStats.matches.filter(m => m.serve_efficiency_p1);
  const serveEffP2 = h2hStats.matches.filter(m => m.serve_efficiency_p2);
  
  if (serveEffP1.length > 0 || serveEffP2.length > 0) {
    const avgServeP1 = serveEffP1.length > 0 
      ? (serveEffP1.reduce((sum, m) => sum + (m.serve_efficiency_p1 || 0), 0) / serveEffP1.length).toFixed(1)
      : '-';
    const avgServeP2 = serveEffP2.length > 0
      ? (serveEffP2.reduce((sum, m) => sum + (m.serve_efficiency_p2 || 0), 0) / serveEffP2.length).toFixed(1)
      : '-';
    
    summaryData.push(['Ср. эфф. подачи:', avgServeP1 !== '-' ? `${avgServeP1}%` : '-', avgServeP2 !== '-' ? `${avgServeP2}%` : '-']);
  }
  
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  setColumnWidths(summarySheet, [20, 30, 30, 15]);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Сводка');
  
  // === ЛИСТ 2: ТРИГГЕРЫ С ДОКАЗАТЕЛЬСТВАМИ ===
  const triggersData: any[][] = [];
  
  triggersData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  triggersData.push(['                              ДЕТАЛЬНЫЙ АНАЛИЗ ТРИГГЕРОВ                                                   ']);
  triggersData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  triggersData.push(['']);
  
  // Функция для добавления триггеров игрока
  const addPlayerTriggers = (player: H2HPlayer, opponentId: string) => {
    triggersData.push(['┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐']);
    triggersData.push([`│  ТРИГГЕРЫ: ${player.full_name}`]);
    triggersData.push(['└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘']);
    triggersData.push(['']);
    
    if (player.triggers.length === 0) {
      triggersData.push(['  Триггеры не обнаружены для данной пары']);
      triggersData.push(['']);
      return;
    }
    
    for (const trigger of player.triggers) {
      const info = getTriggerInfo(trigger.type);
      const sevInfo = SEVERITY_INFO[trigger.severity] || { level: `Уровень ${trigger.severity}`, description: '' };
      
      triggersData.push([`  ${info.name}`, '', '', '']);
      triggersData.push(['  ──────────────────────────────────────────────────────────────']);
      triggersData.push(['  Описание триггера:', info.description]);
      triggersData.push(['  Значение:', trigger.trigger_value]);
      triggersData.push(['  Серьёзность:', `${trigger.severity}/5 (${sevInfo.level})`]);
      triggersData.push(['  Интерпретация:', sevInfo.description]);
      triggersData.push(['']);
      
      // Добавляем доказательства
      const evidence = buildEvidenceForTrigger(trigger, h2hStats.matches, player.id);
      if (evidence.length > 0) {
        triggersData.push(['  ДОКАЗАТЕЛЬСТВА:']);
        for (const e of evidence) {
          triggersData.push([`  ${e}`]);
        }
      }
      triggersData.push(['']);
    }
  };
  
  addPlayerTriggers(p1, p2.id);
  triggersData.push(['']);
  addPlayerTriggers(p2, p1.id);
  
  const triggersSheet = XLSX.utils.aoa_to_sheet(triggersData);
  setColumnWidths(triggersSheet, [80, 30, 20, 20]);
  XLSX.utils.book_append_sheet(workbook, triggersSheet, 'Триггеры');
  
  // === ЛИСТ 3: ПАТТЕРНЫ ===
  const patternsData: any[][] = [];
  
  patternsData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  patternsData.push(['                              АНАЛИЗ ПАТТЕРНОВ                                                             ']);
  patternsData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  patternsData.push(['']);
  
  patternsData.push([`┌─ ${p1.full_name} ─────────────────────────────────────────────────────────────────────────────────────────┐`]);
  patternsData.push(['']);
  const p1Patterns = analyzePatterns(h2hStats.matches, p1.id);
  for (const pattern of p1Patterns) {
    patternsData.push([`  ${pattern}`]);
  }
  patternsData.push(['']);
  
  patternsData.push([`┌─ ${p2.full_name} ─────────────────────────────────────────────────────────────────────────────────────────┐`]);
  patternsData.push(['']);
  const p2Patterns = analyzePatterns(h2hStats.matches, p2.id);
  for (const pattern of p2Patterns) {
    patternsData.push([`  ${pattern}`]);
  }
  
  const patternsSheet = XLSX.utils.aoa_to_sheet(patternsData);
  setColumnWidths(patternsSheet, [100]);
  XLSX.utils.book_append_sheet(workbook, patternsSheet, 'Паттерны');
  
  // === ЛИСТ 4: ВСЕ МАТЧИ ===
  const matchesData: any[][] = [];
  
  matchesData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  matchesData.push(['                              ПОЛНАЯ ИСТОРИЯ МАТЧЕЙ                                                         ']);
  matchesData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  matchesData.push(['']);
  
  matchesData.push([
    '№',
    'Дата',
    'Счёт',
    'Победитель',
    'Стадия',
    'Сет 1',
    'Сет 2',
    'Сет 3',
    'Сет 4',
    'Сет 5',
    'Подача П1',
    'Приём П1',
    'Подача П2',
    'Приём П2'
  ]);
  
  const sortedMatches = [...h2hStats.matches].sort((a, b) => 
    new Date(b.date).getTime() - new Date(a.date).getTime()
  );
  
  sortedMatches.forEach((match, idx) => {
    const winner = match.winner_id === p1.id ? p1.full_name : p2.full_name;
    const winnerMarker = match.winner_id === p1.id ? '← П1' : 'П2 →';
    
    const sets = match.sets.map(s => `${s.player1_points}:${s.player2_points}`);
    while (sets.length < 5) sets.push('-');
    
    matchesData.push([
      idx + 1,
      formatDate(match.date),
      match.score,
      `${winner} ${winnerMarker}`,
      match.stage || '-',
      sets[0],
      sets[1],
      sets[2],
      sets[3],
      sets[4],
      match.serve_efficiency_p1 ? `${match.serve_efficiency_p1}%` : '-',
      match.receive_efficiency_p1 ? `${match.receive_efficiency_p1}%` : '-',
      match.serve_efficiency_p2 ? `${match.serve_efficiency_p2}%` : '-',
      match.receive_efficiency_p2 ? `${match.receive_efficiency_p2}%` : '-'
    ]);
  });
  
  const matchesSheet = XLSX.utils.aoa_to_sheet(matchesData);
  setColumnWidths(matchesSheet, [5, 12, 8, 32, 15, 8, 8, 8, 8, 8, 10, 10, 10, 10]);
  XLSX.utils.book_append_sheet(workbook, matchesSheet, 'Матчи');
  
  // === ЛИСТ 5: AI АНАЛИЗ ===
  if (h2hStats.ai_analysis) {
    const aiData: any[][] = [];
    
    aiData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
    aiData.push(['                              АНАЛИЗ ИСКУССТВЕННОГО ИНТЕЛЛЕКТА                                              ']);
    aiData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
    aiData.push(['']);
    aiData.push([`Пара: ${p1.full_name} vs ${p2.full_name}`]);
    aiData.push([`Дата анализа: ${new Date().toLocaleString('ru-RU')}`]);
    aiData.push(['']);
    aiData.push(['────────────────────────────────────────────────────────────────────────────────────────────────────────────']);
    aiData.push(['']);
    
    // Убираем think блоки и форматируем
    let aiText = h2hStats.ai_analysis.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
    
    // Разбиваем на строки для лучшего отображения
    const lines = aiText.split('\n').filter(line => line.trim());
    for (const line of lines) {
      aiData.push([line]);
    }
    
    const aiSheet = XLSX.utils.aoa_to_sheet(aiData);
    setColumnWidths(aiSheet, [120]);
    XLSX.utils.book_append_sheet(workbook, aiSheet, 'AI Анализ');
  }
  
  // === СОХРАНЕНИЕ ===
  const safeP1Name = p1.full_name.replace(/[/\\?%*:|"<>]/g, '_').substring(0, 20);
  const safeP2Name = p2.full_name.replace(/[/\\?%*:|"<>]/g, '_').substring(0, 20);
  const fileName = `H2H_${safeP1Name}_vs_${safeP2Name}_${new Date().toISOString().split('T')[0]}.xlsx`;
  
  XLSX.writeFile(workbook, fileName);
}

/**
 * Профессиональный экспорт анализа по дате в Excel
 */
export function exportDateAnalysisToExcel(dateAnalysis: DateAnalysisResult): void {
  const workbook = XLSX.utils.book_new();
  
  // === ЛИСТ 1: СВОДКА ===
  const summaryData: any[][] = [];
  
  summaryData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  summaryData.push(['                              АНАЛИЗ МАТЧЕЙ ПО ДАТЕ                                                         ']);
  summaryData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  summaryData.push(['']);
  summaryData.push(['Дата формирования отчёта:', new Date().toLocaleString('ru-RU')]);
  summaryData.push(['']);
  
  summaryData.push(['┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐']);
  summaryData.push(['│                                    ОБЩАЯ ИНФОРМАЦИЯ                                                     │']);
  summaryData.push(['└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘']);
  summaryData.push(['']);
  summaryData.push(['Анализируемая дата:', formatDate(dateAnalysis.date)]);
  summaryData.push(['Всего матчей:', dateAnalysis.total_matches]);
  summaryData.push(['Количество пар:', dateAnalysis.pairs.length]);
  summaryData.push(['']);
  
  // Топ пары по количеству матчей
  summaryData.push(['┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐']);
  summaryData.push(['│                                    ТОП-10 ПАР ПО МАТЧАМ                                                 │']);
  summaryData.push(['└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘']);
  summaryData.push(['']);
  
  const sortedPairs = [...dateAnalysis.pairs].sort((a, b) => b.total_matches - a.total_matches);
  
  summaryData.push(['№', 'Игрок 1', 'Рейтинг', 'Игрок 2', 'Рейтинг', 'Счёт H2H', 'Матчей']);
  
  sortedPairs.slice(0, 10).forEach((pair, idx) => {
    summaryData.push([
      idx + 1,
      pair.player1.full_name,
      pair.player1.current_rating,
      pair.player2.full_name,
      pair.player2.current_rating,
      `${pair.player1_wins}:${pair.player2_wins}`,
      pair.total_matches
    ]);
  });
  
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  setColumnWidths(summarySheet, [5, 28, 10, 28, 10, 12, 10]);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Сводка');
  
  // === ЛИСТ 2: ВСЕ ПАРЫ ===
  const pairsData: any[][] = [];
  
  pairsData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  pairsData.push([`                              ВСЕ ПАРЫ НА ${formatDate(dateAnalysis.date)}                                 `]);
  pairsData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  pairsData.push(['']);
  
  pairsData.push([
    '№',
    'Игрок 1',
    'Рейтинг 1',
    'Игрок 2',
    'Рейтинг 2',
    'Разн. рейтинга',
    'Побед П1',
    'Побед П2',
    'Матчей',
    'Доминант'
  ]);
  
  dateAnalysis.pairs.forEach((pair, idx) => {
    const ratingDiff = pair.player1.current_rating - pair.player2.current_rating;
    const dominant = pair.player1_wins > pair.player2_wins 
      ? pair.player1.full_name 
      : pair.player2_wins > pair.player1_wins 
        ? pair.player2.full_name 
        : 'Равенство';
    
    pairsData.push([
      idx + 1,
      pair.player1.full_name,
      pair.player1.current_rating,
      pair.player2.full_name,
      pair.player2.current_rating,
      ratingDiff > 0 ? `+${ratingDiff}` : ratingDiff,
      pair.player1_wins,
      pair.player2_wins,
      pair.total_matches,
      dominant
    ]);
  });
  
  const pairsSheet = XLSX.utils.aoa_to_sheet(pairsData);
  setColumnWidths(pairsSheet, [5, 28, 10, 28, 10, 12, 12, 12, 10, 28]);
  XLSX.utils.book_append_sheet(workbook, pairsSheet, 'Пары');
  
  // === ЛИСТ 3: ВСЕ МАТЧИ ===
  const matchesData: any[][] = [];
  
  matchesData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  matchesData.push([`                              ВСЕ МАТЧИ НА ${formatDate(dateAnalysis.date)}                               `]);
  matchesData.push(['═══════════════════════════════════════════════════════════════════════════════════════════════════════════']);
  matchesData.push(['']);
  
  matchesData.push([
    '№',
    'Игрок 1',
    'Игрок 2',
    'Счёт',
    'Победитель',
    'Стадия',
    'Сеты (детально)',
    'Триггеры П1',
    'Триггеры П2'
  ]);
  
  let matchNum = 0;
  for (const pair of dateAnalysis.pairs) {
    for (const match of pair.matches) {
      matchNum++;
      const winner = match.winner_id === pair.player1.id 
        ? pair.player1.full_name 
        : pair.player2.full_name;
      const winnerMarker = match.winner_id === pair.player1.id ? '← П1' : 'П2 →';
      
      const setsStr = match.sets
        .map(s => `${s.player1_points}:${s.player2_points}`)
        .join(' | ');
      
      const p1Triggers = match.player1_triggers.length > 0 
        ? match.player1_triggers.map(t => getTriggerInfo(t.type).name).join(', ')
        : '-';
      const p2Triggers = match.player2_triggers.length > 0
        ? match.player2_triggers.map(t => getTriggerInfo(t.type).name).join(', ')
        : '-';
      
      matchesData.push([
        matchNum,
        pair.player1.full_name,
        pair.player2.full_name,
        match.score,
        `${winner} ${winnerMarker}`,
        match.stage || '-',
        setsStr,
        p1Triggers,
        p2Triggers
      ]);
    }
  }
  
  const matchesSheet = XLSX.utils.aoa_to_sheet(matchesData);
  setColumnWidths(matchesSheet, [5, 28, 28, 8, 32, 15, 35, 30, 30]);
  XLSX.utils.book_append_sheet(workbook, matchesSheet, 'Матчи');
  
  // === СОХРАНЕНИЕ ===
  const fileName = `H2H_Анализ_${dateAnalysis.date}_${new Date().toISOString().split('T')[0]}.xlsx`;
  
  XLSX.writeFile(workbook, fileName);
}
