#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目信息查询工具
获取项目基本信息、成员、阶段等
"""

from typing import Dict, Any, Optional
from langchain_core.tools import tool
from loguru import logger

# 导入Supabase服务
from ...services.supabase_client import supabase_service

@tool
async def get_project_info_tool(
    project_id: str,
    user_id: str,
    is_admin: bool = False
) -> Dict[str, Any]:
    """
    获取项目基本信息

    Args:
        project_id: 项目ID
        user_id: 用户ID
        is_admin: 是否管理员

    Returns:
        项目信息字典
    """
    try:
        if not project_id:
            return {
                'error': '项目ID不能为空',
                'project_name': None,
                'stage': None,
                'description': None
            }

        # 从Supabase获取项目信息
        project_data = await supabase_service.get_project(project_id, user_id, is_admin)

        if not project_data:
            return {
                'error': '项目不存在或无权限访问',
                'project_name': None,
                'stage': None,
                'description': None
            }

        logger.info(f"📋 获取项目信息: {project_data.get('name')} (ID: {project_id})")

        return {
            'project_id': project_id,
            'project_name': project_data.get('name'),
            'stage': project_data.get('stage'),
            'description': project_data.get('description'),
            'created_at': project_data.get('created_at'),
            'updated_at': project_data.get('updated_at'),
            'status': 'success'
        }

    except Exception as e:
        logger.error(f"获取项目信息失败: {e}")
        return {
            'error': f'获取项目信息失败: {str(e)}',
            'project_name': None,
            'stage': None,
            'description': None
        }

@tool
async def get_project_members_tool(
    project_id: str,
    user_id: str,
    is_admin: bool = False
) -> Dict[str, Any]:
    """
    获取项目成员信息

    Args:
        project_id: 项目ID
        user_id: 用户ID
        is_admin: 是否管理员

    Returns:
        项目成员列表
    """
    try:
        # 验证用户是否有权限访问项目
        project_info = await get_project_info_tool(project_id, user_id, is_admin)
        if project_info.get('error'):
            return project_info

        # 获取项目成员
        members = await supabase_service.get_project_members(project_id)

        logger.info(f"👥 获取项目成员: {project_id}, 成员数: {len(members) if members else 0}")

        return {
            'project_id': project_id,
            'members': members or [],
            'member_count': len(members) if members else 0,
            'status': 'success'
        }

    except Exception as e:
        logger.error(f"获取项目成员失败: {e}")
        return {
            'error': f'获取项目成员失败: {str(e)}',
            'members': [],
            'member_count': 0
        }

@tool
async def get_project_files_tool(
    project_id: str,
    user_id: str,
    is_admin: bool = False,
    limit: int = 20
) -> Dict[str, Any]:
    """
    获取项目文件列表

    Args:
        project_id: 项目ID
        user_id: 用户ID
        is_admin: 是否管理员
        limit: 返回文件数量限制

    Returns:
        项目文件列表
    """
    try:
        # 验证用户是否有权限访问项目
        project_info = await get_project_info_tool(project_id, user_id, is_admin)
        if project_info.get('error'):
            return project_info

        # 获取项目文件
        files = await supabase_service.get_project_files(project_id, user_id, is_admin, limit)

        logger.info(f"📁 获取项目文件: {project_id}, 文件数: {len(files) if files else 0}")

        return {
            'project_id': project_id,
            'files': files or [],
            'file_count': len(files) if files else 0,
            'status': 'success'
        }

    except Exception as e:
        logger.error(f"获取项目文件失败: {e}")
        return {
            'error': f'获取项目文件失败: {str(e)}',
            'files': [],
            'file_count': 0
        }

@tool
async def get_project_stats_tool(
    project_id: str,
    user_id: str,
    is_admin: bool = False
) -> Dict[str, Any]:
    """
    获取项目统计信息

    Args:
        project_id: 项目ID
        user_id: 用户ID
        is_admin: 是否管理员

    Returns:
        项目统计数据
    """
    try:
        # 验证用户是否有权限访问项目
        project_info = await get_project_info_tool(project_id, user_id, is_admin)
        if project_info.get('error'):
            return project_info

        # 获取各项统计数据
        members_result = await get_project_members_tool(project_id, user_id, is_admin)
        files_result = await get_project_files_tool(project_id, user_id, is_admin)

        # 计算项目进度（基于阶段）
        stage_order = ['售前', '业务调研', '数据理解', '数据探索', '工程开发', '实施部署']
        current_stage = project_info.get('stage', '')
        stage_index = stage_order.index(current_stage) if current_stage in stage_order else 0
        progress = (stage_index + 1) / len(stage_order) * 100 if stage_order else 0

        stats = {
            'project_id': project_id,
            'project_name': project_info.get('project_name'),
            'stage': project_info.get('stage'),
            'progress_percentage': round(progress, 1),
            'member_count': members_result.get('member_count', 0),
            'file_count': files_result.get('file_count', 0),
            'created_at': project_info.get('created_at'),
            'updated_at': project_info.get('updated_at'),
            'status': 'success'
        }

        logger.info(f"📊 项目统计: {stats['project_name']} - 进度: {stats['progress_percentage']}%")

        return stats

    except Exception as e:
        logger.error(f"获取项目统计失败: {e}")
        return {
            'error': f'获取项目统计失败: {str(e)}',
            'project_id': project_id,
            'status': 'error'
        }