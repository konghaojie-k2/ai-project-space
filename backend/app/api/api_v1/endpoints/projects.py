"""
项目管理API端点
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel
from datetime import datetime
import uuid

# 导入Supabase服务
from app.services.supabase_client import supabase_service
from app.dependencies.auth import (
    get_current_user, get_current_superuser,
    RequireManageProjectsPermission
)


router = APIRouter()



# Pydantic模型
class ProjectResponse(BaseModel):
    """项目响应模型"""
    id: str
    name: str
    description: Optional[str] = None
    status: str
    stage: str
    is_public: bool = False
    allow_file_upload: bool = True
    allow_ai_chat: bool = True
    created_by: str
    created_at: str
    updated_at: str


class ProjectCreate(BaseModel):
    """创建项目请求模型"""
    name: str
    description: Optional[str] = None
    status: str = "active"
    stage: str = "售前"
    is_public: bool = False
    allow_file_upload: bool = True
    allow_ai_chat: bool = True


class ProjectUpdate(BaseModel):
    """更新项目请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    is_public: Optional[bool] = None
    allow_file_upload: Optional[bool] = None
    allow_ai_chat: Optional[bool] = None


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取用户可访问的项目列表"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 获取用户可访问的项目
        projects = await supabase_service.get_user_accessible_projects_enhanced(user_id)

        # 应用过滤条件
        if search:
            projects = [p for p in projects if search.lower() in p.get('name', '').lower() or
                       search.lower() in p.get('description', '').lower()]

        if status_filter:
            projects = [p for p in projects if p.get('status') == status_filter]

        # 应用分页
        projects = projects[skip:skip + limit]

        # 转换为响应格式
        return [
            ProjectResponse(
                id=p.get('id', ''),
                name=p.get('name', ''),
                description=p.get('description'),
                status=p.get('status', 'active'),
                stage=p.get('stage', '售前'),
                is_public=p.get('is_public', False),
                allow_file_upload=p.get('allow_file_upload', True),
                allow_ai_chat=p.get('allow_ai_chat', True),
                created_by=p.get('created_by', ''),
                created_at=p.get('created_at', ''),
                updated_at=p.get('updated_at', '')
            )
            for p in projects
        ]

    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新项目"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 准备项目数据
        project_record = {
            'id': str(uuid.uuid4()),
            'name': project_data.name,
            'description': project_data.description,
            'status': project_data.status,
            'stage': project_data.stage,
            'is_public': project_data.is_public,
            'allow_file_upload': project_data.allow_file_upload,
            'allow_ai_chat': project_data.allow_ai_chat,
            'created_by': user_id
        }

        # 创建项目
        created_project = await supabase_service.create_project(project_record)

        if not created_project:
            raise HTTPException(status_code=500, detail="项目创建失败")

        # 将创建者添加为项目所有者
        await supabase_service.add_project_member_enhanced(
            project_id=created_project['id'],
            user_id=user_id,
            role='owner',
            invited_by=user_id
        )

        logger.info(f"项目创建成功: {project_data.name} by {user_id}")

        return ProjectResponse(
            id=created_project['id'],
            name=created_project['name'],
            description=created_project.get('description'),
            status=created_project['status'],
            stage=created_project['stage'],
            is_public=created_project.get('is_public', False),
            allow_file_upload=created_project.get('allow_file_upload', True),
            allow_ai_chat=created_project.get('allow_ai_chat', True),
            created_by=created_project['created_by'],
            created_at=created_project['created_at'],
            updated_at=created_project['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取项目详情"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查用户是否有项目访问权限
        has_permission = await supabase_service.has_project_permission(
            user_id, project_id, 'read'
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="没有访问此项目的权限")

        # 获取项目详情
        project = await supabase_service.get_project_details(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        return ProjectResponse(
            id=project['id'],
            name=project['name'],
            description=project.get('description'),
            status=project['status'],
            stage=project['stage'],
            is_public=project.get('is_public', False),
            allow_file_upload=project.get('allow_file_upload', True),
            allow_ai_chat=project.get('allow_ai_chat', True),
            created_by=project['created_by'],
            created_at=project['created_at'],
            updated_at=project['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取项目详情失败: {str(e)}")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新项目"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查用户是否有项目编辑权限
        has_permission = await supabase_service.has_project_permission(
            user_id, project_id, 'write'
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="没有编辑此项目的权限")

        # 只更新提供的字段
        update_data = {k: v for k, v in project_data.dict().items() if v is not None}

        # 更新项目
        updated_project = await supabase_service.update_project(project_id, update_data)

        if not updated_project:
            raise HTTPException(status_code=500, detail="项目更新失败")

        return ProjectResponse(
            id=updated_project['id'],
            name=updated_project['name'],
            description=updated_project.get('description'),
            status=updated_project['status'],
            stage=updated_project['stage'],
            is_public=updated_project.get('is_public', False),
            allow_file_upload=updated_project.get('allow_file_upload', True),
            allow_ai_chat=updated_project.get('allow_ai_chat', True),
            created_by=updated_project['created_by'],
            created_at=updated_project['created_at'],
            updated_at=updated_project['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除项目"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查用户是否有项目删除权限
        has_permission = await supabase_service.has_project_permission(
            user_id, project_id, 'delete'
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="没有删除此项目的权限")

        # 这里应该实现项目的级联删除，包括文件、成员等
        # 目前只做基本的项目记录删除
        # TODO: 实现完整的项目删除逻辑

        logger.info(f"项目删除请求: {project_id} by {user_id}")
        return {"message": "项目删除功能正在完善中"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")
