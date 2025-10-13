"""
🧪 Тест прямого подключения к Ollama
Этот скрипт проверяет, что именно возвращает Ollama
"""
import httpx
import json
import asyncio

async def test_ollama():
    print("=" * 60)
    print("🧪 ТЕСТ OLLAMA API")
    print("=" * 60)
    
    api_url = "http://localhost:11434/api/chat"
    model = "llama3.1:8b"
    
    print(f"\n🌐 URL: {api_url}")
    print(f"🤖 Модель: {model}\n")
    
    try:
        print("📤 Отправка тестового запроса...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", api_url, json={
                "model": model,
                "stream": True,
                "messages": [
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
                    
                    print(f"\n🔍 Строка #{line_count}:")
                    print(f"   Длина: {len(line)} символов")
                    print(f"   Начало: [{line[:100]}]")
                    
                    # Пробуем распарсить как JSON
                    try:
                        data = json.loads(line)
                        chunk_count += 1
                        print(f"   ✅ Валидный JSON!")
                        print(f"   📦 Ключи: {list(data.keys())}")
                        
                        # Проверяем структуру Ollama
                        if "message" in data:
                            message = data["message"]
                            print(f"   📝 message.role: {message.get('role')}")
                            content = message.get('content', '')
                            print(f"   📝 message.content: [{content[:50]}...]")
                        
                        if "done" in data:
                            print(f"   🏁 done: {data['done']}")
                            
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
        print(f"❌ Не могу подключиться к Ollama!")
        print(f"   Убедитесь что Ollama запущен:")
        print(f"   > ollama serve")
        print(f"\n   Детали: {e}")
        
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "🚀 " * 20)
    print("Запуск теста Ollama...")
    print("🚀 " * 20 + "\n")
    
    asyncio.run(test_ollama())
    
    print("\n✅ Тест завершен!")
    print("\nЧто проверить:")
    print("1. Статус 200 ✅")
    print("2. Строки содержат валидный JSON ✅")
    print("3. JSON имеет ключ 'message' -> 'content' ✅")
    print("\nЕсли все ОК, проблема в другом месте!")
