"""
Проверка наличия колонок с детальными счетами сетов в последнем загруженном Excel
"""
import pandas as pd
import sys

# Укажи путь к Excel файлу который ты загрузил
# Например: excel_path = "data/matches.xlsx"
excel_path = input("Введи путь к Excel файлу: ")

try:
    df = pd.read_excel(excel_path)
    print(f"\n✅ Excel файл прочитан. Строк: {len(df)}")
    print(f"\n📋 Все колонки ({len(df.columns)}):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")
    
    # Проверяем наличие детальных колонок сетов
    set_columns = [col for col in df.columns if 'сет' in col.lower() and 'счет' in col.lower()]
    
    print(f"\n🎾 Колонки со счетами сетов ({len(set_columns)}):")
    if set_columns:
        for col in set_columns:
            # Показываем пример значения
            sample = df[col].dropna().head(1)
            print(f"  ✓ {col}")
            if not sample.empty:
                print(f"    Пример: {sample.values[0]}")
    else:
        print("  ❌ Не найдено колонок с детальными счетами сетов!")
        print("  📝 Нужны колонки типа:")
        print("     - 'Счет 1 сета Игрок 1'")
        print("     - 'Счет 1 сета Игрок 2'")
        print("     - 'Счет 2 сета Игрок 1'")
        print("     - и т.д.")
    
    # Проверяем есть ли детальный счет в основной колонке
    if 'Счет' in df.columns or 'Счёт' in df.columns:
        score_col = 'Счёт' if 'Счёт' in df.columns else 'Счет'
        print(f"\n📊 Примеры значений в колонке '{score_col}':")
        samples = df[score_col].dropna().head(5)
        for val in samples:
            print(f"  • {val}")
        
        # Проверяем есть ли детальные сеты в скобках
        has_detailed = any('(' in str(val) for val in samples)
        if has_detailed:
            print("  ✓ Найдены детальные счета в скобках!")
        else:
            print("  ⚠️ Нет детальных счетов в скобках (только общий счет типа '3:1')")

except FileNotFoundError:
    print(f"❌ Файл не найден: {excel_path}")
except Exception as e:
    print(f"❌ Ошибка: {e}")
