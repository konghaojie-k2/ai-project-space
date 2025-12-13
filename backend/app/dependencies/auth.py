#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
认证和权限依赖模块

提供FastAPI依赖注入函数，用于API端点的认证和权限验证。
"""

import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.supabase_auth import supabase_auth_service
from app.services.supabase_client import supabase_service
from app.core.config import settings
from app.dependencies.auth_bypass import (
    get_current_user_simple,
    get_optional_current_user_simple,
    bypass_all_permissions,
    bypass_permission_dependency,
    bypass_project_role_dependency,
    bypass_file_access_dependency,
    get_unlimited_projects_limit,
    get_unlimited_file_upload_limit,
    RequireBypassAdminPermission,
    RequireBypassManageUsersPermission,
    RequireBypassManageProjectsPermission,
    RequireBypassWritePermission,
    RequireBypassDeletePermission,
    RequireBypassProjectOwner,
    RequireBypassProjectAdmin,
    RequireBypassProjectMember,
    RequireBypassProjectViewer,
    RequireBypassFileAccess,
    RequireBypassProjectsLimit,
    RequireBypassFileUploadLimit
)

logger = logging.getLogger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer()

def should_bypass_permissions() -> bool:
    """
    检查是否应该绕过权限检查

    Returns:
        是否绕过权限检查
    """
    return settings.BYPASS_ALL_PERMISSIONS

def get_user_dependency(use_bypass: bool = False):
    """
    根据配置获取用户依赖

    Args:
        use_bypass: 是否使用绕过模式

    Returns:
        用户依赖函数
    """
    if should_bypass_permissions() or use_bypass:
        if settings.LOG_PERMISSION_BYPASS:
            logger.info("使用权限绕过模式的用户依赖")
        return get_current_user_simple
    return get_current_user

def get_optional_user_dependency(use_bypass: bool = False):
    """
    根据配置获取可选用户依赖

    Args:
        use_bypass: 是否使用绕过模式

    Returns:
        可选用户依赖函数
    """
    if should_bypass_permissions() or use_bypass:
        if settings.LOG_PERMISSION_BYPASS:
            logger.info("使用权限绕过模式的可选用户依赖")
        return get_optional_current_user_simple
    return get_optional_current_user

async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    从请求头中获取并验证访问令牌

    Args:
        credentials: HTTP Bearer凭据

    Returns:
        访问令牌字符串

    Raises:
        HTTPException: 令牌无效时抛出401错误
    """
    if not settings.use_supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务不可用"
        )

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌缺失",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token

async def get_current_user_tokens(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> tuple[str, Optional[str]]:
    """
    从请求头中获取访问令牌和刷新令牌

    Args:
        credentials: HTTP Bearer凭据

    Returns:
        (访问令牌字符串, 刷新令牌字符串或None)

    Raises:
        HTTPException: 令牌无效时抛出401错误
    """
    if not settings.use_supabase:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="认证服务不可用"
        )

    access_token = credentials.credentials
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="访问令牌缺失",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 尝试从数据库获取refresh token
    refresh_token = None
    try:
        user = await supabase_service.get_user_from_token(access_token)
        if user:
            # 这里可以获取refresh token，但当前简化处理
            refresh_token = ""
    except Exception as e:
        logger.warning(f"获取refresh token失败: {e}")

    return access_token, refresh_token

