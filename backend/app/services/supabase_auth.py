#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Supabase认证服务

基于Supabase Auth的用户认证和授权服务，替换原有的JWT自定义实现。
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.services.supabase_client import supabase_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class SupabaseAuthService:
    """Supabase认证服务类"""

    def __init__(self):
        """初始化认证服务"""
        self.supabase = supabase_service
        self.token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def is_available(self) -> bool:
        """检查认证服务是否可用"""
        return self.supabase.is_available() and settings.use_supabase

    def is_admin_available(self) -> bool:
        """检查管理员认证服务是否可用"""
        return self.supabase.is_admin_available() and settings.use_supabase

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        用户认证

        Args:
            email: 用户邮箱
            password: 用户密码

        Returns:
            认证结果字典，包含用户信息和token，失败返回None
        """
        if not self.is_available():
            logger.error("认证服务不可用")
            return None

        try:
            auth_result = await self.supabase.sign_in(email, password)

            if auth_result:
                logger.info(f"用户认证成功: {email}")
                return {
                    'user': auth_result['user'],
                    'access_token': auth_result['access_token'],
                    'refresh_token': auth_result['refresh_token'],
                    'expires_in': self.token_expire_minutes * 60
                }
            return None

        except Exception as e:
            logger.error(f"用户认证失败 {email}: {e}")
            return None

    async def register_user(self,
                          email: str,
                          password: str,
                          user_metadata: Optional[Dict] = None) -> Optional[Dict]:
        """
        用户注册

        Args:
            email: 用户邮箱
            password: 用户密码
            user_metadata: 用户元数据

        Returns:
            注册结果字典，失败返回None
        """
        if not self.is_available():
            logger.error("认证服务不可用，无法注册用户")
            raise ValueError("认证服务不可用，请检查Supabase配置")

        try:
            # 统一使用Anon Key进行用户注册（与登录保持一致）
            logger.info(f"使用标准注册流程注册用户: {email}")

            if settings.DISABLE_EMAIL_VERIFICATION:
                # 开发环境：可以尝试使用Admin API自动确认邮箱，但只作为可选增强
                if self.is_admin_available():
                    logger.info(f"开发环境，尝试使用Admin API自动确认邮箱: {email}")
                    user_data = await self.supabase.admin_create_user(
                        email, password, user_metadata, email_confirm=True
                    )

                    if user_data:
                        logger.info(f"用户注册成功（已自动确认邮箱）: {email}")
                        return {
                            'user': user_data,
                            'message': '注册成功！邮箱已自动验证，可以直接登录'
                        }
                    else:
                        logger.warning(f"Admin API创建用户失败，回退到标准注册流程: {email}")
                else:
                    logger.info(f"Admin API不可用，直接使用标准注册流程: {email}")

            # 检查是否使用Demo Key，如果是则拒绝注册
            try:
                import base64
                import json
                anon_key = settings.SUPABASE_ANON_KEY or ""
                if anon_key:
                    # 解码JWT payload检查iss字段
                    payload = anon_key.split('.')[1]
                    payload += '=' * (-len(payload) % 4)
                    decoded = base64.b64decode(payload).decode()
                    jwt_data = json.loads(decoded)
                    if jwt_data.get('iss') == 'supabase-demo':
                        logger.error(f"检测到Demo Key，无法创建真实用户: {email}")
                        logger.error("请配置真实的Supabase项目密钥到.env文件中的SUPABASE_ANON_KEY")
                        raise ValueError("无法使用Demo Key创建用户账户，请配置真实的Supabase项目")
            except Exception as decode_error:
                logger.warning(f"JWT解码失败: {decode_error}")

            # 使用标准注册流程（Anon Key，与登录保持一致）
            user_data = await self.supabase.sign_up(email, password, user_metadata)

            if user_data:
                if settings.DISABLE_EMAIL_VERIFICATION:
                    logger.info(f"用户注册成功（开发环境，可能需要手动确认邮箱）: {email}")
                    return {
                        'user': user_data,
                        'message': '注册成功！如果需要邮箱验证，请检查邮箱后登录'
                    }
                else:
                    logger.info(f"用户注册成功，等待邮件验证: {email}")
                    return {
                        'user': user_data,
                        'message': '注册成功！请检查邮箱进行验证后登录'
                    }

            # 如果注册失败，记录详细错误
            logger.error(f"用户注册失败: {email}")
            raise ValueError("用户注册失败，邮箱可能已存在或密码不符合要求")

        except ValueError as e:
            # 重新抛出ValueError，让调用者处理
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"用户注册失败 {email}: {error_msg}", exc_info=True)
            
            # 根据错误类型抛出更具体的异常
            if "email" in error_msg.lower() or "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
                raise ValueError("该邮箱已被注册，请使用其他邮箱或直接登录")
            elif "password" in error_msg.lower() or "weak" in error_msg.lower():
                raise ValueError("密码不符合要求，请确保密码至少6个字符且足够安全")
            elif "supabase" in error_msg.lower() or "service" in error_msg.lower() or "client" in error_msg.lower():
                raise ValueError("认证服务配置错误，请联系管理员")
            else:
                raise ValueError(f"注册失败: {error_msg}")

    async def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """
        刷新访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            新的令牌信息字典，失败返回None
        """
        if not self.is_available():
            logger.error("认证服务不可用")
            return None

        try:
            response = self.supabase.client.auth.refresh_session(refresh_token)

            if response.session:
                logger.info("令牌刷新成功")
                return {
                    'access_token': response.session.access_token,
                    'refresh_token': response.session.refresh_token,
                    'expires_in': self.token_expire_minutes * 60
                }
            return None

        except Exception as e:
            logger.error(f"令牌刷新失败: {e}")
            return None

    async def logout_user(self, access_token: str) -> bool:
        """
        用户登出

        Args:
            access_token: 访问令牌

        Returns:
            登出是否成功
        """
        if not self.is_available():
            logger.error("认证服务不可用")
            return False

        try:
            success = await self.supabase.sign_out(access_token)
            if success:
                logger.info("用户登出成功")
            return success

        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            return False

    async def get_current_user(self, access_token: str) -> Optional[Dict]:
        """
        获取当前用户信息

        Args:
            access_token: 访问令牌

        Returns:
            用户信息字典，token无效返回None
        """
        if not self.is_available():
            logger.error("认证服务不可用")
            return None

        try:
            user_data = await self.supabase.get_user_from_token(access_token)

            if user_data:
                # 尝试获取用户档案信息（如果失败，使用默认值）
                try:
                    profile = await self.supabase.get_profile(user_data['id'])
                    if profile:
                        # 合并认证信息和档案信息
                        user_data.update({
                            'username': profile.get('username'),
                            'full_name': profile.get('full_name'),
                            'avatar_url': profile.get('avatar_url'),
                            'bio': profile.get('bio'),
                            'is_superuser': profile.get('is_superuser', False)
                        })
                except Exception as e:
                    # 如果获取profile失败（可能是RLS策略问题），使用user_metadata中的信息
                    logger.warning(f"获取用户档案失败，使用user_metadata: {e}")
                    user_metadata = user_data.get('user_metadata', {})
                    if not user_data.get('username'):
                        user_data['username'] = user_metadata.get('username')
                    if not user_data.get('full_name'):
                        user_data['full_name'] = user_metadata.get('full_name')

                logger.info(f"获取用户信息成功: {user_data.get('email', 'unknown')}")
                return user_data
            return None

        except Exception as e:
            logger.error(f"获取当前用户失败: {e}")
            return None

    async def update_user_profile(self, user_id: str, profile_data: Dict) -> Optional[Dict]:
        """
        更新用户档案

        Args:
            user_id: 用户ID
            profile_data: 档案更新数据

        Returns:
            更新后的用户档案字典，失败返回None
        """
        if not self.is_available():
            logger.error("认证服务不可用")
            return None

        try:
            updated_profile = await self.supabase.update_profile(user_id, profile_data)

            if updated_profile:
                logger.info(f"用户档案更新成功: {user_id}")
                return updated_profile
            return None

        except Exception as e:
            logger.error(f"用户档案更新失败 {user_id}: {e}")
            return None

    async def check_user_permission(self,
                                  user: Dict,
                                  required_permission: str) -> bool:
        """
        检查用户权限

        Args:
            user: 用户信息字典
            required_permission: 需要的权限

        Returns:
            是否有权限
        """
        if not user:
            return False

        # 超级管理员拥有所有权限
        if user.get('is_superuser', False):
            return True

        # 基础权限检查逻辑
        user_permissions = user.get('permissions', [])

        if isinstance(user_permissions, list):
            return required_permission in user_permissions

        # 如果没有明确的权限列表，根据用户角色判断
        user_role = user.get('role', 'user')

        role_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_projects'],
            'manager': ['read', 'write', 'delete', 'manage_projects'],
            'member': ['read', 'write'],
            'user': ['read'],
        }

        return required_permission in role_permissions.get(user_role, ['read'])

    async def check_project_access(self,
                                 user: Dict,
                                 project_id: str,
                                 required_role: str = 'member') -> bool:
        """
        检查用户项目访问权限

        Args:
            user: 用户信息字典
            project_id: 项目ID
            required_role: 需要的最低角色

        Returns:
            是否有访问权限
        """
        if not user or not project_id:
            return False

        user_id = user.get('id')
        if not user_id:
            return False

        # 超级管理员可以访问所有项目
        if user.get('is_superuser', False):
            return True

        try:
            has_permission = await self.supabase.check_project_permission(
                user_id=user_id,
                project_id=project_id,
                required_role=required_role
            )
            return has_permission

        except Exception as e:
            logger.error(f"检查项目权限失败: {e}")
            return False

    async def get_user_projects(self, user: Dict) -> List[Dict]:
        """
        获取用户可访问的项目列表

        Args:
            user: 用户信息字典

        Returns:
            项目列表
        """
        if not user:
            return []

        user_id = user.get('id')
        if not user_id:
            return []

        try:
            projects = await self.supabase.get_user_projects(user_id)
            return projects

        except Exception as e:
            logger.error(f"获取用户项目失败 {user_id}: {e}")
            return []

    async def change_password(self,
                             user: Dict,
                             current_password: str,
                             new_password: str) -> bool:
        """
        修改用户密码

        Args:
            user: 用户信息字典
            current_password: 当前密码
            new_password: 新密码

        Returns:
            修改是否成功
        """
        if not user or not self.is_available():
            return False

        try:
            email = user.get('email')
            if not email:
                return False

            # 验证当前密码
            auth_result = await self.authenticate_user(email, current_password)
            if not auth_result:
                return False

            # Supabase通过auth.admin.update_user方法修改密码
            # 注意：这需要service_role权限
            if not self.supabase.admin_client_available:
                logger.error("Supabase管理员客户端不可用，无法修改密码")
                return False
            
            response = self.supabase.admin_client.auth.admin.update_user_by_id(
                user['id'],
                {'password': new_password}
            )

            success = response.user is not None
            if success:
                logger.info(f"密码修改成功: {email}")
            return success

        except Exception as e:
            logger.error(f"密码修改失败: {e}")
            return False

    async def reset_password(self, email: str) -> bool:
        """
        重置用户密码（发送密码重置邮件）

        Args:
            email: 用户邮箱

        Returns:
            重置邮件发送是否成功
        """
        if not self.is_available():
            return False

        try:
            response = self.supabase.client.auth.reset_password_for_email(email)
            success = response.data is not None

            if success:
                logger.info(f"密码重置邮件发送成功: {email}")
            return success

        except Exception as e:
            logger.error(f"密码重置邮件发送失败 {email}: {e}")
            return False

    async def delete_user_account(self, user: Dict, password: str) -> bool:
        """
        删除用户账户

        Args:
            user: 用户信息字典
            password: 用户密码（确认删除）

        Returns:
            删除是否成功
        """
        if not user or not self.is_available():
            return False

        try:
            # 验证密码
            email = user.get('email')
            if not email:
                return False

            auth_result = await self.authenticate_user(email, password)
            if not auth_result:
                return False

            # 删除用户（需要service_role权限）
            if not self.supabase.admin_client_available:
                logger.error("Supabase管理员客户端不可用，无法删除用户")
                return False
            
            response = self.supabase.admin_client.auth.admin.delete_user(user['id'])
            success = response.data is not None

            if success:
                logger.info(f"用户账户删除成功: {email}")
            return success

        except Exception as e:
            logger.error(f"用户账户删除失败: {e}")
            return False

    def create_session_data(self, user: Dict, tokens: Dict) -> Dict:
        """
        创建会话数据

        Args:
            user: 用户信息
            tokens: 令牌信息

        Returns:
            会话数据字典
        """
        return {
            'user': {
                'id': user.get('id'),
                'email': user.get('email'),
                'username': user.get('username'),
                'full_name': user.get('full_name'),
                'avatar_url': user.get('avatar_url'),
                'is_superuser': user.get('is_superuser', False)
            },
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'token_type': 'bearer',
            'expires_in': tokens.get('expires_in', self.token_expire_minutes * 60),
            'login_time': datetime.utcnow().isoformat()
        }

    async def validate_token(self, access_token: str) -> Optional[Dict]:
        """
        验证访问令牌的有效性

        Args:
            access_token: 访问令牌

        Returns:
            用户信息字典，token无效返回None
        """
        return await self.get_current_user(access_token)

    def is_token_expired(self, user_data: Dict) -> bool:
        """
        检查令牌是否过期

        Args:
            user_data: 包含登录时间的用户数据

        Returns:
            令牌是否过期
        """
        if not user_data:
            return True

        login_time_str = user_data.get('login_time')
        if not login_time_str:
            return True

        try:
            login_time = datetime.fromisoformat(login_time_str.replace('Z', '+00:00'))
            expiry_time = login_time + timedelta(minutes=self.token_expire_minutes)
            return datetime.utcnow() > expiry_time

        except Exception:
            return True

    async def get_user_permissions(self, user: Dict) -> List[str]:
        """
        获取用户权限列表

        Args:
            user: 用户信息字典

        Returns:
            用户权限列表
        """
        if not user:
            return []

        # 超级管理员拥有所有权限
        if user.get('is_superuser', False):
            return [
                'read', 'write', 'delete', 'manage_users', 'manage_projects',
                'view_all_projects', 'manage_system', 'admin_access'
            ]

        # 基于角色获取权限
        role_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_projects'],
            'manager': ['read', 'write', 'delete', 'manage_projects'],
            'member': ['read', 'write'],
            'user': ['read'],
        }

        user_role = user.get('role', 'user')
        return role_permissions.get(user_role, ['read'])

    async def health_check(self) -> Dict[str, Any]:
        """
        检查认证服务健康状态

        Returns:
            健康状态字典
        """
        status = {
            'available': False,
            'supabase_connection': False,
            'auth_service': False,
            'user_registration': False,
            'user_authentication': False
        }

        if not self.is_available():
            return status

        try:
            status['available'] = True

            # 检查Supabase连接
            supabase_health = await self.supabase.health_check()
            status['supabase_connection'] = supabase_health.get('connection', False)

            # 检查认证服务可用性
            try:
                # 尝试获取当前会话状态
                self.supabase.client.auth.get_session()
                status['auth_service'] = True
            except:
                status['auth_service'] = False

            # 检查用户注册功能
            status['user_registration'] = status['supabase_connection']

            # 检查用户认证功能
            status['user_authentication'] = status['supabase_connection']

        except Exception as e:
            logger.error(f"认证服务健康检查失败: {e}")

        return status


# 全局认证服务实例
supabase_auth_service = SupabaseAuthService()