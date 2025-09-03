"""
认证相关的API端点
"""

from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.services.auth_service import auth_service
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    UserResponse, UserUpdate, MessageResponse
)
from typing import List, Optional
from app.models.user import User


router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """获取当前用户"""
    token = credentials.credentials
    payload = auth_service.verify_token(token, "access")
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌中缺少用户ID",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = auth_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户账户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前管理员用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，需要管理员权限"
        )
    return current_user


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录
    
    - **email**: 用户邮箱
    - **password**: 用户密码
    """
    try:
        # 验证用户凭据
        user = auth_service.authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已被禁用",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建令牌响应
        token_response = auth_service.create_token_response(user)
        
        logger.info(f"用户登录成功: {user.username} ({user.email})")
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录过程中发生错误"
        )


@router.post("/register", response_model=TokenResponse, summary="用户注册")
async def register(
    register_data: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    用户注册
    
    - **username**: 用户名 (3-50字符)
    - **email**: 邮箱地址
    - **password**: 密码 (至少6字符)
    - **full_name**: 全名 (可选)
    """
    try:
        # 创建用户
        from app.schemas.auth import UserCreate
        user_create = UserCreate(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            full_name=register_data.full_name
        )
        
        user = auth_service.create_user(db, user_create)
        
        # 创建令牌响应
        token_response = auth_service.create_token_response(user)
        
        logger.info(f"用户注册成功: {user.username} ({user.email})")
        return token_response
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册过程中发生错误"
        )


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    刷新访问令牌
    
    - **refresh_token**: 刷新令牌
    """
    try:
        # 验证刷新令牌
        payload = auth_service.verify_token(refresh_data.refresh_token, "refresh")
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌中缺少用户ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 获取用户
        user = auth_service.get_user_by_id(db, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已被禁用",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建新的令牌响应
        token_response = auth_service.create_token_response(user)
        
        logger.info(f"令牌刷新成功: {user.username}")
        return token_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌刷新失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新过程中发生错误"
        )


@router.post("/logout", response_model=MessageResponse, summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    用户登出
    
    注意：由于使用JWT，实际的令牌失效需要在客户端处理
    """
    logger.info(f"用户登出: {current_user.username}")
    return MessageResponse(message="登出成功")


@router.get("/profile", response_model=UserResponse, summary="获取用户信息")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        avatar_url=current_user.avatar_url,
        bio=current_user.bio,
        phone=current_user.phone,
        department=current_user.department,
        position=current_user.position,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.patch("/profile", response_model=UserResponse, summary="更新用户信息")
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新当前用户信息
    """
    try:
        # 更新用户信息
        update_data = user_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        db.commit()
        db.refresh(current_user)
        
        logger.info(f"用户信息更新成功: {current_user.username}")
        
        return UserResponse(
            id=str(current_user.id),
            username=current_user.username,
            email=current_user.email,
            full_name=current_user.full_name,
            avatar_url=current_user.avatar_url,
            bio=current_user.bio,
            phone=current_user.phone,
            department=current_user.department,
            position=current_user.position,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            is_superuser=current_user.is_superuser,
            created_at=current_user.created_at,
            updated_at=current_user.updated_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"用户信息更新失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息时发生错误"
        )


@router.post("/change-password", response_model=MessageResponse, summary="修改密码")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    修改用户密码
    
    - **current_password**: 当前密码
    - **new_password**: 新密码 (至少6字符)
    """
    try:
        # 验证当前密码
        if not auth_service.verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )
        
        # 更新密码
        auth_service.update_user_password(db, current_user, password_data.new_password)
        
        logger.info(f"用户密码修改成功: {current_user.username}")
        return MessageResponse(message="密码修改成功")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"密码修改失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码时发生错误"
        )


