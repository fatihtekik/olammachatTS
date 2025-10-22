"""
Скрипт для извлечения и сохранения логов анализа матчей.
Перенаправляет вывод процесса загрузки Excel в текстовый файл.
"""
import sys
import os
from datetime import datetime

# Добавляем путь к backend
sys.path.insert(0, os.path.dirname(__file__))

def setup_logging_to_file(filename=None):
    """
    Настраивает перенаправление вывода в файл
    """
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"match_analysis_log_{timestamp}.txt"
    
    log_file = open(filename, 'w', encoding='utf-8')
    
    # Создаём класс который пишет и в файл и в консоль
    class DualWriter:
        def __init__(self, *files):
            self.files = files
        
        def write(self, text):
            for f in self.files:
                f.write(text)
                f.flush()  # Немедленная запись
        
        def flush(self):
            for f in self.files:
                f.flush()
    
    # Сохраняем оригинальные stdout и stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Перенаправляем в файл + консоль
    sys.stdout = DualWriter(original_stdout, log_file)
    sys.stderr = DualWriter(original_stderr, log_file)
    
    print("="*80)
    print(f"📝 ЛОГИРОВАНИЕ АНАЛИЗА МАТЧЕЙ")
    print(f"⏰ Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Файл логов: {os.path.abspath(filename)}")
    print("="*80)
    print()
    
    return log_file, original_stdout, original_stderr

def parse_log_file(log_file_path, output_file=None):
    """
    Парсит файл логов и извлекает только строки с анализом матчей
    """
    if output_file is None:
        base_name = os.path.splitext(log_file_path)[0]
        output_file = f"{base_name}_matches_only.txt"
    
    print(f"\n📖 Парсинг логов из: {log_file_path}")
    print(f"📝 Сохранение в: {output_file}")
    
    with open(log_file_path, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()
    
    # Фильтруем только строки с анализом матчей
    match_lines = []
    in_match_block = False
    current_match = []
    
    for line in lines:
        # Начало блока матча
        if '📝 Обрабатываем строку' in line or '📊 Рейтинг из поля' in line or \
           '🎾 Детальные сеты' in line or '📊 Счёт из новых колонок' in line or \
           '🏆 Победитель' in line or '✅ Создан матч' in line:
            in_match_block = True
            current_match.append(line)
            
            # Конец блока матча
            if '✅ Создан матч' in line:
                match_lines.extend(current_match)
                match_lines.append('\n')  # Пустая строка между матчами
                current_match = []
                in_match_block = False
    
    # Сохраняем отфильтрованные строки
    with open(output_file, 'w', encoding='utf-8') as outfile:
        outfile.write("="*80 + "\n")
        outfile.write("АНАЛИЗ МАТЧЕЙ - ДЕТАЛЬНАЯ ИНФОРМАЦИЯ\n")
        outfile.write(f"Создано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        outfile.write("="*80 + "\n\n")
        outfile.writelines(match_lines)
        outfile.write("\n" + "="*80 + "\n")
        outfile.write(f"Всего обработано матчей: {len([l for l in match_lines if '✅ Создан матч' in l])}\n")
        outfile.write("="*80 + "\n")
    
    matches_count = len([l for l in match_lines if '✅ Создан матч' in l])
    print(f"✅ Извлечено {matches_count} матчей")
    print(f"📁 Результат сохранён в: {os.path.abspath(output_file)}")
    
    return output_file

def show_match_statistics(log_file_path):
    """
    Показывает статистику по обработанным матчам из лога
    """
    print("\n" + "="*80)
    print("📊 СТАТИСТИКА ОБРАБОТКИ МАТЧЕЙ")
    print("="*80)
    
    with open(log_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Подсчёт матчей
    created_matches = content.count('✅ Создан матч')
    print(f"✅ Создано матчей: {created_matches}")
    
    # Подсчёт побед по счёту
    victories_3_0 = content.count('(3:0)')
    victories_3_1 = content.count('(3:1)')
    victories_3_2 = content.count('(3:2)')
    victories_2_3 = content.count('(2:3)')
    victories_1_3 = content.count('(1:3)')
    victories_0_3 = content.count('(0:3)')
    
    print(f"\n📊 Распределение по счёту:")
    print(f"   3:0 - {victories_3_0} матчей")
    print(f"   3:1 - {victories_3_1} матчей")
    print(f"   3:2 - {victories_3_2} матчей")
    print(f"   2:3 - {victories_2_3} матчей")
    print(f"   1:3 - {victories_1_3} матчей")
    print(f"   0:3 - {victories_0_3} матчей")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Логирование и анализ матчей')
    parser.add_argument('--parse', type=str, help='Путь к файлу логов для парсинга')
    parser.add_argument('--stats', type=str, help='Показать статистику из файла логов')
    parser.add_argument('--output', type=str, help='Имя выходного файла')
    
    args = parser.parse_args()
    
    if args.parse:
        # Парсим существующий лог
        output_file = parse_log_file(args.parse, args.output)
        show_match_statistics(output_file)
    elif args.stats:
        # Показываем статистику
        show_match_statistics(args.stats)
    else:
        print("="*80)
        print("📝 СКРИПТ ЛОГИРОВАНИЯ АНАЛИЗА МАТЧЕЙ")
        print("="*80)
        print("\nИспользование:")
        print("\n1. Для ПАРСИНГА существующего лога:")
        print("   python extract_match_logs.py --parse log_file.txt")
        print("   python extract_match_logs.py --parse log_file.txt --output custom_name.txt")
        print("\n2. Для просмотра СТАТИСТИКИ:")
        print("   python extract_match_logs.py --stats log_file.txt")
        print("\n3. Для ЛОГИРОВАНИЯ при загрузке Excel:")
        print("   Используйте этот модуль как библиотеку:")
        print()
        print("   from extract_match_logs import setup_logging_to_file")
        print("   log_file, _, _ = setup_logging_to_file('my_analysis.txt')")
        print("   # ... ваш код загрузки Excel ...")
        print("   log_file.close()")
        print("\n" + "="*80)
