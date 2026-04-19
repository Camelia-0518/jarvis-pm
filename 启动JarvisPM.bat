@echo off
chcp 65001 >nul
title Jarvis PM - AI产品经理助手
echo =========================================
echo    Jarvis PM - AI产品经理助手
echo =========================================
echo.

REM Check if running from correct directory
if not exist "apps\web\package.json" (
    echo Error: Please run this script from the jarvis-pm root directory
    pause
    exit /b 1
)

REM Switch to Node.js 22
echo [1/4] Checking Node.js version...
for /f "tokens=*" %%a in ('node --version') do set NODE_VERSION=%%a
echo Current Node.js: %NODE_VERSION%
echo.

REM Install frontend dependencies if needed
if not exist "apps\web\node_modules" (
    echo [2/4] Installing frontend dependencies...
    cd apps\web
    call npm install
    cd ..\..
) else (
    echo [2/4] Frontend dependencies already installed
)

REM Install backend dependencies if needed
echo [3/4] Checking backend dependencies...
cd apps\api
if not exist "venv\Lib\site-packages\aiosqlite" (
    echo Installing aiosqlite...
    call venv\Scripts\pip install -q aiosqlite email-validator
)
cd ..\..

echo [4/4] Starting services...
echo.
echo =========================================
echo Starting Jarvis PM...
echo =========================================
echo.
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C in either window to stop
echo.

REM Start backend
echo [1/2] Starting Backend API Server...
start "Jarvis PM API" cmd /k "cd apps\api && call venv\Scripts\python start.py"

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Start frontend
echo [2/2] Starting Frontend Web App...
start "Jarvis PM Web" cmd /k "cd apps\web && npm run dev"

echo.
echo =========================================
echo All services started!
echo =========================================
echo.
echo Open your browser and navigate to:
echo http://localhost:3000
echo.
echo Default login: any email/password (create account on first use)
echo.

REM Keep window open
pause
