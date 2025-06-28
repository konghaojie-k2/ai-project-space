FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器
RUN pip install uv

# 复制项目配置文件
COPY pyproject.toml ./

# 创建虚拟环境并安装依赖
RUN uv venv .venv
ENV PATH="/app/.venv/bin:$PATH"
RUN uv pip install -e .

# 复制应用代码
COPY backend/ ./

# 创建必要的目录
RUN mkdir -p uploads logs

# 设置权限
RUN chmod +x /app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 