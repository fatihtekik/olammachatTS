#!/usr/bin/env python3
"""
Тестовый скрипт для проверки новых эндпоинтов анализа триггеров
"""
import requests
import json
from datetime import datetime, timedelta

# Базовый URL API
BASE_URL = "http://localhost:8000/api/v1/match-analysis"

def test_endpoints():
    """Тестирует все новые эндпоинты"""
    
    print("🧪 Тестирование новых эндпоинтов анализа триггеров")
    print("=" * 60)
    
    # 1. Тест ping эндпоинта
    print("\n1. 📡 Тестирование ping...")
    try:
        response = requests.get(f"{BASE_URL}/ping")
        if response.status_code == 200:
            print("✅ Ping успешен!")
            print(f"   Доступные эндпоинты: {list(response.json().get('endpoints', {}).keys())}")
        else:
            print(f"❌ Ping неудачен: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка ping: {e}")
    
    # 2. Тест получения списка игроков
    print("\n2. 👥 Тестирование получения игроков...")
    try:
        response = requests.get(f"{BASE_URL}/players?limit=5")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Найдено игроков: {data.get('count', 0)}")
            if data.get('players'):
                print(f"   Примеры игроков: {[p['full_name'] for p in data['players'][:3]]}")
        else:
            print(f"❌ Ошибка получения игроков: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка получения игроков: {e}")
    
    # 3. Тест получения типов триггеров
    print("\n3. 🎯 Тестирование типов триггеров...")
    try:
        response = requests.get(f"{BASE_URL}/trigger-types")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Найдено типов триггеров: {data.get('count', 0)}")
            trigger_types = list(data.get('trigger_types', {}).keys())
            print(f"   Новые триггеры: {[t for t in trigger_types if t in ['defeat_0_3', 'won_2_lost_3rd_set', 'led_2_sets_lost_match']]}")
        else:
            print(f"❌ Ошибка получения типов триггеров: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка получения типов триггеров: {e}")
    
    # 4. Тест анализа базы данных
    print("\n4. 🔍 Тестирование анализа базы данных...")
    try:
        # Составляем запрос на анализ последнего месяца
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        request_data = {
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "trigger_types": ["defeat_0_3", "won_2_lost_3rd_set", "led_1_set_lost_match"]
        }
        
        print(f"   Анализируем период: {start_date} - {end_date}")
        response = requests.post(
            f"{BASE_URL}/analyze-database", 
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Анализ завершен!")
            print(f"   Игроков: {data.get('total_players', 0)}")
            print(f"   Матчей: {data.get('total_matches', 0)}")  
            print(f"   Триггеров найдено: {data.get('triggers_found', 0)}")
            if data.get('triggers'):
                print(f"   Примеры триггеров: {[t['trigger_type'] for t in data['triggers'][:3]]}")
        else:
            print(f"❌ Ошибка анализа: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Детали ошибки: {error_data.get('detail', 'Неизвестная ошибка')}")
            except:
                print(f"   Ответ сервера: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
    
    # 5. Тест получения триггеров
    print("\n5. 📋 Тестирование получения триггеров...")
    try:
        response = requests.get(f"{BASE_URL}/triggers?limit=5")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Найдено триггеров: {data.get('count', 0)}")
            if data.get('triggers'):
                for trigger in data['triggers'][:2]:
                    print(f"   {trigger['player_name']}: {trigger['trigger_type']} - {trigger['trigger_value'][:50]}...")
        else:
            print(f"❌ Ошибка получения триггеров: {response.status_code}")
    except Exception as e:
        print(f"❌ Ошибка получения триггеров: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Тестирование завершено!")
    print("\n💡 Для полноценного тестирования:")
    print("   1. Убедитесь, что сервер запущен на localhost:8000")
    print("   2. В базе данных есть матчи для анализа")
    print("   3. Проверьте логи сервера для дополнительной информации")

if __name__ == "__main__":
    test_endpoints()
