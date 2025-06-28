#!/usr/bin/env python3
"""
开发环境启动脚本
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from loguru import logger

def check_port_available(port: int) -> bool:
    """检查端口是否可用"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

def kill_port_process(port: int) -> None:
    """关闭占用端口的进程"""
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f':{port}' in line and 'LISTENING' in line:
                        pid = line.split()[-1]
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                        logger.info(f"已关闭端口 {port} 上的进程 PID: {pid}")
        else:  # Unix/Linux/Mac
            result = subprocess.run(
                f'lsof -ti:{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.stdout:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    subprocess.run(f'kill -9 {pid}', shell=True)
                    logger.info(f"已关闭端口 {port} 上的进程 PID: {pid}")
    except Exception as e:
        logger.warning(f"关闭端口 {port} 进程时出错: {e}")

def setup_environment():
    """设置开发环境"""
    logger.info("🔧 设置开发环境...")
    
    # 创建必要的目录
    directories = [
        "backend/app/api",
        "backend/app/api/api_v1",
        "backend/app/core",
        "backend/app/models",
        "backend/app/schemas",
        "backend/app/services",
        "backend/app/utils",
        "frontend",
        "uploads",
        "logs",
        "temp",
        "static",
        "nginx/conf.d",
        "scripts"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 创建目录: {dir_path}")
    
    # 创建空的__init__.py文件
    init_files = [
        "backend/app/__init__.py",
        "backend/app/api/__init__.py",
        "backend/app/api/api_v1/__init__.py",
        "backend/app/core/__init__.py",
        "backend/app/models/__init__.py",
        "backend/app/schemas/__init__.py",
        "backend/app/services/__init__.py",
        "backend/app/utils/__init__.py",
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        logger.info(f"📄 创建文件: {init_file}")

def create_env_file():
    """创建环境变量文件"""
    env_content = """# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@localhost:5432/ai_project_manager
REDIS_URL=redis://:redis123@localhost:6379/0

# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_SECURE=false

# ChromaDB配置
CHROMA_HOST=localhost
CHROMA_PORT=8001

# AI模型配置
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 安全配置
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256

# 日志配置
LOG_LEVEL=INFO
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    logger.info("📝 创建 .env 文件")

def main():
    """主函数"""
    logger.info("🚀 启动AI项目管理系统开发环境")
    
    # 设置环境
    setup_environment()
    
    # 创建环境变量文件
    if not Path(".env").exists():
        create_env_file()
        logger.info("请编辑 .env 文件，配置您的API密钥和其他设置")
    
    # 检查并关闭占用的端口
    ports_to_check = [8000, 8501]
    for port in ports_to_check:
        if not check_port_available(port):
            logger.warning(f"端口 {port} 被占用，尝试关闭...")
            kill_port_process(port)
            time.sleep(2)
    
    logger.info("✅ 开发环境设置完成!")
    logger.info("📖 下一步操作:")
    logger.info("1. 编辑 .env 文件，配置您的API密钥")
    logger.info("2. 运行 'uv sync' 安装依赖")
    logger.info("3. 运行 'docker-compose up -d postgres redis minio chromadb' 启动基础服务")
    logger.info("4. 运行后端: cd backend && uvicorn app.main:app --reload")
    logger.info("5. 运行前端: cd frontend && streamlit run app.py")

if __name__ == "__main__":
    main() 