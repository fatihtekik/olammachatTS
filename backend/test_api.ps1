$ErrorActionPreference = "Stop"
Write-Host "Testing connection to Ollama API..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -Method Get
    Write-Host "Ollama API is accessible" -ForegroundColor Green
    Write-Host "API Version: $($response.version)" -ForegroundColor Green
} catch {
    Write-Host "Cannot connect to Ollama API: $_" -ForegroundColor Red
    Write-Host "Make sure Ollama is running with 'ollama serve' command" -ForegroundColor Yellow
}

Write-Host "`nTesting Backend API routes..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/" -Method Get
    Write-Host "Backend root endpoint is accessible" -ForegroundColor Green
} catch {
    Write-Host "Cannot connect to backend root: $_" -ForegroundColor Red
}

# Test the status endpoint that's failing
Write-Host "`nTesting /api/v1/ollama/status endpoint..."
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ollama/status" -Method Get
    Write-Host "Status endpoint response: $($response | ConvertTo-Json)" -ForegroundColor Green
} catch {
    Write-Host "Cannot access status endpoint: $_" -ForegroundColor Red
}

# Test other API endpoints for comparison
$endpoints = @(
    "/api/v1/auth/profile", 
    "/api/v1/chat-sessions/",
    "/api/v1/ollama/models"
)

foreach ($endpoint in $endpoints) {
    Write-Host "`nTesting $endpoint endpoint..."
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000$endpoint" -Method Get -ErrorAction SilentlyContinue
        Write-Host "Endpoint is accessible" -ForegroundColor Green
    } catch {
        Write-Host "Cannot access endpoint: $($_.Exception.Message)" -ForegroundColor Red
    }
}
