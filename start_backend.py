#!/usr/bin/env python3
"""
后端服务启动脚本
"""

import subprocess
import sys
from pathlib import Path

def main():
    """启动后端服务"""
    print("🚀 启动AI项目管理系统后端服务...")
    
    # 切换到backend目录
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("❌ backend目录不存在")
        return
    
    # 启动uvicorn服务器
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app", 
        "--reload", 
        "--host", "0.0.0.0", 
        "--port", "8000"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    print("按 Ctrl+C 停止服务")
    
    try:
        subprocess.run(cmd, cwd=backend_dir, check=True)
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main() 