@router.post("/forgot-password", response_model=MessageResponse, summary="忘记密码")
async def forgot_password(
    forgot_data: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    忘记密码 - 发送重置邮件
    
    - **email**: 用户邮箱
    
    注意：这是一个模拟实现，实际应用中需要集成邮件服务
    """
    try:
        # 检查用户是否存在
        user = auth_service.get_user_by_email(db, forgot_data.email)
        
        # 无论用户是否存在，都返回成功消息（安全考虑）
        logger.info(f"忘记密码请求: {forgot_data.email}")
        
        # TODO: 实际实现中应该：
        # 1. 生成重置令牌
        # 2. 保存到数据库或缓存
        # 3. 发送重置邮件
        
        return MessageResponse(message="如果该邮箱存在，重置链接已发送到您的邮箱")
        
    except Exception as e:
        logger.error(f"忘记密码处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理忘记密码请求时发生错误"
        )


@router.post("/reset-password", response_model=MessageResponse, summary="重置密码")
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    重置密码
    
    - **token**: 重置令牌
    - **new_password**: 新密码 (至少6字符)
    
    注意：这是一个模拟实现，实际应用中需要验证重置令牌
    """
    try:
        # TODO: 实际实现中应该：
        # 1. 验证重置令牌
        # 2. 检查令牌是否过期
        # 3. 获取对应的用户
        # 4. 更新密码
        # 5. 删除或标记令牌为已使用
        
        logger.info(f"密码重置请求: token={reset_data.token[:10]}...")
        
        return MessageResponse(message="密码重置成功，请使用新密码登录")
        
    except Exception as e:
        logger.error(f"密码重置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置密码时发生错误"
        )


# 用户管理接口（管理员功能）

@router.get("/users", response_model=List[UserResponse], summary="获取所有用户列表")
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取所有用户列表（管理员权限）
    
    - **skip**: 跳过的记录数
    - **limit**: 返回的记录数限制
    - **search**: 搜索用户名或邮箱
    """
    try:
        query = db.query(User)
        
        if search:
            query = query.filter(
                (User.username.contains(search)) | 
                (User.email.contains(search))
            )
        
        users = query.offset(skip).limit(limit).all()
        
        return [
            UserResponse(
                id=str(user.id),
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                avatar_url=user.avatar_url,
                bio=user.bio,
                phone=user.phone,
                department=user.department,
                position=user.position,
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_superuser=user.is_superuser,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            for user in users
        ]
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表时发生错误"
        )


@router.get("/users/{user_id}", response_model=UserResponse, summary="获取指定用户信息")
async def get_user_by_id(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取指定用户的详细信息（管理员权限）
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            phone=user.phone,
            department=user.department,
            position=user.position,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息时发生错误"
        )


@router.patch("/users/{user_id}", response_model=UserResponse, summary="更新用户信息")
async def update_user_by_admin(
    user_id: int,
    user_update: UserUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    管理员更新用户信息
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 更新用户信息
        update_data = user_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"管理员 {current_admin.username} 更新了用户 {user.username} 的信息")
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            phone=user.phone,
            department=user.department,
            position=user.position,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新用户信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息时发生错误"
        )


@router.patch("/users/{user_id}/status", response_model=MessageResponse, summary="更新用户状态")
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    管理员启用/禁用用户账户
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 不能禁用自己
        if user.id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能修改自己的账户状态"
            )
        
        user.is_active = is_active
        db.commit()
        
        action = "启用" if is_active else "禁用"
        logger.info(f"管理员 {current_admin.username} {action}了用户 {user.username}")
        
        return MessageResponse(message=f"用户账户已{action}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新用户状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户状态时发生错误"
        )


@router.patch("/users/{user_id}/admin", response_model=MessageResponse, summary="设置/取消管理员权限")
async def update_user_admin_status(
    user_id: int,
    is_superuser: bool,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    管理员设置或取消用户的管理员权限
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 不能修改自己的管理员权限
        if user.id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能修改自己的管理员权限"
            )
        
        user.is_superuser = is_superuser
        db.commit()
        
        action = "设置" if is_superuser else "取消"
        logger.info(f"管理员 {current_admin.username} {action}了用户 {user.username} 的管理员权限")
        
        return MessageResponse(message=f"用户管理员权限已{action}")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新管理员权限失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新管理员权限时发生错误"
        )


@router.patch("/users/{user_id}/verify", response_model=MessageResponse, summary="验证用户邮箱")
async def verify_user_email(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    管理员手动验证用户邮箱
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        user.is_verified = True
        db.commit()
        
        logger.info(f"管理员 {current_admin.username} 验证了用户 {user.username} 的邮箱")
        
        return MessageResponse(message=f"用户 {user.username} 邮箱已验证")
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"验证用户邮箱失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证用户邮箱时发生错误"
        )


@router.get("/users/stats/summary", summary="获取用户统计信息")
async def get_user_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    获取用户统计信息（管理员权限）
    """
    try:
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        verified_users = db.query(User).filter(User.is_verified == True).count()
        admin_users = db.query(User).filter(User.is_superuser == True).count()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "verified_users": verified_users,
            "unverified_users": total_users - verified_users,
            "admin_users": admin_users,
            "regular_users": total_users - admin_users
        }
        
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户统计时发生错误"
        )
