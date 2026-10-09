@echo off
title BizIQ Multi-Agent Platform Launcher
cls
echo ======================================================================
echo   BizIQ - Unified Multi-Agent Business Intelligence Assistant
echo ======================================================================
echo.
echo Starting BizIQ Unified Server (Gateway + 4 AI Agents + Web Frontend)...
echo.
.\security-agent\venv\Scripts\python.exe run_biziq.py
pause
