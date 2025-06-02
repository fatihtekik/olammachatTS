@echo off
echo Активация виртуального окружения...
call venv\Scripts\activate.bat
echo Виртуальное окружение активировано.
echo.
echo Для запуска приложения введите:
echo uvicorn main:app --reload
