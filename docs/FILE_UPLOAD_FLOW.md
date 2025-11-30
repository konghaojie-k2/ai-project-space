# 文件上传流程说明

## 概述

文件上传分为两个主要流程：
1. **文件存储流程**：将文件上传到 Supabase Storage 并创建数据库记录
2. **RAG 数据流程**：将文件内容上传到外部 RAG 服务（8002端口）用于知识库检索

## 流程图

```mermaid
flowchart TD
    Start([用户选择文件]) --> Frontend[前端组件 FileUpload]
    
    Frontend --> ValidateFrontend{前端验证}
    ValidateFrontend -->|文件无效| Error1[显示错误信息]
    ValidateFrontend -->|文件有效| CreateFormData[创建 FormData<br/>包含: files, stage, project_id,<br/>description, access_level]
    
    CreateFormData --> CallAPI[调用 API<br/>POST /api/v1/files/upload]
    
    CallAPI --> Backend[后端接收请求]
    
    Backend --> AuthCheck{用户认证检查}
    AuthCheck -->|未认证| Error2[返回 401]
    AuthCheck -->|已认证| ValidateFile{文件验证}
    
    ValidateFile -->|大小超限| Error3[返回 400: 文件大小超过限制]
    ValidateFile -->|类型不支持| Error4[返回 400: 文件类型不支持]
    ValidateFile -->|验证通过| CheckProject{是否指定 project_id?}
    
    CheckProject -->|是| CheckPermission{权限检查<br/>用户是否为项目成员?}
    CheckPermission -->|无权限| Error5[返回 403: 无权限上传]
    CheckPermission -->|有权限| ReadFile[读取文件内容]
    CheckProject -->|否| ReadFile
    
    ReadFile --> UploadStorage[上传到 Supabase Storage<br/>路径: uploads/username/filename]
    
    UploadStorage --> StorageResult{Storage 上传结果}
    StorageResult -->|失败| Error6[返回 500: Storage 上传失败]
    StorageResult -->|成功| CreateDBRecord[创建数据库记录<br/>使用 admin_client 绕过 RLS<br/>表: files]
    
    CreateDBRecord --> DBResult{数据库记录创建结果}
    DBResult -->|失败| Error7[返回 500: 数据库操作失败]
    DBResult -->|成功| FileSuccess[文件存储成功<br/>返回 FileResponse]
    
    FileSuccess --> CheckRAG{是否指定 project_id<br/>且 RAG 服务可用?}
    
    CheckRAG -->|否| EndSuccess[返回成功响应]
    CheckRAG -->|是| CheckKB[检查/创建项目知识库<br/>名称: project_{project_id}]
    
    CheckKB --> KBResult{知识库操作结果}
    KBResult -->|失败| LogKBError[记录错误日志<br/>继续执行]
    KBResult -->|成功| PrepareRAG[准备 RAG 上传数据<br/>重新读取文件内容<br/>构建元数据 metadata]
    
    LogKBError --> PrepareRAG
    PrepareRAG --> UploadRAG[上传到 RAG 服务<br/>端口: 8002<br/>端点: /api/v1/knowledge-bases/{kb_name}/chunks/upload]
    
    UploadRAG --> RAGResult{RAG 上传结果}
    RAGResult -->|失败| LogRAGError[记录错误日志<br/>不影响文件存储成功]
    RAGResult -->|成功| CreateMapping[创建映射记录<br/>表: rag_mappings<br/>关联: local_file_id ↔ external_document_id]
    
    LogRAGError --> EndSuccess
    CreateMapping --> MappingResult{映射记录创建结果}
    MappingResult -->|失败| LogMappingError[记录警告日志]
    MappingResult -->|成功| RAGSuccess[RAG 数据上传成功]
    
    LogMappingError --> EndSuccess
    RAGSuccess --> EndSuccess
    
    EndSuccess --> UpdateUI[前端更新 UI<br/>显示上传成功]
    
    Error1 --> End
    Error2 --> End
    Error3 --> End
    Error4 --> End
    Error5 --> End
    Error6 --> End
    Error7 --> End
    
    End([流程结束])
    
    style Start fill:#e1f5ff
    style End fill:#ffe1e1
    style FileSuccess fill:#e1ffe1
    style RAGSuccess fill:#e1ffe1
    style EndSuccess fill:#e1ffe1
    style Error1 fill:#ffe1e1
    style Error2 fill:#ffe1e1
    style Error3 fill:#ffe1e1
    style Error4 fill:#ffe1e1
    style Error5 fill:#ffe1e1
    style Error6 fill:#ffe1e1
    style Error7 fill:#ffe1e1
    style UploadStorage fill:#fff4e1
    style CreateDBRecord fill:#fff4e1
    style UploadRAG fill:#e1f4ff
    style CreateMapping fill:#e1f4ff
```

