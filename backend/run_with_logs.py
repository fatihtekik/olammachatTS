"""
Обёртка для main.py с автоматическим логированием в файл.
Запускает FastAPI сервер и сохраняет все логи в файл.
"""
import sys
import os
from datetime import datetime
import subprocess

def run_with_logging():
    """Запускает main.py с перенаправлением вывода в файл"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"server_log_{timestamp}.txt"
    
    print("="*80)
    print("🚀 ЗАПУСК СЕРВЕРА С ЛОГИРОВАНИЕМ")
    print("="*80)
    print(f"⏰ Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Файл логов: {log_filename}")
    print(f"💡 Все логи (включая анализ матчей) будут сохранены в этот файл")
    print("="*80)
    print()
    
    # Открываем файл для записи логов
    with open(log_filename, 'w', encoding='utf-8', buffering=1) as log_file:
        # Записываем заголовок
        log_file.write("="*80 + "\n")
        log_file.write("ЛОГИ СЕРВЕРА OLLAMACHAT\n")
        log_file.write(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write("="*80 + "\n\n")
        log_file.flush()
        
        try:
            # Запускаем main.py с перенаправлением stdout и stderr
            # Используем Tee-эффект: вывод идёт и в консоль и в файл
            process = subprocess.Popen(
                [sys.executable, 'main.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Читаем вывод построчно и дублируем в файл
            for line in iter(process.stdout.readline, ''):
                if line:
                    print(line, end='')  # В консоль
                    log_file.write(line)  # В файл
                    log_file.flush()  # Немедленная запись
            
            process.wait()
            
            # Записываем завершение
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            footer = f"\n{'='*80}\nВремя завершения: {end_time}\n{'='*80}\n"
            log_file.write(footer)
            print(footer)
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Сервер остановлен пользователем")
            log_file.write("\n\n⚠️ Сервер остановлен пользователем (Ctrl+C)\n")
        except Exception as e:
            error_msg = f"\n\n❌ Ошибка: {e}\n"
            print(error_msg)
            log_file.write(error_msg)
    
    print(f"\n✅ Логи сохранены в: {os.path.abspath(log_filename)}")
    print(f"\n💡 Для извлечения только логов матчей используйте:")
    print(f"   python extract_match_logs.py --parse {log_filename}")

if __name__ == "__main__":
    run_with_logging()
