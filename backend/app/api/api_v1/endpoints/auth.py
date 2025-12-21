#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
认证相关的API端点
基于Supabase Auth的用户认证和授权
"""

from typing import Annotated, Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.services.supabase_auth import supabase_auth_service
from app.schemas.auth import (
    LoginRequest, RegisterRequest, TokenResponse, RefreshTokenRequest,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest,
    UserResponse, UserUpdate, MessageResponse
)
from app.dependencies.auth import (
    get_current_user, get_current_active_user, get_current_superuser,
    RateLimitAuth
)

# 重新导出依赖函数，方便其他模块使用
__all__ = [
    'get_current_user',
    'get_current_active_user', 
    'get_current_superuser',
    'get_current_admin_user',  # 别名，指向superuser
    'RateLimitAuth'
]

# 为兼容性创建别名
get_current_admin_user = get_current_superuser


router = APIRouter()


@router.post("/login", response_model=TokenResponse, summary="用户登录")
async def login(
    login_data: LoginRequest,
    _=Depends(RateLimitAuth)
):
    """
    用户登录

    - **email**: 用户邮箱
    - **password**: 用户密码
    """
    import time
    start_time = time.time()
    perf_log = {}  # 性能日志字典

    try:
        logger.info(f"🔐 开始登录流程: {login_data.email}")

        # 步骤1: 认证用户
        step_start = time.time()
        logger.info("📊 步骤1: 开始认证用户...")
        auth_result = await supabase_auth_service.authenticate_user(
            login_data.email,
            login_data.password
        )
        perf_log['authenticate_user'] = time.time() - step_start

        if not auth_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 步骤2: 提取用户信息
        step_start = time.time()
        user = auth_result.get('user')
        access_token = auth_result.get('access_token')
        refresh_token = auth_result.get('refresh_token')
        perf_log['extract_auth_result'] = time.time() - step_start

        # 直接使用authenticate_user返回的用户信息，避免重复API调用
        # authenticate_user已经返回了完整的用户信息，不需要再调用get_current_user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户信息获取失败",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 步骤3: 处理用户数据
        step_start = time.time()
        # 从user中提取信息，优先使用user_metadata
        user_metadata = user.get('user_metadata', {})
        email = user.get('email', '')
        
        # 处理username：优先使用user_metadata中的username，否则使用email前缀
        username = user_metadata.get('username') or user.get('username')
        if not username:
            username = email.split('@')[0] if email else 'user'
            logger.warning(f"用户 {email} 没有username，使用email前缀: {username}")

        # 提取其他用户信息
        full_name = user_metadata.get('full_name') or user.get('full_name')
        avatar_url = user_metadata.get('avatar_url') or user.get('avatar_url')
        email_confirmed_at = user.get('email_confirmed_at')
        is_verified = email_confirmed_at is not None
        perf_log['process_user_data'] = time.time() - step_start

        # 步骤4: 创建响应
        step_start = time.time()
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=auth_result.get('expires_in', 7200),
            user={
                "id": user.get('id'),
                "email": email,
                "username": username,
                "full_name": full_name,
                "avatar_url": avatar_url,
                "bio": user_metadata.get('bio'),
                "phone": user.get('phone'),
                "department": user_metadata.get('department'),
                "position": user_metadata.get('position'),
                "is_active": user.get('is_active', True),
                "is_verified": is_verified,
                "is_superuser": user_metadata.get('is_superuser', False) or user.get('is_superuser', False),
                "created_at": user.get('created_at') or datetime.utcnow(),
                "updated_at": user.get('updated_at') or datetime.utcnow()
            }
        )
        perf_log['create_response'] = time.time() - step_start

        total_time = time.time() - start_time
        
        # 输出性能详情
        perf_details = []
        for key, value in perf_log.items():
            if isinstance(value, float):
                perf_details.append(f"{key}={value:.3f}s")
        perf_str = ", ".join(perf_details)
        
        logger.info(f"✅ 登录成功: {username or email}, 总耗时: {total_time:.3f}s")
        logger.info(f"📊 性能详情: {perf_str}")

        return token_response

    except HTTPException:
        raise
    except Exception as e:
        error_time = time.time() - start_time
        # 输出性能详情以便定位问题
        perf_details = []
        for key, value in perf_log.items():
            if isinstance(value, float):
                perf_details.append(f"{key}={value:.3f}s")
        perf_str = ", ".join(perf_details) if perf_details else "无性能数据"
        logger.error(f"❌ 登录失败，总耗时: {error_time:.3f}s, 错误: {str(e)}")
        logger.error(f"📊 失败前性能详情: {perf_str}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录过程中发生错误"
        )


@router.post("/register", response_model=MessageResponse, summary="用户注册")
async def register(
    register_data: RegisterRequest,
    _=Depends(RateLimitAuth)
):
    """
    用户注册

    - **username**: 用户名 (3-50字符)
    - **email**: 邮箱地址
    - **password**: 密码 (至少6字符)
    - **full_name**: 全名 (可选)
    """
    try:
        # 检查Supabase服务是否可用
        if not supabase_auth_service.is_available():
            logger.error("Supabase认证服务不可用，无法注册用户")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务不可用，请检查Supabase配置"
            )

        # 使用Supabase注册用户
        user_metadata = {
            "username": register_data.username
        }

        if register_data.full_name:
            user_metadata["full_name"] = register_data.full_name

        auth_result = await supabase_auth_service.register_user(
            register_data.email,
            register_data.password,
            user_metadata
        )

        if not auth_result:
            error_detail = "用户注册失败，邮箱可能已存在或密码不符合要求"
            logger.error(f"用户注册失败: {register_data.email} - {error_detail}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail
            )

        user = auth_result.get('user')
        message = auth_result.get('message', '注册成功！请检查邮箱进行验证后登录')

        logger.info(f"用户注册成功: {register_data.username} ({register_data.email})")

        # 返回注册结果消息
        return MessageResponse(message=message)

    except HTTPException:
        raise
    except ValueError as e:
        # 捕获ValueError（来自supabase_auth_service的详细错误信息）
        error_msg = str(e)
        logger.error(f"注册失败: {error_msg}")
        
        # 根据错误信息判断状态码
        if "认证服务不可用" in error_msg or "配置错误" in error_msg:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        
        raise HTTPException(
            status_code=status_code,
            detail=error_msg
        )
    except Exception as e:
        error_msg = str(e)
        logger.error(f"注册失败: {error_msg}", exc_info=True)
        
        # 根据错误类型返回不同的错误信息
        if "email" in error_msg.lower() or "already exists" in error_msg.lower():
            detail = "该邮箱已被注册，请使用其他邮箱或直接登录"
            status_code = status.HTTP_400_BAD_REQUEST
        elif "password" in error_msg.lower():
            detail = "密码不符合要求，请确保密码至少6个字符"
            status_code = status.HTTP_400_BAD_REQUEST
        elif "supabase" in error_msg.lower() or "service" in error_msg.lower():
            detail = "认证服务配置错误，请联系管理员"
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            detail = f"注册过程中发生错误: {error_msg}"
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        raise HTTPException(
            status_code=status_code,
            detail=detail
        )


@router.post("/refresh", response_model=TokenResponse, summary="刷新令牌")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    _=Depends(RateLimitAuth)
):
    """
    刷新访问令牌

    - **refresh_token**: 刷新令牌
    """
    try:
        # 使用Supabase刷新令牌
        token_result = await supabase_auth_service.refresh_token(
            refresh_data.refresh_token
        )

        if not token_result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = token_result.get('access_token')
        refresh_token = token_result.get('refresh_token')
        expires_in = token_result.get('expires_in', 7200)

        # �新令牌获取用户信息
        full_user = await supabase_auth_service.get_current_user(access_token)
        if not full_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌刷新后用户信息获取失败",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 创建响应
        # 处理created_at和updated_at，如果为None则使用当前时间
        # 如果返回的是字符串，需要转换为datetime对象
        created_at = full_user.get('created_at')
        updated_at = full_user.get('updated_at')
        
        # 处理created_at
        if created_at is None:
            created_at = datetime.utcnow()
        elif isinstance(created_at, str):
            try:
                # 尝试解析ISO格式字符串
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.utcnow()
        elif not isinstance(created_at, datetime):
            created_at = datetime.utcnow()
        
        # 处理updated_at
        if updated_at is None:
            updated_at = datetime.utcnow()
        elif isinstance(updated_at, str):
            try:
                # 尝试解析ISO格式字符串
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = datetime.utcnow()
        elif not isinstance(updated_at, datetime):
            updated_at = datetime.utcnow()
        
        token_response = TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user={
                "id": full_user.get('id'),
                "email": full_user.get('email'),
                "username": full_user.get('username'),
                "full_name": full_user.get('full_name'),
                "avatar_url": full_user.get('avatar_url'),
                "bio": full_user.get('bio'),
                "phone": full_user.get('phone'),
                "department": full_user.get('department'),
                "position": full_user.get('position'),
                "is_active": full_user.get('is_active', True),
                "is_verified": full_user.get('email_confirmed', False),
                "is_superuser": full_user.get('is_superuser', False),
                "created_at": created_at,
                "updated_at": updated_at
            }
        )

        logger.info(f"令牌刷新成功: {full_user.get('username', full_user.get('email'))}")
        
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
    current_user: dict = Depends(get_current_user)
):
    """
    用户登出

    注意：Supabase会自动处理令牌失效
    """
    logger.info(f"用户登出: {current_user.get('username', current_user.get('email'))}")
    return MessageResponse(message="登出成功")


@router.get("/profile", response_model=dict, summary="获取用户信息")
async def get_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前用户信息
    """
    return {
        "id": current_user.get('id'),
        "username": current_user.get('username'),
        "email": current_user.get('email'),
        "full_name": current_user.get('full_name'),
        "avatar_url": current_user.get('avatar_url'),
        "bio": current_user.get('bio'),
        "phone": current_user.get('phone'),
        "department": current_user.get('department'),
        "position": current_user.get('position'),
        "is_active": current_user.get('is_active', True),
        "is_verified": current_user.get('email_confirmed', False),
        "is_superuser": current_user.get('is_superuser', False),
        "created_at": current_user.get('created_at'),
        "updated_at": current_user.get('updated_at')
    }


