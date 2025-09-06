"""
项目管理API端点
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from loguru import logger
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectStage
from app.api.api_v1.endpoints.auth import get_current_user, get_current_admin_user


router = APIRouter()



# Pydantic模型
class ProjectResponse(BaseModel):
    """项目响应模型"""
    id: str
    name: str
    description: Optional[str] = None
    status: str
    stage: str
    is_public: bool
    allow_file_upload: bool
    allow_ai_chat: bool
    creator_id: int
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
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目列表"""
    try:
        logger.info(f"获取项目列表: user_id={current_user.id}, search={search}, status={status}")
        
        # 构建查询
        query = db.query(Project)
        
        # 如果不是管理员，只能看到公开项目或自己创建的项目
        if not current_user.is_superuser:
            query = query.filter(
                or_(
                    Project.is_public == True,
                    Project.creator_id == current_user.id
                )
            )
        
        # 搜索过滤
        if search:
            query = query.filter(
                or_(
                    Project.name.contains(search),
                    Project.description.contains(search)
                )
            )
        
        # 状态过滤
        if status:
            query = query.filter(Project.status == status)
        
        # 分页
        projects = query.offset(skip).limit(limit).all()
        
        # 转换为响应格式
        result = []
        for project in projects:
            result.append(ProjectResponse(
                id=str(project.id),
                name=project.name,
                description=project.description,
                status=project.status.value if isinstance(project.status, ProjectStatus) else project.status,
                stage=project.current_stage.value if isinstance(project.current_stage, ProjectStage) else project.current_stage,
                is_public=project.is_public,
                allow_file_upload=project.allow_file_upload,
                allow_ai_chat=project.allow_ai_chat,
                creator_id=project.creator_id,
                created_at=project.created_at.isoformat(),
                updated_at=project.updated_at.isoformat()
            ))
        
        logger.info(f"返回 {len(result)} 个项目")
        return result
        
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目列表失败"
        )


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新项目"""
    try:
        logger.info(f"创建项目: {project_data.name}, creator_id={current_user.id}")
        
        # 创建项目
        project = Project(
            name=project_data.name,
            description=project_data.description,
            status=project_data.status,
            current_stage=project_data.stage,
            is_public=project_data.is_public,
            allow_file_upload=project_data.allow_file_upload,
            allow_ai_chat=project_data.allow_ai_chat,
            creator_id=current_user.id
        )
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        logger.info(f"项目创建成功: id={project.id}")
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            status=project.status.value if isinstance(project.status, ProjectStatus) else project.status,
            stage=project.current_stage.value if isinstance(project.current_stage, ProjectStage) else project.current_stage,
            is_public=project.is_public,
            allow_file_upload=project.allow_file_upload,
            allow_ai_chat=project.allow_ai_chat,
            creator_id=project.creator_id,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建项目失败"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目详情"""
    try:
        project = db.query(Project).filter(Project.id == int(project_id)).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )
        
        # 权限检查
        if not current_user.is_superuser and not project.is_public and project.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限访问此项目"
            )
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            status=project.status.value if isinstance(project.status, ProjectStatus) else project.status,
            stage=project.current_stage.value if isinstance(project.current_stage, ProjectStage) else project.current_stage,
            is_public=project.is_public,
            allow_file_upload=project.allow_file_upload,
            allow_ai_chat=project.allow_ai_chat,
            creator_id=project.creator_id,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目详情失败"
        )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新项目"""
    try:
        project = db.query(Project).filter(Project.id == int(project_id)).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )
        
        # 权限检查 - 只有管理员或项目创建者可以更新
        if not current_user.is_superuser and project.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限修改此项目"
            )
        
        # 更新字段
        if project_data.name is not None:
            project.name = project_data.name
        if project_data.description is not None:
            project.description = project_data.description
        if project_data.status is not None:
            project.status = project_data.status
        if project_data.stage is not None:
            project.current_stage = project_data.stage
        if project_data.is_public is not None:
            project.is_public = project_data.is_public
        if project_data.allow_file_upload is not None:
            project.allow_file_upload = project_data.allow_file_upload
        if project_data.allow_ai_chat is not None:
            project.allow_ai_chat = project_data.allow_ai_chat
        
        db.commit()
        db.refresh(project)
        
        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            status=project.status.value if isinstance(project.status, ProjectStatus) else project.status,
            stage=project.current_stage.value if isinstance(project.current_stage, ProjectStage) else project.current_stage,
            is_public=project.is_public,
            allow_file_upload=project.allow_file_upload,
            allow_ai_chat=project.allow_ai_chat,
            creator_id=project.creator_id,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新项目失败"
        )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除项目"""
    try:
        project = db.query(Project).filter(Project.id == int(project_id)).first()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目不存在"
            )
        
        # 权限检查 - 只有管理员或项目创建者可以删除
        if not current_user.is_superuser and project.creator_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此项目"
            )
        
        db.delete(project)
        db.commit()
        
        return {"message": "项目删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目失败: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除项目失败"
        )
