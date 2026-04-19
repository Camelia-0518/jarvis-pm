# Jarvis PM Server Cleanup Script
# 强制清理占用开发端口的 Python/uvicorn 进程

param(
    [int]$Port = 8000,
    [switch]$KillAllPython
)

Write-Host "🧹 Jarvis PM 服务器清理脚本" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

# Method 1: Kill by port
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connections) {
    Write-Host "发现端口 $Port 占用:" -ForegroundColor Yellow
    $connections | ForEach-Object {
        try {
            $proc = Get-Process -Id $_.OwningProcess -ErrorAction Stop
            Write-Host "  PID $($_.OwningProcess) - $($proc.ProcessName) - $($proc.Path)" -ForegroundColor DarkGray
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction Stop
            Write-Host "  ✓ 已终止 PID $($_.OwningProcess)" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ 无法终止 PID $($_.OwningProcess): $_" -ForegroundColor Red
        }
    }
} else {
    Write-Host "端口 $Port 未被占用" -ForegroundColor Green
}

# Method 2: Kill all uvicorn/python processes (optional)
if ($KillAllPython) {
    Write-Host "`n正在查找所有 uvicorn/python 进程..." -ForegroundColor Yellow
    Get-Process -Name python, python3, python3.11, python3.12 -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*main:app*"
    } | ForEach-Object {
        try {
            Stop-Process -Id $_.Id -Force
            Write-Host "  ✓ 已终止 $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ 无法终止 $($_.ProcessName) (PID: $($_.Id)): $_" -ForegroundColor Red
        }
    }
}

# Method 3: Common alternative ports
foreach ($altPort in @(8000, 8002, 8080, 3000)) {
    if ($altPort -eq $Port) { continue }
    $altConns = Get-NetTCPConnection -LocalPort $altPort -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -ne 0 }
    if ($altConns) {
        $altPids = $altConns | Select-Object -ExpandProperty OwningProcess -Unique
        $altProcs = $altPids | ForEach-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue } | Where-Object { $_.ProcessName -match "python|node" }
        if ($altProcs) {
            Write-Host "`n端口 $altPort 也被占用:" -ForegroundColor Yellow
            $altProcs | ForEach-Object {
                Write-Host "  $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor DarkGray
            }
        }
    }
}

Write-Host "`n✅ 清理完成" -ForegroundColor Cyan
Write-Host "提示: 使用 -KillAllPython 参数可强制终止所有 uvicorn 进程" -ForegroundColor DarkGray
