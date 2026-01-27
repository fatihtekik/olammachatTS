import * as XLSX from 'xlsx';

// === ТИПЫ ДАННЫХ ===
interface SetData {
  set_number: number;
  player_points: number;
  opponent_points: number;
  won: boolean;
}

interface EvidenceData {
  date: string;
  time?: string;
  opponent: string;
  opponent_rating?: number;
  score: string;
  sets?: SetData[];
  highlight: string;
  serve_efficiency?: number;
  receive_efficiency?: number;
  was_favorite: boolean;
  rating_diff: number;
  red_flags: string[];
}

interface PlayerStats {
  matches_played: number;
  wins: number;
  losses: number;
  win_rate: number;
  sets_won: number;
  sets_lost: number;
  recent_form: string | string[];
  recent_matches?: Array<{
    date: string;
    opponent: string;
    result: 'W' | 'L';
    score: string;
    time?: string;
  }>;
}

interface Trigger {
  id: string;
  player_id: string;
  player_name: string;
  player_rating?: number;
  trigger_type: string;
  trigger_subtype?: string;
  trigger_value: string;
  severity_level: number;
  period_start: string;
  period_end: string;
  is_pair: boolean;
  trigger_metadata?: any;
  created_at: string;
  ai_analysis?: string;
  player_stats?: PlayerStats;
  evidence?: EvidenceData[];
}

interface AnalysisResult {
  period_start: string;
  period_end: string;
  total_players: number;
  total_matches: number;
  triggers_found: number;
  top_performers: any[];
  problem_players: any[];
  triggers: Trigger[];
}

// Маппинг типов триггеров на русские названия
const triggerTypeNames: Record<string, string> = {
  'top_performers': 'Топ игроки',
  'losers_50_percent': 'Слабые результаты (<50%)',
  'defeat_0_3': 'Поражения 0:3',
  'won_2_lost_3rd_set': 'Проигрыш после 2:0',
  'early_final_exit_advanced': 'Досрочный уход',
  'led_1_set_lost_match': 'Потеря лидерства (1:0)',
  'led_2_sets_lost_match': 'Критический проигрыш (2:0)',
  'psychological_breakdown': 'Психологические проблемы',
  'comeback_inability': 'Проблемы с камбеками',
  'pressure_situations': 'Игра под давлением',
  'time_performance': 'Слабая форма в ночное время',
  'losing_streaks': 'Проигрыши в ряд',
  'post_holiday_problems': 'Проблемы после праздников'
};

// Маппинг уровней серьезности
const severityNames: Record<number, string> = {
  1: 'Низкая',
  2: 'Средняя',
  3: 'Высокая'
};

// Убираем think-блоки из AI анализа
const cleanAIResponse = (text: string | undefined): string => {
  if (!text) return '';
  // Убираем <think>...</think> блоки
  return text.replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
};

// Форматируем дату
const formatDate = (dateString: string): string => {
  if (!dateString) return '';
  try {
    return new Date(dateString).toLocaleDateString('ru-RU');
  } catch {
    return dateString;
  }
};

// Форматируем форму игрока
const formatRecentForm = (form: string | string[] | undefined): string => {
  if (!form) return '';
  if (Array.isArray(form)) {
    return form.join('');
  }
  return form;
};

// Форматируем сеты в строку
const formatSets = (sets: SetData[] | undefined): string => {
  if (!sets || sets.length === 0) return '';
  return sets
    .sort((a, b) => a.set_number - b.set_number)
    .map(s => `${s.player_points}:${s.opponent_points}`)
    .join(' | ');
};

// Форматируем красные флаги
const formatRedFlags = (flags: string[] | undefined): string => {
  if (!flags || flags.length === 0) return '';
  return flags.join('; ');
};

/**
 * Экспортирует результаты анализа игроков в Excel файл
 */