@router.patch("/profile", response_model=dict, summary="更新用户信息")
async def update_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新当前用户信息
    """
    try:
        # 准备更新数据
        update_data = user_update.model_dump(exclude_unset=True)
        user_id = current_user.get('id')

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID获取失败"
            )

        # 使用Supabase更新用户资料
        updated_profile = await supabase_auth_service.update_user_profile(
            user_id,
            update_data
        )

        if not updated_profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新用户信息失败"
            )

        logger.info(f"用户信息更新成功: {current_user.get('username', current_user.get('email'))}")

        # 返回更新后的用户信息
        return {
            "id": updated_profile.get('id', user_id),
            "username": updated_profile.get('username', current_user.get('username')),
            "email": current_user.get('email'),  # 邮箱通常不能通过此方法更改
            "full_name": updated_profile.get('full_name', current_user.get('full_name')),
            "avatar_url": updated_profile.get('avatar_url', current_user.get('avatar_url')),
            "bio": updated_profile.get('bio', current_user.get('bio')),
            "phone": updated_profile.get('phone', current_user.get('phone')),
            "department": updated_profile.get('department', current_user.get('department')),
            "position": updated_profile.get('position', current_user.get('position')),
            "is_active": current_user.get('is_active', True),
            "is_verified": current_user.get('email_confirmed', False),
            "is_superuser": current_user.get('is_superuser', False),
            "created_at": current_user.get('created_at'),
            "updated_at": updated_profile.get('updated_at', current_user.get('updated_at'))
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户信息更新失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息时发生错误"
        )


@router.post("/change-password", response_model=MessageResponse, summary="修改密码")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    修改用户密码

    - **current_password**: 当前密码
    - **new_password**: 新密码 (至少6字符)
    """
    try:
        # 使用Supabase修改密码
        success = await supabase_auth_service.change_password(
            current_user,
            password_data.current_password,
            password_data.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误或密码修改失败"
            )

        logger.info(f"用户密码修改成功: {current_user.get('username', current_user.get('email'))}")
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
    _=Depends(RateLimitAuth)
):
    """
    忘记密码 - 发送重置邮件

    - **email**: 用户邮箱
    """
    try:
        # 使用Supabase发送密码重置邮件
        success = await supabase_auth_service.reset_password(forgot_data.email)

        if success:
            logger.info(f"忘记密码邮件发送成功: {forgot_data.email}")
            return MessageResponse(message="重置密码邮件已发送到您的邮箱")
        else:
            # 无论用户是否存在，都返回成功消息（安全考虑）
            logger.info(f"忘记密码请求: {forgot_data.email}")
            return MessageResponse(message="如果该邮箱存在，重置链接已发送到您的邮箱")

    except Exception as e:
        logger.error(f"忘记密码处理失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="处理忘记密码请求时发生错误"
        )


