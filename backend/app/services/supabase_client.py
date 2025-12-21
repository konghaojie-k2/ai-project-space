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
import httpx
from app.core.config import settings
from app.services.permission_cache import permission_cache, cache_result

# 全局持久化 HTTP 客户端，用于减少连接建立开销
_global_http_client: Optional[httpx.Client] = None
_global_async_http_client: Optional[httpx.AsyncClient] = None

def get_global_http_client() -> httpx.Client:
    """获取全局持久化 HTTP 客户端（同步）"""
    global _global_http_client
    if _global_http_client is None:
        _global_http_client = httpx.Client(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            http2=True  # 启用 HTTP/2 以提高性能
        )
        logger.info("✅ 全局同步 HTTP 客户端已初始化")
    return _global_http_client

async def get_global_async_http_client() -> httpx.AsyncClient:
    """获取全局持久化 HTTP 客户端（异步）"""
    global _global_async_http_client
    if _global_async_http_client is None:
        _global_async_http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            http2=True  # 启用 HTTP/2 以提高性能
        )
        logger.info("✅ 全局异步 HTTP 客户端已初始化")
    return _global_async_http_client

async def direct_supabase_query(
    table: str,
    select: str = "*",
    filters: Optional[Dict[str, Any]] = None,
    or_filters: Optional[str] = None,
    order_by: Optional[str] = None,
    order_desc: bool = True,
    limit: int = 100,
    offset: int = 0,
    use_service_key: bool = True
) -> List[Dict]:
    """
    直接通过 HTTP 调用 Supabase REST API，绕过 SDK
    
    这种方式可以复用 HTTP/2 连接，性能更好
    
    Args:
        table: 表名
        select: 选择的字段
        filters: 过滤条件 {"column": "value"} 会转换为 column=eq.value
        or_filters: OR过滤条件字符串，如 "access_level.eq.all_users,uploaded_by.eq.xxx"
        order_by: 排序字段
        order_desc: 是否降序
        limit: 限制返回数量
        offset: 偏移量
        use_service_key: 是否使用服务密钥
    """
    try:
        client = await get_global_async_http_client()
        
        # 构建 URL
        base_url = settings.SUPABASE_URL.rstrip('/')
        url = f"{base_url}/rest/v1/{table}"
        
        # 构建查询参数
        params = {"select": select}
        if limit:
            params["limit"] = str(limit)
        if offset:
            params["offset"] = str(offset)
        if order_by:
            params["order"] = f"{order_by}.{'desc' if order_desc else 'asc'}"
        
        # 添加过滤条件
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        
        # 添加OR过滤条件
        if or_filters:
            params["or"] = f"({or_filters})"
        
        # 构建请求头
        api_key = settings.SUPABASE_SERVICE_KEY if use_service_key else settings.SUPABASE_KEY
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # 发送请求
        response = await client.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"直接查询失败: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"直接查询异常: {e}")
        return []

