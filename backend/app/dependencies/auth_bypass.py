#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
权限绕过依赖模块

用于性能优化时暂时绕过复杂的权限检查，保留基础认证功能。
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.supabase_auth import supabase_auth_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer认证方案
security = HTTPBearer()

async def get_current_user_simple(
    credentials: HTTPAuthorizationCredentials
) -> Dict[str, Any]:
    """
    简化版用户获取 - 仅验证JWT有效性，不进行复杂权限查询

    Args:
        credentials: HTTP Bearer凭据

    Returns:
        用户信息字典（仅包含基础信息，无权限详情）

    Raises:
        HTTPException: 认证失败时抛出401错误
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

    try:
        # 仅验证JWT令牌有效性，获取基础用户信息
        user = await supabase_auth_service.get_current_user(token)

        if not user:
            if settings.LOG_PERMISSION_BYPASS:
                logger.warning(f"权限绕过模式：Token验证失败: token={token[:20]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的访问令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 权限绕过模式：记录日志但不查询权限
        if settings.LOG_PERMISSION_BYPASS:
            logger.info(f"权限绕过模式：用户 {user.get('id')} 认证成功，跳过权限检查")

        # 返回简化的用户对象，不包含复杂的权限查询结果
        simple_user = {
            'id': user.get('id'),
            'email': user.get('email'),
            'full_name': user.get('user_metadata', {}).get('full_name', ''),
            'avatar_url': user.get('user_metadata', {}).get('avatar_url', ''),
            'is_superuser': user.get('is_superuser', False),
            'bypass_mode': True  # 标记为权限绕过模式
        }

        return simple_user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"权限绕过模式下获取用户失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_optional_current_user_simple(
    authorization: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    简化版可选用户获取 - 仅验证JWT有效性

    Args:
        authorization: Authorization请求头

    Returns:
        用户信息字典或None
    """
    if not settings.use_supabase or not authorization:
        return None

    try:
        # 提取Bearer token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
            user = await supabase_auth_service.get_current_user(token)

            if not user:
                return None

            # 权限绕过模式：返回简化用户信息
            if settings.LOG_PERMISSION_BYPASS:
                logger.info(f"权限绕过模式：可选认证用户 {user.get('id')} 认证成功")

            return {
                'id': user.get('id'),
                'email': user.get('email'),
                'full_name': user.get('user_metadata', {}).get('full_name', ''),
                'avatar_url': user.get('user_metadata', {}).get('avatar_url', ''),
                'is_superuser': user.get('is_superuser', False),
                'bypass_mode': True
            }

        return None
    except Exception:
        return None

async def bypass_all_permissions(
    permission: str = None,
    project_id: str = None,
    file_id: str = None
) -> bool:
    """
    统一权限绕过函数

    Args:
        permission: 权限名称（不使用，仅接口兼容）
        project_id: 项目ID（不使用，仅接口兼容）
        file_id: 文件ID（不使用，仅接口兼容）

    Returns:
        权限检查结果（总是返回True）
    """
    if settings.BYPASS_ALL_PERMISSIONS:
        if settings.LOG_PERMISSION_BYPASS:
            logger.info(f"权限绕过模式：跳过权限检查 - permission={permission}, project_id={project_id}, file_id={file_id}")
        return True

    # 如果未启用权限绕过，返回False（需要走正常权限检查）
    return False

# 权限绕过模式的依赖函数
async def bypass_permission_dependency(
    current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """
    权限绕过依赖函数

    Args:
        current_user: 当前用户信息

    Returns:
        用户信息（无修改，直接通过）
    """
    if settings.LOG_PERMISSION_BYPASS:
        logger.info(f"权限绕过模式：权限检查通过 - user_id={current_user.get('id')}")
    return current_user

async def bypass_project_role_dependency(
    project_id: str,
    current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """
    项目角色权限绕过依赖函数

    Args:
        project_id: 项目ID（不使用）
        current_user: 当前用户信息

    Returns:
        用户信息（无修改，直接通过）
    """
    if settings.LOG_PERMISSION_BYPASS:
        logger.info(f"权限绕过模式：项目权限检查通过 - project_id={project_id}, user_id={current_user.get('id')}")
    return current_user

async def bypass_file_access_dependency(
    file_id: str,
    current_user: Dict[str, Any]
) -> Dict[str, Any]:
    """
    文件访问权限绕过依赖函数

    Args:
        file_id: 文件ID（不使用）
        current_user: 当前用户信息

    Returns:
        用户信息（无修改，直接通过）
    """
    if settings.LOG_PERMISSION_BYPASS:
        logger.info(f"权限绕过模式：文件访问权限检查通过 - file_id={file_id}, user_id={current_user.get('id')}")
    return current_user

# 获取简化的用户限制（权限绕过模式下给予更高限制）
async def get_unlimited_projects_limit(
    current_user: Dict[str, Any]
) -> int:
    """
    获取无限制的项目数量（权限绕过模式）

    Args:
        current_user: 当前用户信息

    Returns:
        项目数量限制（权限绕过模式下给予高限制）
    """
    if settings.BYPASS_ALL_PERMISSIONS:
        if settings.LOG_PERMISSION_BYPASS:
            logger.info(f"权限绕过模式：用户 {current_user.get('id')} 获得无限制项目访问")
        return 1000  # 给予很高的限制

    # 如果未启用权限绕过，调用原有逻辑
    # 这里需要导入原函数，为避免循环导入，直接返回一个合理值
    return 100

async def get_unlimited_file_upload_limit(
    current_user: Dict[str, Any]
) -> int:
    """
    获取无限制的文件上传大小（权限绕过模式）

    Args:
        current_user: 当前用户信息

    Returns:
        文件上传大小限制（权限绕过模式下给予高限制）
    """
    if settings.BYPASS_ALL_PERMISSIONS:
        if settings.LOG_PERMISSION_BYPASS:
            logger.info(f"权限绕过模式：用户 {current_user.get('id')} 获得无限制文件上传")
        return settings.STORAGE_MAX_FILE_SIZE  # 使用系统最大限制

    # 如果未启用权限绕过，调用原有逻辑
    # 这里为避免循环导入，直接返回一个合理值
    return 50 * 1024 * 1024  # 50MB

# 权限绕过模式的简化依赖（替换原有复杂权限检查）
def create_bypass_dependency():
    """
    创建权限绕过依赖

    Returns:
        权限绕过依赖函数
    """
    async def bypass_dependency(current_user: Dict[str, Any] = None) -> bool:
        """权限绕过依赖函数"""
        return settings.BYPASS_ALL_PERMISSIONS

    return bypass_dependency

# 用于替换原有权限依赖的简化版本
RequireBypassAdminPermission = bypass_permission_dependency
RequireBypassManageUsersPermission = bypass_permission_dependency
RequireBypassManageProjectsPermission = bypass_permission_dependency
RequireBypassWritePermission = bypass_permission_dependency
RequireBypassDeletePermission = bypass_permission_dependency

RequireBypassProjectOwner = bypass_project_role_dependency
RequireBypassProjectAdmin = bypass_project_role_dependency
RequireBypassProjectMember = bypass_project_role_dependency
RequireBypassProjectViewer = bypass_project_role_dependency

RequireBypassFileAccess = bypass_file_access_dependency
RequireBypassProjectsLimit = get_unlimited_projects_limit
RequireBypassFileUploadLimit = get_unlimited_file_upload_limit