# 重置密码功能已内置在Supabase的邮件链接中，无需单独实现
@router.post("/reset-password", response_model=MessageResponse, summary="重置密码")
async def reset_password(reset_data: ResetPasswordRequest):
    """
    重置密码

    - **token**: 重置令牌（从邮件链接中获取）
    - **new_password**: 新密码 (至少6字符)

    注意：实际的重置密码操作在Supabase的邮件链接中完成
    """
    try:
        logger.info(f"密码重置请求: token={reset_data.token[:10]}...")

        # Supabase的重置密码通常通过邮件链接完成，这里提供一个占位符
        return MessageResponse(message="请使用邮件中的链接重置密码")

    except Exception as e:
        logger.error(f"密码重置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置密码时发生错误"
        )


# 注意：用户管理功能已迁移到Supabase Dashboard和数据库层面
# 管理员可以通过Supabase Dashboard直接管理用户，或使用Supabase SQL Editor

@router.get("/users", response_model=List[dict], summary="获取用户列表")
async def get_users(
    current_user: dict = Depends(get_current_superuser),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
):
    """
    获取用户列表（仅管理员）
    """
    try:
        if not supabase_auth_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务不可用"
            )
        
        # 使用Supabase Admin API获取用户列表
        users = await supabase_auth_service.list_all_users()
        
        # 应用搜索过滤
        if search:
            search_lower = search.lower()
            users = [
                u for u in users
                if search_lower in u.get('email', '').lower() or
                   search_lower in u.get('username', '').lower() or
                   search_lower in u.get('full_name', '').lower()
            ]
        
        # 应用分页
        users = users[skip:skip + limit]
        
        # 转换为响应格式
        return [
            {
                "id": user.get('id'),
                "username": user.get('username'),
                "email": user.get('email'),
                "full_name": user.get('full_name'),
                "avatar_url": user.get('avatar_url'),
                "bio": user.get('bio'),
                "phone": user.get('phone'),
                "department": user.get('department'),
                "position": user.get('position'),
                "is_active": user.get('is_active', True),
                "is_verified": user.get('email_confirmed_at') is not None,
                "is_superuser": user.get('is_superuser', False),
                "created_at": user.get('created_at'),
                "updated_at": user.get('updated_at')
            }
            for user in users
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表时发生错误"
        )


