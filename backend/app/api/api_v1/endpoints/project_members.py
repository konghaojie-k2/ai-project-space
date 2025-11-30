"""
项目成员管理API端点
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.dependencies.auth import get_current_user
from app.services.supabase_client import supabase_service
from app.services.supabase_auth import supabase_auth_service
from pydantic import BaseModel


router = APIRouter()


# Pydantic模型
class ProjectMemberResponse(BaseModel):
    """项目成员响应模型"""
    project_id: str
    user_id: str  # 改为字符串（UUID）
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    role: str
    joined_at: str
    is_superuser: bool = False


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
):
    """获取项目成员列表"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")
        
        # 使用简单的权限检查：检查用户是否是项目成员或创建者
        # 避免使用有问题的 RPC 函数
        has_permission = False
        
        try:
            # 检查是否是项目创建者
            project = await supabase_service.get_project_details(project_id)
            if project:
                if project.get('created_by') == user_id:
                    has_permission = True
                    logger.debug(f"✅ 用户是项目创建者: {user_id} -> {project_id}")
                else:
                    # 检查是否是项目成员
                    from app.services.supabase_client import run_supabase_query
                    client_to_use = supabase_service.admin_client if supabase_service.admin_client else supabase_service.client
                    if client_to_use:
                        try:
                            member_query = lambda: client_to_use.table('project_members').select('user_id').eq(
                                'project_id', project_id
                            ).eq('user_id', user_id).limit(1).execute()
                            member_response = await run_supabase_query(member_query)
                            if member_response.data and len(member_response.data) > 0:
                                has_permission = True
                                logger.debug(f"✅ 用户是项目成员: {user_id} -> {project_id}")
                        except Exception as e:
                            logger.warning(f"⚠️ 检查项目成员身份失败: {e}")
            else:
                logger.warning(f"⚠️ 项目不存在: {project_id}")
        except Exception as e:
            logger.error(f"❌ 权限检查异常: {e}", exc_info=True)
        
        if not has_permission:
            logger.warning(f"❌ 用户无权限访问项目: {user_id} -> {project_id}")
            raise HTTPException(status_code=403, detail="没有访问此项目的权限")
        
        # 获取项目成员列表（包含用户档案信息）
        members = await supabase_service.get_project_members_with_profiles(project_id)
        
        logger.info(f"📊 获取项目成员列表: project_id={project_id}, 成员数量={len(members) if members else 0}")
        if members:
            logger.info(f"📊 成员数据示例: {members[0] if len(members) > 0 else '无'}")
        
        # 转换为响应格式
        result = []
        # 获取所有用户信息以便获取邮箱
        all_users = await supabase_auth_service.list_all_users()
        user_email_map = {u.get('id'): u.get('email', '') for u in all_users}
        
        logger.info(f"📊 用户总数: {len(all_users)}, 邮箱映射数量: {len(user_email_map)}")
        
        for member in members:
            try:
                profile = member.get('profiles') or {}
                member_user_id = member.get('user_id', '')
                
                logger.debug(f"📊 处理成员: user_id={member_user_id}, profile={profile}")
                
                # 从用户列表中获取邮箱
                user_email = user_email_map.get(member_user_id, '')
                
                # 如果邮箱为空，尝试从profile中获取
                if not user_email and profile:
                    user_email = profile.get('email', '')
                
                result.append(ProjectMemberResponse(
                    project_id=member.get('project_id', project_id),
                    user_id=str(member_user_id),  # 确保是字符串
                    username=profile.get('username', '未知用户') if profile else '未知用户',
                    email=user_email or '',
                    full_name=profile.get('full_name') if profile else None,
                    avatar_url=profile.get('avatar_url') if profile else None,
                    department=profile.get('department') if profile else None,
                    position=profile.get('position') if profile else None,
                    role=member.get('role', 'member'),
                    joined_at=str(member.get('joined_at', '')),
                    is_superuser=profile.get('system_role') == 'super_admin' or profile.get('is_superuser', False) if profile else False
                ))
            except Exception as e:
                logger.error(f"❌ 转换成员数据失败: {member}, 错误: {e}")
                continue
        
        logger.info(f"✅ 最终返回成员数量: {len(result)}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目成员列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取项目成员列表失败: {str(e)}")