export const exportAnalysisToExcel = (analysisResult: AnalysisResult): void => {
  if (!analysisResult || !analysisResult.triggers || analysisResult.triggers.length === 0) {
    alert('Нет данных для экспорта');
    return;
  }

  // Создаём workbook
  const workbook = XLSX.utils.book_new();

  // === ЛИСТ 1: СВОДКА ===
  const summaryData = [
    ['СВОДКА АНАЛИЗА ИГРОКОВ'],
    [],
    ['Период анализа', `${formatDate(analysisResult.period_start)} - ${formatDate(analysisResult.period_end)}`],
    ['Дата экспорта', formatDate(new Date().toISOString())],
    [],
    ['Статистика'],
    ['Всего игроков проанализировано', analysisResult.total_players],
    ['Всего матчей за период', analysisResult.total_matches],
    ['Триггеров найдено', analysisResult.triggers_found],
  ];

  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData);
  
  // Устанавливаем ширину колонок
  summarySheet['!cols'] = [
    { wch: 35 },
    { wch: 40 }
  ];
  
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Сводка');

  // === ЛИСТ 2: ВСЕ ТРИГГЕРЫ ===
  const triggersHeaders = [
    'Игрок',
    'Рейтинг',
    'Тип триггера',
    'Описание',
    'Уровень серьезности',
    'Матчи',
    'Победы',
    'Поражения',
    'Винрейт (%)',
    'Сеты (выигр/проигр)',
    'Форма (5 последних)',
    'Период триггера',
    'AI Анализ'
  ];

  const triggersData = analysisResult.triggers.map(trigger => [
    trigger.player_name,
    trigger.player_rating || '',
    triggerTypeNames[trigger.trigger_type] || trigger.trigger_type,
    trigger.trigger_value,
    severityNames[trigger.severity_level] || trigger.severity_level,
    trigger.player_stats?.matches_played || '',
    trigger.player_stats?.wins || '',
    trigger.player_stats?.losses || '',
    trigger.player_stats?.win_rate ? trigger.player_stats.win_rate.toFixed(1) : '',
    trigger.player_stats ? `${trigger.player_stats.sets_won}:${trigger.player_stats.sets_lost}` : '',
    formatRecentForm(trigger.player_stats?.recent_form),
    `${formatDate(trigger.period_start)} - ${formatDate(trigger.period_end)}`,
    cleanAIResponse(trigger.ai_analysis)
  ]);

  const triggersSheetData = [triggersHeaders, ...triggersData];
  const triggersSheet = XLSX.utils.aoa_to_sheet(triggersSheetData);
  
  // Устанавливаем ширину колонок
  triggersSheet['!cols'] = [
    { wch: 25 },  // Игрок
    { wch: 10 },  // Рейтинг
    { wch: 30 },  // Тип триггера
    { wch: 50 },  // Описание
    { wch: 18 },  // Серьезность
    { wch: 8 },   // Матчи
    { wch: 8 },   // Победы
    { wch: 10 },  // Поражения
    { wch: 12 },  // Винрейт
    { wch: 15 },  // Сеты
    { wch: 15 },  // Форма
    { wch: 25 },  // Период
    { wch: 100 }  // AI Анализ - увеличенная ширина для длинного текста
  ];

  // Включаем перенос текста для колонки AI Анализ
  for (let i = 1; i <= triggersData.length; i++) {
    const cellRef = XLSX.utils.encode_cell({ r: i, c: 12 }); // Колонка M (AI Анализ)
    if (triggersSheet[cellRef]) {
      triggersSheet[cellRef].s = { alignment: { wrapText: true, vertical: 'top' } };
    }
  }
  
  XLSX.utils.book_append_sheet(workbook, triggersSheet, 'Все триггеры');

  // === ЛИСТ 3: ДОКАЗАТЕЛЬСТВА (EVIDENCE) ===
  const evidenceHeaders = [
    'Игрок',
    'Рейтинг игрока',
    'Тип триггера',
    'Дата матча',
    'Время',
    'Соперник',
    'Рейтинг соперника',
    'Статус игрока',
    'Разница рейтинга',
    'Итоговый счёт',
    'Счёт по сетам',
    'Подача (%)',
    'Приём (%)',
    'Описание',
    'Красные флаги'
  ];

  const evidenceData: any[][] = [];
  
  analysisResult.triggers.forEach(trigger => {
    if (trigger.evidence && trigger.evidence.length > 0) {
      trigger.evidence.forEach(ev => {
        evidenceData.push([
          trigger.player_name,
          trigger.player_rating || '',
          triggerTypeNames[trigger.trigger_type] || trigger.trigger_type,
          formatDate(ev.date),
          ev.time || '',
          ev.opponent,
          ev.opponent_rating || '',
          ev.was_favorite ? 'Фаворит' : 'Аутсайдер',
          ev.rating_diff,
          ev.score,
          formatSets(ev.sets),
          ev.serve_efficiency !== undefined ? ev.serve_efficiency.toFixed(1) : '',
          ev.receive_efficiency !== undefined ? ev.receive_efficiency.toFixed(1) : '',
          ev.highlight,
          formatRedFlags(ev.red_flags)
        ]);
      });
    }
  });

  if (evidenceData.length > 0) {
    const evidenceSheetData = [evidenceHeaders, ...evidenceData];
    const evidenceSheet = XLSX.utils.aoa_to_sheet(evidenceSheetData);
    
    // Устанавливаем ширину колонок
    evidenceSheet['!cols'] = [
      { wch: 25 },  // Игрок
      { wch: 12 },  // Рейтинг игрока
      { wch: 25 },  // Тип триггера
      { wch: 12 },  // Дата
      { wch: 8 },   // Время
      { wch: 25 },  // Соперник
      { wch: 14 },  // Рейтинг соперника
      { wch: 12 },  // Статус
      { wch: 15 },  // Разница
      { wch: 12 },  // Итоговый счёт
      { wch: 25 },  // Счёт по сетам
      { wch: 10 },  // Подача
      { wch: 10 },  // Приём
      { wch: 50 },  // Описание
      { wch: 40 }   // Красные флаги
    ];
    
    XLSX.utils.book_append_sheet(workbook, evidenceSheet, 'Доказательства');
  }

  // === ЛИСТ 4: ИГРОКИ (группировка) ===
  const playersMap = new Map<string, {
    playerName: string;
    playerRating: number | undefined;
    triggers: Trigger[];
    stats: PlayerStats | undefined;
  }>();

  analysisResult.triggers.forEach(trigger => {
    const existing = playersMap.get(trigger.player_id);
    if (existing) {
      existing.triggers.push(trigger);
      // Обновляем stats если есть более полные данные
      if (!existing.stats && trigger.player_stats) {
        existing.stats = trigger.player_stats;
      }
    } else {
      playersMap.set(trigger.player_id, {
        playerName: trigger.player_name,
        playerRating: trigger.player_rating,
        triggers: [trigger],
        stats: trigger.player_stats
      });
    }
  });

  const playersHeaders = [
    'Игрок',
    'Рейтинг',
    'Количество триггеров',
    'Типы триггеров',
    'Макс. серьезность',
    'Матчи',
    'Победы',
    'Поражения',
    'Винрейт (%)',
    'Сеты (выигр/проигр)',
    'Форма (5 последних)'
  ];

  const playersData = Array.from(playersMap.values()).map(player => {
    const maxSeverity = Math.max(...player.triggers.map(t => t.severity_level || 0));
    const triggerTypesSet = new Set(player.triggers.map(t => 
      triggerTypeNames[t.trigger_type] || t.trigger_type
    ));
    const triggerTypesStr = Array.from(triggerTypesSet).join('; ');
    
    return [
      player.playerName,
      player.playerRating || '',
      player.triggers.length,
      triggerTypesStr,
      severityNames[maxSeverity] || maxSeverity,
      player.stats?.matches_played || '',
      player.stats?.wins || '',
      player.stats?.losses || '',
      player.stats?.win_rate ? player.stats.win_rate.toFixed(1) : '',
      player.stats ? `${player.stats.sets_won}:${player.stats.sets_lost}` : '',
      formatRecentForm(player.stats?.recent_form)
    ];
  });

  // Сортируем по количеству триггеров (убывание)
  playersData.sort((a, b) => (b[2] as number) - (a[2] as number));

  const playersSheetData = [playersHeaders, ...playersData];
  const playersSheet = XLSX.utils.aoa_to_sheet(playersSheetData);
  
  // Устанавливаем ширину колонок
  playersSheet['!cols'] = [
    { wch: 25 },  // Игрок
    { wch: 10 },  // Рейтинг
    { wch: 18 },  // Кол-во триггеров
    { wch: 50 },  // Типы триггеров
    { wch: 18 },  // Макс. серьезность
    { wch: 8 },   // Матчи
    { wch: 8 },   // Победы
    { wch: 10 },  // Поражения
    { wch: 12 },  // Винрейт
    { wch: 15 },  // Сеты
    { wch: 15 }   // Форма
  ];
  
  XLSX.utils.book_append_sheet(workbook, playersSheet, 'Игроки');

  // === ЛИСТ 5: ПОСЛЕДНИЕ МАТЧИ ===
  const recentMatchesHeaders = [
    'Игрок',
    'Рейтинг',
    'Дата матча',
    'Соперник',
    'Результат',
    'Счёт',
    'Время'
  ];

  const recentMatchesData: any[][] = [];
  
  analysisResult.triggers.forEach(trigger => {
    if (trigger.player_stats?.recent_matches && trigger.player_stats.recent_matches.length > 0) {
      trigger.player_stats.recent_matches.forEach(match => {
        recentMatchesData.push([
          trigger.player_name,
          trigger.player_rating || '',
          formatDate(match.date),
          match.opponent,
          match.result === 'W' ? 'Победа' : 'Поражение',
          match.score,
          match.time || ''
        ]);
      });
    }
  });

  if (recentMatchesData.length > 0) {
    // Убираем дубликаты (один игрок может иметь несколько триггеров)
    const uniqueMatches = new Map<string, any[]>();
    recentMatchesData.forEach(row => {
      const key = `${row[0]}-${row[2]}-${row[3]}-${row[5]}`; // игрок-дата-соперник-счёт
      if (!uniqueMatches.has(key)) {
        uniqueMatches.set(key, row);
      }
    });

    const recentMatchesSheetData = [recentMatchesHeaders, ...Array.from(uniqueMatches.values())];
    const recentMatchesSheet = XLSX.utils.aoa_to_sheet(recentMatchesSheetData);
    
    // Устанавливаем ширину колонок
    recentMatchesSheet['!cols'] = [
      { wch: 25 },  // Игрок
      { wch: 10 },  // Рейтинг
      { wch: 12 },  // Дата
      { wch: 25 },  // Соперник
      { wch: 12 },  // Результат
      { wch: 12 },  // Счёт
      { wch: 10 }   // Время
    ];
    
    XLSX.utils.book_append_sheet(workbook, recentMatchesSheet, 'Последние матчи');
  }

  // === ЛИСТ 6: СТАТИСТИКА ПО ТРИГГЕРАМ ===
  const triggerStatsMap = new Map<string, { count: number; players: Set<string> }>();
  
  analysisResult.triggers.forEach(trigger => {
    const existing = triggerStatsMap.get(trigger.trigger_type);
    if (existing) {
      existing.count++;
      existing.players.add(trigger.player_name);
    } else {
      triggerStatsMap.set(trigger.trigger_type, {
        count: 1,
        players: new Set([trigger.player_name])
      });
    }
  });

  const triggerStatsHeaders = [
    'Тип триггера',
    'Количество срабатываний',
    'Уникальных игроков',
    'Игроки'
  ];

  const triggerStatsData = Array.from(triggerStatsMap.entries())
    .sort((a, b) => b[1].count - a[1].count)
    .map(([type, data]) => [
      triggerTypeNames[type] || type,
      data.count,
      data.players.size,
      Array.from(data.players).join(', ')
    ]);

  const triggerStatsSheetData = [triggerStatsHeaders, ...triggerStatsData];
  const triggerStatsSheet = XLSX.utils.aoa_to_sheet(triggerStatsSheetData);
  
  // Устанавливаем ширину колонок
  triggerStatsSheet['!cols'] = [
    { wch: 35 },  // Тип триггера
    { wch: 22 },  // Количество
    { wch: 18 },  // Уникальных игроков
    { wch: 80 }   // Игроки
  ];
  
  XLSX.utils.book_append_sheet(workbook, triggerStatsSheet, 'Статистика по триггерам');

  // === ЛИСТ 7: ДЕТАЛЬНЫЙ AI АНАЛИЗ ===
  const aiAnalysisHeaders = [
    'Игрок',
    'Рейтинг',
    'Тип триггера',
    'Описание проблемы',
    'AI Анализ (полный текст)'
  ];

  const aiAnalysisData: any[][] = [];
  
  // Собираем уникальные записи игрок + триггер с AI анализом
  const seenAiAnalysis = new Set<string>();
  
  analysisResult.triggers.forEach(trigger => {
    const aiText = cleanAIResponse(trigger.ai_analysis);
    if (aiText) {
      const key = `${trigger.player_id}-${trigger.trigger_type}`;
      if (!seenAiAnalysis.has(key)) {
        seenAiAnalysis.add(key);
        aiAnalysisData.push([
          trigger.player_name,
          trigger.player_rating || '',
          triggerTypeNames[trigger.trigger_type] || trigger.trigger_type,
          trigger.trigger_value,
          aiText
        ]);
      }
    }
  });

  if (aiAnalysisData.length > 0) {
    const aiAnalysisSheetData = [aiAnalysisHeaders, ...aiAnalysisData];
    const aiAnalysisSheet = XLSX.utils.aoa_to_sheet(aiAnalysisSheetData);
    
    // Устанавливаем ширину колонок
    aiAnalysisSheet['!cols'] = [
      { wch: 25 },   // Игрок
      { wch: 10 },   // Рейтинг
      { wch: 30 },   // Тип триггера
      { wch: 50 },   // Описание проблемы
      { wch: 150 }   // AI Анализ - очень широкая колонка
    ];
    
    // Включаем перенос текста для колонки AI Анализ
    for (let i = 1; i <= aiAnalysisData.length; i++) {
      const cellRef = XLSX.utils.encode_cell({ r: i, c: 4 }); // Колонка E (AI Анализ)
      if (aiAnalysisSheet[cellRef]) {
        aiAnalysisSheet[cellRef].s = { alignment: { wrapText: true, vertical: 'top' } };
      }
    }
    
    XLSX.utils.book_append_sheet(workbook, aiAnalysisSheet, 'AI Анализ игроков');
  }

  // === СОХРАНЯЕМ ФАЙЛ ===
  const dateStart = formatDate(analysisResult.period_start).replace(/\./g, '-');
  const dateEnd = formatDate(analysisResult.period_end).replace(/\./g, '-');
  const fileName = `Анализ_игроков_${dateStart}_${dateEnd}.xlsx`.replace(/\s+/g, '_');
  
  XLSX.writeFile(workbook, fileName);
  
  console.log(`✅ Excel файл "${fileName}" успешно создан с ${XLSX.utils.book_new().SheetNames?.length || 6} листами`);
};

export default exportAnalysisToExcel;