## 详细流程说明

### 1. 文件存储流程（必执行）

#### 1.1 前端处理
- **组件**: `FileUpload.tsx`
- **步骤**:
  1. 用户选择文件
  2. 前端验证文件（大小、类型）
  3. 创建 `FormData`，包含：
     - `files`: 文件对象
     - `stage`: 项目阶段
     - `project_id`: 项目ID（可选）
     - `description`: 文件描述
     - `access_level`: 访问级别（默认：all_users）
  4. 调用 `apiUpload('/api/v1/files/upload', formData)`

#### 1.2 后端处理 - 文件验证
- **端点**: `POST /api/v1/files/upload`
- **验证项**:
  - 文件大小：最大 100MB
  - 文件类型：pdf, docx, xlsx, pptx, txt, md, 图片, 视频, 音频等
  - 用户认证：通过 `get_current_user` 依赖
  - 项目权限：如果指定了 `project_id`，检查用户是否为项目成员（至少需要 `member` 角色）

#### 1.3 后端处理 - 文件存储
- **服务**: `supabase_file_service.upload_file()`
- **步骤**:
  1. 生成唯一文件ID（UUID）
  2. 构建存储路径：`uploads/{username}/{file_id}{extension}`
  3. 上传到 Supabase Storage
  4. 获取文件公开URL
  5. 创建数据库记录（`files` 表）：
     - 使用 `admin_client`（Service Key）绕过 RLS 策略
     - 如果 `admin_client` 不可用，使用 `client` 并设置认证上下文
  6. 返回文件记录

#### 1.4 数据库记录结构
```json
{
  "id": "uuid",
  "original_name": "原始文件名",
  "stored_name": "存储文件名",
  "file_path": "存储路径",
  "file_size": 文件大小,
  "file_type": "MIME类型",
  "file_extension": "文件扩展名",
  "project_id": "项目ID（可选）",
  "uploaded_by": "用户ID（UUID）",
  "access_level": "访问级别",
  "description": "文件描述",
  "tags": ["标签列表"],
  "metadata": {
    "storage_url": "文件URL",
    "bucket": "存储桶名称"
  },
  "created_at": "创建时间",
  "updated_at": "更新时间"
}
```

### 2. RAG 数据流程（条件执行）

#### 2.1 执行条件
- 必须指定 `project_id`
- RAG 服务必须可用（`rag_client.is_available()` 返回 `true`）
- RAG 服务运行在 **8002 端口**

#### 2.2 知识库管理
- **知识库名称**: `project_{project_id}`
- **操作**:
  1. 检查知识库是否存在
  2. 如果不存在，创建知识库
  3. 如果创建失败，记录错误但继续执行（不影响文件存储）

