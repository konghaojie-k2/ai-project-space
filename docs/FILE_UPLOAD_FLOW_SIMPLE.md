# 文件上传流程 - 简化版

## 双流程架构

文件上传分为两个独立的流程：

### 流程1: 文件存储（必执行）
```
用户选择文件
    ↓
前端验证（大小、类型）
    ↓
POST /api/v1/files/upload
    ↓
后端验证（权限、文件）
    ↓
上传到 Supabase Storage
    ↓
创建数据库记录（files表）
    ↓
返回文件信息 ✅
```

### 流程2: RAG 数据（条件执行）
```
[仅在指定 project_id 时执行]
    ↓
检查/创建项目知识库（project_{project_id}）
    ↓
上传到 RAG 服务（8002端口）
    ↓
RAG 处理（解析、分块、向量化）
    ↓
创建映射记录（rag_mappings表）
    ↓
完成 ✅
```

## 完整流程图

```mermaid
graph TB
    subgraph "前端流程"
        A[用户选择文件] --> B[前端验证]
        B --> C[创建 FormData]
        C --> D[调用 API]
    end
    
    subgraph "后端 - 文件存储流程"
        D --> E[用户认证检查]
        E --> F[文件验证]
        F --> G{验证通过?}
        G -->|否| ERR1[返回错误]
        G -->|是| H{有 project_id?}
        H -->|是| I[权限检查]
        I --> J{有权限?}
        J -->|否| ERR2[返回 403]
        J -->|是| K[读取文件]
        H -->|否| K
        K --> L[上传到 Supabase Storage]
        L --> M[创建数据库记录 files表]
        M --> SUCCESS1[文件存储成功 ✅]
    end
    
    subgraph "后端 - RAG 数据流程"
        SUCCESS1 --> N{有 project_id<br/>且 RAG 可用?}
        N -->|否| END[返回成功]
        N -->|是| O[检查/创建知识库]
        O --> P[上传到 RAG 服务 8002]
        P --> Q{RAG 上传成功?}
        Q -->|否| WARN1[记录错误日志]
        Q -->|是| R[创建映射记录 rag_mappings]
        R --> SUCCESS2[RAG 数据上传成功 ✅]
        WARN1 --> END
        SUCCESS2 --> END
    end
    
    ERR1 --> END
    ERR2 --> END
    
    style SUCCESS1 fill:#90EE90
    style SUCCESS2 fill:#90EE90
    style END fill:#87CEEB
    style ERR1 fill:#FFB6C1
    style ERR2 fill:#FFB6C1
    style WARN1 fill:#FFD700
```

## 关键点

1. **文件存储是主要流程**，必须成功
2. **RAG 数据是附加流程**，失败不影响文件存储
3. **两个流程并行执行**，互不阻塞
4. **RAG 服务端口**: 8002
5. **使用 admin_client 绕过 RLS**，确保数据库记录创建成功

