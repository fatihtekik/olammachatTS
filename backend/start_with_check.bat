@echo off
echo ===== Testing Ollama Connection =====
echo.

REM Try to connect to Ollama API to check if it's running
echo Checking if Ollama is running...
curl -s http://localhost:11434/api/version > nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Cannot connect to Ollama at http://localhost:11434
    echo Please ensure that Ollama is installed and running with 'ollama serve'
    echo.
    goto :EOF
) else (
    echo Ollama is running.
    echo.
)

REM List available models
echo Checking available models...
echo.
curl -s http://localhost:11434/api/tags
echo.
echo.

REM Start the backend server
echo ===== Starting backend server =====
echo.
python main.py
