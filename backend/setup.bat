@echo off
echo ======================================
echo     Инициализация проекта FastAPI
echo ======================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ОШИБКА] Python не найден. Установите Python 3.8 или выше.
    exit /b 1
)

echo [OK] Python найден

REM Создание виртуального окружения
if not exist venv (
    echo Создание виртуального окружения...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение.
        exit /b 1
    )
    echo [OK] Виртуальное окружение создано
) else (
    echo [OK] Виртуальное окружение уже существует
)

REM Активация виртуального окружения
echo Активация виртуального окружения...
call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo [ПРЕДУПРЕЖДЕНИЕ] Не удалось активировать виртуальное окружение обычным способом. Попробуем другие методы.
    
    echo Попытка запуска Python из виртуального окружения напрямую...
    SET PATH=%CD%\venv\Scripts;%PATH%
    SET PYTHON_EXE=%CD%\venv\Scripts\python.exe
    
    if exist "%PYTHON_EXE%" (
        echo [OK] Установлен путь к Python из виртуального окружения
    ) else (
        echo [ОШИБКА] Не удалось найти Python в виртуальном окружении.
        exit /b 1
    )
) else (
    echo [OK] Виртуальное окружение активировано
)

REM Установка зависимостей
echo Установка зависимостей из requirements.txt...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ОШИБКА] Не удалось установить зависимости.
    exit /b 1
)
echo [OK] Зависимости установлены

REM Создание .env файла
if not exist .env (
    echo Создание файла .env из шаблона...
    copy .env.example .env
    if %ERRORLEVEL% NEQ 0 (
        echo [ОШИБКА] Не удалось создать файл .env.
    ) else (
        echo [OK] Файл .env создан
    )
) else (
    echo [OK] Файл .env уже существует
)

echo.
echo ======================================
echo     Настройка базы данных PostgreSQL
echo ======================================
echo.
echo Перед продолжением убедитесь, что:
echo 1. PostgreSQL установлен
echo 2. В PostgreSQL создана база данных olammachat
echo 3. Файл .env содержит правильные настройки подключения
echo.
echo Нажмите любую клавишу для продолжения или Ctrl+C для отмены...
pause > nul

echo.
echo ======================================
echo        Запуск приложения FastAPI
echo ======================================
echo.
echo Приложение будет запущено в режиме разработки.
echo Интерфейс API будет доступен по адресу: http://localhost:8000/docs
echo.
echo Нажмите Ctrl+C для остановки сервера.
echo.

REM Запуск сервера разработки
uvicorn main:app --reload
