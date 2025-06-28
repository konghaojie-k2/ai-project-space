#!/usr/bin/env python3
"""
前端服务启动脚本 - Next.js版本
"""

import subprocess
import sys
import os
import psutil
from pathlib import Path

def check_port_in_use(port):
    """检查端口是否被占用"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port:
            return True, conn.pid
    return False, None

def kill_process_on_port(port):
    """关闭占用指定端口的进程"""
    try:
        for conn in psutil.net_connections():
            if conn.laddr.port == port and conn.pid:
                process = psutil.Process(conn.pid)
                print(f"🔄 关闭端口 {port} 上的进程: {process.name()} (PID: {conn.pid})")
                process.terminate()
                process.wait(timeout=5)
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
        print(f"⚠️ 无法关闭进程: {e}")
        return False
    return False

def check_node_installed():
    """检查Node.js是否安装"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js已安装: {version}")
            # 检查版本是否满足要求 (需要 >= 16.0.0)
            version_num = version.replace('v', '').split('.')[0]
            if int(version_num) >= 16:
                return True
            else:
                print(f"❌ Node.js版本过低，需要 >= 16.0.0，当前版本: {version}")
                return False
        else:
            print("❌ Node.js未安装")
            return False
    except FileNotFoundError:
        print("❌ Node.js未安装")
        return False

def check_npm_installed():
    """检查npm是否安装"""
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ npm已安装: {result.stdout.strip()}")
            return True
        else:
            print("❌ npm未安装")
            return False
    except FileNotFoundError:
        print("❌ npm未安装")
        return False

def install_dependencies():
    """安装前端依赖"""
    print("📦 安装前端依赖...")
    try:
        subprocess.run(['npm', 'install'], check=True, cwd='frontend')
        print("✅ 依赖安装完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False

def main():
    """启动前端服务"""
    print("🚀 启动AI项目管理系统前端服务 (Next.js)...")
    
    # 检查前端目录是否存在
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("❌ frontend目录不存在")
        return
    
    # 检查Node.js环境
    if not check_node_installed():
        print("\n📋 安装指南:")
        print("1. 访问 https://nodejs.org/")
        print("2. 下载并安装 LTS 版本 (推荐 v18 或 v20)")
        print("3. 重启命令行工具后重新运行此脚本")
        return
    
    if not check_npm_installed():
        print("请确保npm已正确安装")
        return
    
    # 检查package.json是否存在
    package_json = frontend_dir / "package.json"
    if not package_json.exists():
        print("❌ package.json不存在")
        return
    
    # 检查并关闭占用3000端口的进程
    port_in_use, pid = check_port_in_use(3000)
    if port_in_use:
        print(f"⚠️ 端口3000被进程占用 (PID: {pid})")
        if kill_process_on_port(3000):
            print("✅ 已关闭占用端口的进程")
        else:
            print("❌ 无法关闭占用端口的进程，请手动关闭")
            return
    
    # 检查node_modules是否存在，如果不存在则安装依赖
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("📦 首次运行，正在安装依赖...")
        if not install_dependencies():
            return
    
    # 启动Next.js开发服务器
    print("🚀 启动Next.js开发服务器...")
    print("📱 访问地址: http://localhost:3000")
    print("🔗 API代理: http://localhost:3000/api -> http://localhost:8000/api")
    print("⏹️  按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        subprocess.run(['npm', 'run', 'dev'], cwd=frontend_dir, check=True)
    except KeyboardInterrupt:
        print("\n🛑 前端服务已停止")
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        print("\n🔧 可能的解决方案:")
        print("1. 删除 node_modules 文件夹: rmdir /s node_modules (Windows)")
        print("2. 重新安装依赖: npm install")
        print("3. 检查package.json文件是否正确")
        print("4. 确保没有其他进程占用3000端口")

if __name__ == "__main__":
    main() 