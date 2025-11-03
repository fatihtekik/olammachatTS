"""
🧪 Тест прямого подключения к LM Studio
Этот скрипт проверяет, что именно возвращает LM Studio
"""
import httpx
import json
import asyncio

async def test_lmstudio():
    print("=" * 60)
    print("🧪 ТЕСТ LM STUDIO API")
    print("=" * 60)
    
    # LM Studio использует OpenAI-совместимый API
    api_url = "http://localhost:1234/v1/chat/completions"
    
    print(f"\n🌐 URL: {api_url}")
    print(f"🤖 Модель: <любая загруженная в LM Studio>\n")
    
    try:
        print("📤 Отправка тестового запроса...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", api_url, json={
                "model": "local-model",  # LM Studio игнорирует это, использует загруженную модель
                "stream": True,
                "messages": [
                    {"role": "system", "content": "Ты аналитик по настольному теннису."},
                    {"role": "user", "content": "Привет! Скажи короткое приветствие."}
                ]
            }) as response:
                
                print(f"📨 Статус: {response.status_code}")
                print(f"📋 Заголовки: {dict(response.headers)}\n")
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    print(f"❌ Ошибка HTTP {response.status_code}:")
                    print(f"   {error_text[:500]}")
                    return
                
                print("✅ Начинаем получать строки...\n")
                
                line_count = 0
                chunk_count = 0
                
                async for line in response.aiter_lines():
                    line_count += 1
                    
                    if not line.strip():
                        print(f"   [{line_count}] <пустая строка>")
                        continue
                    
                    # LM Studio отправляет строки с префиксом "data: "
                    if line.startswith("data: "):
                        line = line[6:]  # Убираем "data: "
                    
                    # Пропускаем маркер окончания
                    if line.strip() == "[DONE]":
                        print(f"\n🏁 Получен маркер [DONE]")
                        break
                    
                    print(f"\n🔍 Строка #{line_count}:")
                    print(f"   Длина: {len(line)} символов")
                    print(f"   Начало: [{line[:100]}]")
                    
                    # Пробуем распарсить как JSON
                    try:
                        data = json.loads(line)
                        chunk_count += 1
                        print(f"   ✅ Валидный JSON!")
                        print(f"   📦 Ключи: {list(data.keys())}")
                        
                        # Проверяем структуру OpenAI (LM Studio)
                        if "choices" in data and len(data["choices"]) > 0:
                            choice = data["choices"][0]
                            print(f"   📝 choices[0] ключи: {list(choice.keys())}")
                            
                            if "delta" in choice:
                                delta = choice["delta"]
                                print(f"   📝 delta ключи: {list(delta.keys())}")
                                content = delta.get('content', '')
                                if content:
                                    print(f"   📝 delta.content: [{content[:50]}...]")
                                    
                            if "finish_reason" in choice:
                                print(f"   🏁 finish_reason: {choice['finish_reason']}")
                        
                        # Показываем весь JSON для первого чанка
                        if chunk_count == 1:
                            print(f"   📄 Полный JSON:")
                            print(f"      {json.dumps(data, ensure_ascii=False, indent=6)}")
                            
                    except json.JSONDecodeError as e:
                        print(f"   ❌ НЕ JSON! Ошибка: {e}")
                        print(f"   Полная строка: [{line}]")
                    
                    # Останавливаем после 5 строк для краткости
                    if line_count >= 5:
                        print(f"\n... (остальные строки пропущены)")
                        break
                
                print(f"\n{'='*60}")
                print(f"📊 ИТОГО:")
                print(f"   Всего строк: {line_count}")
                print(f"   Валидных JSON: {chunk_count}")
                print(f"{'='*60}\n")
                
    except httpx.ConnectError as e:
        print(f"❌ Не могу подключиться к LM Studio!")
        print(f"   Убедитесь что:")
        print(f"   1. LM Studio запущен")
        print(f"   2. Модель загружена (Load model)")
        print(f"   3. Сервер включен (Local Server)")
        print(f"\n   Детали: {e}")
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("Запуск теста LM Studio...")
    print("🚀 " * 20 + "\n")
    
    asyncio.run(test_lmstudio())
    
    print("\n✅ Тест завершен!")
    print("\nЧто проверить:")
    print("1. Статус 200 ✅")
    print("2. Строки начинаются с 'data: ' ✅")
    print("3. JSON имеет ключ 'choices' -> 'delta' -> 'content' ✅")
    print("\nЕсли все ОК, LM Studio работает правильно!")
