#!/usr/bin/env python3
"""
Тестовый скрипт для проверки логирования триггеров в консоль
"""
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

import json
from datetime import datetime, timedelta

# Базовый URL API
BASE_URL = "http://localhost:8000/api/v1/match-analysis"

def test_trigger_logging():
    """Тестирует логирование триггеров в консоль"""
    
    print("🧪 ТЕСТИРОВАНИЕ СИСТЕМЫ ЛОГИРОВАНИЯ ТРИГГЕРОВ")
    print("=" * 80)
    
    if not HAS_REQUESTS:
        print("❌ Модуль 'requests' не установлен.")
        print("💡 Установите его командой: pip install requests")
        return
    
    try:
        # Проверяем доступность сервера
        print("\n1. 🌐 Проверка доступности сервера...")
        try:
            response = requests.get(f"{BASE_URL}/ping", timeout=5)
            if response.status_code == 200:
                print("✅ Сервер доступен!")
            else:
                print(f"⚠️  Сервер отвечает с кодом: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Сервер недоступен: {e}")
            print("💡 Убедитесь, что backend запущен на localhost:8000")
            return
        
        # Составляем запрос на анализ последнего месяца
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        request_data = {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "trigger_types": [
                "defeat_0_3", 
                "won_2_lost_3rd_set", 
                "losing_streaks",
                "top_performers",
                "losers_50_percent"
            ]
        }
        
        print(f"\n2. 📅 Настройка анализа:")
        print(f"   Период: {start_date} - {end_date}")
        print(f"   Триггеры: {', '.join(request_data['trigger_types'])}")
        
        print(f"\n3. � Запуск анализа...")
        print("=" * 80)
        print("📺 ВНИМАНИЕ: Детальный вывод триггеров смотрите в консоли сервера!")
        print("=" * 80)
        
        response = requests.post(
            f"{BASE_URL}/analyze-database", 
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Анализ завершен успешно!")
            print(f"📊 Краткие результаты:")
            print(f"   👥 Игроков проанализировано: {data.get('total_players', 0)}")
            print(f"   ⚽ Матчей в периоде: {data.get('total_matches', 0)}")  
            print(f"   🎯 Триггеров обнаружено: {data.get('triggers_found', 0)}")
            
            if data.get('triggers_found', 0) > 0:
                print(f"\n🔍 В консоли сервера должны отображаться:")
                print(f"   • Имя игрока")
                print(f"   • Название триггера")
                print(f"   • Номер триггера (N из N)")
                print(f"   • Конкретные матчи с форматом:")
                print(f"     - ФИО vs ФИО")
                print(f"     - Рейтинг 1 | Рейтинг 2")
                print(f"     - Дата матча | Начало матча (например, 22:00)")
            else:
                print(f"\n📝 Триггеры не обнаружены в указанном периоде")
                print(f"💡 Попробуйте:")
                print(f"   - Увеличить период анализа")
                print(f"   - Добавить больше данных матчей")
                print(f"   - Проверить наличие игроков в базе данных")
                
        else:
            print(f"❌ Ошибка анализа: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Детали ошибки: {error_data.get('detail', 'Неизвестная ошибка')}")
            except:
                print(f"   Ответ сервера: {response.text[:200]}")
                
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
    
    print("\n" + "=" * 80)
    print("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("\n💡 Для просмотра детального логирования триггеров:")
    print("   1. Откройте консоль где запущен backend сервер")
    print("   2. Там должны отображаться подробные данные о найденных триггерах")
    print("   3. Для каждого триггера показываются конкретные матчи")
    print("   4. Формат: Имя vs Имя, рейтинги, дата, время начала")
    print("=" * 80)

if __name__ == "__main__":
    test_trigger_logging()
