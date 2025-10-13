import * as XLSX from 'xlsx';
import { generateExampleExcelData } from './excelParser';

export const downloadExampleExcelFile = () => {
  const exampleData = generateExampleExcelData();
  
  // Создаем новую рабочую книгу
  const workbook = XLSX.utils.book_new();
  
  // Создаем лист с данными
  const worksheet = XLSX.utils.json_to_sheet(exampleData);
  
  // Добавляем лист в книгу
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Матчи');
  
  // Скачиваем файл
  XLSX.writeFile(workbook, 'пример_матчей.xlsx');
};

// Функция для проверки структуры загруженного файла
export const validateExcelStructure = (data: any[]): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];
  
  if (!data || data.length === 0) {
    errors.push('Файл не содержит данных');
    return { isValid: false, errors };
  }
  
  const firstRow = data[0];
  const availableFields = Object.keys(firstRow);
  
  // Проверяем наличие обязательных полей (с учетом вариантов названий)
  const fieldVariants = {
    'Игрок 1': ['Игрок 1', 'игрок 1', 'Игрок1', 'Player 1'],
    'Игрок 2': ['Игрок 2', 'игрок 2', 'Игрок2', 'Player 2'],
    'Счёт': ['Счёт', 'счёт', 'Счет', 'Score', 'score'],
    'Стадия': ['Стадия', 'стадия', 'Этап', 'этап', 'Stage'],
    'Турнир': ['Турнир', 'турнир', 'Tournament', 'tournament']
  };
  
  for (const [field, variants] of Object.entries(fieldVariants)) {
    const hasField = variants.some(variant => 
      availableFields.some(available => 
        available.toLowerCase() === variant.toLowerCase()
      )
    );
    
    if (!hasField) {
      errors.push(`Не найдено поле "${field}" или его варианты: ${variants.join(', ')}`);
    }
  }
  
  return {
    isValid: errors.length === 0,
    errors
  };
};
