"""
项目成员管理API端点
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from loguru import logger

from app.core.database import get_db
from app.models.user import User
from app.models.project_member import ProjectMember, ProjectRole
from app.api.api_v1.endpoints.auth import get_current_user, get_current_admin_user
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取项目成员列表"""
    try:
        logger.info(f"获取项目成员列表: project_id={project_id}")
        
        # 使用原生SQL查询项目成员，避免模型关系问题
        from sqlalchemy import text
        
        sql = text("""
            SELECT 
                pm.project_id,
                pm.user_id,
                u.username,
                u.email,
                u.full_name,
                u.avatar_url,
                u.department,
                u.position,
                pm.role,
                pm.joined_at,
                u.is_superuser
            FROM project_members pm
            JOIN users u ON pm.user_id = u.id
            WHERE pm.project_id = :project_id
            ORDER BY pm.joined_at DESC
        """)
        
        members_result = db.execute(sql, {"project_id": project_id}).fetchall()
        
        result = []
        for row in members_result:
            result.append(ProjectMemberResponse(
                project_id=row[0],
                user_id=row[1],
                username=row[2],
                email=row[3],
                full_name=row[4],
                avatar_url=row[5],
                department=row[6],
                position=row[7],
                role=row[8],
                joined_at=row[9],
                is_superuser=bool(row[10])
            ))
        
        logger.info(f"返回 {len(result)} 个项目成员")
        return result
        
    except Exception as e:
        logger.error(f"获取项目成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取项目成员失败"
        )


@router.post("/projects/{project_id}/members")
async def add_project_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加项目成员"""
    try:
        logger.info(f"添加项目成员: project_id={project_id}, email={member_data.email}, role={member_data.role}")
        
        # 通过邮箱查找用户
        user = db.query(User).filter(User.email == member_data.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在，请检查邮箱地址"
            )
        
        # 使用原生SQL检查是否已经是成员
        from sqlalchemy import text
        
        check_sql = text("SELECT COUNT(*) FROM project_members WHERE project_id = :project_id AND user_id = :user_id")
        existing_result = db.execute(check_sql, {"project_id": project_id, "user_id": user.id}).fetchone()
        
        
        if existing_result[0] > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户已经是项目成员"
            )
        
        # 使用原生SQL创建成员关系
        insert_sql = text("""
            INSERT INTO project_members (project_id, user_id, role, joined_at, updated_at)
            VALUES (:project_id, :user_id, :role, datetime('now'), datetime('now'))
        """)
        
        db.execute(insert_sql, {
            "project_id": project_id,
            "user_id": user.id,
            "role": member_data.role.upper()
        })
        db.commit()
        
        logger.info(f"成功添加项目成员: project_id={project_id}, user_id={user.id}, role={member_data.role}")
        return {"message": "成员添加成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"添加项目成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加项目成员失败"
        )


@router.put("/projects/{project_id}/members/{user_id}")
async def update_project_member(
    project_id: str,
    user_id: int,
    member_data: ProjectMemberUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新项目成员角色"""
    try:
        logger.info(f"更新项目成员角色: project_id={project_id}, user_id={user_id}, role={member_data.role}")
        
        # 使用原生SQL更新，避免模型关系问题
        from sqlalchemy import text
        
        # 先检查成员是否存在
        check_sql = text("SELECT COUNT(*) FROM project_members WHERE project_id = :project_id AND user_id = :user_id")
        result = db.execute(check_sql, {"project_id": project_id, "user_id": user_id}).fetchone()
        
        if result[0] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目成员不存在"
            )
        
        # 更新角色
        update_sql = text("""
            UPDATE project_members 
            SET role = :role, updated_at = datetime('now') 
            WHERE project_id = :project_id AND user_id = :user_id
        """)
        db.execute(update_sql, {
            "project_id": project_id, 
            "user_id": user_id, 
            "role": member_data.role.upper()
        })
        db.commit()
        
        logger.info(f"成功更新项目成员角色: project_id={project_id}, user_id={user_id}, role={member_data.role}")
        return {"message": "成员角色更新成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新项目成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新项目成员失败"
        )


@router.delete("/projects/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: str,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """移除项目成员"""
    try:
        logger.info(f"移除项目成员: project_id={project_id}, user_id={user_id}")
        
        # 使用原生SQL删除，避免模型关系问题
        from sqlalchemy import text
        
        # 先检查成员是否存在
        check_sql = text("SELECT COUNT(*) FROM project_members WHERE project_id = :project_id AND user_id = :user_id")
        result = db.execute(check_sql, {"project_id": project_id, "user_id": user_id}).fetchone()
        
        if result[0] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="项目成员不存在"
            )
        
        # 删除成员关系
        delete_sql = text("DELETE FROM project_members WHERE project_id = :project_id AND user_id = :user_id")
        db.execute(delete_sql, {"project_id": project_id, "user_id": user_id})
        db.commit()
        
        logger.info(f"成功移除项目成员: project_id={project_id}, user_id={user_id}")
        return {"message": "成员移除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"移除项目成员失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除项目成员失败"
        )
