# 文件上传RLS错误修复报告

## 问题描述

文件上传到Supabase Storage时失败，错误信息：
```
ERROR | app.services.supabase_file_service:upload_file:204 - 文件上传失败: 
{'statusCode': 403, 'error': Unauthorized, 'message': new row violates row-level security policy}
```

## 根本原因

1. **RLS策略限制**：Supabase的Row Level Security (RLS)策略要求 `uploaded_by = auth.uid()`
2. **客户端选择错误**：`create_file_record` 方法使用 `anon_client`（Anon Key），即使设置了认证上下文，也可能因为RLS策略而失败
3. **认证上下文问题**：虽然代码尝试设置认证上下文，但这种方式不够可靠

## 修复方案

### 1. 使用admin_client创建文件记录

修改 `backend/app/services/supabase_client.py` 中的 `create_file_record` 方法：

```python
async def create_file_record(self, file_data: Dict) -> Optional[Dict]:
    """
    创建文件记录
    使用admin_client（Service Key）绕过RLS限制，因为这是服务端操作
    """
    # 优先使用admin_client（Service Key）绕过RLS限制
    client_to_use = self.admin_client if self.admin_client else self.client
    
    if not client_to_use:
        logger.error("Supabase客户端未初始化，无法创建文件记录")
        return None

    try:
        response = client_to_use.table('files').insert({
            **file_data,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }).execute()
        # ...
```

**关键改进**：
- 优先使用 `admin_client`（Service Key），可以绕过RLS限制
- 如果 `admin_client` 不可用，回退到 `client`（Anon Key）
- 添加了详细的错误日志

### 2. 移除不必要的认证上下文设置

修改 `backend/app/api/api_v1/endpoints/files.py`：

- 移除了 `set_auth_context` 调用
- 移除了 `clear_auth_context` 调用
- 移除了 `tokens` 参数依赖

**原因**：使用 `admin_client` 后，不需要设置认证上下文，因为Service Key会绕过RLS限制。

### 3. 添加UUID格式验证和project_id规范化

修改 `backend/app/services/supabase_file_service.py` 中的 `upload_file` 方法：

- 添加了 `user_id` UUID格式验证
- 添加了 `project_id` 规范化处理（如果是时间戳，尝试查找对应的UUID）
- 添加了详细的警告日志

## 修复文件清单

1. `backend/app/services/supabase_client.py`
   - 修改 `create_file_record` 方法，使用 `admin_client`

2. `backend/app/api/api_v1/endpoints/files.py`
   - 移除认证上下文设置代码
   - 移除 `tokens` 参数

3. `backend/app/services/supabase_file_service.py`
   - 添加UUID格式验证
   - 添加project_id规范化处理

## 测试建议

1. **测试文件上传功能**
   - 上传单个文件
   - 上传多个文件
   - 上传到项目
   - 上传到无项目（project_id为None）

2. **验证数据库记录**
   - 检查 `files` 表中的记录是否正确创建
   - 验证 `uploaded_by` 字段是否为正确的UUID格式
   - 验证 `project_id` 字段是否正确

3. **验证Storage上传**
   - 检查文件是否成功上传到Supabase Storage
   - 验证文件URL是否可访问

## 注意事项

1. **Service Key安全**：确保 `SUPABASE_SERVICE_KEY` 环境变量正确设置，并且不要泄露
2. **权限控制**：虽然使用Service Key绕过了RLS，但代码中仍然有权限检查（通过 `current_user`）
3. **错误处理**：如果 `admin_client` 不可用，会回退到 `client`，但可能仍然会遇到RLS问题

## 后续优化建议

1. 考虑添加更详细的错误处理和重试机制
2. 考虑添加文件上传的进度跟踪
3. 考虑添加文件上传的批量处理优化

