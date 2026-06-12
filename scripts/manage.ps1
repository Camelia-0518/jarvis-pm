#!/usr/bin/env pwsh
# Jarvis PM Process Manager
# Usage: .\scripts\manage.ps1 [start|stop|restart|status]

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Command = "status"
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "apps\api"
$FrontendDir = Join-Path $ProjectRoot "apps\web"
$PidFile = Join-Path $PSScriptRoot ".jarvis-pm.pids"

# Port config (read .env first, default 8000)
$BackendPort = 8000
$FrontendPort = 3000
$EnvFile = Join-Path $BackendDir ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*PORT\s*=\s*(\d+)') {
            $BackendPort = [int]$matches[1]
        }
    }
}

# Color output
function Write-Info($msg) { Write-Host $msg -ForegroundColor Cyan }
function Write-Ok($msg) { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg) { Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg) { Write-Host $msg -ForegroundColor Red }

# Get PIDs by port
function Get-ProcessByPort($port) {
    Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Where-Object { $_.OwningProcess -ne 0 -and $_.State -eq "Listen" } |
        Select-Object -ExpandProperty OwningProcess -Unique
}

# Kill process by port (including children)
function Kill-PortProcess($port, $name) {
    $pids = Get-ProcessByPort $port
    if (-not $pids) {
        Write-Ok "  $name port $port is free"
        return
    }
    foreach ($procId in $pids) {
        try {
            $proc = Get-Process -Id $procId -ErrorAction Stop
            # Kill children first
            $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $procId" -ErrorAction SilentlyContinue
            foreach ($child in $children) {
                try {
                    Stop-Process -Id $child.ProcessId -Force -ErrorAction Stop
                    Write-Ok "  Killed child PID $($child.ProcessId)"
                } catch {
                    Write-Warn "  Cannot kill child PID $($child.ProcessId): $_"
                }
            }
            Stop-Process -Id $procId -Force -ErrorAction Stop
            Write-Ok "  Killed $name PID $procId ($($proc.ProcessName))"
        } catch {
            Write-Warn "  Cannot kill $name PID $procId : $_"
        }
    }
    # Fallback: check again after 500ms
    Start-Sleep -Milliseconds 500
    $pids2 = Get-ProcessByPort $port
    if ($pids2) {
        foreach ($procId2 in $pids2) {
            try {
                taskkill /F /PID $procId2 | Out-Null
                Write-Ok "  taskkill fallback OK PID $procId2"
            } catch {
                Write-Err "  taskkill fallback failed PID $procId2"
            }
        }
    }
}

