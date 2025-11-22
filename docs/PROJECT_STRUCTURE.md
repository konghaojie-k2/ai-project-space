# AI项目管理系统 - 项目结构说明

## 项目概述
这是一个基于AI加持的项目管理系统，支持多模态内容和智能问答功能。

## 项目目录结构

```
ai-project-manager/
├── .venv/                      # UV虚拟环境目录
├── .cursor/                    # Cursor IDE配置目录
├── backend/                    # 后端服务
│   ├── app/                    # 主应用代码
│   │   ├── __init__.py         # 应用包初始化
│   │   ├── main.py             # FastAPI主应用入口
│   │   ├── core/               # 核心配置模块
│   │   │   ├── __init__.py     # 核心模块初始化
│   │   │   ├── config.py       # 应用配置管理
│   │   │   └── logging.py      # 日志配置
│   │   └── models/             # 数据模型定义
│   │       ├── __init__.py     # 模型包初始化
│   │       ├── base.py         # 基础模型类
│   │       ├── user.py         # 用户模型
│   │       ├── project.py      # 项目模型
│   │       ├── file.py         # 文件模型
│   │       └── qa.py           # 问答模型
│   └── Dockerfile              # 后端Docker配置
├── frontend/                   # 前端界面
│   └── Dockerfile              # 前端Docker配置
├── pyproject.toml              # 项目配置和依赖管理
├── uv.lock                     # UV锁定文件
├── docker-compose.yml          # Docker Compose配置
├── start_dev.py                # 开发环境启动脚本
├── README.md                   # 项目说明文档
├── project_requirements.md     # 项目需求文档
└── PROJECT_STRUCTURE.md        # 本文档
```

## 核心文件说明

### 配置文件
- **pyproject.toml**: 项目元数据、依赖管理、构建配置
- **uv.lock**: UV包管理器的锁定文件，确保依赖版本一致性
- **docker-compose.yml**: 容器编排配置，包含PostgreSQL、Redis、MinIO等服务

### 后端核心文件
- **backend/app/main.py**: FastAPI应用主入口，定义API路由
- **backend/app/core/config.py**: 应用配置管理，使用pydantic-settings
- **backend/app/core/logging.py**: 日志配置，使用loguru库
- **backend/app/models/**: 数据模型定义，基于SQLAlchemy 2.0

### 数据模型
- **base.py**: 基础模型类，包含通用字段
- **user.py**: 用户认证和权限管理
- **project.py**: 项目管理和阶段控制
- **file.py**: 文件上传、处理和向量化
- **qa.py**: 问答会话和笔记管理

### 开发工具
- **start_dev.py**: 开发环境一键启动脚本，包含端口检查和服务启动

## 技术栈详解

### 后端技术栈
- **FastAPI**: 高性能异步Web框架
- **SQLAlchemy 2.0**: 现代化ORM，支持异步操作
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和会话存储
- **MinIO**: 对象存储服务
- **ChromaDB**: 向量数据库，用于RAG功能

### AI和机器学习
- **OpenAI API**: 大语言模型接口
- **LangChain**: AI应用开发框架
- **Sentence Transformers**: 文本向量化
- **torch**: PyTorch深度学习框架

### 文件处理
- **pypdf**: PDF文件解析
- **python-docx**: Word文档处理
- **openpyxl**: Excel文件处理
- **opencv-python**: 图像处理
- **pillow**: 图像处理库

### 前端技术栈
- **Streamlit**: 快速原型开发框架
- **Plotly**: 交互式图表
- **Altair**: 统计可视化

## PyTorch (torch) 的作用

在我们的AI项目管理系统中，**torch**（PyTorch）主要用于以下几个方面：

### 1. 文本向量化 (Text Embeddings)
```python
# sentence-transformers库依赖torch
from sentence_transformers import SentenceTransformer

# 用于将文档内容转换为向量表示
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(texts)
```

### 2. 多模态内容理解
- **图像处理**: 结合opencv-python处理上传的图片
- **文档理解**: 对PDF、Word等文档进行智能解析
- **内容分类**: 自动识别文档类型和重要程度

### 3. 本地AI模型推理
- 支持加载本地的transformer模型
- 提供离线AI能力，减少对外部API的依赖
- 自定义模型微调和优化

### 4. RAG系统核心
```python
# 向量相似度计算
import torch
import torch.nn.functional as F

def compute_similarity(query_embedding, doc_embeddings):
    # 计算查询与文档的相似度
    similarities = F.cosine_similarity(
        query_embedding.unsqueeze(0), 
        doc_embeddings, 
        dim=1
    )
    return similarities
```

### 5. 性能优化
- **GPU加速**: 利用CUDA进行向量计算加速
- **批处理**: 批量处理文档向量化
- **内存管理**: 高效的张量操作

## 依赖关系图

```
torch (PyTorch)
├── sentence-transformers  # 文本向量化
├── transformers          # Transformer模型
├── tokenizers           # 文本分词
└── chromadb            # 向量数据库（可选torch后端）
```

## 开发环境设置

1. **安装依赖**:
   ```bash
   uv sync
   ```

2. **启动开发环境**:
   ```bash
   python start_dev.py
   ```

3. **Docker部署**:
   ```bash
   docker-compose up -d
   ```

## 注意事项

- **torch安装**: 根据系统选择CPU或GPU版本
- **内存需求**: AI模型可能需要较大内存
- **GPU支持**: 可选择CUDA版本提升性能
- **模型缓存**: 首次运行会下载预训练模型

这个项目结构设计遵循了现代Python项目的最佳实践，支持容器化部署和云原生架构。 