# 迁移到Supabase数据库 - 进度跟踪

## ✅ 已完成的迁移

1. **认证系统** - 已完全迁移到Supabase Auth
2. **文件管理** - `files_rag.py` 和部分 `files_enhanced.py` 已使用Supabase
3. **权限系统** - 已使用Supabase RLS策略

## ⚠️ 需要迁移的文件

### 1. `backend/app/api/chat.py` - 聊天API
**当前状态**: 使用SQLAlchemy + 本地数据库
**需要迁移**: 
- ✅ Supabase客户端已有方法：
  - `create_chat_session()`
  - `create_chat_message()`
  - `get_chat_session_messages()`
  - `get_user_chat_sessions()`
- ❌ 需要添加的方法：
  - `get_chat_session()` - 获取单个会话
  - `update_chat_session()` - 更新会话
  - `delete_chat_session()` - 删除会话
  - `get_chat_stats()` - 获取统计信息

**迁移步骤**:
1. 移除 `get_db` 依赖
2. 使用 `supabase_service` 替代所有数据库操作
3. 更新所有端点使用Supabase方法

### 2. `backend/app/api/api_v1/endpoints/projects.py` - 项目管理
**当前状态**: 使用SQLAlchemy + 本地数据库
**需要迁移**: 
- ✅ Supabase客户端已有方法：
  - `create_project()`
  - `get_project_details()`
  - `update_project()`
  - `get_user_projects()`
- ❌ 需要检查的方法：
  - 项目搜索和过滤
  - 项目统计

**迁移步骤**:
1. 移除 `get_db` 依赖
2. 使用 `supabase_service` 替代所有数据库操作
3. 更新所有端点使用Supabase方法

### 3. `backend/app/api/api_v1/endpoints/files_enhanced.py` - 增强文件管理
**当前状态**: 部分使用Supabase，但仍导入 `get_db`
**需要迁移**: 
- 移除未使用的 `get_db` 导入
- 确保所有操作都使用 `supabase_file_service`

### 4. `backend/app/api/api_v1/endpoints/project_members.py` - 项目成员管理
**当前状态**: 使用SQLAlchemy + 本地数据库
**需要迁移**: 
- ✅ Supabase客户端已有方法：
  - `add_project_member_enhanced()`
  - `get_project_members_with_profiles()`
  - `update_project_member_role()`
  - `remove_project_member()`
- ❌ 需要检查的方法：
  - 成员搜索和过滤

**迁移步骤**:
1. 移除 `get_db` 依赖
2. 使用 `supabase_service` 替代所有数据库操作

## 📝 迁移检查清单

对于每个需要迁移的文件：

- [ ] 移除 `from ..core.database import get_db`
- [ ] 移除 `from sqlalchemy.orm import Session`
- [ ] 移除所有 `db: Session = Depends(get_db)` 参数
- [ ] 导入 `from app.services.supabase_client import supabase_service`
- [ ] 替换所有 `db.query()` 为 Supabase 客户端调用
- [ ] 替换所有 `db.add()` / `db.commit()` 为 Supabase `insert()` / `update()`
- [ ] 更新错误处理以适应Supabase响应格式
- [ ] 测试所有端点功能

## 🔧 已修复的问题

1. ✅ SQLAlchemy `metadata` 保留字冲突 - 已使用显式列名修复
2. ✅ 表名不匹配 (`conversations` vs `chat_sessions`) - 已修复
3. ✅ 字段名不匹配 (`conversation_id` vs `session_id`) - 已修复

## 📌 注意事项

1. **向后兼容**: 保持API响应格式不变
2. **错误处理**: Supabase的错误格式与SQLAlchemy不同，需要适配
3. **事务处理**: Supabase不支持传统事务，需要调整逻辑
4. **RLS策略**: 确保所有查询都遵循Row Level Security策略

