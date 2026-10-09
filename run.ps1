# BizIQ Multi-Agent Platform PowerShell Launcher
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  🧠 BizIQ - Unified Multi-Agent Business Intelligence Assistant" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting BizIQ Unified Gateway & Web Application..." -ForegroundColor Green
Write-Host "  • Frontend & API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  • Swagger Docs:   http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host ""

& ".\security-agent\venv\Scripts\python.exe" run_biziq.py
