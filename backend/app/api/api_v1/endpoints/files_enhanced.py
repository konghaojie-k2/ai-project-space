#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强文件管理API端点
基于Supabase权限系统的文件管理
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from loguru import logger

from app.services.supabase_file_service import supabase_file_service
from app.dependencies.auth import get_current_user
from app.schemas.file import (
    FileResponse, FileCreate, FileUpdate, FileSearchRequest,
    FileShareRequest
)
from app.schemas.auth import MessageResponse

router = APIRouter()


@router.post("/upload", response_model=FileResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    access_level: str = Form("all_users"),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    上传文件

    - **file**: 上传的文件
    - **project_id**: 项目ID（可选）
    - **access_level**: 访问级别
    - **description**: 文件描述
    - **tags**: 文件标签
    """
    try:
        # 检查服务可用性
        if not supabase_file_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="文件服务不可用"
            )

        # 验证访问级别
        valid_access_levels = ["all_users", "project_members", "admins_only", "owner_only"]
        if access_level not in valid_access_levels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的访问级别，有效值: {valid_access_levels}"
            )

        # 验证项目权限（如果指定了项目）
        if project_id and access_level in ["project_members", "admins_only", "owner_only"]:
            # 这里可以添加项目权限检查逻辑
            pass

        # 读取文件内容
        file_content = await file.read()
        filename = file.filename

        # 上传文件
        file_record = await supabase_file_service.upload_file(
            file_path=f"uploads/{current_user.get('username', 'user')}",
            file_content=file_content,
            filename=filename,
            user_id=current_user.get('id'),
            project_id=project_id,
            access_level=access_level,
            description=description,
            tags=tags.split(',') if tags else None
        )

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件上传失败"
            )

        logger.info(f"用户 {current_user.get('username')} 上传文件: {filename}")
        return FileResponse(**file_record)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件上传过程中发生错误"
        )


@router.get("/", response_model=List[FileResponse], summary="获取文件列表")
async def list_files(
    project_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户可访问的文件列表

    - **project_id**: 项目ID过滤
    - **limit**: 返回数量限制
    """
    try:
        files = await supabase_file_service.get_user_files(
            user_id=current_user.get('id'),
            project_id=project_id,
            limit=limit
        )

        logger.info(f"用户 {current_user.get('username')} 获取文件列表: {len(files)} 个文件")
        return files

    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件列表失败"
        )


@router.get("/{file_id}", response_model=FileResponse, summary="获取文件信息")
async def get_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    获取文件详细信息

    - **file_id**: 文件ID
    """
    try:
        file_info = await supabase_file_service.get_file_info(file_id)

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )

        return FileResponse(**file_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件信息失败 {file_id}: {e}")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取文件信息失败"
        )


@router.put("/{file_id}/access-level", response_model=MessageResponse, summary="更新文件访问级别")
async def update_file_access_level(
    file_id: str,
    access_level: str,
    current_user: dict = Depends(get_current_user)
):
    """
    更新文件访问级别

    - **file_id**: 文件ID
    - **access_level**: 新的访问级别
    """
    try:
        # 验证访问级别
        valid_access_levels = ["all_users", "project_members", "admins_only", "owner_only"]
        if access_level not in valid_access_levels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的访问级别，有效值: {valid_access_levels}"
            )

        success = await supabase_file_service.update_file_access_level(
            file_id=file_id,
            access_level=access_level,
            user_id=current_user.get('id')
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足或文件不存在"
            )

        logger.info(f"用户 {current_user.get('username')} 更新文件 {file_id} 访问级别: {access_level}")
        return MessageResponse(message="文件访问级别更新成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文件访问级别失败 {file_id}: {e}")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新文件访问级别失败"
        )


@router.delete("/{file_id}", response_model=MessageResponse, summary="删除文件")
async def delete_file(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    删除文件

    - **file_id**: 文件ID
    """
    try:
        success = await supabase_file_service.delete_file(
            file_id=file_id,
            user_id=current_user.get('id')
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足或文件不存在"
            )

        logger.info(f"用户 {current_user.get('username')} 删除文件: {file_id}")
        return MessageResponse(message="文件删除成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败 {file_id}: {e}")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除文件失败"
        )


@router.post("/{file_id}/share", response_model=MessageResponse, summary="分享文件")
async def share_file(
    file_id: str,
    share_request: FileShareRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    分享文件给其他用户

    - **file_id**: 文件ID
    - **share_request**: 分享请求
    """
    try:
        # 验证文件存在和权限
        file_info = await supabase_file_service.get_file_info(file_id)
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在"
            )

        # 检查分享权限（只有文件所有者可以分享）
        if file_info.get('uploaded_by') != current_user.get('id'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有文件上传者可以分享文件"
            )

        # 查找目标用户
        from app.services.supabase_client import supabase_service
        target_user_response = supabase_service.client.table('profiles').select(
            'id', 'username', 'full_name', 'email'
        ).eq('email', share_request.user_email).single().execute()

        if not target_user_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标用户不存在"
            )

        target_user_id = target_user_response.data['id']

        # 创建文件分享
        success = await supabase_file_service.share_file(
            file_id=file_id,
            share_with_user_id=target_user_id,
            permissions={
                'can_view': share_request.can_view,
                'can_download': share_request.can_download,
                'can_edit': share_request.can_edit
            },
            expires_at=share_request.expires_at
        )

        if not success:
            raise HTTPException(
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="文件分享失败"
            )

        logger.info(f"用户 {current_user.get('username')} 分享文件 {file_id} 给 {share_request.user_email}")
        return MessageResponse(message="文件分享成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件分享失败 {file_id}: {e}")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件分享失败"
        )


@router.get("/{file_id}/shares", summary="获取文件分享记录")
async def get_file_shares(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    获取文件分享记录

    - **file_id**: 文件ID
    """
    try:
        shares = await supabase_file_service.get_file_shares(file_id)
        return shares

    except Exception as e:
        logger.error(f"获取文件分享记录失败 {file_id}: {e}")
        return []


@router.post("/search", response_model=List[FileResponse], summary="搜索文件")
async def search_files(
    search_request: FileSearchRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    搜索文件

    - **search_request**: 搜索请求
    """
    try:
        files = await supabase_file_service.search_files(
            query=search_request.query,
            user_id=current_user.get('id'),
            project_id=search_request.project_id,
            file_type=search_request.file_type,
            limit=search_request.limit or 20
        )

        return files

    except Exception as e:
        logger.error(f"搜索文件失败: {e}")
        return []


@router.get("/stats", summary="获取文件统计信息")
async def get_file_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    获取用户文件统计信息
    """
    try:
        stats = await supabase_file_service.get_file_stats(current_user.get('id'))
        return stats

    except Exception as e:
        logger.error(f"获取文件统计失败: {e}")
        return {
            "total_files": 0,
            "total_size": 0,
            "by_type": {},
            "by_project": {}
        }


@router.put("/{file_id}/metadata", response_model=MessageResponse, summary="更新文件元数据")
async def update_file_metadata(
    file_id: str,
    metadata_updates: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    更新文件元数据

    - **file_id**: 文件ID
    - **metadata_updates**: 元数据更新
    """
    try:
        success = await supabase_file_service.update_file_metadata(
            file_id=file_id,
            metadata_updates=metadata_updates,
            user_id=current_user.get('id')
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足或文件不存在"
            )

        logger.info(f"用户 {current_user.get('username')} 更新文件 {file_id} 元数据")
        return MessageResponse(message="文件元数据更新成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新文件元数据失败 {file_id}: {e}")
        raise HTTPException(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新文件元数据失败"
        )