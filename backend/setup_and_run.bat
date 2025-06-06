@echo off
REM Активация виртуального окружения и установка зависимостей
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

echo Установка зависимостей...
pip install -r requirements.txt

echo Среда настроена. Теперь вы можете запустить сервер командой:
echo python main.py
