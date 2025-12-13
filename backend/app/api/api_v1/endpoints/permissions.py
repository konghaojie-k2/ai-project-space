#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
权限管理API端点
提供权限检查、缓存管理和批量操作功能
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from datetime import datetime
import logging

from app.services.supabase_client import supabase_service
from app.services.permission_cache import permission_cache
from app.dependencies.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ========================================
# 请求/响应模型
# ========================================

class PermissionCheckRequest(BaseModel):
    """权限检查请求"""
    resource_type: str = Field(..., description="资源类型 (project, file, system)")
    resource_id: str = Field(..., description="资源ID")
    permission: str = Field(..., description="所需权限")


class BatchPermissionCheckRequest(BaseModel):
    """批量权限检查请求"""
    user_id: Optional[str] = Field(None, description="用户ID（如果不提供则使用当前用户）")
    checks: List[PermissionCheckRequest] = Field(..., description="权限检查列表")


class PermissionCheckResponse(BaseModel):
    """权限检查响应"""
    granted: bool = Field(..., description="是否有权限")
    reason: Optional[str] = Field(None, description="原因说明")
    cache_hit: bool = Field(False, description="是否命中缓存")


class BatchPermissionCheckResponse(BaseModel):
    """批量权限检查响应"""
    results: Dict[str, PermissionCheckResponse] = Field(..., description="检查结果")
    total_count: int = Field(..., description="总检查数量")
    granted_count: int = Field(..., description="有权限的数量")
    cache_hit_rate: float = Field(..., description="缓存命中率")


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    local_hits: int = Field(..., description="本地缓存命中次数")
    redis_hits: int = Field(..., description="Redis缓存命中次数")
    misses: int = Field(..., description="缓存未命中次数")
    hit_rate: float = Field(..., description="命中率")
    local_cache_size: int = Field(..., description="本地缓存大小")
    redis_available: bool = Field(..., description="Redis是否可用")


class WarmUpCacheRequest(BaseModel):
    """缓存预热请求"""
    user_id: Optional[str] = Field(None, description="用户ID（如果不提供则使用当前用户）")
    project_ids: Optional[List[str]] = Field(None, description="项目ID列表")


# ========================================
# 权限检查端点
# ========================================

@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(
    request: PermissionCheckRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    检查用户权限

    Args:
        request: 权限检查请求
        current_user: 当前认证用户

    Returns:
        权限检查结果
    """
    try:
        user_id = current_user.get('id')
        resource_type = request.resource_type
        resource_id = request.resource_id
        permission = request.permission

        # 记录开始时间
        start_time = datetime.utcnow()

        # 根据资源类型进行权限检查
        if resource_type == 'project':
            # 使用优化的权限检查
            granted = await supabase_service.check_project_permission_optimized(
                user_id, resource_id, permission
            )
            reason = f"项目权限检查: {permission}" if granted else "权限不足"
        elif resource_type == 'system':
            # 系统权限检查
            is_superuser = current_user.get('is_superuser', False)
            system_role = current_user.get('system_role', 'user')

            # 系统权限映射
            system_permissions = {
                'super_admin': ['read', 'write', 'delete', 'manage_users', 'manage_projects', 'admin_access'],
                'admin': ['read', 'write', 'delete', 'manage_users', 'manage_projects'],
                'manager': ['read', 'write', 'delete', 'manage_projects'],
                'member': ['read', 'write'],
                'user': ['read']
            }

            user_permissions = system_permissions.get(system_role, ['read'])
            if is_superuser:
                user_permissions = system_permissions['super_admin']

            granted = permission in user_permissions
            reason = f"系统权限检查: {permission}" if granted else "权限不足"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的资源类型: {resource_type}"
            )

        # 计算响应时间
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # 记录性能日志
        if response_time > 100:  # 超过100ms记录警告
            logger.warning(
                f"慢权限检查: {response_time:.2f}ms - "
                f"User: {user_id}, Resource: {resource_type}:{resource_id}, "
                f"Permission: {permission}"
            )

        return PermissionCheckResponse(
            granted=granted,
            reason=reason
        )

    except Exception as e:
        logger.error(f"权限检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="权限检查失败"
        )


@router.post("/batch-check", response_model=BatchPermissionCheckResponse)
async def batch_check_permissions(
    request: BatchPermissionCheckRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    批量检查权限

    优化点：
    1. 减少网络往返次数
    2. 提高缓存命中率
    3. 并行处理权限检查

    Args:
        request: 批量权限检查请求
        current_user: 当前认证用户

    Returns:
        批量权限检查结果
    """
    try:
        # 确定用户ID
        user_id = request.user_id or current_user.get('id')
        checks = request.checks

        if not checks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="权限检查列表不能为空"
            )

        # 准备权限请求数据
        permission_requests = []
        result_keys = []

        for i, check in enumerate(checks):
            if check.resource_type == 'project':
                permission_requests.append({
                    'user_id': user_id,
                    'project_id': check.resource_id,
                    'permission': check.permission
                })
                result_keys.append(f"{i}")

        # 执行批量权限检查
        if permission_requests:
            batch_results = await supabase_service.batch_check_permissions(permission_requests)
        else:
            batch_results = {}

        # 组装结果
        results = {}
        granted_count = 0
        cache_hit_count = 0

        for i, check in enumerate(checks):
            key = str(i)
            resource_key = f"{user_id}:{check.resource_id}:{check.permission}"

            if check.resource_type == 'project':
                granted = batch_results.get(resource_key, False)
                reason = f"项目权限检查: {check.permission}" if granted else "权限不足"
            else:
                # 其他资源类型的权限检查
                granted = False
                reason = "暂不支持该资源类型的批量检查"

            results[key] = PermissionCheckResponse(
                granted=granted,
                reason=reason
            )

            if granted:
                granted_count += 1

        # 计算缓存命中率
        cache_hit_rate = 0.0
        if results:
            cache_hits = sum(1 for r in results.values() if r.cache_hit)
            cache_hit_rate = cache_hits / len(results)

        return BatchPermissionCheckResponse(
            results=results,
            total_count=len(checks),
            granted_count=granted_count,
            cache_hit_rate=cache_hit_rate
        )

    except Exception as e:
        logger.error(f"批量权限检查失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量权限检查失败"
        )