@router.post("/projects/{project_id}/members")
async def add_project_member(
    project_id: str,
    member_data: ProjectMemberCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """添加项目成员"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")
        
        # 检查用户是否有添加成员的权限
        has_permission = await supabase_service.has_project_permission(
            user_id, project_id, 'write'
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="没有添加项目成员的权限")
        
        # 根据邮箱查找用户
        # 首先从所有用户列表中查找
        all_users = await supabase_auth_service.list_all_users()
        target_user = None
        for u in all_users:
            if u.get('email', '').lower() == member_data.email.lower():
                target_user = u
                break
        
        if not target_user:
            raise HTTPException(status_code=404, detail=f"用户 {member_data.email} 不存在")
        
        target_user_id = target_user.get('id')
        if not target_user_id:
            raise HTTPException(status_code=400, detail="用户ID无效")
        
        # 检查用户是否已经是项目成员
        existing_members = await supabase_service.get_project_members_with_profiles(project_id)
        for member in existing_members:
            if member.get('user_id') == target_user_id:
                raise HTTPException(status_code=400, detail="用户已经是项目成员")
        
        # 添加项目成员
        success = await supabase_service.add_project_member_enhanced(
            project_id=project_id,
            user_id=target_user_id,
            role=member_data.role,
            invited_by=user_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="添加项目成员失败")
        
        # 返回新添加的成员信息
        members = await supabase_service.get_project_members_with_profiles(project_id)
        new_member = None
        for member in members:
            if member.get('user_id') == target_user_id:
                profile = member.get('profiles') or {}
                new_member = ProjectMemberResponse(
                    project_id=member.get('project_id', project_id),
                    user_id=member.get('user_id', ''),
                    username=profile.get('username', '未知用户'),
                    email=member_data.email,
                    full_name=profile.get('full_name'),
                    avatar_url=profile.get('avatar_url'),
                    department=profile.get('department'),
                    position=profile.get('position'),
                    role=member.get('role', member_data.role),
                    joined_at=member.get('joined_at', ''),
                    is_superuser=profile.get('system_role') == 'super_admin' or profile.get('is_superuser', False)
                )
                break
        
        if new_member:
            return new_member
        else:
            raise HTTPException(status_code=500, detail="添加成功但无法获取成员信息")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加项目成员失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加项目成员失败: {str(e)}")


@router.put("/projects/{project_id}/members/{user_id}")
async def update_project_member(
    project_id: str,
    user_id: str,  # 改为字符串（UUID）
    member_data: ProjectMemberUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """更新项目成员角色"""
    try:
        current_user_id = current_user.get('id')
        if not current_user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")
        
        # 检查当前用户是否有更新成员的权限
        has_permission = await supabase_service.has_project_permission(
            current_user_id, project_id, 'write'
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="没有更新项目成员的权限")
        
        # 更新项目成员角色
        success = await supabase_service.update_project_member_role(
            project_id=project_id,
            user_id=user_id,
            role=member_data.role
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="更新项目成员角色失败")
        
        # 返回更新后的成员信息
        members = await supabase_service.get_project_members_with_profiles(project_id)
        updated_member = None
        for member in members:
            if member.get('user_id') == user_id:
                profile = member.get('profiles') or {}
                updated_member = ProjectMemberResponse(
                    project_id=member.get('project_id', project_id),
                    user_id=member.get('user_id', ''),
                    username=profile.get('username', '未知用户'),
                    email=profile.get('email', ''),
                    full_name=profile.get('full_name'),
                    avatar_url=profile.get('avatar_url'),
                    department=profile.get('department'),
                    position=profile.get('position'),
                    role=member.get('role', member_data.role),
                    joined_at=member.get('joined_at', ''),
                    is_superuser=profile.get('system_role') == 'super_admin' or profile.get('is_superuser', False)
                )
                break
        
        if updated_member:
            return updated_member
        else:
            raise HTTPException(status_code=500, detail="更新成功但无法获取成员信息")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目成员角色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新项目成员角色失败: {str(e)}")


@router.delete("/projects/{project_id}/members/{user_id}")
async def remove_project_member(
    project_id: str,
    user_id: str,  # 改为字符串（UUID）
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """移除项目成员"""
    try:
        current_user_id = current_user.get('id')
        if not current_user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")
        
        # 检查当前用户是否有移除成员的权限
        has_permission = await supabase_service.has_project_permission(
            current_user_id, project_id, 'write'
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="没有移除项目成员的权限")
        
        # 不能移除项目创建者
        project = await supabase_service.get_project_details(project_id)
        if project and project.get('created_by') == user_id:
            raise HTTPException(status_code=400, detail="不能移除项目创建者")
        
        # 移除项目成员
        success = await supabase_service.remove_project_member(
            project_id=project_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="移除项目成员失败")
        
        return {"message": "项目成员已成功移除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除项目成员失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"移除项目成员失败: {str(e)}")
