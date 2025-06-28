# 项目管理系统需求文档

## 项目概述

一个基于AI加持的项目管理系统，支持按项目阶段进行文件/网址上传，形成项目专用上下文，允许项目组成员进行智能问答，优质问答可保存为笔记。

## 核心特点

- **多模态支持**: 文本、图片、视频、音频、PDF等多种格式
- **AI加持**: 集成大语言模型，支持智能问答和内容分析
- **人人可以共享**: 支持多用户协作，权限管理
- **越用越好**: 基于使用数据持续优化AI响应质量

## 功能需求

### 1. 项目阶段管理
- 售前阶段
- 业务调研阶段
- 数据理解阶段
- 数据探索阶段
- 工程开发阶段
- 实施部署阶段

### 2. 文件上传与管理
- 支持多种文件格式（PDF、Word、Excel、PPT、图片、视频等）
- 网址链接内容抓取
- 文件版本控制
- 分阶段组织文件

### 3. AI问答系统
- 基于项目上下文的智能问答
- 多模态内容理解
- 问答历史记录
- 优质问答保存为笔记

### 4. 用户权限管理
- 项目创建者/管理员
- 项目成员
- 访客权限
- 角色权限控制

### 5. 笔记管理
- 问答转笔记
- 笔记分类标签
- 笔记搜索
- 笔记分享

## 技术架构

### 后端技术栈
- **框架**: FastAPI (高性能异步Web框架)
- **数据库**: PostgreSQL + Redis
- **文件存储**: MinIO (对象存储)
- **向量数据库**: Chroma/Weaviate (用于RAG)
- **AI模型**: 支持OpenAI API兼容的模型
- **任务队列**: Celery + Redis

### 前端技术栈
- **框架**: Next.js 14 (App Router模式)
- **样式**: Tailwind CSS 3
- **UI组件**: Headless UI / Radix UI
- **状态管理**: Zustand / React Query
- **图表**: Chart.js / Recharts
- **文件上传**: react-dropzone
- **表单**: React Hook Form + Zod
- **动画**: Framer Motion
- **图标**: Lucide React / Heroicons

### 部署方案
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx
- **HTTPS**: Let's Encrypt
- **监控**: Prometheus + Grafana
- **前端部署**: Vercel / Netlify (可选)

## 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端界面      │    │   API网关       │    │   AI服务        │
│   (Next.js 14)  │◄──►│   (FastAPI)     │◄──►│   (LLM/RAG)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   文件存储      │    │   关系数据库    │    │   向量数据库    │
│   (MinIO)       │    │   (PostgreSQL)  │    │   (Chroma)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 开发计划

### Phase 1: 基础架构搭建 (1-2周)
1. 项目结构初始化
   - Next.js 14项目初始化 (App Router)
   - Tailwind CSS配置
   - TypeScript配置
   - ESLint + Prettier配置
2. 数据库设计
   - PostgreSQL数据库设计
   - Alembic迁移脚本
3. 基础API开发
   - FastAPI项目结构
   - 基础CRUD接口
4. 用户认证系统
   - JWT认证
   - 用户注册/登录API
   - Next.js认证中间件

### Phase 2: 核心组件开发 (2-3周)
1. 前端核心组件
   - 布局组件 (Header, Sidebar, Layout)
   - 通用UI组件 (Button, Input, Modal等)
   - 项目阶段组件
   - 响应式设计实现
2. 用户界面开发
   - 登录/注册页面
   - 项目管理界面
   - 用户权限管理
3. 状态管理
   - Zustand store配置
   - React Query数据获取
4. 路由和导航
   - App Router页面结构
   - 动态路由配置

### Phase 3: 文件管理系统 (2-3周)
1. 文件上传功能
   - react-dropzone集成
   - 拖拽上传界面
   - 文件预览组件
   - 上传进度显示
2. 文件解析处理
   - 多格式文件处理
   - 文件内容提取
3. 网址内容抓取
   - URL内容抓取界面
   - 内容预览组件
4. 阶段性组织
   - 文件分类界面
   - 阶段切换组件

### Phase 4: AI问答系统 (3-4周)
1. RAG系统集成
   - 向量数据库连接
   - 文档检索优化
2. 多模态内容处理
   - 图片/视频内容理解
   - 音频转文字
3. 问答接口开发
   - 实时问答界面
   - 聊天组件开发
   - 打字机效果
4. 上下文管理
   - 会话历史管理
   - 上下文切换

### Phase 5: 高级功能与优化 (2-3周)
1. 笔记管理系统
   - 富文本编辑器
   - 笔记分类标签
   - 搜索功能
2. 协作功能
   - 实时协作
   - 评论系统
   - 通知系统
3. 数据可视化
   - Chart.js/Recharts图表
   - 项目进度仪表板
   - 使用统计分析
4. 性能优化
   - 代码分割
   - 图片优化
   - 缓存策略
   - SEO优化

### Phase 6: 测试与部署 (1-2周)
1. 测试
   - 单元测试 (Jest + Testing Library)
   - 集成测试
   - E2E测试 (Playwright)
2. 部署配置
   - Docker容器化
   - CI/CD流水线
   - 生产环境配置
3. 文档编写
   - 用户手册
   - 开发文档
   - API文档

## 前端文件结构

```
frontend/
├── app/                          # App Router目录
│   ├── (auth)/                   # 认证路由组
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/              # 主应用路由组
│   │   ├── projects/
│   │   ├── files/
│   │   ├── chat/
│   │   └── notes/
│   ├── api/                      # API路由
│   ├── globals.css               # 全局样式
│   ├── layout.tsx                # 根布局
│   └── page.tsx                  # 首页
├── components/                   # 组件目录
│   ├── ui/                       # 基础UI组件
│   ├── layout/                   # 布局组件
│   ├── forms/                    # 表单组件
│   └── features/                 # 功能组件
├── lib/                          # 工具库
│   ├── api.ts                    # API客户端
│   ├── auth.ts                   # 认证工具
│   ├── utils.ts                  # 通用工具
│   └── validations.ts            # 表单验证
├── hooks/                        # 自定义Hooks
├── store/                        # 状态管理
├── types/                        # TypeScript类型
├── public/                       # 静态资源
├── tailwind.config.js            # Tailwind配置
├── next.config.js                # Next.js配置
└── package.json                  # 依赖配置
```

## 预期成果

- 一个现代化的项目管理系统
- 响应式设计，支持移动端和桌面端
- 优秀的用户体验和交互设计
- 支持多模态AI问答
- 组件化的可维护架构
- 详细的类型定义和文档 