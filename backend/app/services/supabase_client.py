#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Supabase客户端封装服务

提供统一的Supabase数据库和认证服务接口。
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


def user_to_dict(user) -> Dict:
    """
    将Supabase User对象转换为字典
    
    Args:
        user: Supabase User对象（Pydantic模型）
    
    Returns:
        用户信息字典
    """
    if user is None:
        return {}
    
    return {
        'id': getattr(user, 'id', None),
        'email': getattr(user, 'email', None),
        'email_confirmed_at': getattr(user, 'email_confirmed_at', None),
        'created_at': getattr(user, 'created_at', None),
        'updated_at': getattr(user, 'updated_at', None),
        'user_metadata': getattr(user, 'user_metadata', {}),
        'app_metadata': getattr(user, 'app_metadata', {}),
        'phone': getattr(user, 'phone', None),
        'banned_until': getattr(user, 'banned_until', None),
    }


class SupabaseService:
    """Supabase服务封装类"""

    def __init__(self):
        """初始化Supabase客户端"""
        if not settings.use_supabase:
            logger.warning("Supabase配置未设置，某些功能将不可用")
            self.client = None
            self.admin_client = None
            return

        try:
            # 用户认证操作使用Anon Key
            anon_key = settings.supabase_anon_key
            if anon_key:
                self.client: Client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=anon_key
                )
                logger.info("Supabase客户端初始化成功 (使用Anon Key)")
            else:
                self.client = None
                logger.warning("Supabase Anon Key未设置，用户认证功能将不可用")
            
            # 管理员操作使用Service Key
            if settings.SUPABASE_SERVICE_KEY:
                self.admin_client: Client = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_SERVICE_KEY
                )
                logger.info("Supabase管理员客户端初始化成功 (使用Service Key)")
            else:
                self.admin_client = None
                logger.warning("Supabase Service Key未设置，管理员功能将不可用")
                
        except Exception as e:
            logger.error(f"Supabase客户端初始化失败: {e}")
            self.client = None
            self.admin_client = None

    def is_available(self) -> bool:
        """检查Supabase服务是否可用"""
        return self.client is not None

    @property
    def admin_client_available(self) -> bool:
        """检查管理员客户端是否可用"""
        return self.admin_client is not None

    def set_auth_context(self, token: str) -> bool:
        """
        设置Supabase客户端的认证上下文

        Args:
            token: JWT访问令牌

        Returns:
            设置是否成功
        """
        try:
            if self.client and token:
                # 设置session，需要access_token和refresh_token参数
                # 这里只有access_token，refresh_token可以设为空字符串
                self.client.auth.set_session(token, '')
                logger.debug("✅ Supabase客户端认证上下文设置成功")
                return True
            return False
        except Exception as e:
            logger.error(f"设置Supabase认证上下文失败: {e}")
            return False

    def clear_auth_context(self) -> bool:
        """
        清除Supabase客户端的认证上下文

        Returns:
            清除是否成功
        """
        try:
            if self.client:
                self.client.auth.sign_out()
                logger.debug("✅ Supabase客户端认证上下文清除成功")
                return True
            return False
        except Exception as e:
            logger.error(f"清除Supabase认证上下文失败: {e}")
            return False

    # ========================================
    # 认证相关方法
    # ========================================

    async def get_user_from_token(self, token: str) -> Optional[Dict]:
        """
        从JWT token获取用户信息

        Args:
            token: JWT token字符串

        Returns:
            用户信息字典，如果token无效返回None
        """
        if not self.client:
            return None

        try:
            # 使用Supabase验证token
            user_response = self.client.auth.get_user(token)
            if user_response and user_response.user:
                user_dict = user_to_dict(user_response.user)
                logger.info(f"用户认证成功: {user_dict.get('email', 'unknown')}")
                return user_dict
            return None
        except Exception as e:
            logger.error(f"Token验证失败: {e}")
            return None

    async def sign_up(self, email: str, password: str, user_metadata: Optional[Dict] = None) -> Optional[Dict]:
        """
        用户注册

        Args:
            email: 用户邮箱
            password: 用户密码
            user_metadata: 用户元数据

        Returns:
            用户信息字典，注册失败返回None
        """
        if not self.client:
            logger.error("Supabase客户端未初始化，无法进行用户注册")
            return None

        try:
            # 使用anon key客户端注册用户
            # 注意：如果启用了邮箱验证，用户需要验证邮箱后才能登录
            response = self.client.auth.sign_up({
                'email': email,
                'password': password,
                'options': {
                    'data': user_metadata or {},
                    'email_redirect_to': None  # 可以设置重定向URL
                }
            })

            if response.user:
                user_dict = user_to_dict(response.user)
                logger.info(f"用户注册成功: {email}")
                return user_dict
            
            # 检查响应中的错误信息
            if hasattr(response, 'error') and response.error:
                error_msg = response.error.message if hasattr(response.error, 'message') else str(response.error)
                logger.error(f"用户注册失败 {email}: {error_msg}")
            else:
                logger.warning(f"用户注册失败 {email}: 响应中没有用户信息")
            
            return None
        except Exception as e:
            logger.error(f"用户注册失败 {email}: {e}", exc_info=True)
            return None
    
    async def admin_create_user(self, email: str, password: str, user_metadata: Optional[Dict] = None, email_confirm: bool = True) -> Optional[Dict]:
        """
        使用Admin API创建用户（自动确认邮箱，无需验证）

        Args:
            email: 用户邮箱
            password: 用户密码
            user_metadata: 用户元数据
            email_confirm: 是否自动确认邮箱（默认True）

        Returns:
            用户信息字典，创建失败返回None
        """
        if not self.admin_client:
            logger.error("Supabase管理员客户端未初始化，无法创建用户")
            return None

        try:
            # 使用Admin API创建用户，可以自动确认邮箱（需要Service Key）
            response = self.admin_client.auth.admin.create_user({
                'email': email,
                'password': password,
                'email_confirm': email_confirm,  # 自动确认邮箱
                'user_metadata': user_metadata or {}
            })

            if response.user:
                user_dict = user_to_dict(response.user)
                logger.info(f"管理员创建用户成功: {email} (邮箱已自动确认)")
                return user_dict
            
            # 检查响应中的错误信息
            if hasattr(response, 'error') and response.error:
                error_msg = response.error.message if hasattr(response.error, 'message') else str(response.error)
                logger.error(f"管理员创建用户失败 {email}: {error_msg}")
            else:
                logger.warning(f"管理员创建用户失败 {email}: 响应中没有用户信息")
            
            return None
        except Exception as e:
            logger.error(f"管理员创建用户失败 {email}: {e}", exc_info=True)
            return None
    
    async def admin_reset_password(self, email: str, new_password: str) -> bool:
        """
        使用Admin API重置用户密码（无需旧密码）

        Args:
            email: 用户邮箱
            new_password: 新密码

        Returns:
            重置是否成功
        """
        if not self.admin_client:
            logger.error("Supabase管理员客户端未初始化，无法重置密码")
            return False

        try:
            # 先查找用户（使用admin客户端）
            users_response = self.admin_client.auth.admin.list_users()
            target_user = None
            
            if hasattr(users_response, 'users'):
                for user in users_response.users:
                    if hasattr(user, 'email') and user.email == email:
                        target_user = user
                        break
            elif isinstance(users_response, dict) and 'users' in users_response:
                for user_data in users_response['users']:
                    if isinstance(user_data, dict) and user_data.get('email') == email:
                        target_user = user_data
                        break
            
            if not target_user:
                logger.error(f"未找到用户: {email}")
                return False
            
            user_id = target_user.id if hasattr(target_user, 'id') else target_user.get('id')
            
            # 使用Admin API更新密码（需要Service Key）
            response = self.admin_client.auth.admin.update_user_by_id(
                user_id,
                {'password': new_password}
            )
            
            if response.user:
                logger.info(f"管理员重置密码成功: {email}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"管理员重置密码失败 {email}: {e}", exc_info=True)
            return False

    async def sign_in(self, email: str, password: str) -> Optional[Dict]:
        """
        用户登录

        Args:
            email: 用户邮箱
            password: 用户密码

        Returns:
            包含用户信息和token的字典，登录失败返回None
        """
        if not self.client:
            logger.error("Supabase客户端未初始化，无法进行用户登录")
            return None

        try:
            # 使用anon key客户端进行用户登录
            response = self.client.auth.sign_in_with_password({
                'email': email,
                'password': password
            })

            if response.user:
                # 检查用户邮箱是否已验证
                user = response.user
                # User对象是Pydantic模型，使用属性访问或转换为字典
                # 使用getattr安全访问属性
                email_confirmed_at = getattr(user, 'email_confirmed_at', None)
                email_confirmed = email_confirmed_at is not None
                
                # 检查用户是否被禁用
                banned_until = getattr(user, 'banned_until', None)
                is_banned = banned_until is not None
                
                if not email_confirmed:
                    logger.warning(f"用户邮箱未验证: {email}")
                    # 注意：如果Supabase要求邮箱验证，未验证的用户可能无法登录
                    # 这里仍然返回用户信息，但前端可能需要提示用户验证邮箱
                
                if is_banned:
                    logger.error(f"用户被禁用: {email}, 禁用直到: {banned_until}")
                    return None
                
                # 检查是否有session（登录成功）
                if response.session:
                    # 将User对象转换为字典以便返回
                    user_dict = user_to_dict(user)
                    
                    logger.info(f"用户登录成功: {email}")
                    logger.info(f"   邮箱已验证: {email_confirmed}")
                    logger.info(f"   用户ID: {user_dict.get('id', 'N/A')}")
                    
                    return {
                        'user': user_dict,
                        'session': {
                            'access_token': response.session.access_token,
                            'refresh_token': response.session.refresh_token,
                            'expires_in': getattr(response.session, 'expires_in', None),
                            'expires_at': getattr(response.session, 'expires_at', None),
                            'token_type': getattr(response.session, 'token_type', 'bearer'),
                        },
                        'access_token': response.session.access_token,
                        'refresh_token': response.session.refresh_token,
                        'email_confirmed': email_confirmed
                    }
                else:
                    logger.warning(f"用户登录成功但无session: {email}")
                    logger.warning(f"   这可能表示邮箱未验证或其他限制")
                    return None
            
            # 检查响应中的错误信息
            if hasattr(response, 'error') and response.error:
                error_msg = response.error.message if hasattr(response.error, 'message') else str(response.error)
                logger.error(f"用户登录失败 {email}: {error_msg}")
            else:
                logger.warning(f"用户登录失败 {email}: 响应中没有用户信息")
            
            return None
        except Exception as e:
            logger.error(f"用户登录失败 {email}: {e}", exc_info=True)
            return None

    async def sign_out(self, token: str) -> bool:
        """
        用户登出

        Args:
            token: JWT token

        Returns:
            登出是否成功
        """
        if not self.client:
            return False

        try:
            self.client.auth.sign_out(token)
            logger.info("用户登出成功")
            return True
        except Exception as e:
            logger.error(f"用户登出失败: {e}")
            return False

    # ========================================
    # 数据库操作方法 - 用户档案
    # ========================================

    async def get_profile(self, user_id: str) -> Optional[Dict]:
        """
        获取用户档案

        Args:
            user_id: 用户ID

        Returns:
            用户档案字典，不存在返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('profiles').select('*').eq('id', user_id).execute()

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"获取用户档案失败 {user_id}: {e}")
            return None

    async def update_profile(self, user_id: str, profile_data: Dict) -> Optional[Dict]:
        """
        更新用户档案

        Args:
            user_id: 用户ID
            profile_data: 要更新的档案数据

        Returns:
            更新后的用户档案字典，更新失败返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('profiles').update({
                **profile_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', user_id).execute()

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"更新用户档案失败 {user_id}: {e}")
            return None

    # ========================================
    # 数据库操作方法 - 项目管理
    # ========================================

    async def create_project(self, project_data: Dict) -> Optional[Dict]:
        """
        创建项目

        Args:
            project_data: 项目数据字典

        Returns:
            创建的项目字典，创建失败返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('projects').insert({
                **project_data,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

            if response.data:
                logger.info(f"项目创建成功: {project_data.get('name', 'unknown')}")
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"项目创建失败: {e}")
            return None

    async def get_user_projects(self, user_id: str) -> List[Dict]:
        """
        获取用户可访问的项目列表

        Args:
            user_id: 用户ID

        Returns:
            项目列表
        """
        if not self.client:
            return []

        try:
            response = self.client.table('user_projects').select('*').eq('user_id', user_id).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"获取用户项目列表失败 {user_id}: {e}")
            return []

    async def get_project_details(self, project_id: str) -> Optional[Dict]:
        """
        获取项目详情

        Args:
            project_id: 项目ID

        Returns:
            项目详情字典，不存在返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('projects').select('*').eq('id', project_id).execute()

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"获取项目详情失败 {project_id}: {e}")
            return None

    async def update_project(self, project_id: str, project_data: Dict) -> Optional[Dict]:
        """
        更新项目信息

        Args:
            project_id: 项目ID
            project_data: 要更新的项目数据

        Returns:
            更新后的项目字典，更新失败返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('projects').update({
                **project_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"更新项目失败 {project_id}: {e}")
            return None

    # ========================================
    # 数据库操作方法 - 项目成员
    # ========================================

    async def add_project_member(self, project_id: str, user_id: str, role: str = 'member') -> bool:
        """
        添加项目成员

        Args:
            project_id: 项目ID
            user_id: 用户ID
            role: 成员角色

        Returns:
            添加是否成功
        """
        if not self.client:
            return False

        try:
            response = self.client.table('project_members').insert({
                'project_id': project_id,
                'user_id': user_id,
                'role': role,
                'joined_at': datetime.utcnow().isoformat()
            }).execute()

            success = len(response.data) > 0
            if success:
                logger.info(f"项目成员添加成功: {project_id} - {user_id}")
            return success
        except Exception as e:
            logger.error(f"添加项目成员失败: {e}")
            return False

    async def get_project_members(self, project_id: str) -> List[Dict]:
        """
        获取项目成员列表

        Args:
            project_id: 项目ID

        Returns:
            成员列表
        """
        if not self.client:
            return []

        try:
            response = self.client.table('project_members').select(
                '''
                *,
                user:profiles(id, username, full_name, avatar_url)
                '''
            ).eq('project_id', project_id).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"获取项目成员列表失败 {project_id}: {e}")
            return []

    async def update_project_member_role(self, project_id: str, user_id: str, role: str) -> bool:
        """
        更新项目成员角色

        Args:
            project_id: 项目ID
            user_id: 用户ID
            role: 新角色

        Returns:
            更新是否成功
        """
        if not self.client:
            return False

        try:
            response = self.client.table('project_members').update({
                'role': role
            }).eq('project_id', project_id).eq('user_id', user_id).execute()

            success = len(response.data) > 0
            if success:
                logger.info(f"项目成员角色更新成功: {project_id} - {user_id} -> {role}")
            return success
        except Exception as e:
            logger.error(f"更新项目成员角色失败: {e}")
            return False

    async def remove_project_member(self, project_id: str, user_id: str) -> bool:
        """
        移除项目成员

        Args:
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            移除是否成功
        """
        if not self.client:
            return False

        try:
            response = self.client.table('project_members').delete().eq(
                'project_id', project_id
            ).eq('user_id', user_id).execute()

            success = len(response.data) > 0
            if success:
                logger.info(f"项目成员移除成功: {project_id} - {user_id}")
            return success
        except Exception as e:
            logger.error(f"移除项目成员失败: {e}")
            return False

    async def check_project_permission(self, user_id: str, project_id: str, required_role: str) -> bool:
        """
        检查用户在项目中的权限

        Args:
            user_id: 用户ID
            project_id: 项目ID
            required_role: 需要的最低角色

        Returns:
            是否有权限
        """
        if not self.client:
            return False

        try:
            # 检查是否为项目创建者
            project = await self.get_project_details(project_id)
            if project and project.get('created_by') == user_id:
                return True

            # 检查项目成员角色
            response = self.client.table('project_members').select('role').eq(
                'project_id', project_id
            ).eq('user_id', user_id).execute()

            if response.data:
                user_role = response.data[0]['role']
                role_hierarchy = {'owner': 4, 'admin': 3, 'member': 2, 'viewer': 1}

                return role_hierarchy.get(user_role, 0) >= role_hierarchy.get(required_role, 0)

            return False
        except Exception as e:
            logger.error(f"检查项目权限失败: {e}")
            return False

    # ========================================
    # 数据库操作方法 - 文件管理
    # ========================================

    async def create_file_record(self, file_data: Dict, access_token: Optional[str] = None) -> Optional[Dict]:
        """
        创建文件记录
        优先使用admin_client（Service Key）绕过RLS限制
        如果admin_client不可用，使用client并设置认证上下文

        Args:
            file_data: 文件数据字典
            access_token: 可选的访问令牌（用于设置client的认证上下文）

        Returns:
            创建的文件记录字典，创建失败返回None
        """
        # 优先使用admin_client（Service Key）绕过RLS限制
        client_to_use = None
        use_auth_context = False
        
        if self.admin_client:
            client_to_use = self.admin_client
            logger.info("✅ 使用admin_client创建文件记录（Service Key）")
        elif self.client:
            client_to_use = self.client
            use_auth_context = True
            logger.warning("⚠️ admin_client不可用，使用client创建文件记录（需要设置认证上下文）")
            if not access_token:
                logger.error("❌ 使用client但未提供access_token，可能无法创建文件记录")
        else:
            logger.error("❌ Supabase客户端未初始化，无法创建文件记录")
            return None

        # 如果使用client，需要设置认证上下文
        if use_auth_context and access_token:
            auth_set = self.set_auth_context(access_token)
            if not auth_set:
                logger.warning("⚠️ 设置认证上下文失败，可能影响文件记录创建")
        
        try:
            response = client_to_use.table('files').insert({
                **file_data,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

            if response.data:
                logger.info(f"✅ 文件记录创建成功: {file_data.get('original_name', 'unknown')}")
                return response.data[0]
            else:
                logger.warning(f"⚠️ 文件记录创建响应为空: {file_data.get('original_name', 'unknown')}")
                return None
        except Exception as e:
            logger.error(f"❌ 文件记录创建失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 如果使用admin_client失败，尝试使用client（如果提供了access_token）
            if client_to_use == self.admin_client and self.client and access_token:
                logger.info("🔄 admin_client失败，尝试使用client并设置认证上下文")
                try:
                    auth_set = self.set_auth_context(access_token)
                    if auth_set:
                        response = self.client.table('files').insert({
                            **file_data,
                            'created_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        }).execute()
                        if response.data:
                            logger.info(f"✅ 使用client创建文件记录成功: {file_data.get('original_name', 'unknown')}")
                            return response.data[0]
                except Exception as retry_error:
                    logger.error(f"❌ 使用client重试也失败: {retry_error}")
            
            return None
        finally:
            # 清理认证上下文（如果设置了）
            if use_auth_context:
                try:
                    self.clear_auth_context()
                except Exception:
                    pass

    async def get_project_files(self, project_id: str) -> List[Dict]:
        """
        获取项目文件列表

        Args:
            project_id: 项目ID

        Returns:
            文件列表
        """
        if not self.client:
            return []

        try:
            response = self.client.table('files').select('*').eq('project_id', project_id).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"获取项目文件列表失败 {project_id}: {e}")
            return []

    # ========================================
    # 数据库操作方法 - 聊天
    # ========================================

    async def create_chat_session(self, session_data: Dict) -> Optional[Dict]:
        """
        创建聊天会话

        Args:
            session_data: 会话数据字典

        Returns:
            创建的会话记录字典，创建失败返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('chat_sessions').insert({
                **session_data,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute()

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"聊天会话创建失败: {e}")
            return None

    async def create_chat_message(self, message_data: Dict) -> Optional[Dict]:
        """
        创建聊天消息

        Args:
            message_data: 消息数据字典

        Returns:
            创建的消息记录字典，创建失败返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('chat_messages').insert({
                **message_data,
                'created_at': datetime.utcnow().isoformat()
            }).execute()

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"聊天消息创建失败: {e}")
            return None

    async def get_chat_session_messages(self, session_id: str) -> List[Dict]:
        """
        获取聊天会话消息列表

        Args:
            session_id: 会话ID

        Returns:
            消息列表
        """
        if not self.client:
            return []

        try:
            response = self.client.table('chat_messages').select('*').eq(
                'session_id', session_id
            ).order('created_at', asc=True).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"获取聊天消息失败 {session_id}: {e}")
            return []

    async def get_user_chat_sessions(self, user_id: str) -> List[Dict]:
        """
        获取用户聊天会话列表

        Args:
            user_id: 用户ID

        Returns:
            会话列表
        """
        if not self.client:
            return []

        try:
            response = self.client.table('chat_sessions').select('*').eq(
                'user_id', user_id
            ).order('updated_at', desc=True).execute()

            return response.data or []
        except Exception as e:
            logger.error(f"获取用户聊天会话失败 {user_id}: {e}")
            return []
    
    async def get_chat_session(self, session_id: str) -> Optional[Dict]:
        """
        获取单个聊天会话

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典，不存在返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('chat_sessions').select('*').eq(
                'id', session_id
            ).single().execute()

            return response.data if response.data else None
        except Exception as e:
            logger.error(f"获取聊天会话失败 {session_id}: {e}")
            return None
    
    async def update_chat_session(self, session_id: str, update_data: Dict) -> Optional[Dict]:
        """
        更新聊天会话

        Args:
            session_id: 会话ID
            update_data: 要更新的数据

        Returns:
            更新后的会话信息字典，更新失败返回None
        """
        if not self.client:
            return None

        try:
            response = self.client.table('chat_sessions').update({
                **update_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', session_id).execute()

            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"更新聊天会话失败 {session_id}: {e}")
            return None
    
    async def delete_chat_session(self, session_id: str) -> bool:
        """
        删除聊天会话

        Args:
            session_id: 会话ID

        Returns:
            删除是否成功
        """
        if not self.client:
            return False

        try:
            response = self.client.table('chat_sessions').delete().eq(
                'id', session_id
            ).execute()

            return len(response.data) > 0 if response.data else False
        except Exception as e:
            logger.error(f"删除聊天会话失败 {session_id}: {e}")
            return False
    
    async def get_chat_stats(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """
        获取聊天统计信息

        Args:
            user_id: 用户ID（可选，如果提供则只统计该用户的）

        Returns:
            统计信息字典
        """
        if not self.client:
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'ai_messages': 0
            }

        try:
            # 统计会话数
            sessions_query = self.client.table('chat_sessions').select('id', count='exact')
            if user_id:
                sessions_query = sessions_query.eq('user_id', user_id)
            sessions_response = sessions_query.execute()
            total_conversations = sessions_response.count if hasattr(sessions_response, 'count') else 0

            # 统计消息数
            messages_query = self.client.table('chat_messages').select('id', count='exact')
            if user_id:
                # 需要通过session关联查询
                user_sessions = await self.get_user_chat_sessions(user_id)
                session_ids = [s['id'] for s in user_sessions]
                if session_ids:
                    messages_query = messages_query.in_('session_id', session_ids)
                else:
                    total_messages = 0
                    ai_messages = 0
                    return {
                        'total_conversations': total_conversations,
                        'total_messages': 0,
                        'ai_messages': 0
                    }
            messages_response = messages_query.execute()
            total_messages = messages_response.count if hasattr(messages_response, 'count') else 0

            # 统计AI消息数
            ai_query = self.client.table('chat_messages').select('id', count='exact').eq('role', 'assistant')
            if user_id:
                user_sessions = await self.get_user_chat_sessions(user_id)
                session_ids = [s['id'] for s in user_sessions]
                if session_ids:
                    ai_query = ai_query.in_('session_id', session_ids)
                else:
                    ai_messages = 0
                    return {
                        'total_conversations': total_conversations,
                        'total_messages': total_messages,
                        'ai_messages': 0
                    }
            ai_response = ai_query.execute()
            ai_messages = ai_response.count if hasattr(ai_response, 'count') else 0

            return {
                'total_conversations': total_conversations,
                'total_messages': total_messages,
                'ai_messages': ai_messages
            }
        except Exception as e:
            logger.error(f"获取聊天统计失败: {e}")
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'ai_messages': 0
            }

    # ========================================
    # 健康检查
    # ========================================

    async def health_check(self) -> Dict[str, Any]:
        """
        检查Supabase服务健康状态

        Returns:
            健康状态字典
        """
        status = {
            'available': False,
            'connection': False,
            'auth': False,
            'database': False
        }

        if not self.client:
            return status

        try:
            status['available'] = True

            # 检查数据库连接
            try:
                response = self.client.table('profiles').select('count').limit(1).execute()
                status['database'] = response.data is not None
            except:
                status['database'] = False

            # 检查认证服务（使用系统token测试）
            try:
                auth_status = self.client.auth.get_session()
                status['auth'] = True
            except:
                status['auth'] = False

            status['connection'] = status['database']  # 数据库连接作为主要连接指标

        except Exception as e:
            logger.error(f"Supabase健康检查失败: {e}")

        return status

    # ========================================
    # 增强权限方法 (基于新的权限模型)
    # ========================================

    async def get_effective_project_permissions(
        self,
        user_id: str,
        project_id: str
    ) -> Optional[Dict]:
        """
        获取用户在项目中的完整权限 (使用新的权限系统)

        Args:
            user_id: 用户ID
            project_id: 项目ID

        Returns:
            权限字典，包含所有权限信息
        """
        if not self.client:
            return None

        try:
            response = self.client.rpc(
                'get_effective_project_permissions',
                {
                    'project_uuid': project_id,
                    'user_uuid': user_id
                }
            ).execute()

            return response.data[0] if response.data else None

        except Exception as e:
            logger.error(f"获取项目有效权限失败: {e}")
            return None

    async def has_project_permission(
        self,
        user_id: str,
        project_id: str,
        required_permission: str = 'read'
    ) -> bool:
        """
        检查用户是否有特定项目权限 (使用新的权限系统)

        Args:
            user_id: 用户ID
            project_id: 项目ID
            required_permission: 需要的权限类型 ('read', 'write', 'delete', 'manage_members', 'manage_settings')

        Returns:
            是否有权限
        """
        if not self.client:
            return False

        try:
            response = self.client.rpc(
                'has_project_permission',
                {
                    'project_uuid': project_id,
                    'user_uuid': user_id,
                    'required_permission': required_permission
                }
            ).execute()

            return response.data == True if response.data else False

        except Exception as e:
            logger.error(f"检查项目权限失败: {e}")
            return False

    async def get_user_accessible_projects_enhanced(
        self,
        user_id: str
    ) -> List[Dict]:
        """
        获取用户可访问的项目列表 (使用权限视图)

        Args:
            user_id: 用户ID

        Returns:
            项目列表，包含用户在项目中的角色和权限级别
        """
        if not self.client:
            return []

        try:
            response = self.client.table('user_accessible_projects').select('*').execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取用户可访问项目失败: {e}")
            return []

    async def get_user_permission_summary(
        self,
        user_id: str
    ) -> Optional[Dict]:
        """
        获取用户权限汇总信息

        Args:
            user_id: 用户ID

        Returns:
            用户权限汇总字典
        """
        if not self.client:
            return None

        try:
            response = self.client.table('user_permission_summary').select('*').eq(
                'user_id', user_id
            ).single().execute()

            return response.data if response.data else None

        except Exception as e:
            logger.error(f"获取用户权限汇总失败: {e}")
            return None

    async def add_project_member_enhanced(
        self,
        project_id: str,
        user_id: str,
        role: str = 'member',
        invited_by: Optional[str] = None
    ) -> bool:
        """
        添加项目成员 (增强版本)

        Args:
            project_id: 项目ID
            user_id: 用户ID
            role: 角色
            invited_by: 邀请人ID

        Returns:
            添加是否成功
        """
        if not self.client:
            return False

        try:
            response = self.client.table('project_members').insert({
                'project_id': project_id,
                'user_id': user_id,
                'role': role,
                'invited_by': invited_by,
                'is_active': True,
                'permissions': '{}',
                'joined_at': datetime.utcnow().isoformat()
            }).execute()

            if response.data:
                logger.info(f"项目成员添加成功: {user_id} -> {project_id} ({role})")
                return True
            return False

        except Exception as e:
            logger.error(f"添加项目成员失败: {e}")
            return False

    async def get_project_members_with_profiles(
        self,
        project_id: str
    ) -> List[Dict]:
        """
        获取项目成员列表（包含用户档案信息）

        Args:
            project_id: 项目ID

        Returns:
            成员列表，包含用户档案信息
        """
        if not self.client:
            return []

        try:
            response = self.client.table('project_members').select('''
                *,
                profiles!project_members_user_id_fkey (
                    id, username, full_name, email, avatar_url, system_role
                )
            ''').eq('project_id', project_id).eq('is_active', True).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取项目成员失败: {e}")
            return []

    async def get_permission_audit_log(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取权限审计日志

        Args:
            entity_type: 实体类型
            entity_id: 实体ID
            limit: 返回数量限制

        Returns:
            审计日志列表
        """
        if not self.client:
            return []

        try:
            query = self.client.table('permission_audit_log').select('''
                *,
                performed_by_profile:profiles!permission_audit_log_performed_by_fkey (
                    username, full_name
                ),
                target_user_profile:profiles!permission_audit_log_target_user_id_fkey (
                    username, full_name
                )
            ''').order('created_at', desc=True).limit(limit)

            if entity_type:
                query = query.eq('entity_type', entity_type)
            if entity_id:
                query = query.eq('entity_id', entity_id)

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取权限审计日志失败: {e}")
            return []


# 全局Supabase服务实例
supabase_service = SupabaseService()