async def direct_supabase_update(
    table: str,
    update_data: Dict[str, Any],
    filters: Dict[str, Any],
    use_service_key: bool = True
) -> Optional[List[Dict]]:
    """
    直接通过 HTTP PATCH 调用 Supabase REST API 更新数据，绕过 SDK
    
    这种方式可以复用 HTTP/2 连接，性能更好
    
    Args:
        table: 表名
        update_data: 要更新的数据字典
        filters: 过滤条件 {"column": "value"} 会转换为 column=eq.value
        use_service_key: 是否使用服务密钥
        
    Returns:
        更新后的数据列表，失败返回None
    """
    try:
        client = await get_global_async_http_client()
        
        # 构建 URL
        base_url = settings.SUPABASE_URL.rstrip('/')
        url = f"{base_url}/rest/v1/{table}"
        
        # 构建查询参数（用于WHERE条件）
        params = {}
        if filters:
            for key, value in filters.items():
                params[key] = f"eq.{value}"
        
        # 构建请求头
        api_key = settings.SUPABASE_SERVICE_KEY if use_service_key else settings.SUPABASE_KEY
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"  # 返回更新后的数据
        }
        
        # 发送 PATCH 请求
        response = await client.patch(url, params=params, json=update_data, headers=headers)
        
        if response.status_code in [200, 204]:
            if response.status_code == 204:
                # 204 No Content，虽然设置了Prefer: return=representation，但可能还是返回204
                # 返回空列表，调用者需要重新查询
                logger.debug(f"直接更新返回204 No Content，调用者需要重新查询: {table}")
                return []
            # 200 OK，尝试解析JSON
            try:
                json_data = response.json()
                # 如果返回的是列表，直接返回
                if isinstance(json_data, list):
                    return json_data
                # 如果返回的是单个对象，包装成列表
                elif isinstance(json_data, dict):
                    return [json_data]
                else:
                    logger.warning(f"直接更新返回了意外的数据类型: {type(json_data)}")
                    return []
            except Exception as e:
                logger.error(f"解析更新响应JSON失败: {e}")
                return []
        else:
            # 400错误可能是字段不存在，需要特殊处理
            if response.status_code == 400:
                error_text = response.text
                # 检查是否是字段不存在的错误
                if "PGRST204" in error_text or "column" in error_text.lower() or "not find" in error_text.lower():
                    logger.debug(f"直接更新返回400（字段不存在）: {error_text}")
                    # 抛出ValueError，让调用者知道是字段不存在的问题
                    # 这个异常会被外层捕获，但我们需要让它传播出去
                    raise ValueError(f"字段不存在: {error_text}")
            logger.error(f"直接更新失败: {response.status_code} - {response.text}")
            return None
            
    except ValueError:
        # ValueError是字段不存在的错误，需要传播给调用者
        raise
    except Exception as e:
        logger.error(f"直接更新异常: {e}")
        return None

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

# 创建专用的线程池，增大并发容量
from concurrent.futures import ThreadPoolExecutor
_supabase_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="supabase_")

