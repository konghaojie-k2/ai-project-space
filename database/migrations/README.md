# 数据库迁移说明

## 文件概览

本目录包含了AI项目管理系统的所有数据库迁移文件：

### 主要迁移文件

1. **`init_complete_database.sql`** - 完整数据库初始化脚本（推荐使用）
   - 整合了所有迁移文件和修复补丁
   - 包含完整的表结构、索引、RLS策略、触发器和函数
   - 适用于全新数据库的初始化

2. **`001_initial_schema.sql`** - 初始数据库架构
   - 基础表结构定义
   - 基本的触发器和视图

3. **`002_row_level_security.sql`** - 行级安全策略
   - RLS策略定义
   - 用户权限控制

4. **`003_enhanced_permissions.sql`** - 增强权限模型
   - 扩展用户权限系统
   - 审计日志功能

5. **`004_rag_document_mapping.sql`** - RAG文档映射表
   - 外部RAG服务集成
   - 文档映射关系

### 修复补丁文件

- **`002_fix_rls_recursion.sql`** - 修复RLS策略递归问题
- **`003_fix_audit_log_rls.sql`** - 修复审计日志RLS递归问题
- **`004_fix_project_members_rls.sql`** - 修复项目成员表RLS递归问题
- **`005_fix_audit_trigger_service_key.sql`** - 修复Service Key审计触发器

## 使用方法

### 新建数据库（推荐）

```sql
-- 使用完整的初始化脚本
\i database/migrations/init_complete_database.sql
```

### 分步迁移（不推荐）

如果需要分步迁移，请按以下顺序执行：

1. `\i database/migrations/001_initial_schema.sql`
2. `\i database/migrations/002_row_level_security.sql`
3. `\i database/migrations/003_enhanced_permissions.sql`
4. `\i database/migrations/004_rag_document_mapping.sql`

然后应用所有修复补丁：

1. `\i database/migrations/002_fix_rls_recursion.sql`
2. `\i database/migrations/003_fix_audit_log_rls.sql`
3. `\i database/migrations/004_fix_project_members_rls.sql`
4. `\i database/migrations/005_fix_audit_trigger_service_key.sql`

## 数据库架构

### 核心表

- **`profiles`** - 用户档案（扩展auth.users）
- **`projects`** - 项目管理
- **`project_members`** - 项目成员关系
- **`files`** - 文件管理
- **`rag_document_mapping`** - RAG文档映射
- **`chat_sessions`** - 聊天会话
- **`chat_messages`** - 聊天消息
- **`permission_audit_log`** - 权限审计日志

### 权限系统

- 基于Row Level Security (RLS)
- 支持角色层级：super_admin > admin > manager > member > user
- 项目级别权限：owner > admin > member > viewer
- 文件访问级别：all_users > project_members > admins_only > owner_only

### 集成功能

- **Supabase Auth** - 用户认证
- **外部RAG服务** - 文档向量化和问答
- **审计日志** - 权限变更追踪
- **自动触发器** - 用户注册、更新时间戳等

## 注意事项

1. **权限递归问题**：所有RLS策略都使用了SECURITY DEFINER函数来避免递归
2. **Service Key支持**：审计触发器已适配Service Key操作（auth.uid()为NULL的情况）
3. **外部RAG集成**：使用rag_document_mapping表连接本地文件和外部RAG服务
4. **索引优化**：为所有RLS策略和常用查询创建了适当的索引

## 验证数据库

初始化完成后，可以运行以下查询验证：

```sql
-- 检查所有表是否创建成功
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 检查RLS是否启用
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

-- 检查所有函数
SELECT proname, prosrc
FROM pg_proc
WHERE pronamespace = 'public'::regnamespace
ORDER BY proname;
```

## 更新数据库

如果需要对数据库进行更新，请：

1. 创建新的迁移文件（按编号顺序）
2. 更新`init_complete_database.sql`文件
3. 更新本README文档