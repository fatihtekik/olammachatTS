@echo off
echo ======================================
echo     Запуск FastAPI сервера
echo ======================================
echo.

set PYTHONPATH=%~dp0

REM Проверяем наличие виртуального окружения
if exist venv (
    echo Использование виртуального окружения...
    call venv\Scripts\activate.bat
) else (
    echo [ПРЕДУПРЕЖДЕНИЕ] Виртуальное окружение не найдено, используем системный Python
)

echo Запуск сервера разработки FastAPI...
uvicorn main:app --reload --host 0.0.0.0 --port 8000

REM Если произошла ошибка
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ОШИБКА] Не удалось запустить сервер FastAPI
    echo Возможные причины:
    echo 1. Не установлен uvicorn (pip install uvicorn)
    echo 2. Проблема с доступом к порту 8000
    echo 3. Ошибка в коде приложения
    echo.
    echo Попробуйте установить зависимости:
    echo .\install_dependencies.ps1
    echo.
    pause
    exit /b 1
)
