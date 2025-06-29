import * as XLSX from 'xlsx';
import { MatchData } from '../types/chat';

export interface ExcelMatchData {
  игрок_1: string;
  игрок_2: string;
  рейтинг_1: number;
  рейтинг_2: number;
  счёт: string;
  этап: string;
  турнир: string;
  лига: string;
}

export const parseExcelFile = async (file: File): Promise<ExcelMatchData[]> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      try {
        const data = e.target?.result;
        if (!data) {
          reject(new Error('Не удалось прочитать файл'));
          return;
        }

        // Читаем Excel файл
        const workbook = XLSX.read(data, { type: 'binary' });
        
        // Берем первый лист
        const firstSheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[firstSheetName];
        
        // Конвертируем в JSON
        const jsonData = XLSX.utils.sheet_to_json(worksheet);
          console.log('Данные из Excel:', jsonData);
        
        // Преобразуем данные в нужный формат
        const matchesData: ExcelMatchData[] = jsonData.map((row: any, index: number) => {
          // Попробуем разные варианты названий колонок
          const getColumnValue = (possibleNames: string[]): any => {
            for (const name of possibleNames) {
              if (row[name] !== undefined && row[name] !== null && row[name] !== '') {
                return row[name];
              }
            }
            return '';
          };

          // Функция для извлечения имени и рейтинга из строки вида "Имя Фамилия Отчество rating: 123.45"
          const parsePlayerData = (playerString: string): { name: string; rating: number } => {
            if (!playerString) {
              return { name: '', rating: 1000 };
            }
            
            const ratingMatch = playerString.match(/rating:\s*(\d+(?:\.\d+)?)/);
            const rating = ratingMatch ? parseFloat(ratingMatch[1]) : 1000;
            
            // Убираем "rating: XXX.XX" из строки чтобы получить только имя
            const name = playerString.replace(/\s*rating:\s*\d+(?:\.\d+)?/, '').trim();
            
            return { name: name || `Игрок (строка ${index + 1})`, rating };
          };

          // Получаем данные игроков
          const player1String = String(getColumnValue([
            'Игрок 1', 'игрок 1', 'Игрок1', 'игрок1', 'Player 1', 'player 1'
          ]) || '');
          
          const player2String = String(getColumnValue([
            'Игрок 2', 'игрок 2', 'Игрок2', 'игрок2', 'Player 2', 'player 2'
          ]) || '');

          const player1Data = parsePlayerData(player1String);
          const player2Data = parsePlayerData(player2String);

          // Получаем информацию о турнире и лиге из колонки "Турнир"
          const tournamentString = String(getColumnValue([
            'Турнир', 'турнир', 'Tournament', 'tournament'
          ]) || 'Неизвестно');
          
          // Пытаемся извлечь турнир и лигу из строки вида "Турнир А5. Лига 450-500"
          const tournamentMatch = tournamentString.match(/^(.*?)\.\s*Лига\s*(.*?)$/);
          const tournament = tournamentMatch ? tournamentMatch[1].trim() : tournamentString;
          const league = tournamentMatch ? `Лига ${tournamentMatch[2].trim()}` : 'Неизвестно';

          return {
            игрок_1: player1Data.name,
            игрок_2: player2Data.name,
            рейтинг_1: player1Data.rating,
            рейтинг_2: player2Data.rating,
            
            счёт: String(getColumnValue([
              'Счёт', 'счёт', 'Счет', 'счет', 'Score', 'score'
            ]) || '0-0'),
            
            этап: String(getColumnValue([
              'Стадия', 'стадия', 'Этап', 'этап', 'Stage', 'stage'
            ]) || 'Неизвестно'),
            
            турнир: tournament,
            лига: league
          };
        });

        console.log('Обработанные данные матчей:', matchesData);
        resolve(matchesData);
        
      } catch (error) {
        console.error('Ошибка при парсинге Excel файла:', error);
        reject(new Error(`Ошибка при обработке Excel файла: ${error}`));
      }
    };
    
    reader.onerror = () => {
      reject(new Error('Ошибка при чтении файла'));
    };
    
    reader.readAsBinaryString(file);
  });
};

// Функция для создания примера Excel файла
export const generateExampleExcelData = () => {
  return [
    {
      'Игрок 1': 'Лбов Юрий Вячеславович rating: 476.81',
      'Счёт': '2-3 (4-11 11-6 11-4 8-11 6-11)',
      'Игрок 2': 'Малиновский Роман Александрович rating: 464.68',
      'Стадия': 'Группа',
      'Турнир': 'Турнир А5. Лига 450-500'
    },
    {
      'Игрок 1': 'Кутузов Олег Геннадьевич rating: 567.63',
      'Счёт': '1-3 (11-7 11-13 11-13 9-11)',
      'Игрок 2': 'Пандур Иван Георгиевич rating: 561.78',
      'Стадия': 'Группа',
      'Турнир': 'Турнир А6. Лига 550-600'
    },
    {
      'Игрок 1': 'Немашкало Владимир Фёдорович rating: 314.45',
      'Счёт': '0-3 (3-11 8-11 8-11)',
      'Игрок 2': 'Кольмин Александр Александрович rating: 321.19',
      'Стадия': 'Группа',
      'Турнир': 'Турнир А4. Лига 300-350'
    }
  ];
};
