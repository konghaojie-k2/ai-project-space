# AI项目管理系统

一个基于AI加持的项目管理系统，支持按项目阶段进行文件/网址上传，形成项目专用上下文，允许项目组成员进行智能问答，优质问答可保存为笔记。

## ✨ 特点

- **多模态支持**: 文本、图片、视频、音频、PDF等多种格式
- **AI加持**: 集成大语言模型，支持智能问答和内容分析  
- **人人可以共享**: 支持多用户协作，权限管理
- **越用越好**: 基于使用数据持续优化AI响应质量
- **按阶段管理**: 售前/业务调研/数据理解/数据探索/工程开发/实施部署

## 🏗️ 技术架构

### 后端技术栈
- **框架**: FastAPI (高性能异步Web框架)
- **数据库**: PostgreSQL + Redis
- **文件存储**: MinIO (对象存储)
- **向量数据库**: ChromaDB (用于RAG)
- **AI模型**: 支持OpenAI API兼容的模型

### 前端技术栈
- **框架**: Streamlit (快速原型开发)
- **UI组件**: Streamlit原生组件
- **图表**: Plotly/Altair

### 部署方案
- **容器化**: Docker + Docker Compose
- **包管理**: UV (快速Python包管理器)
- **日志**: Loguru
- **配置**: Pydantic Settings

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Docker & Docker Compose
- UV包管理器

### 1. 克隆项目

```bash
git clone <repository-url>
cd ai-project-manager
```

### 2. 安装UV并设置环境

```bash
# 安装UV
pip install uv

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

uv sync
```

### 3. 设置开发环境

```bash
# 运行环境设置脚本
python start_dev.py
```

### 4. 配置环境变量

编辑 `.env` 文件，配置您的API密钥：

```env
# AI模型配置
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# 其他配置...
```

### 5. 启动基础服务

```bash
# 启动数据库、Redis、MinIO、ChromaDB
docker-compose up -d postgres redis minio chromadb
```

### 6. 启动应用

#### 方式一：分别启动（推荐开发）

```bash
# 终端1: 启动后端
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端2: 启动前端  
cd frontend
streamlit run app.py --server.port 8501
```

#### 方式二：Docker Compose启动

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 7. 访问应用

- **前端界面**: http://localhost:8501
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **MinIO控制台**: http://localhost:9001 (minioadmin/minioadmin123)

## 📁 项目结构

```
ai-project-manager/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── schemas/        # Pydantic模式
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   └── Dockerfile
├── frontend/               # 前端服务
│   ├── pages/             # Streamlit页面
│   ├── components/        # 组件
│   ├── utils/             # 工具函数
│   └── app.py             # 主应用
├── nginx/                 # Nginx配置
├── scripts/               # 脚本文件
├── docker-compose.yml     # Docker编排
├── pyproject.toml         # 项目配置
└── README.md             # 项目文档
```

## 🔧 开发指南

### 代码规范

项目使用以下工具确保代码质量：

- **Black**: 代码格式化
- **Isort**: 导入排序
- **Flake8**: 代码检查
- **MyPy**: 类型检查

```bash
# 格式化代码
black .
isort .

# 代码检查
flake8 .
mypy backend/
```

### 数据库迁移

```bash
# 生成迁移文件
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

### 测试

```bash
# 运行测试
pytest

# 测试覆盖率
pytest --cov=backend/app tests/
```

## 🎯 功能特性

### 项目管理
- ✅ 多阶段项目组织
- ✅ 用户权限管理
- ✅ 项目成员协作

### 文件管理
- ✅ 多格式文件上传
- ✅ 网址内容抓取
- ✅ 文件版本控制
- ✅ 智能内容提取

### AI问答
- ✅ 基于RAG的智能问答
- ✅ 多模态内容理解
- ✅ 问答历史记录
- ✅ 质量评估反馈

### 笔记系统
- ✅ 问答转笔记
- ✅ 笔记分类标签
- ✅ 笔记搜索分享
- ✅ 协作编辑

## 🛠️ 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接URL | postgresql+asyncpg://... |
| `REDIS_URL` | Redis连接URL | redis://... |
| `OPENAI_API_KEY` | OpenAI API密钥 | - |
| `SECRET_KEY` | JWT密钥 | - |
| `LOG_LEVEL` | 日志级别 | INFO |

### 项目配置

- **项目阶段**: 可在 `settings.PROJECT_STAGES` 中自定义
- **用户角色**: 可在 `settings.USER_ROLES` 中配置
- **文件类型**: 可在 `settings.ALLOWED_FILE_TYPES` 中设置

## 🚀 部署

### 生产环境部署

1. **配置环境变量**
```bash
cp .env.example .env.prod
# 编辑 .env.prod 设置生产环境配置
```

2. **构建镜像**
```bash
docker-compose -f docker-compose.yml build
```

3. **启动服务**
```bash
docker-compose -f docker-compose.yml up -d
```

### 监控和日志

- 日志文件位置: `logs/`
- 健康检查: `http://localhost:8000/health`
- 监控指标: 可集成Prometheus + Grafana

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如果您遇到问题或有建议，请：

1. 查看 [FAQ](docs/FAQ.md)
2. 搜索现有的 [Issues](../../issues)
3. 创建新的 [Issue](../../issues/new)

## 🙏 致谢

感谢以下开源项目的启发：
- [Open Notebook](https://github.com/lfnovo/open-notebook)
- [QAnything](https://github.com/netease-youdao/QAnything)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Streamlit](https://streamlit.io/)

---

⭐ 如果这个项目对您有帮助，请给我们一个星标！ 