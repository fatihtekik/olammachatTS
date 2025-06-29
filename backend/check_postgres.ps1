Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

Write-Host "======================================"
Write-Host "   Проверка и настройка PostgreSQL   " -ForegroundColor Cyan
Write-Host "======================================"
Write-Host ""

# Проверка наличия PostgreSQL
try {
    $pgVersion = psql --version
    Write-Host "[OK] PostgreSQL найден: $pgVersion" -ForegroundColor Green
    $pgInstalled = $true
} catch {
    Write-Host "[ПРЕДУПРЕЖДЕНИЕ] PostgreSQL не найден или не в PATH." -ForegroundColor Yellow
    $pgInstalled = $false
}

if (-not $pgInstalled) {
    Write-Host ""
    Write-Host "Для работы приложения нужно установить PostgreSQL:" -ForegroundColor Yellow
    Write-Host "1. Скачайте и установите PostgreSQL с официального сайта: https://www.postgresql.org/download/"
    Write-Host "2. Добавьте bin директорию PostgreSQL в переменную PATH"
    Write-Host "3. Создайте базу данных с именем 'olammachat'"
    Write-Host "4. Обновите настройки подключения в файле .env"
    Write-Host ""
    Write-Host "Нажмите любую клавишу для завершения..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit
}

# Чтение настроек из .env
$envFile = ".env"
if (Test-Path -Path $envFile) {
    $envContent = Get-Content -Path $envFile
    $dbUrl = $envContent | Where-Object { $_ -match '^DATABASE_URL=' } | ForEach-Object { $_ -replace '^DATABASE_URL=', '' }
    
    if ($dbUrl) {
        Write-Host "Найдена строка подключения к базе данных в .env: $dbUrl" -ForegroundColor Green
    } else {
        Write-Host "[ОШИБКА] Не удалось найти строку подключения в .env" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[ОШИБКА] Файл .env не найден" -ForegroundColor Red
    exit 1
}

# Парсим строку подключения
try {
    if ($dbUrl -match 'postgresql://([^:]+):([^@]+)@([^/]+)/(.+)') {
        $username = $Matches[1]
        $password = $Matches[2]
        $host = $Matches[3]
        $dbName = $Matches[4]
        
        Write-Host "Параметры подключения:" -ForegroundColor Cyan
        Write-Host "- Имя пользователя: $username"
        Write-Host "- Хост: $host"
        Write-Host "- База данных: $dbName"
    } else {
        Write-Host "[ОШИБКА] Неверный формат строки подключения" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ОШИБКА] Не удалось разобрать строку подключения: $_" -ForegroundColor Red
    exit 1
}

# Попытка подключения к PostgreSQL
Write-Host ""
Write-Host "Проверка подключения к PostgreSQL..." -ForegroundColor Yellow

$env:PGPASSWORD = $password
$testConnection = $null

try {
    $testConnection = psql -h $host -U $username -c "SELECT 1" postgres 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Подключение к PostgreSQL успешно" -ForegroundColor Green
    } else {
        Write-Host "[ОШИБКА] Не удалось подключиться к PostgreSQL: $testConnection" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ОШИБКА] Ошибка при подключении к PostgreSQL: $_" -ForegroundColor Red
    exit 1
}

# Проверка существования базы данных
Write-Host ""
Write-Host "Проверка наличия базы данных $dbName..." -ForegroundColor Yellow

try {
    $dbExists = psql -h $host -U $username -t -c "SELECT 1 FROM pg_database WHERE datname='$dbName'" postgres 2>&1
    if ($dbExists -match '1') {
        Write-Host "[OK] База данных $dbName уже существует" -ForegroundColor Green
    } else {
        Write-Host "База данных $dbName не существует, создаем..." -ForegroundColor Yellow
        $createDb = psql -h $host -U $username -c "CREATE DATABASE $dbName" postgres 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] База данных $dbName успешно создана" -ForegroundColor Green
        } else {
            Write-Host "[ОШИБКА] Не удалось создать базу данных: $createDb" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host "[ОШИБКА] Ошибка при проверке базы данных: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "PostgreSQL настроен успешно!" -ForegroundColor Green
Write-Host "Теперь вы можете запустить миграции и сервер." -ForegroundColor Cyan
Write-Host ""
Write-Host "Запуск миграции: python -m alembic upgrade head" -ForegroundColor Yellow
Write-Host "Запуск сервера: uvicorn main:app --reload" -ForegroundColor Yellow
