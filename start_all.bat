@echo off
REM Windows batch script to start the unified backend system

echo ========================================
echo Starting Beauty Shop Backend System
echo ========================================

REM Start Backend API with LangGraph integrated (Port 8000)
echo.
echo Starting Backend API (with LangGraph) on port 8000...
cd backend
uvicorn app.main:app --reload --port 8000

echo.
echo ========================================
echo Backend stopped
echo ========================================
pause
