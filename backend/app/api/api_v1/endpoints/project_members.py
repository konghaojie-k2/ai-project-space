"""
项目成员管理API端点
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

# TODO: 迁移到 Supabase
# from app.models.user import User
# from app.models.project_member import ProjectMember, ProjectRole
from app.dependencies.auth import get_current_user
from pydantic import BaseModel


router = APIRouter()


# Pydantic模型
class ProjectMemberResponse(BaseModel):
    """项目成员响应模型"""
    project_id: str
    user_id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    role: str
    joined_at: str
    is_superuser: bool


class ProjectMemberCreate(BaseModel):
    """添加项目成员请求模型"""
    email: str
    role: str = "member"


class ProjectMemberUpdate(BaseModel):
    """更新项目成员请求模型"""
    role: str


@router.get("/projects/{project_id}/members", response_model=List[ProjectMemberResponse])
async def get_project_members(
    project_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    # TODO: 迁移到 Supabase，移除 db 依赖
):
    """获取项目成员列表（需要迁移到 Supabase）"""
    # TODO: 迁移到 Supabase
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="此端点需要迁移到 Supabase，暂时不可用"
    )


@router.post("/projects/{project_id}/members")
async def add_project_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    # TODO: 迁移到 Supabase，移除 db 依赖
):
    """添加项目成员（需要迁移到 Supabase）"""
    # TODO: 迁移到 Supabase
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="此端点需要迁移到 Supabase，暂时不可用"
    )


@router.put("/projects/{project_id}/members/{user_id}")
async def update_project_member(
    project_id: str,
    user_id: int,
    member_data: ProjectMemberUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    # TODO: 迁移到 Supabase，移除 db 依赖
):
    """更新项目成员角色（需要迁移到 Supabase）"""
    # TODO: 迁移到 Supabase
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="此端点需要迁移到 Supabase，暂时不可用"
    )


@router.delete("/projects/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: str,
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    # TODO: 迁移到 Supabase，移除 db 依赖
):
    """移除项目成员（需要迁移到 Supabase）"""
    # TODO: 迁移到 Supabase
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="此端点需要迁移到 Supabase，暂时不可用"
    )