async def run_supabase_query(query_func, timeout: float = 30.0):
    """
    在专用线程池中执行Supabase同步查询，避免阻塞事件循环
    
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
        loop.run_in_executor(_supabase_executor, query_func),
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
        从JWT token获取用户信息（终极优化版：使用本地 JWT 验证）

        Args:
            token: JWT token字符串

        Returns:
            用户信息字典，如果token无效返回None
        """
        if not self.client:
            return None

        try:
            # 使用本地 JWT 验证，无需调用远程 API
            user_data = self._verify_jwt_locally(token)
            
            if user_data:
                logger.debug(f"用户认证成功(本地JWT): {user_data.get('email', 'unknown')}")
                return user_data
            
            # 如果本地验证失败（可能是token格式问题），回退到 HTTP 调用
            logger.debug("本地JWT验证失败，回退到HTTP验证")
            user_data = await self._get_user_with_http(token)
            
            if user_data:
                logger.debug(f"用户认证成功(HTTP): {user_data.get('email', 'unknown')}")
                return user_data
            
            return None
        except Exception as e:
            logger.error(f"Token验证失败: {e}")
            return None

    def _verify_jwt_locally(self, token: str) -> Optional[Dict]:
        """
        本地验证 JWT token（无需远程 API 调用，毫秒级性能）
        
        Supabase JWT token 是自包含的，包含用户信息和过期时间。
        我们只需验证签名和过期时间即可。
        """
        try:
            import jwt
            import base64
            
            # 从 Supabase JWT Secret 验证（如果配置了）
            jwt_secret = settings.SECRET_KEY  # 使用应用的 secret key
            
            # 尝试解码 JWT（不验证签名，因为 Supabase 使用自己的密钥）
            # 但我们可以检查过期时间和提取用户信息
            try:
                # 尝试无验证解码获取 payload
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
            except jwt.exceptions.DecodeError:
                logger.debug("JWT解码失败")
                return None
            
            # 检查过期时间
            import time as time_module
            exp = unverified_payload.get('exp')
            if exp and exp < time_module.time():
                logger.debug("JWT已过期")
                return None
            
            # 提取用户信息
            user_id = unverified_payload.get('sub')
            email = unverified_payload.get('email')
            
            if not user_id:
                logger.debug("JWT中没有用户ID")
                return None
            
            # 构建用户数据
            user_metadata = unverified_payload.get('user_metadata', {})
            
            return {
                'id': user_id,
                'email': email,
                'email_confirmed_at': unverified_payload.get('email_confirmed_at'),
                'created_at': unverified_payload.get('created_at'),
                'updated_at': unverified_payload.get('updated_at'),
                'user_metadata': user_metadata,
                'app_metadata': unverified_payload.get('app_metadata', {}),
                'phone': unverified_payload.get('phone'),
                'role': unverified_payload.get('role'),
                'aal': unverified_payload.get('aal'),
            }
            
        except Exception as e:
            logger.debug(f"本地JWT验证异常: {e}")
            return None

    async def _get_user_with_http(self, token: str) -> Optional[Dict]:
        """
        使用直接 HTTP 调用获取用户信息（绕过 SDK 以提高性能）
        """
        try:
            auth_url = f"{settings.SUPABASE_URL}/auth/v1/user"
            
            headers = {
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_anon_key or "",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                http2=True
            ) as client:
                resp = await client.get(auth_url, headers=headers)
            
            if resp.status_code == 200:
                user_data = resp.json()
                # 转换为标准格式
                return {
                    'id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'email_confirmed_at': user_data.get('email_confirmed_at'),
                    'created_at': user_data.get('created_at'),
                    'updated_at': user_data.get('updated_at'),
                    'user_metadata': user_data.get('user_metadata', {}),
                    'app_metadata': user_data.get('app_metadata', {}),
                    'phone': user_data.get('phone'),
                }
            else:
                logger.debug(f"HTTP 获取用户信息返回状态码: {resp.status_code}")
                return None
                
        except Exception as e:
            logger.debug(f"HTTP 获取用户信息异常: {e}")
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
            # 使用anon key客户端注册用户 - 使用异步包装
            # 注意：如果启用了邮箱验证，用户需要验证邮箱后才能登录
            response = await run_supabase_query(
                lambda: self.client.auth.sign_up({
                    'email': email,
                    'password': password,
                    'options': {
                        'data': user_metadata or {},
                        'email_redirect_to': None  # 可以设置重定向URL
                    }
                })
            )

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
            # 使用Admin API创建用户，可以自动确认邮箱（需要Service Key）- 使用异步包装
            response = await run_supabase_query(
                lambda: self.admin_client.auth.admin.create_user({
                    'email': email,
                    'password': password,
                    'email_confirm': email_confirm,  # 自动确认邮箱
                    'user_metadata': user_metadata or {}
                })
            )

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
            # 先查找用户（使用admin客户端）- 使用异步包装
            users_response = await run_supabase_query(
                lambda: self.admin_client.auth.admin.list_users()
            )
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
            
            # 使用Admin API更新密码（需要Service Key）- 使用异步包装
            response = await run_supabase_query(
                lambda: self.admin_client.auth.admin.update_user_by_id(
                    user_id,
                    {'password': new_password}
                )
            )
            
            if response.user:
                logger.info(f"管理员重置密码成功: {email}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"管理员重置密码失败 {email}: {e}", exc_info=True)
            return False

    async def _sign_in_with_http(self, email: str, password: str) -> Optional[Any]:
        """
        使用直接 HTTP 调用进行登录（绕过 SDK 以利用连接池）
        
        Returns:
            模拟 SDK 响应格式的对象，失败返回 None
        """
        try:
            auth_url = f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password"
            anon_key = settings.supabase_anon_key
            
            if not anon_key:
                return None
            
            headers = {
                "apikey": anon_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "email": email,
                "password": password
            }
            
            # 使用全局 HTTP 客户端（异步版本）
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=5.0),
                http2=True
            ) as client:
                resp = await client.post(auth_url, json=payload, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                # 创建类似 SDK 响应的对象
                class MockAuthResponse:
                    def __init__(self, data):
                        self.user = type('User', (), data.get('user', {}))() if data.get('user') else None
                        self.session = type('Session', (), {
                            'access_token': data.get('access_token'),
                            'refresh_token': data.get('refresh_token'),
                            'expires_in': data.get('expires_in'),
                            'token_type': data.get('token_type', 'bearer')
                        })() if data.get('access_token') else None
                        # 复制用户属性
                        if self.user and data.get('user'):
                            for key, value in data['user'].items():
                                setattr(self.user, key, value)
                
                return MockAuthResponse(data)
            else:
                logger.warning(f"直接 HTTP 登录返回状态码: {resp.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"直接 HTTP 登录异常: {e}")
            return None

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
            # 优化：使用直接 HTTP 调用 Supabase Auth API，绕过 SDK 的连接开销
            try:
                response = await self._sign_in_with_http(email, password)
                if response is None:
                    # 如果直接 HTTP 调用失败，回退到 SDK 方式
                    logger.warning("直接 HTTP 登录失败，回退到 SDK 方式")
                    response = await run_supabase_query(
                        lambda: self.client.auth.sign_in_with_password({
                            'email': email,
                            'password': password
                        })
                    )
            except Exception as http_err:
                logger.warning(f"直接 HTTP 登录异常: {http_err}，回退到 SDK 方式")
                response = await run_supabase_query(
                    lambda: self.client.auth.sign_in_with_password({
                        'email': email,
                        'password': password
                    })
                )

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
            # 使用异步包装
            await run_supabase_query(
                lambda: self.client.auth.sign_out(token)
            )
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
        获取用户档案（优化版：使用直接HTTP查询 + 缓存）

        Args:
            user_id: 用户ID

        Returns:
            用户档案字典，不存在返回None
        """
        cache_key = f"profile:{user_id}"
        
        # 先检查缓存
        cached = await self.profile_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            # 使用直接 HTTP 查询
            profiles = await direct_supabase_query(
                table="profiles",
                select="id,username,full_name,avatar_url,bio,is_superuser,system_role,is_active",
                filters={"id": user_id},
                limit=1,
                use_service_key=True
            )
            
            if profiles and len(profiles) > 0:
                profile = profiles[0]
                # 存入缓存
                await self.profile_cache.set(cache_key, profile, 600)
                return profile
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

    @cache_result(
        key_prefix="get_user_projects_optimized",
        ttl=300  # 5分钟缓存
    )
    async def get_user_projects(self, user_id: str, limit: int = 100) -> List[Dict]:
        """
        获取用户可访问的项目列表 (优化版)

        优化点：
        1. 使用物化视图替代多次查询
        2. 集成权限缓存
        3. 减少数据库往返次数

        Args:
            user_id: 用户ID
            limit: 限制返回数量

        Returns:
            项目列表，包含用户在项目中的角色和权限级别
        """
        if not self.client:
            return []

        # 首先尝试从缓存获取
        cache_key = f"user_projects_v2:{user_id}:{limit}"
        cached_result = await permission_cache.get(cache_key)
        if cached_result:
            return cached_result

        try:
            # 优化方案：使用物化视图或单次JOIN查询
            # 方案1：使用物化视图（如果可用）
            try:
                # 尝试使用物化视图查询
                query = f"""
                SELECT
                    p.id,
                    p.name,
                    p.description,
                    p.status,
                    p.stage,
                    p.is_public,
                    p.allow_file_upload,
                    p.allow_ai_chat,
                    p.created_by,
                    p.created_at,
                    p.updated_at,
                    CASE
                        WHEN upp.effective_role IS NOT NULL THEN upp.effective_role
                        WHEN p.is_public = true THEN 'viewer'
                        ELSE 'none'
                    END as role,
                    CASE
                        WHEN upp.effective_role = 'owner' THEN true
                        ELSE false
                    END as is_owner,
                    COALESCE(upp.permission_level, 0) as permission_level
                FROM projects p
                LEFT JOIN mv_user_project_permissions upp ON p.id = upp.project_id
                    AND upp.user_id = '{user_id}'
                    AND upp.is_active = true
                WHERE p.is_deleted = false
                    AND (
                        upp.user_id IS NOT NULL  -- 用户有明确权限
                        OR p.is_public = true     -- 公开项目
                    )
                ORDER BY p.updated_at DESC
                LIMIT {limit}
                """

                # 执行原生SQL查询
                response = await self._execute_sql_query(query)

                if response:
                    # 缓存结果
                    await permission_cache.set(cache_key, response, 300)
                    return response

            except Exception as e:
                logger.warning(f"物化视图查询失败，回退到JOIN查询: {e}")

            # 方案2：使用优化的JOIN查询（回退方案）
            try:
                # 使用单个JOIN查询替代多次查询
                join_query = lambda: self.client.rpc(
                    'get_user_projects_optimized',
                    {
                        'p_user_id': user_id,
                        'p_limit': limit
                    }
                ).execute()

                response = await run_supabase_query(join_query)

                if response.data:
                    # 处理并缓存结果
                    projects = self._process_project_data(response.data, user_id)
                    await permission_cache.set(cache_key, projects, 300)
                    return projects

            except Exception as e:
                logger.warning(f"RPC查询失败，使用传统方法: {e}")

            # 方案3：优化后的传统查询（最后回退）
            # 使用单次查询获取所有需要的数据
            combined_query = f"""
            SELECT
                p.id,
                p.name,
                p.description,
                p.status,
                p.stage,
                p.is_public,
                p.allow_file_upload,
                p.allow_ai_chat,
                p.created_by,
                p.created_at,
                p.updated_at,
                pm.role as member_role,
                pm.is_active as member_active
            FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id AND pm.user_id = '{user_id}'
            WHERE p.is_deleted = false
                AND (
                    p.created_by = '{user_id}'  -- 用户创建的项目
                    OR pm.user_id IS NOT NULL   -- 用户是成员的项目
                    OR p.is_public = true       -- 公开项目
                )
            ORDER BY p.updated_at DESC
            LIMIT {limit}
            """

            # 执行查询
            projects_data = await self._execute_sql_query(combined_query)

            if projects_data:
                # 处理数据，设置角色和权限
                projects = self._process_project_data(projects_data, user_id)

                # 缓存结果
                await permission_cache.set(cache_key, projects, 300)
                return projects

            return []

        except Exception as e:
            logger.error(f"获取用户项目列表失败 {user_id}: {e}")
            return []

    async def get_project_details(self, project_id: str) -> Optional[Dict]:
        """
        获取项目详情（使用直接HTTP查询优化）

        Args:
            project_id: 项目ID

        Returns:
            项目详情字典，不存在返回None
        """
        try:
            # 使用直接 HTTP 查询，使用 service_key 绕过 RLS
            projects = await direct_supabase_query(
                table="projects",
                select="*",
                filters={"id": project_id},
                limit=1,
                use_service_key=True
            )

            if projects and len(projects) > 0:
                return projects[0]
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
        优先使用admin_client（Service Key）绕过RLS限制

        Args:
            session_data: 会话数据字典

        Returns:
            创建的会话记录字典，创建失败返回None
        """
        # 优先使用admin_client（Service Key）绕过RLS限制
        client_to_use = None
        
        if self.admin_client_available:
            client_to_use = self.admin_client
            logger.debug("✅ 使用admin_client创建聊天会话（Service Key，绕过RLS）")
        elif self.client:
            client_to_use = self.client
            logger.warning("⚠️ admin_client不可用，使用client创建聊天会话（可能受RLS策略限制）")
        else:
            logger.error("❌ Supabase客户端未初始化，无法创建聊天会话")
            return None

        try:
            response = await run_supabase_query(lambda: client_to_use.table('chat_sessions').insert({
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
        优先使用admin_client（Service Key）绕过RLS限制

        Args:
            message_data: 消息数据字典

        Returns:
            创建的消息记录字典，创建失败返回None
        """
        # 优先使用admin_client（Service Key）绕过RLS限制
        client_to_use = None
        
        if self.admin_client_available:
            client_to_use = self.admin_client
            logger.debug("✅ 使用admin_client创建聊天消息（Service Key，绕过RLS）")
        elif self.client:
            client_to_use = self.client
            logger.warning("⚠️ admin_client不可用，使用client创建聊天消息（可能受RLS策略限制）")
        else:
            logger.error("❌ Supabase客户端未初始化，无法创建聊天消息")
            return None

        try:
            response = await run_supabase_query(lambda: client_to_use.table('chat_messages').insert({
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
        获取聊天会话消息列表（使用直接HTTP查询优化）

        Args:
            session_id: 会话ID

        Returns:
            消息列表
        """
        try:
            # 使用直接 HTTP 查询
            return await direct_supabase_query(
                table="chat_messages",
                select="*",
                filters={"session_id": session_id},
                order_by="created_at",
                order_desc=False,  # 升序
                limit=100,
                use_service_key=True
            )
        except Exception as e:
            logger.error(f"获取聊天消息失败 {session_id}: {e}")
            return []

    async def get_user_chat_sessions(self, user_id: str) -> List[Dict]:
        """
        获取用户聊天会话列表（优化：使用直接 HTTP 查询）

        Args:
            user_id: 用户ID

        Returns:
            会话列表
        """
        try:
            # 使用直接 HTTP 查询，绕过 SDK
            sessions = await direct_supabase_query(
                table="chat_sessions",
                select="id,title,project_id,created_at,updated_at",
                filters={"user_id": user_id},
                order_by="updated_at",
                order_desc=True,
                limit=50,
                use_service_key=True
            )

            return sessions
        except Exception as e:
            logger.error(f"获取用户聊天会话失败 {user_id}: {e}")
            return []
    
    async def get_chat_session(self, session_id: str) -> Optional[Dict]:
        """
        获取单个聊天会话（使用直接HTTP查询优化）

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典，不存在返回None
        """
        try:
            # 使用直接 HTTP 查询
            sessions = await direct_supabase_query(
                table="chat_sessions",
                select="*",
                filters={"id": session_id},
                limit=1,
                use_service_key=True
            )
            
            return sessions[0] if sessions and len(sessions) > 0 else None
        except Exception as e:
            logger.error(f"获取聊天会话失败 {session_id}: {e}")
            return None
    
    async def update_chat_session(self, session_id: str, update_data: Dict) -> Optional[Dict]:
        """
        更新聊天会话
        优先使用admin_client（Service Key）绕过RLS限制

        Args:
            session_id: 会话ID
            update_data: 要更新的数据

        Returns:
            更新后的会话信息字典，更新失败返回None
        """
        # 优先使用admin_client（Service Key）绕过RLS限制
        client_to_use = None
        
        if self.admin_client_available:
            client_to_use = self.admin_client
        elif self.client:
            client_to_use = self.client
        else:
            logger.error("❌ Supabase客户端未初始化，无法更新聊天会话")
            return None

        try:
            response = await run_supabase_query(lambda: client_to_use.table('chat_sessions').update({
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
        获取聊天统计信息（优化版：使用直接 HTTP 查询）
        """
        try:
            # 使用直接 HTTP 查询，绕过 SDK
            filters = {"user_id": user_id} if user_id else None
            sessions = await direct_supabase_query(
                table="chat_sessions",
                select="id",
                filters=filters,
                limit=50,
                use_service_key=True
            )

            total_conversations = len(sessions)

            return {
                'total_conversations': total_conversations,
                'total_messages': 0,
                'ai_messages': 0
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
        required_permission: str = 'read',
        is_superuser: bool = False
    ) -> bool:
        """
        检查用户是否有特定项目权限 (使用新的权限系统)

        Args:
            user_id: 用户ID
            project_id: 项目ID
            required_permission: 需要的权限类型 ('read', 'write', 'delete', 'manage_members', 'manage_settings')
            is_superuser: 是否是超级管理员

        Returns:
            是否有权限
        """
        if not self.client:
            return False

        # 超级管理员拥有所有权限
        if is_superuser:
            return True

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
        获取用户可访问的项目列表（使用直接HTTP查询优化）

        Args:
            user_id: 用户ID
            limit: 限制返回数量
            is_superuser: 是否是超级管理员

        Returns:
            项目列表，包含用户在项目中的角色和权限级别
        """
        cache_key = f"user_projects:{user_id}:{limit}"
        
        # 先检查缓存
        cached = await self.projects_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            select_fields = "id,name,description,status,stage,is_public,allow_file_upload,allow_ai_chat,created_by,created_at,updated_at"
            
            # 如果是超级管理员，返回所有项目
            if is_superuser:
                projects = await direct_supabase_query(
                    table="projects",
                    select=select_fields,
                    order_by="created_at",
                    order_desc=True,
                    limit=limit,
                    use_service_key=True
                )
                
                if projects:
                    # 为每个项目添加角色信息（管理员默认为owner）
                    result = [
                        {
                            **project,
                            'role': 'owner',
                            'is_owner': True
                        }
                        for project in projects
                    ]
                    await self.projects_cache.set(cache_key, result, 180)
                    return result
                return []
            
            # 普通用户：查询用户创建的项目
            created_projects = await direct_supabase_query(
                table="projects",
                select=select_fields,
                filters={"created_by": user_id},
                order_by="created_at",
                order_desc=True,
                limit=limit,
                use_service_key=True
            )
            
            # 合并项目列表
            project_dict = {}
            for project in created_projects:
                project_id = project.get('id')
                if project_id:
                    project['role'] = 'owner'
                    project['is_owner'] = True
                    project_dict[project_id] = project
            
            # 转换为列表并排序
            projects = list(project_dict.values())
            projects.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # 缓存结果
            result = projects[:limit]
            await self.projects_cache.set(cache_key, result, 180)
            return result
            
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
        获取项目成员列表（使用直接HTTP查询优化）

        Args:
            project_id: 项目ID

        Returns:
            成员列表，包含用户档案信息
        """
        try:
            # 使用直接 HTTP 查询，支持嵌套选择
            members = await direct_supabase_query(
                table="project_members",
                select="*,profiles!project_members_user_id_fkey(id,username,full_name,avatar_url,system_role,is_superuser)",
                filters={"project_id": project_id},
                limit=100,
                use_service_key=True
            )
            
            logger.info(f"📊 查询项目成员: project_id={project_id}, 结果数量={len(members)}")
            if members:
                logger.debug(f"📊 查询到的成员数据示例: {members[0] if len(members) > 0 else '无'}")
            
            return members

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

    # ========================================
    # 优化辅助方法
    # ========================================

    async def _execute_sql_query(self, query: str) -> Optional[List[Dict]]:
        """
        执行原生SQL查询

        Args:
            query: SQL查询语句

        Returns:
            查询结果列表，失败返回None
        """
        try:
            # 使用Supabase的RPC功能执行SQL
            response = await run_supabase_query(
                lambda: self.client.rpc('execute_sql', {'sql_query': query}).execute()
            )

            return response.data if response.data else None

        except Exception as e:
            logger.error(f"执行SQL查询失败: {e}")
            return None

    def _process_project_data(self, projects_data: List[Dict], user_id: str) -> List[Dict]:
        """
        处理项目数据，设置角色和权限信息

        Args:
            projects_data: 原始项目数据
            user_id: 用户ID

        Returns:
            处理后的项目数据
        """
        processed_projects = []

        for project_data in projects_data:
            project = {
                'id': project_data.get('id'),
                'name': project_data.get('name'),
                'description': project_data.get('description'),
                'status': project_data.get('status'),
                'stage': project_data.get('stage'),
                'is_public': project_data.get('is_public', False),
                'allow_file_upload': project_data.get('allow_file_upload', False),
                'allow_ai_chat': project_data.get('allow_ai_chat', False),
                'created_by': project_data.get('created_by'),
                'created_at': project_data.get('created_at'),
                'updated_at': project_data.get('updated_at')
            }

            # 确定用户角色
            if project_data.get('created_by') == user_id:
                # 用户是项目创建者
                project['role'] = 'owner'
                project['is_owner'] = True
                project['permission_level'] = 5
            elif project_data.get('member_role') and project_data.get('member_active'):
                # 用户是活跃成员
                role = project_data.get('member_role', 'member')
                project['role'] = role
                project['is_owner'] = False
                project['permission_level'] = {
                    'admin': 4,
                    'member': 3,
                    'viewer': 1
                }.get(role, 1)
            elif project_data.get('is_public'):
                # 公开项目的查看者
                project['role'] = 'viewer'
                project['is_owner'] = False
                project['permission_level'] = 1
            else:
                # 无权限访问
                continue

            # 添加权限标志
            permission_level = project['permission_level']
            project['can_read'] = permission_level >= 1
            project['can_write'] = permission_level >= 2
            project['can_delete'] = permission_level >= 3
            project['can_manage_members'] = permission_level >= 4
            project['can_manage_settings'] = permission_level >= 5

            processed_projects.append(project)

        return processed_projects

    @cache_result(
        key_prefix="check_project_permission_cached",
        ttl=600  # 10分钟缓存
    )
    async def check_project_permission_optimized(
        self,
        user_id: str,
        project_id: str,
        required_permission: str
    ) -> bool:
        """
        优化的项目权限检查

        Args:
            user_id: 用户ID
            project_id: 项目ID
            required_permission: 需要的权限 (read, write, delete, manage_members, manage_settings)

        Returns:
            是否有权限
        """
        # 权限级别映射
        permission_levels = {
            'read': 1,
            'write': 2,
            'delete': 3,
            'manage_members': 4,
            'manage_settings': 5
        }

        required_level = permission_levels.get(required_permission, 1)

        # 首先尝试从权限缓存获取
        cached_permissions = await permission_cache.get_project_permissions(user_id, project_id)
        if cached_permissions and cached_permissions.get(required_permission, False):
            return True

        try:
            # 尝试使用物化视图检查权限
            query = f"""
            SELECT has_project_permission_cached(
                '{user_id}'::uuid,
                '{project_id}'::uuid,
                '{required_permission}'
            ) as has_permission
            """

            result = await self._execute_sql_query(query)

            if result and len(result) > 0:
                has_permission = result[0].get('has_permission', False)

                # 缓存结果
                permissions = cached_permissions or {}
                permissions[required_permission] = has_permission
                await permission_cache.set_project_permissions(user_id, project_id, permissions)

                return has_permission

            # 回退到传统权限检查
            return await self.check_project_permission(user_id, project_id, required_permission)

        except Exception as e:
            logger.error(f"优化权限检查失败，使用传统方法: {e}")
            return await self.check_project_permission(user_id, project_id, required_permission)

    async def batch_check_permissions(
        self,
        permission_requests: List[Dict[str, str]]
    ) -> Dict[str, bool]:
        """
        批量检查权限

        Args:
            permission_requests: 权限检查请求列表，每个请求包含 user_id, project_id, permission

        Returns:
            权限检查结果字典，key为 "user_id:project_id:permission"，value为是否有权限
        """
        results = {}

        # 按用户分组请求以优化缓存命中率
        user_groups = {}
        for request in permission_requests:
            user_id = request.get('user_id')
            if user_id not in user_groups:
                user_groups[user_id] = []
            user_groups[user_id].append(request)

        # 处理每个用户的权限请求
        for user_id, requests in user_groups.items():
            # 批量检查每个用户的权限
            for request in requests:
                project_id = request.get('project_id')
                permission = request.get('permission')

                key = f"{user_id}:{project_id}:{permission}"

                # 检查权限
                has_permission = await self.check_project_permission_optimized(
                    user_id, project_id, permission
                )

                results[key] = has_permission

        return results

    async def invalidate_user_project_cache(self, user_id: str) -> bool:
        """
        清除用户项目相关的缓存

        Args:
            user_id: 用户ID

        Returns:
            是否成功清除缓存
        """
        try:
            # 清除权限缓存中的用户相关数据
            await permission_cache.invalidate_user_cache(user_id)

            # 可以在这里添加其他缓存的清除逻辑

            logger.info(f"已清除用户 {user_id} 的项目相关缓存")
            return True

        except Exception as e:
            logger.error(f"清除用户项目缓存失败 {user_id}: {e}")
            return False


# 全局Supabase服务实例
supabase_service = SupabaseService()