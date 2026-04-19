#!/usr/bin/env pwsh
# Jarvis PM Node.js 版本切换脚本

Write-Host "🔧 正在为 Jarvis PM 切换 Node.js 版本..." -ForegroundColor Cyan

$nvmPath = "$env:APPDATA\nvm\nvm.exe"
if (Test-Path $nvmPath) {
    & $nvmPath use 22.20.0
    Write-Host "✅ 已切换到 Node v22.20.0" -ForegroundColor Green
    Write-Host ""
    node --version
} else {
    Write-Host "❌ 未找到 nvm-windows，请确保已安装" -ForegroundColor Red
}