async def get_current_user(
    token: str = Depends(get_current_user_token)
) -> Dict[str, Any]:
    """
    获取当前已认证用户

    Args:
        token: 访问令牌

    Returns:
        用户信息字典

    Raises:
        HTTPException: 认证失败时抛出401错误
    """
    try:
        # 使用get_current_user方法获取完整用户信息（包含profile）
        user = await supabase_auth_service.get_current_user(token)

        if not user:
            logger.warning(f"Token验证失败: token={token[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 注意：Supabase的JWT token自带过期时间，不需要手动检查
        # is_token_expired方法检查的是login_time，但get_current_user返回的数据可能没有这个字段
        # 如果token无效，Supabase会直接返回None，所以这里不需要额外检查过期

        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取当前用户失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    获取当前活跃用户

    Args:
        current_user: 当前用户信息

    Returns:
        活跃用户信息字典

    Raises:
        HTTPException: 用户不活跃时抛出400错误
    """
    # 检查用户是否被禁用（根据实际业务逻辑调整）
    if current_user.get('disabled', False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )

    return current_user

async def get_current_superuser(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    获取当前超级管理员用户

    Args:
        current_user: 当前活跃用户

    Returns:
        超级管理员用户信息字典

    Raises:
        HTTPException: 用户不是超级管理员时抛出403错误
    """
    if not current_user.get('is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要超级管理员权限"
        )

    return current_user

async def get_optional_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    获取当前用户（可选认证）

    Args:
        authorization: Authorization请求头

    Returns:
        用户信息字典，未认证时返回None
    """
    if not settings.use_supabase or not authorization:
        return None

    try:
        # 提取Bearer token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            result = await supabase_auth_service.validate_token(token)
            return result
        return None
    except Exception:
        return None

def require_permission(permission: str):
    """
    权限要求装饰器工厂函数

    Args:
        permission: 需要的权限名称

    Returns:
        权限验证依赖函数
    """
    async def permission_dependency(
        current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """权限验证依赖函数"""

        # 权限绕过检查
        if should_bypass_permissions():
            if settings.LOG_PERMISSION_BYPASS:
                logger.info(f"权限绕过模式：跳过权限检查 - permission={permission}")
            return current_user

        # 正常权限检查
        has_permission = await supabase_auth_service.check_user_permission(
            current_user, permission
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要 {permission} 权限"
            )

        return current_user

    return permission_dependency

def require_project_role(required_role: str = 'member'):
    """
    项目角色要求装饰器工厂函数

    Args:
        required_role: 需要的最低项目角色

    Returns:
        项目角色验证依赖函数
    """
    async def project_role_dependency(
        project_id: str,
        current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """项目角色验证依赖函数"""

        # 权限绕过检查
        if should_bypass_permissions():
            if settings.LOG_PERMISSION_BYPASS:
                logger.info(f"权限绕过模式：跳过项目权限检查 - project_id={project_id}, required_role={required_role}")
            return current_user

        # 正常项目权限检查
        has_access = await supabase_auth_service.check_project_access(
            current_user, project_id, required_role
        )

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要项目 {required_role} 角色或更高权限"
            )

        return current_user

    return project_role_dependency

def require_file_access():
    """
    文件访问权限要求装饰器工厂函数

    Returns:
        文件访问权限验证依赖函数
    """
    async def file_access_dependency(
        file_id: str,
        current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        """文件访问权限验证依赖函数"""

        # 权限绕过检查
        if should_bypass_permissions():
            if settings.LOG_PERMISSION_BYPASS:
                logger.info(f"权限绕过模式：跳过文件访问权限检查 - file_id={file_id}")
            return current_user

        if not supabase_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="存储服务不可用"
            )

        # 获取文件信息 - 使用异步包装
        from app.services.supabase_client import run_supabase_query
        file_info = await run_supabase_query(
            lambda: supabase_service.client.table('files').select('*').eq(
                'id', file_id
            ).single().execute()
        )

        if not file_info.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )

        file_data = file_info.data
        access_level = file_data.get('access_level', 'all_users')
        uploaded_by = file_data.get('uploaded_by')
        project_id = file_data.get('project_id')

        user_id = current_user.get('id')
        is_superuser = current_user.get('is_superuser', False)

        # 检查文件访问权限
        has_access = False

        if access_level == 'all_users':
            has_access = True
        elif access_level == 'owner_only' and uploaded_by == user_id:
            has_access = True
        elif access_level == 'admins_only' and is_superuser:
            has_access = True
        elif access_level == 'project_members' and project_id:
            # 检查项目成员权限
            has_access = await supabase_auth_service.check_project_access(
                current_user, project_id, 'member'
            )
        elif uploaded_by == user_id:
            # 文件上传者总是有访问权限
            has_access = True

        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足，无法访问此文件"
            )

        return current_user

    return file_access_dependency

def get_user_projects_limit(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> int:
    """
    获取用户项目数量限制

    Args:
        current_user: 当前用户

    Returns:
        项目数量限制
    """
    # 权限绕过检查
    if should_bypass_permissions():
        if settings.LOG_PERMISSION_BYPASS:
            logger.info(f"权限绕过模式：用户 {current_user.get('id')} 获得无限制项目访问")
        return 1000  # 给予很高的限制

    if current_user.get('is_superuser', False):
        return float('inf')  # 超级管理员无限制

    user_role = current_user.get('role', 'user')

    role_limits = {
        'admin': 100,
        'manager': 50,
        'member': 20,
        'user': 10
    }

    return role_limits.get(user_role, 10)

def get_file_upload_limit(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> int:
    """
    获取用户文件上传大小限制

    Args:
        current_user: 当前用户

    Returns:
        文件大小限制（字节）
    """
    # 权限绕过检查
    if should_bypass_permissions():
        if settings.LOG_PERMISSION_BYPASS:
            logger.info(f"权限绕过模式：用户 {current_user.get('id')} 获得无限制文件上传")
        return settings.STORAGE_MAX_FILE_SIZE  # 使用系统最大限制

    if current_user.get('is_superuser', False):
        return settings.STORAGE_MAX_FILE_SIZE  # 超级管理员使用系统默认限制

    user_role = current_user.get('role', 'user')

    role_limits = {
        'admin': 200 * 1024 * 1024,  # 200MB
        'manager': 100 * 1024 * 1024,  # 100MB
        'member': 50 * 1024 * 1024,   # 50MB
        'user': 20 * 1024 * 1024      # 20MB
    }

    return min(role_limits.get(user_role, 20 * 1024 * 1024), settings.STORAGE_MAX_FILE_SIZE)

async def validate_user_project_access(
    user_id: str,
    project_id: str,
    required_role: str = 'member'
) -> bool:
    """
    验证用户项目访问权限（工具函数）

    Args:
        user_id: 用户ID
        project_id: 项目ID
        required_role: 需要的最低角色

    Returns:
        是否有访问权限
    """
    # 权限绕过检查
    if should_bypass_permissions():
        if settings.LOG_PERMISSION_BYPASS:
            logger.info(f"权限绕过模式：项目权限验证通过 - user_id={user_id}, project_id={project_id}, required_role={required_role}")
        return True

    if not supabase_service.is_available():
        logger.error("Supabase服务不可用，无法验证项目权限")
        return False

    try:
        # 检查是否为项目创建者 - 使用异步包装
        from app.services.supabase_client import run_supabase_query
        project = await run_supabase_query(
            lambda: supabase_service.client.table('projects').select('created_by').eq(
                'id', project_id
            ).single().execute()
        )

        if project.data and project.data.get('created_by') == user_id:
            return True

        # 检查项目成员权限 - 使用异步包装
        member = await run_supabase_query(
            lambda: supabase_service.client.table('project_members').select('role').eq(
                'project_id', project_id
            ).eq('user_id', user_id).single().execute()
        )

        if member.data:
            user_role = member.data.get('role')
            role_hierarchy = {'owner': 4, 'admin': 3, 'member': 2, 'viewer': 1}

            return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)

        return False

    except Exception as e:
        logger.error(f"验证用户项目权限失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

class RateLimiter:
    """简单的内存速率限制器"""

    def __init__(self):
        self.requests = {}

    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        检查是否允许请求

        Args:
            key: 限制键（通常是用户IP或ID）
            limit: 限制请求数
            window: 时间窗口（秒）

        Returns:
            是否允许请求
        """
        import time

        now = time.time()
        window_start = now - window

        if key not in self.requests:
            self.requests[key] = []

        # 清理过期的请求记录
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > window_start
        ]

        # 检查是否超过限制
        if len(self.requests[key]) >= limit:
            return False

        # 记录当前请求
        self.requests[key].append(now)
        return True

