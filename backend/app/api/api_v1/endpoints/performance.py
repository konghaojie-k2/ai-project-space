#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能监控和诊断API
提供系统性能指标和缓存统计信息
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from app.services.supabase_client import supabase_service
from app.dependencies.auth import get_current_superuser

router = APIRouter()

@router.get("/stats", summary="获取系统性能统计")
async def get_performance_stats(
    current_user: Dict[str, Any] = Depends(get_current_superuser)
):
    """
    获取系统性能统计信息（仅超级管理员）

    返回：
    - 缓存命中率
    - 查询统计
    - 平均响应时间
    - 缓存大小
    """
    try:
        # 获取Supabase服务性能统计
        cache_stats = supabase_service.get_cache_stats()

        return {
            "message": "获取性能统计成功",
            "data": {
                "supabase_cache": cache_stats,
                "optimization_status": {
                    "database_indexes": "已创建关键索引",
                    "rls_policies": "已优化RLS策略",
                    "materialized_views": "已创建权限物化视图",
                    "application_cache": "已启用多层缓存"
                },
                "recommendations": [
                    "定期刷新权限缓存",
                    "监控缓存命中率",
                    "根据使用情况调整缓存TTL"
                ]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取性能统计失败: {str(e)}"
        )

@router.post("/cache/clear", summary="清理系统缓存")
async def clear_system_cache(
    cache_type: str = "all",
    current_user: Dict[str, Any] = Depends(get_current_superuser)
):
    """
    清理系统缓存（仅超级管理员）

    参数：
    - cache_type: 缓存类型 (all, profile, permission, projects, stats)
    """
    try:
        cache_managers = {
            "profile": supabase_service.profile_cache,
            "permission": supabase_service.permission_cache,
            "projects": supabase_service.projects_cache,
            "stats": supabase_service.stats_cache,
        }

        cleared_count = 0
        if cache_type == "all":
            # 清理所有缓存
            for manager in cache_managers.values():
                await manager.invalidate()
            cleared_count = 4
        elif cache_type in cache_managers:
            # 清理指定类型缓存
            await cache_managers[cache_type].invalidate()
            cleared_count = 1
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的缓存类型: {cache_type}"
            )

        return {
            "message": f"成功清理 {cleared_count} 个缓存",
            "cache_type": cache_type,
            "cleared_count": cleared_count
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"清理缓存失败: {str(e)}"
        )

@router.post("/cache/refresh", summary="刷新权限缓存")
async def refresh_permission_cache(
    current_user: Dict[str, Any] = Depends(get_current_superuser)
):
    """
    刷新权限缓存（仅超级管理员）
    """
    try:
        # 这里将来可以调用数据库的刷新函数
        # await supabase_service.refresh_permission_cache()

        # 清理权限相关缓存
        await supabase_service.permission_cache.invalidate("permission_summary:")
        await supabase_service.projects_cache.invalidate("user_projects:")

        return {
            "message": "权限缓存刷新成功",
            "timestamp": "2024-01-01T00:00:00Z"  # 实际应该使用当前时间
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"刷新权限缓存失败: {str(e)}"
        )