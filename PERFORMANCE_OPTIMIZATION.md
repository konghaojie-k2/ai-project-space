# 性能优化实施指南

## 问题诊断结果

通过深度分析，确认了系统性能问题的根本原因：
- **过度复杂的数据库权限架构设计**
- **复杂的RLS策略导致每次查询都要执行大量计算**
- **缺乏应用层缓存机制**
- **前端没有超时控制和错误处理**

## 已实施的优化方案

### 1. 数据库层面优化 ✅

**关键索引创建** (`database/performance_optimization.sql`)：
- 为权限检查字段添加复合索引
- 为用户查询添加优化索引
- 为RLS策略添加专门索引

**物化视图创建**：
- `user_project_permissions` - 用户项目权限预计算
- 权限检查函数优化
- 批量权限检查函数

**RLS策略简化**：
- 使用物化视图替代复杂查询
- 减少嵌套函数调用
- 优化权限检查逻辑

### 2. 应用层优化 ✅

**SupabaseService缓存机制** (`backend/app/services/supabase_client.py`)：
- 多层缓存管理器（PermissionCache）
- 缓存TTL控制
- 缓存命中率统计
- 缓存清理和刷新机制

**优化的查询方法**：
- `get_profile()` - 用户档案缓存（10分钟）
- `get_chat_stats()` - 聊天统计缓存（2分钟）
- `get_user_accessible_projects_enhanced()` - 项目列表缓存（3分钟）
- 统计查询优化，避免复杂JOIN

### 3. 前端优化 ✅

**Dashboard页面优化** (`frontend/app/dashboard/page.tsx`)：
- 5秒API请求超时控制
- 8秒Dashboard加载总超时
- 错误状态和重试机制
- 优雅降级处理

### 4. 监控API ✅

**性能监控端点** (`backend/app/api/api_v1/endpoints/performance.py`)：
- `/api/v1/performance/stats` - 获取性能统计
- `/api/v1/performance/cache/clear` - 清理缓存
- `/api/v1/performance/cache/refresh` - 刷新权限缓存

## 部署步骤

### 第1步：执行数据库优化

```sql
-- 在Supabase控制台的SQL编辑器中执行
-- 或使用 psql 连接到您的数据库

-- 执行性能优化脚本
\i database/performance_optimization.sql
```

**或直接在Supabase控制台执行以下关键SQL：**

```sql
-- 1. 创建关键索引
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_project_members_user_project
ON public.project_members(user_id, project_id, is_active, role);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_profiles_active_users
ON public.profiles(id, is_active, system_role) WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chat_sessions_user_project
ON public.chat_sessions(user_id, project_id, created_at);

-- 2. 创建权限物化视图
DROP MATERIALIZED VIEW IF EXISTS public.user_project_permissions;

CREATE MATERIALIZED VIEW public.user_project_permissions AS
SELECT
    pm.user_id,
    pm.project_id,
    pm.role,
    p.created_by = pm.user_id as is_owner,
    p.is_public,
    pm.is_active,
    p.created_by as project_creator,
    p.name as project_name,
    p.description as project_description,
    p.created_at as project_created_at
FROM public.project_members pm
JOIN public.projects p ON pm.project_id = p.id
WHERE pm.is_active = true
UNION ALL
SELECT
    p.created_by as user_id,
    p.id as project_id,
    'owner' as role,
    true as is_owner,
    p.is_public,
    true as is_active,
    p.created_by as project_creator,
    p.name as project_name,
    p.description as project_description,
    p.created_at as project_created_at
FROM public.projects p
WHERE NOT EXISTS (
    SELECT 1 FROM public.project_members pm
    WHERE pm.project_id = p.id AND pm.user_id = p.created_by
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_project_permissions_user
ON public.user_project_permissions(user_id, project_id, is_active);

-- 3. 创建刷新函数
CREATE OR REPLACE FUNCTION public.refresh_user_permissions()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY public.user_project_permissions;
END;
$$ LANGUAGE plpgsql;
```

### 第2步：重启后端服务

```bash
cd backend
# 停止当前服务
# 重新启动以应用缓存机制
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 第3步：重启前端服务

```bash
cd frontend
npm run dev
```

## 性能预期

**优化效果预测：**
- **登录性能**: 从5秒降低到1秒以内（提升80%+）
- **Dashboard加载**: 从45秒降低到5秒以内（提升89%+）
- **系统响应**: 整体提升60-90%
- **并发能力**: 显著提升，减少数据库负载

## 监控和验证

### 1. 使用性能监控API

```bash
# 获取性能统计（需要超级管理员权限）
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/performance/stats

# 清理缓存
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/performance/cache/clear

# 刷新权限缓存
curl -X POST -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/performance/cache/refresh
```

### 2. 关键性能指标

**缓存命中率:**
- 目标：> 70%
- 优秀：> 85%

**平均查询时间:**
- 目标：< 200ms
- 优秀：< 100ms

**API响应时间:**
- 登录：< 1s
- Dashboard：< 3s
- 文件列表：< 500ms

### 3. 日志监控

监控关键日志：
```
✅ 缓存命中: profile:user_id
💾 缓存设置: user_projects:user_id
🚀 使用缓存文件统计 (用户: admin_user)
```

## 故障排除

### 问题1：物化视图不存在

**症状：**
```
relation "public.user_project_permissions" does not exist
```

**解决方案：** 确保已执行数据库优化脚本

### 问题2：缓存不生效

**症状：** 性能没有明显改善

**解决方案：**
1. 检查后端服务是否重启
2. 查看日志确认缓存机制启用
3. 检查SupabaseService实例是否正确初始化

### 问题3：权限检查失败

**症状：** 用户无法访问项目

**解决方案：**
1. 执行 `SELECT public.refresh_user_permissions();` 刷新权限缓存
2. 检查物化视图数据是否正确
3. 验证索引是否创建成功

## 维护建议

### 定期维护任务

1. **每日任务**：
   - 监控缓存命中率
   - 检查错误日志

2. **每周任务**：
   - 刷新权限缓存
   - 分析慢查询日志

3. **每月任务**：
   - 更新表统计信息
   - 检查索引使用情况

### 自动化建议

如果您的Supabase支持pg_cron扩展，可以设置自动刷新：

```sql
-- 每5分钟自动刷新权限缓存（需要pg_cron扩展）
SELECT cron.schedule(
    'refresh-user-permissions',
    '*/5 * * * *',
    'SELECT public.refresh_user_permissions();'
);
```

## 回滚方案

如果遇到问题，可以通过以下方式回滚：

```sql
-- 删除物化视图
DROP MATERIALIZED VIEW IF EXISTS public.user_project_permissions;

-- 删除新增索引（谨慎操作）
DROP INDEX IF EXISTS idx_project_members_user_project;
DROP INDEX IF EXISTS idx_profiles_active_users;
-- ... 其他索引
```

---

**⚠️ 重要提醒：**
1. 在生产环境执行数据库操作前请先备份数据库
2. 建议在测试环境先验证优化效果
3. 监控系统性能，如有问题及时调整