# Kill zombie python/uvicorn processes
function Kill-ZombiePython() {
    $matched = Get-Process -Name python, python3, python3.11, python3.12 -ErrorAction SilentlyContinue |
        Where-Object {
            $cmd = try { (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine } catch { "" }
            $cmd -like "*uvicorn*" -or $cmd -like "*main:app*" -or $cmd -like "*start.py*" -or $cmd -like "*multiprocessing-fork*"
        }
    $matched | ForEach-Object {
        try {
            # Kill children first
            $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($_.Id)" -ErrorAction SilentlyContinue
            foreach ($child in $children) {
                try {
                    Stop-Process -Id $child.ProcessId -Force -ErrorAction Stop
                    Write-Ok "  Killed child PID $($child.ProcessId)"
                } catch {
                    Write-Warn "  Cannot kill child PID $($child.ProcessId)"
                }
            }
            Stop-Process -Id $_.Id -Force
            Write-Ok "  Cleaned zombie PID $($_.Id) ($($_.ProcessName))"
        } catch {
            Write-Warn "  Cannot clean zombie PID $($_.Id)"
        }
    }
}

# Kill all python processes in project directory (nuclear option)
function Kill-AllProjectPython() {
    Get-Process -Name python, python3, python3.11, python3.12 -ErrorAction SilentlyContinue |
        Where-Object {
            $cmd = try { (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine } catch { "" }
            $cmd -like "*$BackendDir*" -or $cmd -like "*$ProjectRoot*"
        } |
        ForEach-Object {
            try {
                Stop-Process -Id $_.Id -Force
                Write-Ok "  Killed project python PID $($_.Id) ($($_.ProcessName))"
            } catch {
                Write-Warn "  Cannot kill project python PID $($_.Id)"
            }
        }
}

# Read PID file
function Read-PidFile() {
    if (Test-Path $PidFile) {
        try {
            return Get-Content $PidFile -Raw | ConvertFrom-Json
        } catch {
            return @{ backend = @(); frontend = @() }
        }
    }
    return @{ backend = @(); frontend = @() }
}

# Write PID file
function Write-PidFile($backendPids, $frontendPids) {
    $data = @{
        backend = $backendPids
        frontend = $frontendPids
        startedAt = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    }
    $data | ConvertTo-Json | Set-Content $PidFile
}

# Remove PID file
function Remove-PidFile() {
    if (Test-Path $PidFile) {
        Remove-Item $PidFile -Force
    }
}

# Check Node.js version
function Check-NodeVersion() {
    try {
        $ver = node --version 2>$null
        Write-Info "Node.js version: $ver"
        if ($ver -notmatch "^v(18|20|22)") {
            Write-Warn "Recommended Node.js 18/20/22, current $ver"
        }
    } catch {
        Write-Err "Node.js not installed"
        exit 1
    }
}

# Check dependencies
function Check-Dependencies() {
    if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Warn "Frontend deps missing, installing..."
        Push-Location $FrontendDir
        npm install
        Pop-Location
    }
    $venvPython = Join-Path $BackendDir "venv\Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Write-Err "Backend venv not found: $venvPython"
        Write-Info "Please run in apps\api: python -m venv venv"
        exit 1
    }
}

# ========== Commands ==========

