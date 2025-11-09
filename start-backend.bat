@echo off
REM 快速启动后端应用脚本
REM 使用方法: start-backend.bat

echo 🚀 启动后端应用...

REM 检查是否在正确的目录
if not exist "backend" (
    echo ❌ 错误: 找不到backend目录，请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 切换到backend目录
cd backend
echo 📁 当前目录: %CD%

REM 检查是否存在虚拟环境
if not exist "../.venv" (
    echo ❌ 错误: 找不到虚拟环境，请先运行 uv init
    cd ..
    pause
    exit /b 1
)

REM 终止可能运行的Python进程
echo 🔄 终止现有的Python进程...
taskkill /F /IM python.exe /T >nul 2>&1
if %errorlevel% == 0 (
    echo ✅ 已终止现有Python进程
) else (
    echo ℹ️  没有找到运行中的Python进程
)

REM 等待端口释放
timeout /t 2 /nobreak >nul

REM 启动后端服务
echo 🌟 启动FastAPI服务器...
echo 📍 服务地址: http://localhost:8001
echo 📖 API文档: http://localhost:8001/docs
echo 🛑 按 Ctrl+C 停止服务
echo.

uv run uvicorn app.main:app --host 0.0.0.0 --port 8001

REM 返回根目录
cd ..
echo 📁 已返回项目根目录
pause
