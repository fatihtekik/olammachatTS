# Инструкции по запуску бэкенда OllamaChat

## Быстрая настройка

Для быстрой настройки и запуска бэкенда на Windows выполните:

### Вариант 1: Установка всех компонентов за один шаг
```powershell
# Запустить PowerShell с обходом политики выполнения для установки всех зависимостей
powershell -ExecutionPolicy Bypass -File .\install_dependencies.ps1
```

### Вариант 2: Полная настройка и запуск
```cmd
# Запуск скрипта установки и настройки
.\setup.bat
```

Эти скрипты автоматически:
1. Создадут виртуальное окружение (если нужно)
2. Установят все зависимости
3. Создадут файл .env из шаблона
4. Настроят все для запуска

## Установка и настройка вручную

### 1. Создание виртуального окружения

```bash
# Windows
python -m venv venv

# Для активации в PowerShell (есть несколько вариантов):
# Вариант 1: Разрешить выполнение скриптов в текущей сессии
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\venv\Scripts\Activate.ps1

# Вариант 2: Запустить cmd.exe и выполнить в нем
cmd /c "venv\Scripts\activate.bat && powershell"

# Вариант 3: Указать полный путь без использования скрипта
& venv\Scripts\python.exe

# Вариант 4: Использовать приложенный batch-файл (самый простой способ)
.\activate.bat

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка базы данных

1. Установите PostgreSQL если он еще не установлен
2. Создайте базу данных:

```sql
CREATE DATABASE olammachat;
```

3. Скопируйте файл .env.example в .env и настройте параметры:

```bash
cp .env.example .env
```

4. Отредактируйте .env файл, указав правильные параметры подключения к базе данных и секретный ключ

### 4. Запуск миграций

```bash
python -m alembic upgrade head
```

## Решение проблем с выполнением скриптов в PowerShell

Если вы получаете ошибку о том, что выполнение скриптов отключено в системе, вы можете:

1. **Временно разрешить выполнение скриптов только для текущей сессии PowerShell**:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   ```

2. **Изменить политику выполнения для вашего пользователя**:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

3. **Использовать командную строку (cmd) вместо PowerShell**:
   ```cmd
   venv\Scripts\activate.bat
   ```

Подробнее о политиках выполнения PowerShell можно узнать, выполнив:
```powershell
Get-Help about_Execution_Policies
```

## Запуск приложения

```bash
# Для разработки
uvicorn main:app --reload

# Для production
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Быстрые скрипты для запуска

В корневом каталоге проекта есть два скрипта для упрощения запуска:

- `activate.bat` - для Windows Command Prompt (cmd)
- `activate.ps1` - для Windows PowerShell (с автоматическим обходом политики выполнения)

Чтобы использовать PowerShell скрипт, можно выполнить:
```powershell
# Запустить с временным обходом политики выполнения
powershell -ExecutionPolicy Bypass -File .\activate.ps1
```

## API документация

После запуска приложения документация API доступна по адресам:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Дополнительные скрипты для управления приложением

В проекте доступны следующие скрипты для упрощения работы:

### 1. Проверка и настройка базы данных
```powershell
# Проверяет наличие PostgreSQL и создает базу данных, если нужно
powershell -ExecutionPolicy Bypass -File .\check_postgres.ps1
```

### 2. Запуск сервера разработки
```cmd
# Запускает сервер разработки FastAPI
.\run_server.bat
```

### 3. Установка зависимостей
```powershell
# Устанавливает все необходимые пакеты Python
powershell -ExecutionPolicy Bypass -File .\install_dependencies.ps1
```

### 4. Активация виртуального окружения
```powershell
# PowerShell с обходом политики выполнения
powershell -ExecutionPolicy Bypass -File .\activate.ps1

# Command Prompt
.\activate.bat
```

## Интеграция с фронтендом

Для интеграции с фронтендом необходимо:

1. В настройках фронтенда указать адрес API бэкенда (по умолчанию http://localhost:8000)
2. Настроить систему авторизации на фронтенде для работы с JWT токенами
