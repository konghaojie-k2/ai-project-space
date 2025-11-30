#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Supabase客户端封装服务

提供统一的Supabase数据库和认证服务接口。
"""

import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass

from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class CacheItem:
    """缓存项数据结构"""
    data: Any
    timestamp: float
    ttl: float  # 生存时间（秒）

class PermissionCache:
    """权限缓存管理器"""

    def __init__(self, default_ttl: int = 300):  # 5分钟默认缓存
        self.cache: Dict[str, CacheItem] = {}
        self.default_ttl = default_ttl
        self._lock = asyncio.Lock()

    def _is_expired(self, item: CacheItem) -> bool:
        """检查缓存项是否过期"""
        return time.time() - item.timestamp > item.ttl

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        async with self._lock:
            item = self.cache.get(key)
            if item and not self._is_expired(item):
                logger.debug(f"✅ 缓存命中: {key}")
                return item.data
            elif item and self._is_expired(item):
                # 清理过期缓存
                del self.cache[key]
                logger.debug(f"⏰ 缓存过期: {key}")
        return None

    async def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """设置缓存项"""
        async with self._lock:
            self.cache[key] = CacheItem(
                data=data,
                timestamp=time.time(),
                ttl=ttl or self.default_ttl
            )
            logger.debug(f"💾 缓存设置: {key}")

    async def invalidate(self, pattern: Optional[str] = None) -> None:
        """清理缓存"""
        async with self._lock:
            if pattern:
                # 按模式清理缓存
                keys_to_remove = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self.cache[key]
                logger.debug(f"🗑️ 按模式清理缓存: {pattern}, 清理了 {len(keys_to_remove)} 项")
            else:
                # 清理所有缓存
                count = len(self.cache)
                self.cache.clear()
                logger.debug(f"🗑️ 清理所有缓存: {count} 项")

async def run_supabase_query(query_func, timeout: float = 30.0):
    """
    在线程池中执行Supabase同步查询，避免阻塞事件循环
    
    Args:
        query_func: 返回Supabase查询对象的函数
        timeout: 查询超时时间（秒），默认30秒
        
    Returns:
        查询结果
        
    Raises:
        asyncio.TimeoutError: 如果查询超时
    """
    loop = asyncio.get_event_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(None, query_func),
        timeout=timeout
    )


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
        else:
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
                    try:
                        self.admin_client: Client = create_client(
                            supabase_url=settings.SUPABASE_URL,
                            supabase_key=settings.SUPABASE_SERVICE_KEY
                        )
                        logger.info("✅ Supabase管理员客户端初始化成功 (使用Service Key)")
                        logger.info(f"🔍 Service Key长度: {len(settings.SUPABASE_SERVICE_KEY)} 字符")
                        logger.info(f"🔍 Service Key前缀: {settings.SUPABASE_SERVICE_KEY[:20]}...")
                    except Exception as admin_error:
                        logger.error(f"❌ 创建admin_client失败: {admin_error}")
                        self.admin_client = None
                else:
                    self.admin_client = None
                    logger.warning("⚠️ Supabase Service Key未设置，管理员功能将不可用")
                    logger.warning("⚠️ 提示：请在.env文件中配置SUPABASE_SERVICE_KEY以绕过RLS策略")

            except Exception as e:
                logger.error(f"Supabase客户端初始化失败: {e}")
                self.client = None
                self.admin_client = None

        # 初始化缓存管理器
        self.profile_cache = PermissionCache(default_ttl=600)  # 用户档案缓存10分钟
        self.permission_cache = PermissionCache(default_ttl=300)  # 权限缓存5分钟
        self.projects_cache = PermissionCache(default_ttl=180)  # 项目列表缓存3分钟
        
        # 记录最终初始化状态
        logger.info(f"📊 Supabase服务初始化完成:")
        logger.info(f"   - client (Anon Key): {'✅ 已初始化' if self.client else '❌ 未初始化'}")
        logger.info(f"   - admin_client (Service Key): {'✅ 已初始化' if self.admin_client else '❌ 未初始化'}")
        if not self.admin_client:
            logger.warning("⚠️ 警告: admin_client未初始化，RLS策略可能阻止某些操作")
            logger.warning("⚠️ 请检查.env文件中的SUPABASE_SERVICE_KEY配置")
        self.stats_cache = PermissionCache(default_ttl=120)  # 统计数据缓存2分钟

        # 性能监控
        self.query_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_time': 0.0
        }

    def is_available(self) -> bool:
        """检查Supabase服务是否可用"""
        return self.client is not None

    def is_admin_available(self) -> bool:
        """检查Supabase管理员服务是否可用"""
        return self.admin_client is not None

    @property
    def admin_client_available(self) -> bool:
        """检查管理员客户端是否可用"""
        return self.admin_client is not None

    async def _execute_with_stats(self, query_func, cache_key: str = None,
                                 cache_manager: Optional[PermissionCache] = None,
                                 ttl: Optional[int] = None) -> Any:
        """
        执行查询并记录统计信息，支持缓存
        """
        start_time = time.time()
        self.query_stats['total_queries'] += 1

        # 尝试从缓存获取数据
        if cache_key and cache_manager:
            cached_data = await cache_manager.get(cache_key)
            if cached_data is not None:
                self.query_stats['cache_hits'] += 1
                self.query_stats['total_time'] += time.time() - start_time
                return cached_data
            else:
                self.query_stats['cache_misses'] += 1

        try:
            # 执行查询
            result = await run_supabase_query(query_func)

            # 将结果存入缓存
            if cache_key and cache_manager:
                await cache_manager.set(cache_key, result, ttl)

            self.query_stats['total_time'] += time.time() - start_time
            return result

        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            self.query_stats['total_time'] += time.time() - start_time
            raise

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        hit_rate = 0.0
        if self.query_stats['total_queries'] > 0:
            hit_rate = (self.query_stats['cache_hits'] / self.query_stats['total_queries']) * 100

        return {
            'total_queries': self.query_stats['total_queries'],
            'cache_hits': self.query_stats['cache_hits'],
            'cache_misses': self.query_stats['cache_misses'],
            'hit_rate': f"{hit_rate:.2f}%",
            'average_query_time': f"{self.query_stats['total_time'] / max(1, self.query_stats['total_queries']):.3f}s",
            'profile_cache_size': len(self.profile_cache.cache),
            'permission_cache_size': len(self.permission_cache.cache),
            'projects_cache_size': len(self.projects_cache.cache),
            'stats_cache_size': len(self.stats_cache.cache)
        }

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
            error_msg = str(e)
            # 检查是否使用的是Demo Key（通过JWT解码检查）
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

            # 在开发环境下，如果邮件发送失败但用户可能已创建，尝试获取用户信息
            if settings.DISABLE_EMAIL_VERIFICATION and "Error sending confirmation email" in error_msg:
                logger.warning(f"邮件发送失败，但在开发环境下尝试继续: {email}")
                logger.info(f"用户可能已创建但邮件发送失败: {email}，在开发环境下允许继续")
                # 返回None，让上层逻辑处理

            logger.error(f"用户注册失败 {email}: {error_msg}", exc_info=True)
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
            logger.error("Supabase管理员客户端未初始化，无法创建用户（请检查SUPABASE_SERVICE_KEY配置）")
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
            error_msg = str(e)
            # 401错误通常表示Service Key无效或未配置
            if "401" in error_msg or "Unauthorized" in error_msg or "Invalid authentication credentials" in error_msg:
                logger.error(f"管理员创建用户失败 {email}: Service Key无效或未正确配置（401 Unauthorized）")
                logger.error("请检查.env文件中的SUPABASE_SERVICE_KEY配置是否正确")
            else:
                logger.error(f"管理员创建用户失败 {email}: {error_msg}", exc_info=True)
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
        获取用户档案（优化版，带缓存）

        Args:
            user_id: 用户ID

        Returns:
            用户档案字典，不存在返回None
        """
        cache_key = f"profile:{user_id}"
        client_to_use = self.admin_client if self.admin_client else self.client

        if not client_to_use:
            return None

        query_func = lambda: client_to_use.table('profiles').select(
            'id, username, full_name, avatar_url, bio, is_superuser, system_role, is_active'
        ).eq('id', user_id).single().execute()

        try:
            response = await self._execute_with_stats(
                query_func,
                cache_key=cache_key,
                cache_manager=self.profile_cache,
                ttl=600
            )
            return response.data if response.data else None
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
            response = await run_supabase_query(lambda: self.client.table('profiles').update({
                **profile_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', user_id).execute())

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
        优先使用admin_client（Service Key）绕过RLS限制

        Args:
            project_data: 项目数据字典

        Returns:
            创建的项目字典，创建失败返回None
        """
        # 优先使用admin_client（Service Key）绕过RLS限制
        client_to_use = None
        
        logger.info(f"🔍 检查admin_client状态（创建项目）: admin_client={self.admin_client is not None}, admin_client_available={self.admin_client_available}")
        
        if self.admin_client_available:
            client_to_use = self.admin_client
            logger.info("✅ 使用admin_client创建项目（Service Key，绕过RLS）")
        elif self.client:
            client_to_use = self.client
            logger.warning("⚠️ admin_client不可用，使用client创建项目（可能受RLS策略限制）")
            logger.warning("⚠️ 提示：请检查.env文件中的SUPABASE_SERVICE_KEY配置")
        else:
            logger.error("❌ Supabase客户端未初始化，无法创建项目")
            return None

        try:
            insert_data = {
                **project_data,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            client_type = 'admin_client' if client_to_use == self.admin_client else 'client'
            logger.info(f"📝 创建项目: {project_data.get('name', 'unknown')}, 使用客户端: {client_type}")
            
            response = await run_supabase_query(lambda: client_to_use.table('projects').insert(insert_data).execute())

            if response.data:
                logger.info(f"✅ 项目创建成功: {project_data.get('name', 'unknown')}")
                return response.data[0]
            else:
                logger.warning(f"⚠️ 项目创建响应为空: {project_data.get('name', 'unknown')}")
                return None
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 项目创建失败: {error_msg}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 如果是RLS策略错误，提供更明确的提示
            if "row-level security" in error_msg.lower() or "RLS" in error_msg.upper():
                logger.error("❌ RLS策略违反！请确保：")
                logger.error("   1. SUPABASE_SERVICE_KEY已正确配置在.env文件中")
                logger.error("   2. Service Key具有足够的权限绕过RLS策略")
                logger.error("   3. projects表的RLS策略允许通过Service Key插入数据")
            
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
            response = await run_supabase_query(lambda: self.client.table('user_projects').select('*').eq('user_id', user_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('projects').select('*').eq('id', project_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('projects').update({
                **project_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('project_members').insert({
                'project_id': project_id,
                'user_id': user_id,
                'role': role,
                'joined_at': datetime.utcnow().isoformat()
            }).execute())

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
            response = await run_supabase_query(lambda: self.client.table('project_members').select(
                '''
                *,
                user:profiles(id, username, full_name, avatar_url)
                '''
            ).eq('project_id', project_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('project_members').update({
                'role': role
            }).eq('project_id', project_id).eq('user_id', user_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('project_members').delete().eq(
                'project_id', project_id
            ).eq('user_id', user_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('project_members').select('role').eq(
                'project_id', project_id
            ).eq('user_id', user_id).execute())

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
        
        # 检查admin_client是否可用（注意：admin_client_available是@property，不需要括号）
        logger.info(f"🔍 检查admin_client状态: admin_client={self.admin_client is not None}, admin_client_available={self.admin_client_available}")
        
        if self.admin_client_available:
            client_to_use = self.admin_client
            logger.info("✅ 使用admin_client创建文件记录（Service Key，绕过RLS）")
            logger.info(f"🔍 admin_client类型: {type(self.admin_client)}")
        elif self.client:
            client_to_use = self.client
            use_auth_context = True
            logger.warning("⚠️ admin_client不可用，使用client创建文件记录（需要设置认证上下文）")
            logger.warning("⚠️ 提示：请检查.env文件中的SUPABASE_SERVICE_KEY配置")
            logger.warning(f"⚠️ 当前配置状态: SUPABASE_SERVICE_KEY={'已配置' if settings.SUPABASE_SERVICE_KEY else '未配置'}")
            if not access_token:
                logger.error("❌ 使用client但未提供access_token，可能无法创建文件记录（RLS策略可能阻止）")
        else:
            logger.error("❌ Supabase客户端未初始化，无法创建文件记录")
            logger.error(f"❌ 客户端状态: client={self.client is not None}, admin_client={self.admin_client is not None}")
            return None

        # 如果使用client，需要设置认证上下文
        if use_auth_context and access_token:
            auth_set = self.set_auth_context(access_token)
            if not auth_set:
                logger.warning("⚠️ 设置认证上下文失败，可能影响文件记录创建")
        
        try:
            # 记录使用的客户端类型和文件信息
            client_type = 'admin_client' if client_to_use == self.admin_client else 'client'
            logger.info(f"📝 创建文件记录: {file_data.get('original_name', 'unknown')}, 使用客户端: {client_type}")
            logger.info(f"📝 文件数据: id={file_data.get('id')}, uploaded_by={file_data.get('uploaded_by')}, project_id={file_data.get('project_id')}")
            
            # 确保使用正确的客户端执行插入操作
            insert_data = {
                **file_data,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            logger.info(f"📝 准备插入数据到files表，使用客户端: {client_type}")
            
            response = await run_supabase_query(lambda: client_to_use.table('files').insert(insert_data).execute())

            if response.data:
                logger.info(f"✅ 文件记录创建成功: {file_data.get('original_name', 'unknown')}")
                return response.data[0]
            else:
                logger.warning(f"⚠️ 文件记录创建响应为空: {file_data.get('original_name', 'unknown')}")
                return None
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 文件记录创建失败: {error_msg}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            
            # 如果是RLS策略错误，提供更明确的提示
            if "row-level security" in error_msg.lower() or "RLS" in error_msg.upper():
                logger.error("❌ RLS策略违反！请确保：")
                logger.error("   1. SUPABASE_SERVICE_KEY已正确配置在.env文件中")
                logger.error("   2. Service Key具有足够的权限绕过RLS策略")
                logger.error("   3. files表的RLS策略允许通过Service Key插入数据")
            
            # 如果使用admin_client失败，尝试使用client（如果提供了access_token）
            if client_to_use == self.admin_client and self.client and access_token:
                logger.info("🔄 admin_client失败，尝试使用client并设置认证上下文")
                try:
                    auth_set = self.set_auth_context(access_token)
                    if auth_set:
                        response = await run_supabase_query(lambda: self.client.table('files').insert({
                            **file_data,
                            'created_at': datetime.utcnow().isoformat(),
                            'updated_at': datetime.utcnow().isoformat()
                        }).execute())
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
            response = await run_supabase_query(lambda: self.client.table('files').select('*').eq('project_id', project_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('chat_sessions').insert({
                **session_data,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }).execute())

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
            response = await run_supabase_query(lambda: self.client.table('chat_messages').insert({
                **message_data,
                'created_at': datetime.utcnow().isoformat()
            }).execute())

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
            # Supabase Python客户端的order()方法不接受asc参数
            # 默认是升序，如果要降序使用desc=True
            response = await run_supabase_query(lambda: self.client.table('chat_messages').select('*').eq(
                'session_id', session_id
            ).order('created_at').execute())

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
            response = await run_supabase_query(lambda: self.client.table('chat_sessions').select('*').eq(
                'user_id', user_id
            ).order('updated_at', desc=True).execute())

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
            response = await run_supabase_query(lambda: self.client.table('chat_sessions').select('*').eq(
                'id', session_id
            ).single().execute())

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
            response = await run_supabase_query(lambda: self.client.table('chat_sessions').update({
                **update_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', session_id).execute())

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
            response = await run_supabase_query(lambda: self.client.table('chat_sessions').delete().eq(
                'id', session_id
            ).execute())

            return len(response.data) > 0 if response.data else False
        except Exception as e:
            logger.error(f"删除聊天会话失败 {session_id}: {e}")
            return False
    
    async def get_chat_stats(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """
        获取聊天统计信息（优化版，使用缓存和简化查询）
        """
        cache_key = f"chat_stats:{user_id or 'global'}"
        client_to_use = self.admin_client if self.admin_client else self.client

        if not client_to_use:
            return {
                'total_conversations': 0,
                'total_messages': 0,
                'ai_messages': 0
            }

        # 优化的统计查询，直接使用message_count字段避免复杂JOIN
        if user_id:
            query_func = lambda: client_to_use.table('chat_sessions').select(
                'id, message_count'
            ).eq('user_id', user_id).limit(1000).execute()
        else:
            query_func = lambda: client_to_use.table('chat_sessions').select(
                'id, message_count'
            ).limit(1000).execute()

        try:
            response = await self._execute_with_stats(
                query_func,
                cache_key=cache_key,
                cache_manager=self.stats_cache,
                ttl=120
            )

            if not response.data:
                return {
                    'total_conversations': 0,
                    'total_messages': 0,
                    'ai_messages': 0
                }

            # 简化的统计计算
            sessions = response.data
            total_conversations = len(sessions)
            total_messages = sum(session.get('message_count', 0) for session in sessions)

            # 估算AI消息数量（假设50%是AI回复）
            ai_messages = total_messages // 2

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

            # 检查数据库连接（使用更快的表）
            try:
                response = await run_supabase_query(lambda: self.client.table('files').select('count').limit(1).execute())
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
        user_id: str,
        limit: int = 100,
        is_superuser: bool = False
    ) -> List[Dict]:
        """
        获取用户可访问的项目列表 (优化版)

        Args:
            user_id: 用户ID
            limit: 限制返回数量
            is_superuser: 是否是超级管理员

        Returns:
            项目列表，包含用户在项目中的角色和权限级别
        """
        cache_key = f"user_projects:{user_id}:{limit}"
        client_to_use = self.admin_client if self.admin_client else self.client

        if not client_to_use:
            return []

        try:
            # 如果是超级管理员，返回所有项目
            if is_superuser:
                query_func = lambda: client_to_use.table('projects').select(
                    'id, name, description, status, stage, is_public, allow_file_upload, allow_ai_chat, created_by, created_at, updated_at'
                ).order('created_at', desc=True).limit(limit).execute()
                
                response = await self._execute_with_stats(
                    query_func,
                    cache_key=cache_key,
                    cache_manager=self.projects_cache,
                    ttl=180
                )
                
                if response.data:
                    # 为每个项目添加角色信息（管理员默认为owner）
                    return [
                        {
                            **project,
                            'role': 'owner',
                            'is_owner': True
                        }
                        for project in response.data
                    ]
                return []
            
            # 普通用户：查询用户创建的项目 + 用户作为成员的项目
            # 1. 查询用户创建的项目
            created_projects_query = lambda: client_to_use.table('projects').select(
                'id, name, description, status, stage, is_public, allow_file_upload, allow_ai_chat, created_by, created_at, updated_at'
            ).eq('created_by', user_id).order('created_at', desc=True).execute()
            
            created_response = await run_supabase_query(created_projects_query)
            created_projects = created_response.data if created_response.data else []
            
            # 2. 查询用户作为成员的项目
            members_query = lambda: client_to_use.table('project_members').select(
                'project_id, role, projects(id, name, description, status, stage, is_public, allow_file_upload, allow_ai_chat, created_by, created_at, updated_at)'
            ).eq('user_id', user_id).eq('is_active', True).execute()
            
            members_response = await run_supabase_query(members_query)
            member_projects = []
            if members_response.data:
                for member in members_response.data:
                    project = member.get('projects')
                    if project:
                        project['role'] = member.get('role', 'member')
                        project['is_owner'] = project.get('created_by') == user_id
                        member_projects.append(project)
            
            # 合并项目列表，去重（优先保留创建的项目）
            project_dict = {}
            for project in created_projects:
                project_id = project.get('id')
                if project_id:
                    project['role'] = 'owner'
                    project['is_owner'] = True
                    project_dict[project_id] = project
            
            for project in member_projects:
                project_id = project.get('id')
                if project_id and project_id not in project_dict:
                    project_dict[project_id] = project
            
            # 转换为列表并排序
            projects = list(project_dict.values())
            projects.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return projects[:limit]
            
        except Exception as e:
            logger.error(f"获取用户可访问项目失败 {user_id}: {e}")
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
            response = await run_supabase_query(lambda: self.client.table('user_permission_summary').select('*').eq(
                'user_id', user_id
            ).single().execute())

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
        优先使用admin_client（Service Key）绕过RLS限制

        Args:
            project_id: 项目ID
            user_id: 用户ID
            role: 角色
            invited_by: 邀请人ID

        Returns:
            添加是否成功
        """
        # 优先使用admin_client（Service Key）绕过RLS限制
        client_to_use = None
        
        if self.admin_client_available:
            client_to_use = self.admin_client
            logger.debug("✅ 使用admin_client添加项目成员（Service Key，绕过RLS）")
        elif self.client:
            client_to_use = self.client
            logger.warning("⚠️ admin_client不可用，使用client添加项目成员（可能受RLS策略限制）")
        else:
            logger.error("❌ Supabase客户端未初始化，无法添加项目成员")
            return False

        try:
            response = await run_supabase_query(lambda: client_to_use.table('project_members').insert({
                'project_id': project_id,
                'user_id': user_id,
                'role': role,
                'invited_by': invited_by,
                'is_active': True,
                'permissions': '{}',
                'joined_at': datetime.utcnow().isoformat()
            }).execute())

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
            # 查询项目成员，兼容 is_active 字段可能不存在或为 NULL 的情况
            # 使用异步查询执行
            def query_func():
                query = self.client.table('project_members').select('''
                    *,
                    profiles!project_members_user_id_fkey (
                        id, username, full_name, avatar_url, system_role, is_superuser
                    )
                ''').eq('project_id', project_id)
                
                # 如果 is_active 字段存在，只返回 is_active=True 或 NULL 的记录
                # 如果 is_active 字段不存在，返回所有记录
                try:
                    return query.or_('is_active.is.null,is_active.eq.true').execute()
                except Exception:
                    # 如果 or_ 语法不支持，尝试不使用 is_active 过滤
                    return query.execute()
            
            response = await run_supabase_query(query_func)
            
            logger.info(f"📊 查询项目成员: project_id={project_id}, 结果数量={len(response.data) if response.data else 0}")
            if response.data:
                logger.debug(f"📊 查询到的成员数据示例: {response.data[0] if len(response.data) > 0 else '无'}")
            
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
            
            response = await run_supabase_query(lambda: query.execute())
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取权限审计日志失败: {e}")
            return []


# 全局Supabase服务实例
supabase_service = SupabaseService()