# 全局速率限制器实例
rate_limiter = RateLimiter()

def create_rate_limiter(limit: int, window: int):
    """
    创建速率限制依赖

    Args:
        limit: 限制请求数
        window: 时间窗口（秒）

    Returns:
        速率限制依赖函数
    """
    async def rate_limit_dependency(
        request: Request,
        current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
    ):
        """速率限制依赖函数"""
        # 使用用户ID或IP作为限制键
        if current_user:
            key = f"user:{current_user.get('id')}"
        else:
            key = f"ip:{request.client.host}"

        if not rate_limiter.is_allowed(key, limit, window):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请稍后再试。限制: {limit}次/{window}秒"
            )

    return rate_limit_dependency

# 预定义的权限依赖
RequireAdminPermission = require_permission('admin_access')
RequireManageUsersPermission = require_permission('manage_users')
RequireManageProjectsPermission = require_permission('manage_projects')
RequireWritePermission = require_permission('write')
RequireDeletePermission = require_permission('delete')

# 预定义的项目角色依赖
RequireProjectOwner = require_project_role('owner')
RequireProjectAdmin = require_project_role('admin')
RequireProjectMember = require_project_role('member')
RequireProjectViewer = require_project_role('viewer')

# 预定义的速率限制依赖
RateLimitAuth = create_rate_limiter(5, 60)  # 认证相关：5次/分钟
RateLimitUpload = create_rate_limiter(10, 60)  # 文件上传：10次/分钟
RateLimitSearch = create_rate_limiter(30, 60)  # 搜索功能：30次/分钟