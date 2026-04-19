@echo off
chcp 65001 >nul
title Jarvis PM API Server
echo ========================================
echo    Jarvis PM API Server
echo ========================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements.txt

REM Start server
echo.
echo 🚀 Starting API Server...
echo 📚 Documentation: http://localhost:8000/docs
echo 🔍 Health Check: http://localhost:8000/health
echo.

python start.py

pause