#### 2.3 RAG 文件上传
- **服务**: `rag_client.upload_file()`
- **端点**: `POST http://localhost:8002/api/v1/knowledge-bases/{kb_name}/chunks/upload`
- **步骤**:
  1. 重新读取文件内容（因为之前已读取过）
  2. 构建元数据：
     ```json
     {
       "uploaded_by": "用户名",
       "user_id": "用户ID",
       "upload_time": "上传时间",
       "description": "文件描述",
       "tags": ["标签列表"],
       "content_type": "MIME类型",
       "file_size": 文件大小,
       "stage": "项目阶段"
     }
     ```
  3. 上传文件到 RAG 服务
  4. RAG 服务处理：
     - 文件解析（PDF、Word、Excel等）
     - 文本提取
     - 分块（chunking）
     - 向量化（embedding）
     - 存储到向量数据库
  5. 返回文档ID和分块数量

#### 2.4 映射记录创建
- **表**: `rag_mappings`
- **目的**: 关联本地文件记录和 RAG 文档
- **字段**:
  - `local_file_id`: 本地文件ID（`files` 表的 `id`）
  - `external_document_id`: RAG 文档ID
  - `external_collection_name`: RAG 知识库名称
  - `project_id`: 项目ID
  - `chunk_count`: 分块数量

## 错误处理

### 文件存储流程错误
- **文件验证失败**: 返回 400，前端显示错误信息
- **权限不足**: 返回 403，前端显示权限错误
- **Storage 上传失败**: 返回 500，记录错误日志
- **数据库操作失败**: 返回 500，记录错误日志

### RAG 数据流程错误
- **RAG 服务不可用**: 记录警告日志，**不影响文件存储成功**
- **知识库创建失败**: 记录错误日志，继续执行
- **RAG 上传失败**: 记录错误日志，**不影响文件存储成功**
- **映射记录创建失败**: 记录警告日志，**不影响文件存储成功**

**重要**: RAG 流程的任何错误都不会影响文件存储流程的成功。文件存储是主要流程，RAG 是附加流程。

## 配置要求

### 必需配置
- `SUPABASE_URL`: Supabase 项目URL
- `SUPABASE_ANON_KEY`: Supabase Anon Key
- `SUPABASE_SERVICE_KEY`: Supabase Service Key（用于绕过RLS）

### RAG 服务配置
- `RAG_API_ENDPOINT`: RAG 服务端点（默认：`http://localhost:8002`）
- `RAG_API_KEY`: RAG 服务API密钥（可选）
- `RAG_COLLECTION_NAME`: 默认知识库名称（默认：`project_management`）

## 数据流图

```
前端 (FileUpload.tsx)
    ↓ FormData
后端 API (/api/v1/files/upload)
    ↓
    ├─→ Supabase Storage (文件存储)
    │       ↓
    │   Supabase Database (files表)
    │       ↓
    │   返回 FileResponse
    │
    └─→ RAG Service (8002端口) [条件执行]
            ↓
        RAG 知识库 (project_{project_id})
            ↓
        Supabase Database (rag_mappings表)
            ↓
        返回映射记录
```

## 相关文件

### 前端
- `frontend/components/features/FileUpload.tsx`: 文件上传组件
- `frontend/lib/api.ts`: API 请求工具（`apiUpload` 函数）

### 后端
- `backend/app/api/api_v1/endpoints/files.py`: 文件上传API端点
- `backend/app/services/supabase_file_service.py`: Supabase文件服务
- `backend/app/services/supabase_client.py`: Supabase客户端（`create_file_record` 方法）
- `backend/app/services/rag_client.py`: RAG服务客户端
- `backend/app/services/rag_mapping_service.py`: RAG映射服务

## 注意事项

1. **RLS 策略**: 文件记录创建使用 `admin_client`（Service Key）绕过 RLS。如果 `SUPABASE_SERVICE_KEY` 未配置，将使用普通 `client` 并设置认证上下文，可能受到 RLS 策略限制。

2. **文件大小限制**: 默认最大 100MB（Supabase Storage 限制）

3. **RAG 服务依赖**: RAG 流程是可选的，即使 RAG 服务不可用，文件存储仍然可以成功。

4. **并发处理**: 前端使用延迟上传（`index * 100ms`）避免并发过多。

5. **错误恢复**: RAG 流程的任何错误都不会回滚文件存储，确保文件存储的可靠性。

