# Start both servers for local development (100% free stack).
# Usage: .\scripts\dev.ps1

$root = Split-Path $PSScriptRoot -Parent

Start-Process pwsh -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root\apps\api'; & '$root\.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --port 8000"

Start-Process pwsh -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root\apps\web'; npm run dev"

Write-Host "API    -> http://localhost:8000  (docs at /docs)"
Write-Host "Web UI -> http://localhost:3000"
