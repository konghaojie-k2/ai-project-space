#!/usr/bin/env python3
"""
后端服务启动脚本
自动设置环境变量并启动FastAPI服务
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # 设置环境变量解决OpenMP冲突
    os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
    
    # 设置项目根目录
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    print("🚀 启动AI项目管理系统后端服务...")
    print("📁 工作目录:", backend_dir)
    print("🔧 环境变量 KMP_DUPLICATE_LIB_OK=TRUE 已设置")
    
    try:
        # 使用uv运行uvicorn
        cmd = [
            "uv", "run", "python", "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ]
        
        print("📡 启动命令:", " ".join(cmd))
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 