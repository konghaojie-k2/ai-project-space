# 后端应用启动指南

## 快速启动脚本

为了避免启动后端时的常见错误，项目根目录提供了两个启动脚本：

### 方式一：PowerShell脚本（推荐）
```powershell
.\start-backend.ps1
```

### 方式二：批处理文件
```cmd
start-backend.bat
```

## 脚本功能

这些脚本会自动执行以下操作：

1. ✅ **目录检查** - 确保在正确的项目根目录
2. ✅ **环境检查** - 验证虚拟环境是否存在
3. ✅ **进程清理** - 终止可能冲突的Python进程
4. ✅ **端口检查** - 检查8000端口是否可用
5. ✅ **服务启动** - 启动FastAPI服务器
6. ✅ **错误处理** - 提供清晰的错误信息和建议

## 服务信息

启动成功后，可以访问：

- **API服务**: http://localhost:8000
- **交互式文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc

## 常见问题

### 1. 权限错误
如果PowerShell脚本无法执行，请以管理员身份运行PowerShell并执行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2. 端口占用
脚本会自动尝试清理端口，如果仍有问题，可以手动检查：
```cmd
netstat -ano | findstr :8000
```

### 3. 虚拟环境问题
确保已经初始化uv环境：
```cmd
uv init
```

### 4. 配置文件错误
如果遇到配置解析错误，请检查 `backend/.env` 文件的格式。

## 手动启动（备用方法）

如果脚本无法使用，可以手动执行：

```cmd
cd backend
taskkill /F /IM python.exe /T
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 停止服务

在终端中按 `Ctrl+C` 即可停止服务。