function Start-Services() {
    Write-Info "========== Starting Jarvis PM =========="

    Check-NodeVersion
    Check-Dependencies

    # Step 1: Clean old processes
    Write-Info "[1/4] Cleaning old processes..."
    $oldPids = Read-PidFile
    foreach ($oldPid in $oldPids.backend) {
        try {
            Stop-Process -Id $oldPid -Force -ErrorAction Stop
            Write-Ok "  Killed old backend PID $oldPid"
        } catch {
            Write-Warn "  Old backend PID $oldPid already gone"
        }
    }
    foreach ($oldPid in $oldPids.frontend) {
        try {
            Stop-Process -Id $oldPid -Force -ErrorAction Stop
            Write-Ok "  Killed old frontend PID $oldPid"
        } catch {
            Write-Warn "  Old frontend PID $oldPid already gone"
        }
    }
    Kill-PortProcess $BackendPort "Backend"
    if ($BackendPort -ne 8001) {
        Kill-PortProcess 8001 "Backend(8001)"
    }
    Kill-PortProcess $FrontendPort "Frontend"
    Kill-ZombiePython
    Kill-AllProjectPython
    Write-Ok "Cleanup done"

    # Step 2: Start backend
    Write-Info "[2/4] Starting Backend API (port $BackendPort)..."
    $backendCmd = "cd `"$BackendDir`" ; .\venv\Scripts\python.exe start.py"
    $backendProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd -PassThru -WindowStyle Normal
    $backendPid = $backendProc.Id
    Write-Ok "  Backend started PID $backendPid"

    # Step 3: Wait for backend ready
    Write-Info "[3/4] Waiting for backend ready..."
    $maxWait = 30
    $ready = $false
    for ($i = 0; $i -lt $maxWait; $i++) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-WebRequest -Uri "http://localhost:$BackendPort/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                $ready = $true
                Write-Ok "  Backend health check passed ($i s)"
                break
            }
        } catch {
            Write-Host "." -NoNewline -ForegroundColor DarkGray
        }
    }
    if (-not $ready) {
        Write-Warn "  Backend health check timeout, but may still be starting"
    }

    # Step 4: Start frontend
    Write-Info "[4/4] Starting Frontend Web (port $FrontendPort)..."
    $frontendCmd = "cd `"$FrontendDir`" ; npm run dev"
    $frontendProc = Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd -PassThru -WindowStyle Normal
    $frontendPid = $frontendProc.Id
    Write-Ok "  Frontend started PID $frontendPid"

    # Record PIDs
    Start-Sleep -Seconds 2
    $uvicornPids = Get-Process -Name python -ErrorAction SilentlyContinue |
        Where-Object {
            $cmd = try { (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine } catch { "" }
            $cmd -like "*main:app*" -or $cmd -like "*start.py*"
        } |
        Select-Object -ExpandProperty Id

    Write-PidFile -backendPids @($backendPid) + $uvicornPids -frontendPids @($frontendPid)

    Write-Info ""
    Write-Info "========== Jarvis PM Started =========="
    Write-Ok "  Frontend: http://localhost:$FrontendPort"
    Write-Ok "  Backend:  http://localhost:$BackendPort"
    Write-Ok "  API Docs: http://localhost:$BackendPort/docs"
    Write-Info "========================================"
    Write-Info "Manage commands:"
    Write-Info "  .\scripts\manage.ps1 stop"
    Write-Info "  .\scripts\manage.ps1 restart"
    Write-Info "  .\scripts\manage.ps1 status"
}

function Stop-Services() {
    Write-Info "========== Stopping Jarvis PM =========="

    $oldPids = Read-PidFile
    $killed = 0
    foreach ($oldPid in $oldPids.backend) {
        try {
            Stop-Process -Id $oldPid -Force -ErrorAction Stop
            Write-Ok "  Killed backend PID $oldPid"
            $killed++
        } catch {
            Write-Warn "  Backend PID $oldPid already gone"
        }
    }
    foreach ($oldPid in $oldPids.frontend) {
        try {
            Stop-Process -Id $oldPid -Force -ErrorAction Stop
            Write-Ok "  Killed frontend PID $oldPid"
            $killed++
        } catch {
            Write-Warn "  Frontend PID $oldPid already gone"
        }
    }

    Write-Info "Fallback cleanup..."
    Kill-PortProcess $BackendPort "Backend"
    if ($BackendPort -ne 8001) {
        Kill-PortProcess 8001 "Backend(8001)"
    }
    Kill-PortProcess $FrontendPort "Frontend"
    Kill-ZombiePython
    Kill-AllProjectPython

    Remove-PidFile
    Write-Ok "Stopped"
}

function Show-Status() {
    Write-Info "========== Jarvis PM Status =========="

    $backendPids = Get-ProcessByPort $BackendPort
    $frontendPids = Get-ProcessByPort $FrontendPort

    if ($backendPids) {
        Write-Ok "  Backend (port $BackendPort): Running PID=$($backendPids -join ', ')"
    } else {
        Write-Warn "  Backend (port $BackendPort): Not running"
    }

    if ($frontendPids) {
        Write-Ok "  Frontend (port $FrontendPort): Running PID=$($frontendPids -join ', ')"
    } else {
        Write-Warn "  Frontend (port $FrontendPort): Not running"
    }

    if ($BackendPort -ne 8001) {
        $pids8001 = Get-ProcessByPort 8001
        if ($pids8001) {
            Write-Warn "  Port 8001 also occupied PID=$($pids8001 -join ', ')"
        }
    }

    $saved = Read-PidFile
    if ($saved.startedAt) {
        Write-Info "  Last start: $($saved.startedAt)"
    }
}

function Restart-Services() {
    Stop-Services
    Start-Sleep -Seconds 2
    Start-Services
}

# ========== Main ==========

switch ($Command) {
    "start" { Start-Services }
    "stop" { Stop-Services }
    "restart" { Restart-Services }
    "status" { Show-Status }
    default {
        Write-Info "Usage: .\scripts\manage.ps1 [start|stop|restart|status]"
        Show-Status
    }
}
