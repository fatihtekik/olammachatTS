# Скрипт для безопасной активации виртуального окружения в PowerShell

try {
    Write-Host "Попытка активации виртуального окружения..."
    
    # Проверяем существование виртуального окружения
    if (-not (Test-Path -Path ".\venv\Scripts\Activate.ps1")) {
        Write-Host "Виртуальное окружение не найдено. Создаем новое..."
        python -m venv venv
    }
    
    # Пробуем активировать с временным обходом политики
    Write-Host "Активация виртуального окружения..."
    $currentPolicy = Get-ExecutionPolicy -Scope Process
    Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
    .\venv\Scripts\Activate.ps1
    
    Write-Host "Виртуальное окружение активировано!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Для запуска приложения введите:" -ForegroundColor Cyan
    Write-Host "uvicorn main:app --reload" -ForegroundColor Yellow
    
    # Восстанавливаем предыдущую политику
    Set-ExecutionPolicy -ExecutionPolicy $currentPolicy -Scope Process -Force
}
catch {
    Write-Host "Произошла ошибка при активации виртуального окружения:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Попробуйте альтернативный способ активации:" -ForegroundColor Yellow
    Write-Host "cmd /c ""venv\Scripts\activate.bat && powershell""" -ForegroundColor Yellow
    Write-Host "или используйте:" -ForegroundColor Yellow
    Write-Host ".\activate.bat" -ForegroundColor Yellow
}
