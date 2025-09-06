# 快速启动后端应用脚本
# 使用方法: .\start-backend.ps1

Write-Host "🚀 启动后端应用..." -ForegroundColor Green

# 检查是否在正确的目录
if (-not (Test-Path "backend")) {
    Write-Host "❌ 错误: 找不到backend目录，请确保在项目根目录运行此脚本" -ForegroundColor Red
    exit 1
}

# 切换到backend目录
Set-Location backend

Write-Host "📁 当前目录: $(Get-Location)" -ForegroundColor Cyan

# 检查是否存在虚拟环境
if (-not (Test-Path "../.venv")) {
    Write-Host "❌ 错误: 找不到虚拟环境，请先运行 uv init" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# 终止可能运行的Python进程
Write-Host "🔄 终止现有的Python进程..." -ForegroundColor Yellow
try {
    taskkill /F /IM python.exe /T 2>$null
    Write-Host "✅ 已终止现有Python进程" -ForegroundColor Green
} catch {
    Write-Host "ℹ️  没有找到运行中的Python进程" -ForegroundColor Gray
}

# 等待端口释放
Start-Sleep -Seconds 2

# 检查端口8000是否被占用
$port8000 = netstat -ano | findstr ":8000.*LISTENING"
if ($port8000) {
    Write-Host "⚠️  端口8000仍被占用: $port8000" -ForegroundColor Yellow
}

# 启动后端服务
Write-Host "🌟 启动FastAPI服务器..." -ForegroundColor Green
Write-Host "📍 服务地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📖 API文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "🛑 按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

try {
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
} catch {
    Write-Host "❌ 启动失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 请检查配置文件和依赖是否正确安装" -ForegroundColor Yellow
} finally {
    # 返回根目录
    Set-Location ..
    Write-Host "📁 已返回项目根目录" -ForegroundColor Cyan
}