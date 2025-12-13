#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
高性能权限缓存服务
实现Redis分布式缓存 + 本地缓存双层架构
"""

import asyncio
import json
import time
import hashlib
from typing import Dict, List, Optional, Set, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from functools import wraps
import logging
from enum import Enum

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    LOCAL = "local"
    REDIS = "redis"
    DATABASE = "database"


@dataclass
class CacheItem:
    """缓存项"""
    data: Any
    timestamp: float
    ttl: int
    level: CacheLevel
    hit_count: int = 0


@dataclass
class PermissionResult:
    """权限检查结果"""
    granted: bool
    reason: Optional[str] = None
    cache_hit: bool = False
    source: str = "cache"


class PermissionCache:
    """
    高性能权限缓存管理器

    特性：
    1. 双层缓存架构（本地+Redis）
    2. 缓存分片避免锁竞争
    3. 智能缓存失效策略
    4. 批量操作支持
    5. 缓存预热功能
    """

    def __init__(self, default_ttl: int = 300, local_cache_size: int = 10000):
        self.default_ttl = default_ttl
        self.local_cache_size = local_cache_size

        # 本地缓存分片（减少锁竞争）
        self.shard_count = 16
        self.local_cache_shards = [{} for _ in range(self.shard_count)]
        self.shard_locks = [asyncio.Lock() for _ in range(self.shard_count)]

        # Redis客户端
        self.redis_client: Optional[redis.Redis] = None
        self.redis_available = False

        # 缓存统计
        self.stats = {
            'local_hits': 0,
            'redis_hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }

        # 缓存TTL配置
        self.cache_ttl = {
            'user_permissions': 300,      # 5分钟
            'project_permissions': 600,   # 10分钟
            'user_projects': 180,         # 3分钟
            'system_permissions': 1800,   # 30分钟
            'batch_permissions': 300,     # 5分钟
            'permission_hierarchy': 3600  # 1小时
        }

    async def initialize(self):
        """初始化缓存服务"""
        await self._init_redis()
        logger.info(f"权限缓存服务初始化完成，Redis可用: {self.redis_available}")

    async def _init_redis(self):
        """初始化Redis连接（已禁用，仅使用本地缓存）"""
        # Redis连接已禁用，仅使用本地缓存
        self.redis_available = False
        self.redis_client = None
        logger.info("Redis连接已禁用，仅使用本地缓存")

    def _get_shard_index(self, key: str) -> int:
        """获取缓存分片索引"""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % self.shard_count

    def _get_cache_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        try:
            # 1. 尝试从本地缓存获取
            local_result = await self._get_from_local(key)
            if local_result is not None:
                self.stats['local_hits'] += 1
                return local_result

            # 2. 尝试从Redis获取
            if self.redis_available:
                redis_result = await self._get_from_redis(key)
                if redis_result is not None:
                    self.stats['redis_hits'] += 1
                    # 将Redis结果同步到本地缓存
                    await self._set_to_local(key, redis_result, self.default_ttl)
                    return redis_result

            # 3. 缓存未命中
            self.stats['misses'] += 1
            return None

        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            self.stats['errors'] += 1
            return None

    async def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据"""
        try:
            ttl = ttl or self.default_ttl

            # 并行设置到本地和Redis
            tasks = []

            # 设置到本地缓存
            tasks.append(self._set_to_local(key, data, ttl))

            # 设置到Redis
            if self.redis_available:
                tasks.append(self._set_to_redis(key, data, ttl))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self.stats['sets'] += 1
            return True

        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            self.stats['errors'] += 1
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存数据"""
        try:
            # 并行删除本地和Redis
            tasks = []

            # 删除本地缓存
            tasks.append(self._delete_from_local(key))

            # 删除Redis缓存
            if self.redis_available:
                tasks.append(self._delete_from_redis(key))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

            self.stats['deletes'] += 1
            return True

        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            self.stats['errors'] += 1
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """按模式批量删除缓存"""
        try:
            deleted_count = 0

            # 删除本地缓存匹配的键
            for shard in self.local_cache_shards:
                keys_to_delete = [
                    key for key in shard.keys()
                    if pattern in key
                ]
                for key in keys_to_delete:
                    del shard[key]
                    deleted_count += 1

            # 删除Redis中匹配的键
            if self.redis_available:
                keys = await self.redis_client.keys(f"*{pattern}*")
                if keys:
                    await self.redis_client.delete(*keys)
                    deleted_count += len(keys)

            return deleted_count

        except Exception as e:
            logger.error(f"批量删除缓存失败 {pattern}: {e}")
            return 0

    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户权限（带缓存）"""
        cache_key = self._get_cache_key("user_permissions", user_id=user_id)

        # 尝试从缓存获取
        cached = await self.get(cache_key)
        if cached:
            return set(cached)

        # 返回空集合（需要调用方处理数据库查询）
        return set()

    async def set_user_permissions(self, user_id: str, permissions: Set[str]) -> bool:
        """设置用户权限缓存"""
        cache_key = self._get_cache_key("user_permissions", user_id=user_id)
        return await self.set(
            cache_key,
            list(permissions),
            self.cache_ttl['user_permissions']
        )

    async def get_project_permissions(self, user_id: str, project_id: str) -> Dict[str, bool]:
        """获取用户项目权限（带缓存）"""
        cache_key = self._get_cache_key(
            "project_permissions",
            user_id=user_id,
            project_id=project_id
        )

        # 尝试从缓存获取
        cached = await self.get(cache_key)
        if cached:
            return cached

        # 返回空字典（需要调用方处理数据库查询）
        return {}

    async def set_project_permissions(
        self,
        user_id: str,
        project_id: str,
        permissions: Dict[str, bool]
    ) -> bool:
        """设置用户项目权限缓存"""
        cache_key = self._get_cache_key(
            "project_permissions",
            user_id=user_id,
            project_id=project_id
        )
        return await self.set(
            cache_key,
            permissions,
            self.cache_ttl['project_permissions']
        )

    async def batch_get_permissions(
        self,
        cache_keys: List[str]
    ) -> Dict[str, Any]:
        """批量获取权限缓存"""
        try:
            # 并行获取所有键
            tasks = [self.get(key) for key in cache_keys]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 组装结果
            cache_results = {}
            for key, result in zip(cache_keys, results):
                if not isinstance(result, Exception) and result is not None:
                    cache_results[key] = result

            return cache_results

        except Exception as e:
            logger.error(f"批量获取权限缓存失败: {e}")
            return {}

    async def batch_set_permissions(
        self,
        permission_data: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> int:
        """批量设置权限缓存"""
        try:
            # 并行设置所有键值对
            tasks = []
            for key, data in permission_data.items():
                tasks.append(self.set(key, data, ttl))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计成功设置的数量
            success_count = sum(
                1 for result in results
                if not isinstance(result, Exception) and result is True
            )

            return success_count

        except Exception as e:
            logger.error(f"批量设置权限缓存失败: {e}")
            return 0

    async def invalidate_user_cache(self, user_id: str) -> bool:
        """清除用户相关缓存"""
        try:
            patterns = [
                f"user_permissions:{user_id}",
                f"project_permissions:{user_id}",
                f"user_projects:{user_id}"
            ]

            deleted_count = 0
            for pattern in patterns:
                count = await self.invalidate_pattern(pattern)
                deleted_count += count

            logger.info(f"已清除用户 {user_id} 的缓存，共删除 {deleted_count} 项")
            return True

        except Exception as e:
            logger.error(f"清除用户缓存失败 {user_id}: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = (
            self.stats['local_hits'] +
            self.stats['redis_hits'] +
            self.stats['misses']
        )

        hit_rate = 0
        if total_requests > 0:
            hit_rate = (self.stats['local_hits'] + self.stats['redis_hits']) / total_requests

        local_cache_size = sum(len(shard) for shard in self.local_cache_shards)

        stats = {
            'local_hits': self.stats['local_hits'],
            'redis_hits': self.stats['redis_hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'errors': self.stats['errors'],
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'local_cache_size': local_cache_size,
            'local_cache_size_limit': self.local_cache_size,
            'redis_available': self.redis_available
        }

        # 添加Redis信息
        if self.redis_available and self.redis_client:
            try:
                redis_info = await self.redis_client.info()
                stats['redis_memory'] = redis_info.get('used_memory_human', 'N/A')
                stats['redis_connected_clients'] = redis_info.get('connected_clients', 0)
                stats['redis_keyspace_hits'] = redis_info.get('keyspace_hits', 0)
                stats['redis_keyspace_misses'] = redis_info.get('keyspace_misses', 0)
            except Exception as e:
                logger.error(f"获取Redis统计信息失败: {e}")

        return stats

    async def cleanup_expired(self) -> int:
        """清理过期的本地缓存"""
        try:
            now = time.time()
            cleaned_count = 0

            for shard in self.local_cache_shards:
                expired_keys = [
                    key for key, item in shard.items()
                    if isinstance(item, CacheItem) and
                    now - item.timestamp > item.ttl
                ]

                for key in expired_keys:
                    del shard[key]
                    cleaned_count += 1

            logger.info(f"清理了 {cleaned_count} 个过期缓存项")
            return cleaned_count

        except Exception as e:
            logger.error(f"清理过期缓存失败: {e}")
            return 0

    async def warm_up_permissions(self, user_id: str) -> bool:
        """预热用户权限缓存"""
        try:
            # 这里可以调用实际的服务来预热权限
            # 例如：从数据库预加载用户权限
            logger.info(f"预热用户 {user_id} 的权限缓存")
            return True

        except Exception as e:
            logger.error(f"预热用户权限缓存失败 {user_id}: {e}")
            return False

    # ================== 私有方法 ==================

    async def _get_from_local(self, key: str) -> Optional[Any]:
        """从本地缓存获取"""
        shard_index = self._get_shard_index(key)
        shard = self.local_cache_shards[shard_index]

        item = shard.get(key)
        if item is None:
            return None

        # 检查是否过期
        if isinstance(item, CacheItem):
            if time.time() - item.timestamp > item.ttl:
                del shard[key]
                return None

            item.hit_count += 1
            return item.data

        return None

    async def _set_to_local(self, key: str, data: Any, ttl: int) -> None:
        """设置到本地缓存"""
        shard_index = self._get_shard_index(key)
        shard = self.local_cache_shards[shard_index]
        lock = self.shard_locks[shard_index]

        async with lock:
            # 检查缓存大小限制
            if len(shard) >= self.local_cache_size:
                await self._evict_lru_item(shard)

            # 设置缓存项
            item = CacheItem(
                data=data,
                timestamp=time.time(),
                ttl=ttl,
                level=CacheLevel.LOCAL
            )
            shard[key] = item

    async def _delete_from_local(self, key: str) -> None:
        """从本地缓存删除"""
        shard_index = self._get_shard_index(key)
        shard = self.local_cache_shards[shard_index]
        lock = self.shard_locks[shard_index]

        async with lock:
            shard.pop(key, None)

    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """从Redis获取"""
        if not self.redis_available or not self.redis_client:
            return None

        try:
            cached_data = await self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None

        except Exception as e:
            logger.error(f"从Redis获取缓存失败 {key}: {e}")
            return None

    async def _set_to_redis(self, key: str, data: Any, ttl: int) -> None:
        """设置到Redis"""
        if not self.redis_available or not self.redis_client:
            return

        try:
            serialized_data = json.dumps(data, default=str)
            await self.redis_client.setex(key, ttl, serialized_data)

        except Exception as e:
            logger.error(f"设置Redis缓存失败 {key}: {e}")

    async def _delete_from_redis(self, key: str) -> None:
        """从Redis删除"""
        if not self.redis_available or not self.redis_client:
            return

        try:
            await self.redis_client.delete(key)

        except Exception as e:
            logger.error(f"删除Redis缓存失败 {key}: {e}")

    async def _evict_lru_item(self, shard: Dict[str, CacheItem]) -> None:
        """驱逐LRU缓存项"""
        if not shard:
            return

        # 找到最久未访问的项
        oldest_key = None
        oldest_time = float('inf')

        for key, item in shard.items():
            if item.timestamp < oldest_time:
                oldest_time = item.timestamp
                oldest_key = key

        if oldest_key:
            del shard[oldest_key]


# ================== 缓存装饰器 ==================

def cache_result(
    key_prefix: str,
    ttl: Optional[int] = None,
    cache_level: CacheLevel = CacheLevel.LOCAL
):
    """缓存函数结果的装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = permission_cache._get_cache_key(
                key_prefix,
                args=str(args),
                kwargs=str(kwargs)
            )

            # 尝试从缓存获取
            cached = await permission_cache.get(cache_key)
            if cached is not None:
                return cached

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            await permission_cache.set(cache_key, result, ttl)

            return result

        return wrapper
    return decorator


# ================== 全局实例 ==================

# 创建全局权限缓存实例
permission_cache = PermissionCache()

# 便捷函数
async def get_cached_user_permissions(user_id: str) -> Set[str]:
    """获取缓存的用户权限"""
    return await permission_cache.get_user_permissions(user_id)

async def set_cached_user_permissions(user_id: str, permissions: Set[str]) -> bool:
    """设置用户权限缓存"""
    return await permission_cache.set_user_permissions(user_id, permissions)

async def get_cached_project_permissions(user_id: str, project_id: str) -> Dict[str, bool]:
    """获取缓存的项目权限"""
    return await permission_cache.get_project_permissions(user_id, project_id)

async def set_cached_project_permissions(
    user_id: str,
    project_id: str,
    permissions: Dict[str, bool]
) -> bool:
    """设置项目权限缓存"""
    return await permission_cache.set_project_permissions(user_id, project_id, permissions)

async def invalidate_user_permissions(user_id: str) -> bool:
    """清除用户权限缓存"""
    return await permission_cache.invalidate_user_cache(user_id)