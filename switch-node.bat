@echo off
chcp 65001 >nul
echo 🔧 正在为 Jarvis PM 切换 Node.js 版本...
nvm use 22.20.0
echo ✅ 已切换到 Node v22.20.0
echo.
node --version