# ========================================
# 缓存管理端点
# ========================================

@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """
    获取权限缓存统计信息

    Args:
        current_user: 当前认证用户

    Returns:
        缓存统计信息
    """
    try:
        stats = await permission_cache.get_cache_stats()

        return CacheStatsResponse(
            local_hits=stats['local_hits'],
            redis_hits=stats['redis_hits'],
            misses=stats['misses'],
            hit_rate=stats['hit_rate'],
            local_cache_size=stats['local_cache_size'],
            redis_available=stats['redis_available']
        )

    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取缓存统计失败"
        )


@router.post("/cache/invalidate")
async def invalidate_cache(
    pattern: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    清除权限缓存

    Args:
        pattern: 清除模式（可选）
        user_id: 用户ID（可选）
        current_user: 当前认证用户

    Returns:
        清除结果
    """
    try:
        if user_id:
            # 清除特定用户的缓存
            success = await supabase_service.invalidate_user_project_cache(user_id)
            deleted_count = 1 if success else 0
        elif pattern:
            # 按模式清除缓存
            deleted_count = await permission_cache.invalidate_pattern(pattern)
        else:
            # 清除所有权限缓存
            deleted_count = await permission_cache.invalidate_pattern("permission")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"已清除 {deleted_count} 项缓存"
        }

    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清除缓存失败"
        )


@router.post("/cache/warm-up")
async def warm_up_cache(
    request: WarmUpCacheRequest,
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    预热权限缓存

    Args:
        request: 缓存预热请求
        current_user: 当前认证用户

    Returns:
        预热结果
    """
    try:
        user_id = request.user_id or current_user.get('id')
        project_ids = request.project_ids

        if not project_ids:
            # 获取用户所有项目并预热
            projects = await supabase_service.get_user_projects(user_id)
            project_ids = [project['id'] for project in projects]

        # 预热项目权限
        warmed_count = 0
        for project_id in project_ids:
            try:
                # 检查各项权限以预热缓存
                permissions = ['read', 'write', 'delete', 'manage_members', 'manage_settings']
                for permission in permissions:
                    await supabase_service.check_project_permission_optimized(
                        user_id, project_id, permission
                    )
                warmed_count += 1
            except Exception as e:
                logger.warning(f"预热项目权限失败 {project_id}: {e}")

        return {
            "success": True,
            "warmed_count": warmed_count,
            "total_projects": len(project_ids),
            "message": f"已预热 {warmed_count} 个项目的权限缓存"
        }

    except Exception as e:
        logger.error(f"缓存预热失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缓存预热失败"
        )


# ========================================
# 性能监控端点
# ========================================

@router.get("/performance")
async def get_permission_performance(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """
    获取权限系统性能信息

    Args:
        current_user: 当前认证用户

    Returns:
        性能信息
    """
    try:
        # 获取缓存统计
        cache_stats = await permission_cache.get_cache_stats()

        # 获取系统信息
        import psutil
        import os

        process = psutil.Process(os.getpid())
        system_stats = {
            'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(),
        }

        return {
            "cache_performance": {
                'hit_rate': cache_stats['hit_rate'],
                'local_cache_size': cache_stats['local_cache_size'],
                'redis_available': cache_stats['redis_available'],
                'total_requests': cache_stats['total_requests']
            },
            "system_performance": system_stats,
            "recommendations": _generate_performance_recommendations(cache_stats, system_stats)
        }

    except Exception as e:
        logger.error(f"获取性能信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取性能信息失败"
        )


def _generate_performance_recommendations(cache_stats: Dict, system_stats: Dict) -> List[str]:
    """生成性能优化建议"""
    recommendations = []

    # 缓存命中率建议
    if cache_stats['hit_rate'] < 0.5:
        recommendations.append("缓存命中率较低，建议增加缓存TTL或预热缓存")
    elif cache_stats['hit_rate'] > 0.9:
        recommendations.append("缓存性能良好")

    # 本地缓存大小建议
    if cache_stats['local_cache_size'] > cache_stats['local_cache_size_limit'] * 0.9:
        recommendations.append("本地缓存接近上限，建议清理过期缓存")

    # Redis可用性建议
    if not cache_stats['redis_available']:
        recommendations.append("Redis不可用，建议检查Redis服务状态")

    # 内存使用建议
    if system_stats['memory_usage_mb'] > 500:
        recommendations.append("内存使用较高，建议优化缓存策略")

    return recommendations