Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

Write-Host "======================================"
Write-Host "   Установка зависимостей FastAPI    " -ForegroundColor Cyan
Write-Host "======================================"
Write-Host ""

# Проверка наличия Python
try {
    $pythonVersion = python --version
    Write-Host "[OK] $pythonVersion найден" -ForegroundColor Green
}
catch {
    Write-Host "[ОШИБКА] Python не найден. Установите Python 3.8 или выше." -ForegroundColor Red
    exit 1
}

# Установка основных пакетов для работы с FastAPI
Write-Host "Установка необходимых пакетов..." -ForegroundColor Yellow
pip install fastapi uvicorn sqlalchemy sqlmodel pydantic pydantic-settings alembic psycopg2-binary python-jose[cryptography] passlib[bcrypt] python-multipart

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Основные пакеты установлены" -ForegroundColor Green
} else {
    Write-Host "[ОШИБКА] Не удалось установить основные пакеты" -ForegroundColor Red
}

# Установка зависимостей из requirements.txt
if (Test-Path -Path "requirements.txt") {
    Write-Host "Установка зависимостей из requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Зависимости из requirements.txt установлены" -ForegroundColor Green
    } else {
        Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Не удалось установить некоторые зависимости из requirements.txt" -ForegroundColor Yellow
    }
} else {
    Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Файл requirements.txt не найден, используем базовые зависимости" -ForegroundColor Yellow
}

# Создание файла .env, если его нет
if (-not (Test-Path -Path ".env")) {
    if (Test-Path -Path ".env.example") {
        Write-Host "Создание файла .env из шаблона..." -ForegroundColor Yellow
        Copy-Item -Path ".env.example" -Destination ".env"
        Write-Host "[OK] Файл .env создан" -ForegroundColor Green
    } else {
        Write-Host "[ПРЕДУПРЕЖДЕНИЕ] Файл .env.example не найден, создайте файл .env вручную" -ForegroundColor Yellow
    }
} else {
    Write-Host "[OK] Файл .env уже существует" -ForegroundColor Green
}

Write-Host ""
Write-Host "Установка завершена. Теперь вы можете запустить приложение с помощью:" -ForegroundColor Cyan
Write-Host "uvicorn main:app --reload" -ForegroundColor Yellow