@router.get("/users/stats/summary", response_model=dict, summary="获取用户统计信息")
async def get_user_stats(
    current_user: dict = Depends(get_current_superuser)
):
    """
    获取用户统计信息（仅管理员）
    """
    try:
        if not supabase_auth_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务不可用"
            )
        
        # 获取所有用户
        users = await supabase_auth_service.list_all_users()
        
        # 计算统计信息
        total_users = len(users)
        active_users = sum(1 for u in users if u.get('is_active', True))
        inactive_users = total_users - active_users
        verified_users = sum(1 for u in users if u.get('email_confirmed_at'))
        unverified_users = total_users - verified_users
        admin_users = sum(1 for u in users if u.get('is_superuser', False))
        regular_users = total_users - admin_users
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": inactive_users,
            "verified_users": verified_users,
            "unverified_users": unverified_users,
            "admin_users": admin_users,
            "regular_users": regular_users
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户统计时发生错误"
        )


@router.patch("/users/{user_id}/status", response_model=MessageResponse, summary="更新用户状态")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user: dict = Depends(get_current_superuser)
):
    """
    更新用户状态（启用/禁用）
    """
    try:
        success = await supabase_auth_service.update_user_status(user_id, is_active)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新用户状态失败"
            )
        return MessageResponse(message=f"用户状态已更新为{'启用' if is_active else '禁用'}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户状态失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户状态时发生错误"
        )


@router.patch("/users/{user_id}/admin", response_model=MessageResponse, summary="更新用户管理员权限")
async def update_user_admin_status(
    user_id: str,
    is_superuser: bool,
    current_user: dict = Depends(get_current_superuser)
):
    """
    设置/取消用户管理员权限
    """
    try:
        success = await supabase_auth_service.update_user_admin_status(user_id, is_superuser)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="更新管理员权限失败"
            )
        return MessageResponse(message=f"管理员权限已{'授予' if is_superuser else '撤销'}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新管理员权限失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新管理员权限时发生错误"
        )


@router.get("/users/{user_id}/projects", response_model=List[dict], summary="获取用户参与的所有项目")
async def get_user_projects(
    user_id: str,
    current_user: dict = Depends(get_current_superuser)
):
    """
    获取指定用户参与的所有项目（仅管理员）
    """
    try:
        if not supabase_auth_service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="认证服务不可用"
            )
        
        # 使用Supabase Service获取用户项目
        from app.services.supabase_client import supabase_service
        
        # 获取用户可访问的项目（管理员可以查看任何用户的项目）
        # 注意：这里传入is_superuser=False，因为我们要查询的是指定用户的项目，不是当前管理员的项目
        projects = await supabase_service.get_user_accessible_projects_enhanced(
            user_id=user_id,
            limit=1000,  # 获取足够多的项目
            is_superuser=False
        )
        
        # 转换为响应格式
        return [
            {
                "id": p.get('id'),
                "name": p.get('name'),
                "description": p.get('description'),
                "status": p.get('status', 'active'),
                "stage": p.get('stage', '售前'),
                "is_public": p.get('is_public', False),
                "role": p.get('role', 'member'),  # 用户在项目中的角色
                "is_owner": p.get('is_owner', False),  # 是否是项目创建者
                "created_at": p.get('created_at'),
                "updated_at": p.get('updated_at')
            }
            for p in projects
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户项目列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户项目列表时发生错误"
        )