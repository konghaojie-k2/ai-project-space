#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Supabase文件存储服务
基于Supabase Storage的文件上传、下载和管理
"""

import uuid
import asyncio
import json
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger
from collections import OrderedDict

from app.services.supabase_client import supabase_service, direct_supabase_query, direct_supabase_update, run_supabase_query
from app.core.config import settings


def is_valid_uuid(uuid_string: str) -> bool:
    """
    验证字符串是否为有效的UUID格式
    
    Args:
        uuid_string: 要验证的字符串
        
    Returns:
        是否为有效的UUID
    """
    if not uuid_string:
        return False
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, TypeError, AttributeError):
        return False

# 项目ID规范化缓存（避免重复查询）
_project_id_cache: Dict[str, Optional[str]] = {}

async def normalize_project_id(project_id: str) -> Optional[str]:
    """
    规范化项目ID：如果是时间戳格式，尝试在Supabase中查找对应的UUID
    使用缓存避免重复查询
    
    Args:
        project_id: 项目ID字符串
        
    Returns:
        规范化的UUID格式项目ID，如果无法转换则返回None
    """
    if not project_id:
        return None
    
    # 检查缓存
    if project_id in _project_id_cache:
        return _project_id_cache[project_id]
    
    # 如果是有效的UUID，直接返回并缓存
    if is_valid_uuid(project_id):
        _project_id_cache[project_id] = project_id
        return project_id
    
    # 如果是纯数字（可能是时间戳），尝试在Supabase中查找对应的项目
    # 注意：这个查询可能很慢，所以只查询一次并缓存结果
    if project_id.isdigit():
        try:
            # 将时间戳转换为datetime
            timestamp_ms = int(project_id)
            # 如果是13位数字（毫秒），转换为秒
            if timestamp_ms > 9999999999:
                timestamp_s = timestamp_ms / 1000
            else:
                timestamp_s = timestamp_ms
            
            from datetime import datetime, timezone
            # 使用UTC时区
            target_date = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
            
            # 在Supabase中查找创建时间接近的项目
            # 注意：由于时间戳可能不完全匹配，我们查找创建时间在时间戳前后2小时内的项目
            if supabase_service.client:
                try:
                    # 计算时间范围（前后2小时，使用ISO格式）
                    from datetime import timedelta
                    start_time = (target_date - timedelta(hours=2)).isoformat()
                    end_time = (target_date + timedelta(hours=2)).isoformat()
                    
                    # 使用线程池执行同步查询
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: supabase_service.client.table('projects').select('id').gte(
                            'created_at', start_time
                        ).lte('created_at', end_time).order('created_at').limit(1).execute()
                    )
                    
                    if response.data and len(response.data) > 0:
                        found_uuid = response.data[0].get('id')
                        logger.info(f"✅ 找到时间戳 {project_id} 对应的项目UUID: {found_uuid}")
                        _project_id_cache[project_id] = found_uuid  # 缓存结果
                        return found_uuid
                    else:
                        logger.debug(f"未在Supabase中找到时间戳 {project_id} 对应的项目（时间范围: {start_time} 到 {end_time}）")
                except Exception as e:
                    logger.debug(f"查询项目UUID失败: {e}")
            
            # 如果找不到对应的UUID，返回None并缓存（避免重复查询）
            logger.warning(f"⚠️ 时间戳格式的project_id {project_id} 无法映射到UUID，将跳过项目过滤")
            _project_id_cache[project_id] = None  # 缓存None结果
            return None
        except (ValueError, TypeError) as e:
            logger.warning(f"时间戳格式转换失败 {project_id}: {e}")
            return None
    
    # 其他格式，返回None并缓存
    logger.warning(f"⚠️ 无效的project_id格式: {project_id}")
    _project_id_cache[project_id] = None  # 缓存None结果
    return None

# 用于排序
def desc(field: str) -> str:
    """降序排序辅助函数"""
    return f"{field}.desc"


async def run_supabase_query(query_func):
    """
    在线程池中执行Supabase同步查询，避免阻塞事件循环
    
    Args:
        query_func: 返回Supabase查询对象的函数
        
    Returns:
        查询结果
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, query_func)


class SupabaseFileService:
    """Supabase文件存储服务"""

    def __init__(self):
        """初始化服务"""
        self.bucket_name = settings.STORAGE_BUCKET
        self.service = supabase_service

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.service.is_available() and self.service.client is not None

    async def upload_file(
        self,
        file_path: str,
        file_content: bytes,
        filename: str,
        user_id: str,
        project_id: Optional[str] = None,
        access_level: str = "all_users",
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        access_token: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        上传文件到Supabase Storage并创建数据库记录

        Args:
            file_path: 文件存储路径（相对于bucket）
            file_content: 文件二进制内容
            filename: 原始文件名
            user_id: 用户ID
            project_id: 项目ID（可选）
            access_level: 访问级别
            description: 文件描述
            tags: 文件标签列表

        Returns:
            文件记录字典，失败返回None
        """
        if not self.is_available():
            logger.error("Supabase服务不可用，无法上传文件")
            return None

        try:
            # 生成唯一文件名
            file_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix
            stored_filename = f"{file_id}{file_extension}"
            
            # 构建存储路径
            storage_path = f"{file_path}/{stored_filename}" if file_path else stored_filename

            # 优先使用admin_client（Service Key）进行Storage操作，绕过RLS策略
            storage_client = None
            if self.service.admin_client_available:
                storage_client = self.service.admin_client
                logger.info("✅ 使用admin_client上传文件到Storage（Service Key，绕过RLS）")
            elif self.service.client:
                storage_client = self.service.client
                logger.warning("⚠️ admin_client不可用，使用client上传文件到Storage（可能受RLS策略限制）")
            else:
                logger.error("❌ Supabase客户端未初始化，无法上传文件到Storage")
                return None

            # 上传到Supabase Storage
            logger.info(f"📤 准备上传文件到Storage: {storage_path}, 使用客户端: {'admin_client' if storage_client == self.service.admin_client else 'client'}")
            response = storage_client.storage.from_(self.bucket_name).upload(
                path=storage_path,
                file=file_content,
                file_options={
                    "content-type": self._get_content_type(filename),
                    "upsert": False
                }
            )

            # 检查上传是否成功
            # Supabase Storage的upload方法返回UploadResponse对象
            # 成功时返回UploadResponse(path=..., full_path=..., fullPath=...)
            # 失败时可能返回错误信息或抛出异常
            if hasattr(response, 'path') or hasattr(response, 'full_path') or hasattr(response, 'fullPath'):
                # 上传成功，UploadResponse对象包含path属性
                upload_path = getattr(response, 'path', None) or getattr(response, 'full_path', None) or getattr(response, 'fullPath', None)
                logger.info(f"✅ 文件上传到Storage成功: {upload_path}")
            elif hasattr(response, 'data') and response.data:
                # 某些版本的响应格式
                logger.debug(f"Storage上传响应: {response.data}")
            elif hasattr(response, 'error') and response.error:
                # 上传失败
                logger.error(f"文件上传到Storage失败: {response.error}")
                return None
            else:
                # 未知响应格式，但尝试继续（可能是成功但格式不同）
                logger.warning(f"⚠️ Storage上传响应格式未知: {type(response)} - {response}")
                # 不直接返回None，而是尝试继续，因为可能上传已经成功
                # 如果后续步骤失败，会在这里捕获错误

            # 获取文件URL（使用相同的客户端）
            file_url = storage_client.storage.from_(self.bucket_name).get_public_url(storage_path)

            # 验证user_id格式（确保是有效的UUID）
            if not is_valid_uuid(user_id):
                logger.warning(f"⚠️ user_id格式无效: {user_id}，尝试转换...")
                # 如果user_id不是UUID格式，记录错误但不阻止上传
                # 因为admin_client会绕过RLS，但数据库可能要求UUID格式
            
            # 规范化project_id（如果是时间戳，尝试查找对应的UUID）
            normalized_project_id = None
            if project_id:
                normalized_project_id = await normalize_project_id(project_id)
                if not normalized_project_id:
                    logger.warning(f"⚠️ 无法规范化project_id: {project_id}，将使用原始值")
                    normalized_project_id = project_id
            
            # 创建数据库记录
            file_data = {
                "id": file_id,
                "original_name": filename,
                "stored_name": stored_filename,
                "file_path": storage_path,
                "file_size": len(file_content),
                "file_type": self._get_content_type(filename),
                "file_extension": file_extension,
                "project_id": normalized_project_id,
                "uploaded_by": user_id,  # 确保这是UUID格式
                "access_level": access_level,
                "description": description,
                "tags": tags or [],
                "metadata": {
                    "storage_url": file_url,
                    "bucket": self.bucket_name
                }
            }

            logger.info(f"📝 准备创建数据库记录，文件: {filename}, user_id: {user_id}")
            logger.info(f"📝 检查service状态: admin_client_available={self.service.admin_client_available}")
            
            file_record = await self.service.create_file_record(file_data, access_token=access_token)

            if file_record:
                logger.info(f"✅ 文件上传成功: {filename} -> {storage_path}")
                return file_record
            else:
                logger.error(f"❌ 文件记录创建失败，返回None: {filename}")
                return None

        except Exception as e:
            logger.error(f"❌ 文件上传失败: {e}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            return None

    async def download_file(
        self,
        file_id: str,
        user_id: str,
        file_info: Optional[Dict[str, Any]] = None
    ) -> Optional[bytes]:
        """
        从Supabase Storage下载文件

        Args:
            file_id: 文件ID
            user_id: 用户ID（用于权限检查）
            file_info: 文件信息（可选，如果提供则避免重复查询）

        Returns:
            文件二进制内容，失败返回None
        """
        if not self.is_available():
            return None

        try:
            # 如果未提供file_info，则查询
            if file_info is None:
                file_info = await self.get_file_info(file_id)
            
            if not file_info:
                return None

            # 检查权限（传递file_info避免重复查询）
            if not await self._check_file_access(file_id, user_id, file_info=file_info):
                logger.warning(f"用户 {user_id} 无权限下载文件 {file_id}")
                return None

            # 从Storage下载（使用直接HTTP方式，性能更好）
            storage_path = file_info.get("file_path") or file_info.get("stored_name")
            
            # 使用直接HTTP方式下载Storage文件，绕过SDK
            try:
                from app.services.supabase_client import get_global_async_http_client
                import urllib.parse
                
                client = await get_global_async_http_client()
                base_url = settings.SUPABASE_URL.rstrip('/')
                # Storage API路径格式: /storage/v1/object/{bucket}/{path}
                encoded_path = urllib.parse.quote(storage_path, safe='')
                url = f"{base_url}/storage/v1/object/{self.bucket_name}/{encoded_path}"
                
                # 使用Service Key进行认证
                api_key = settings.SUPABASE_SERVICE_KEY
                headers = {
                    "apikey": api_key,
                    "Authorization": f"Bearer {api_key}"
                }
                
                http_response = await client.get(url, headers=headers)
                
                if http_response.status_code == 200:
                    response = http_response.content
                else:
                    logger.error(f"Storage下载失败: HTTP {http_response.status_code} - {http_response.text}")
                    # 回退到SDK方式
                    storage_client = self.service.admin_client if self.service.admin_client_available else self.service.client
                    if not storage_client:
                        logger.error("❌ Supabase客户端未初始化，无法下载文件")
                        return None
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: storage_client.storage.from_(self.bucket_name).download(storage_path)
                    )
            except Exception as http_error:
                logger.warning(f"直接HTTP下载失败，回退到SDK方式: {http_error}")
                # 回退到SDK方式
                storage_client = self.service.admin_client if self.service.admin_client_available else self.service.client
                if not storage_client:
                    logger.error("❌ Supabase客户端未初始化，无法下载文件")
                    return None
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: storage_client.storage.from_(self.bucket_name).download(storage_path)
                )

            if response:
                logger.info(f"文件下载成功: {file_id}")
                return response

            return None

        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return None

    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息（使用直接HTTP查询优化性能）

        Args:
            file_id: 文件ID

        Returns:
            文件信息字典
        """
        if not self.is_available():
            return None

        try:
            # 使用直接HTTP查询，性能更好
            results = await direct_supabase_query(
                table="files",
                select="*",
                filters={"id": file_id},
                limit=1,
                use_service_key=True
            )

            if results and len(results) > 0:
                return results[0]
            return None

        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None

    async def get_user_files(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户可访问的文件列表（使用直接HTTP查询优化）
        """
        if not self.is_available():
            return []

        try:
            # 构建过滤条件
            filters = {}
            
            if project_id:
                # 规范化项目ID
                normalized_id = await normalize_project_id(project_id)
                if normalized_id:
                    filters["project_id"] = normalized_id
                else:
                    logger.warning(f"无法规范化 project_id: {project_id}，跳过项目过滤")

            # 限制查询数量
            max_limit = min(limit, 100)
            
            # OR过滤条件：用户上传的文件 OR 公开访问的文件
            or_filters = f"access_level.eq.all_users,uploaded_by.eq.{user_id}"

            # 使用直接 HTTP 查询
            return await direct_supabase_query(
                table="files",
                select="*",
                filters=filters if filters else None,
                or_filters=or_filters,
                order_by="created_at",
                order_desc=True,
                limit=max_limit,
                use_service_key=True
            )

        except Exception as e:
            logger.error(f"获取用户文件列表失败: {e}")
            return []

    async def delete_file(
        self,
        file_id: str,
        user_id: str
    ) -> bool:
        """
        删除文件

        Args:
            file_id: 文件ID
            user_id: 用户ID（用于权限检查）

        Returns:
            删除成功返回True
        """
        if not self.is_available():
            return False

        try:
            # 获取文件信息
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return False

            # 检查权限（只有上传者或管理员可以删除）
            if file_info.get('uploaded_by') != user_id:
                logger.warning(f"用户 {user_id} 无权限删除文件 {file_id}")
                return False

            # 从Storage删除（优先使用admin_client）
            storage_path = file_info.get("file_path") or file_info.get("stored_name")
            storage_client = self.service.admin_client if self.service.admin_client_available else self.service.client
            if not storage_client:
                logger.error("❌ Supabase客户端未初始化，无法删除文件")
                return False
            try:
                storage_client.storage.from_(self.bucket_name).remove([storage_path])
            except Exception as storage_error:
                logger.warning(f"从Storage删除文件失败（继续删除数据库记录）: {storage_error}")

            # 删除数据库记录
            response = await run_supabase_query(
                lambda: self.service.client.table('files').delete().eq('id', file_id).execute()
            )

            logger.info(f"文件删除成功: {file_id}")
            return True

        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return False

    async def update_file_access_level(
        self,
        file_id: str,
        access_level: str,
        user_id: str
    ) -> bool:
        """
        更新文件访问级别

        Args:
            file_id: 文件ID
            access_level: 新的访问级别
            user_id: 用户ID（用于权限检查）

        Returns:
            更新成功返回True
        """
        if not self.is_available():
            return False

        try:
            # 获取文件信息
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return False

            # 检查权限（只有上传者可以修改）
            if file_info.get('uploaded_by') != user_id:
                return False

            # 更新访问级别
            response = await run_supabase_query(
                lambda: self.service.client.table('files').update({
                    'access_level': access_level
                }).eq('id', file_id).execute()
            )

            return bool(response.data)

        except Exception as e:
            logger.error(f"更新文件访问级别失败: {e}")
            return False

    async def share_file(
        self,
        file_id: str,
        share_with_user_id: str,
        permissions: Dict[str, bool],
        expires_at: Optional[str] = None
    ) -> bool:
        """
        分享文件给其他用户

        Args:
            file_id: 文件ID
            share_with_user_id: 分享给的用户ID
            permissions: 权限字典
            expires_at: 过期时间（可选）

        Returns:
            分享成功返回True
        """
        if not self.is_available():
            return False

        try:
            # 这里可以实现文件分享逻辑
            # 可以创建一个file_shares表来记录分享关系
            logger.info(f"文件分享: {file_id} -> {share_with_user_id}")
            return True

        except Exception as e:
            logger.error(f"文件分享失败: {e}")
            return False

    async def get_file_shares(self, file_id: str) -> List[Dict[str, Any]]:
        """
        获取文件分享记录

        Args:
            file_id: 文件ID

        Returns:
            分享记录列表
        """
        if not self.is_available():
            return []

        try:
            # 这里可以查询file_shares表
            return []

        except Exception as e:
            logger.error(f"获取文件分享记录失败: {e}")
            return []

    async def search_files(
        self,
        query: Optional[str] = None,
        user_id: str = None,
        project_id: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        搜索文件

        Args:
            query: 搜索关键词
            user_id: 用户ID
            project_id: 项目ID（可选）
            file_type: 文件类型（可选）
            limit: 返回数量限制

        Returns:
            文件列表
        """
        if not self.is_available():
            return []

        try:
            db_query = self.service.client.table('files').select('*')

            if project_id:
                # 规范化项目ID（如果是时间戳，尝试查找对应的UUID）
                normalized_id = await normalize_project_id(project_id)
                if normalized_id:
                    db_query = db_query.eq('project_id', normalized_id)
                else:
                    logger.warning(f"无法规范化 project_id: {project_id}，跳过项目过滤")

            if file_type:
                db_query = db_query.eq('file_type', file_type)

            if query:
                db_query = db_query.or_(
                    f"original_name.ilike.%{query}%,description.ilike.%{query}%"
                )

            # 权限过滤
            if user_id:
                db_query = db_query.or_(
                    f"access_level.eq.all_users,uploaded_by.eq.{user_id}"
                )

            response = await run_supabase_query(
                lambda: db_query.limit(limit).order('created_at').execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"搜索文件失败: {e}")
            return []

    async def get_file_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取文件统计信息（使用直接HTTP查询优化）

        Args:
            user_id: 用户ID

        Returns:
            统计信息字典
        """
        if not self.is_available():
            return {
                "total_files": 0,
                "total_size": 0,
                "by_type": {},
                "by_project": {}
            }

        try:
            # 使用直接 HTTP 查询
            or_filters = f"access_level.eq.all_users,uploaded_by.eq.{user_id}"
            files = await direct_supabase_query(
                table="files",
                select="id,file_size,file_type,project_id",
                or_filters=or_filters,
                limit=100,
                use_service_key=True
            )

            total_files = len(files)
            total_size = sum(f.get('file_size', 0) for f in files)

            # 按类型统计
            by_type = {}
            for f in files:
                file_type = f.get('file_type', 'unknown')
                by_type[file_type] = by_type.get(file_type, 0) + 1

            # 按项目统计
            by_project = {}
            for f in files:
                project_id = f.get('project_id', 'none')
                by_project[project_id] = by_project.get(project_id, 0) + 1

            return {
                "total_files": total_files,
                "total_size": total_size,
                "by_type": by_type,
                "by_project": by_project
            }

        except Exception as e:
            logger.error(f"获取文件统计失败: {e}")
            return {
                "total_files": 0,
                "total_size": 0,
                "by_type": {},
                "by_project": {}
            }

    async def update_file_metadata(
        self,
        file_id: str,
        metadata_updates: Dict[str, Any],
        user_id: str
    ) -> bool:
        """
        更新文件元数据

        Args:
            file_id: 文件ID
            metadata_updates: 元数据更新字典
            user_id: 用户ID（用于权限检查）

        Returns:
            更新成功返回True
        """
        if not self.is_available():
            return False

        try:
            # 获取文件信息
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return False

            # 检查权限
            if file_info.get('uploaded_by') != user_id:
                return False

            # 更新元数据
            update_data = {}
            if 'description' in metadata_updates:
                update_data['description'] = metadata_updates['description']
            if 'tags' in metadata_updates:
                update_data['tags'] = metadata_updates['tags']

            if update_data:
                response = await run_supabase_query(
                    lambda: self.service.client.table('files').update(update_data).eq('id', file_id).execute()
                )
                return bool(response.data)

            return False

        except Exception as e:
            logger.error(f"更新文件元数据失败: {e}")
            return False

    async def _check_file_access(self, file_id: str, user_id: str, file_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        检查用户是否有权限访问文件

        Args:
            file_id: 文件ID
            user_id: 用户ID
            file_info: 文件信息（可选，如果提供则避免重复查询）

        Returns:
            有权限返回True
        """
        try:
            # 如果未提供file_info，则查询
            if file_info is None:
                file_info = await self.get_file_info(file_id)
            
            if not file_info:
                return False

            access_level = file_info.get('access_level', 'all_users')
            uploaded_by = file_info.get('uploaded_by')

            # 上传者总是有权限
            if uploaded_by == user_id:
                return True

            # all_users级别所有人都可以访问
            if access_level == 'all_users':
                return True

            # 其他级别需要进一步检查项目权限等
            # 这里简化处理，实际应该检查项目成员关系
            return False

        except Exception as e:
            logger.error(f"检查文件访问权限失败: {e}")
            return False

    def _get_content_type(self, filename: str) -> str:
        """
        根据文件名获取Content-Type

        Args:
            filename: 文件名

        Returns:
            Content-Type字符串
        """
        extension = Path(filename).suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.txt': 'text/plain',
            '.md': 'text/markdown',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.mp4': 'video/mp4',
            '.mp3': 'audio/mpeg',
        }
        return content_types.get(extension, 'application/octet-stream')

    async def user_can_access_file(self, file_id: str, user_id: str, is_admin: bool = False, file_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        检查用户是否有权限访问文件（公开方法）

        Args:
            file_id: 文件ID
            user_id: 用户ID
            is_admin: 是否为管理员
            file_info: 文件信息（可选，如果提供则避免重复查询）

        Returns:
            有权限返回True
        """
        return await self._check_file_access(file_id, user_id, file_info=file_info)

    async def get_files(
        self,
        project_id: Optional[str] = None,
        stage: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取文件列表（管理员使用，使用直接HTTP查询优化）
        """
        if not self.is_available():
            return []

        try:
            # 构建过滤条件
            filters = {}
            
            if project_id:
                # 规范化项目ID（如果是时间戳，尝试查找对应的UUID）
                normalized_id = await normalize_project_id(project_id)
                if normalized_id:
                    filters["project_id"] = normalized_id
                else:
                    logger.warning(f"无法规范化 project_id: {project_id}，跳过项目过滤")

            # 分页参数
            offset = (page - 1) * size
            max_size = min(size, 100)
            
            # 使用直接 HTTP 查询
            return await direct_supabase_query(
                table="files",
                select="*",
                filters=filters if filters else None,
                order_by="created_at",
                order_desc=True,
                limit=max_size,
                offset=offset,
                use_service_key=True
            )

        except Exception as e:
            logger.error(f"获取文件列表失败: {e}")
            return []

    async def get_files_by_user(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        stage: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户的文件列表

        Args:
            user_id: 用户ID
            project_id: 项目ID筛选
            stage: 项目阶段筛选
            tags: 标签列表
            search: 搜索关键词
            page: 页码
            size: 每页数量

        Returns:
            文件列表
        """
        return await self.get_user_files(user_id, project_id, limit=size)

    async def update_file(
        self,
        file_id: str,
        file_update: Dict[str, Any],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        更新文件信息

        Args:
            file_id: 文件ID
            file_update: 更新数据字典
            user_id: 用户ID（用于权限检查）

        Returns:
            更新后的文件信息，失败返回None
        """
        if not self.is_available():
            return None

        try:
            # 获取文件信息
            file_info = await self.get_file_info(file_id)
            
            if not file_info:
                return None

            # 检查权限
            uploaded_by = file_info.get('uploaded_by')
            
            if str(uploaded_by) != str(user_id):
                logger.warning(f"用户 {user_id} 无权限更新文件 {file_id} (uploaded_by: {uploaded_by})")
                return None

            # 构建更新数据
            update_data = {}
            optional_fields = {}  # 可选字段（如果不存在，不影响其他字段更新）
            
            if 'original_name' in file_update:
                update_data['original_name'] = file_update['original_name']
            if 'description' in file_update:
                update_data['description'] = file_update['description']
            if 'stage' in file_update:
                # stage字段可能不存在，先尝试更新，如果失败则忽略
                optional_fields['stage'] = file_update['stage']
            if 'tags' in file_update:
                # tags字段必须存在，确保正确处理
                tags_value = file_update['tags']
                if tags_value is not None:
                    # 确保tags是列表格式
                    if isinstance(tags_value, list):
                        update_data['tags'] = tags_value
                    else:
                        # 如果不是列表，尝试转换
                        update_data['tags'] = [tags_value] if tags_value else []
                else:
                    # tags为None时，设置为空数组
                    update_data['tags'] = []
            if 'is_public' in file_update:
                update_data['is_public'] = file_update['is_public']

            if not update_data and not optional_fields:
                return file_info

            # 先尝试更新必需字段（不包括可选字段，因为可选字段可能不存在）
            # 如果只有必需字段，直接更新
            if update_data and not optional_fields:
                try:
                    # 使用直接HTTP方式更新，性能更好
                    response_data = await direct_supabase_update(
                        table="files",
                        update_data=update_data,
                        filters={"id": file_id},
                        use_service_key=True
                    )
                    
                    if response_data and len(response_data) > 0:
                        return response_data[0]
                    else:
                        # 更新成功但返回空数据，重新查询文件信息以确保返回最新数据
                        logger.debug(f"数据库更新成功但返回空数据，重新查询文件信息: {file_id}")
                        # 重新查询文件信息（使用已优化的direct_supabase_query）
                        updated_file_info = await self.get_file_info(file_id)
                        if updated_file_info:
                            return updated_file_info
                        else:
                            logger.warning(f"重新查询文件信息失败，返回原文件信息: {file_id}")
                            return file_info
                except Exception as update_error:
                    error_str = str(update_error)
                    logger.error(f"直接HTTP更新失败: {error_str}")
                    # 如果直接HTTP更新失败，回退到SDK方式
                    logger.debug(f"回退到SDK方式更新: {file_id}")
                    try:
                        response = await run_supabase_query(
                            lambda: self.service.client.table('files').update(update_data).eq('id', file_id).execute()
                        )
                        if response.data and len(response.data) > 0:
                            return response.data[0]
                        else:
                            # SDK方式也返回空数据，重新查询
                            updated_file_info = await self.get_file_info(file_id)
                            return updated_file_info if updated_file_info else file_info
                    except Exception as sdk_error:
                        logger.error(f"SDK方式更新也失败: {sdk_error}")
                        return None
            
            # 如果有可选字段，先尝试更新所有字段（包括可选字段）
            # 但如果可选字段导致错误，会回退到只更新必需字段
            all_update_data = {**update_data, **optional_fields}
            try:
                # 使用直接HTTP方式更新，性能更好
                response_data = await direct_supabase_update(
                    table="files",
                    update_data=all_update_data,
                    filters={"id": file_id},
                    use_service_key=True
                )
                
                if response_data and len(response_data) > 0:
                    return response_data[0]
                else:
                    # 更新成功但返回空数据，重新查询文件信息以确保返回最新数据
                    logger.debug(f"数据库更新成功但返回空数据，重新查询文件信息: {file_id}")
                    # 重新查询文件信息（使用已优化的direct_supabase_query）
                    updated_file_info = await self.get_file_info(file_id)
                    if updated_file_info:
                        return updated_file_info
                    else:
                        logger.warning(f"重新查询文件信息失败，返回原文件信息: {file_id}")
                        return file_info
            except ValueError as field_error:
                # 字段不存在的错误，回退到只更新必需字段
                error_str = str(field_error)
                
                # 如果是因为可选字段不存在导致的错误，尝试只更新必需字段
                if optional_fields and update_data:
                    logger.debug(f"可选字段不存在，尝试只更新必需字段: {file_id}")
                    try:
                        # 使用直接HTTP方式更新必需字段，性能更好
                        response_data = await direct_supabase_update(
                            table="files",
                            update_data=update_data,
                            filters={"id": file_id},
                            use_service_key=True
                        )
                        
                        if response_data and len(response_data) > 0:
                            logger.debug(f"必需字段更新成功，跳过了可选字段: {file_id}")
                            return response_data[0]
                        else:
                            # 更新成功但返回空数据，重新查询文件信息
                            logger.debug(f"必需字段更新成功但返回空数据，重新查询文件信息: {file_id}")
                            # 重新查询文件信息（使用已优化的direct_supabase_query）
                            updated_file_info = await self.get_file_info(file_id)
                            if updated_file_info:
                                return updated_file_info
                            else:
                                logger.error(f"重新查询文件信息失败: {file_id}")
                                return None
                    except Exception as required_error:
                        logger.error(f"更新必需字段也失败: {required_error}")
                        return None
                else:
                    # 只有可选字段，字段不存在不算错误
                    logger.debug(f"只有可选字段需要更新，但字段不存在，返回原文件信息: {file_id}")
                    return file_info
            except Exception as optional_error:
                error_str = str(optional_error)
                
                # 如果是因为可选字段不存在导致的错误，尝试只更新必需字段
                if optional_fields and ("not find" in error_str.lower() or "PGRST204" in error_str or "column" in error_str.lower()):
                    logger.debug(f"某些可选字段不存在，尝试只更新必需字段: {file_id}")
                    if update_data:
                        try:
                            # 使用直接HTTP方式更新必需字段，性能更好
                            response_data = await direct_supabase_update(
                                table="files",
                                update_data=update_data,
                                filters={"id": file_id},
                                use_service_key=True
                            )
                            
                            if response_data and len(response_data) > 0:
                                logger.debug(f"必需字段更新成功，跳过了可选字段: {file_id}")
                                return response_data[0]
                            else:
                                # 更新成功但返回空数据，重新查询文件信息
                                logger.debug(f"必需字段更新成功但返回空数据，重新查询文件信息: {file_id}")
                                # 重新查询文件信息（使用已优化的direct_supabase_query）
                                updated_file_info = await self.get_file_info(file_id)
                                if updated_file_info:
                                    return updated_file_info
                                else:
                                    logger.error(f"重新查询文件信息失败: {file_id}")
                                    return None
                        except Exception as required_error:
                            logger.error(f"更新必需字段也失败: {required_error}")
                            return None
                    else:
                        # 只有可选字段，字段不存在不算错误
                        logger.debug(f"只有可选字段需要更新，但字段不存在，返回原文件信息: {file_id}")
                        return file_info
                else:
                    # 其他错误，重新抛出
                    logger.error(f"数据库更新失败（非字段不存在错误）: {error_str}")
                    raise
            
            return None

        except Exception as e:
            logger.error(f"更新文件失败: {e}")
            return None

    async def increment_view_count(self, file_id: str) -> bool:
        """
        增加查看次数

        Args:
            file_id: 文件ID

        Returns:
            更新成功返回True（如果字段不存在，返回True但不报错）
        """
        if not self.is_available():
            return False

        try:
            # 获取当前查看次数
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return False

            current_count = file_info.get('view_count', 0)
            
            # 更新查看次数
            response = await run_supabase_query(
                lambda: self.service.client.table('files').update({
                    'view_count': current_count + 1
                }).eq('id', file_id).execute()
            )

            return bool(response.data)

        except Exception as e:
            error_str = str(e)
            # 如果字段不存在，记录调试信息但不报错
            if "view_count" in error_str and ("not find" in error_str.lower() or "PGRST204" in error_str):
                logger.debug(f"view_count字段不存在，跳过更新查看次数: {file_id}")
                return True  # 字段不存在不算错误，返回True
            else:
                logger.warning(f"更新查看次数失败: {e}")
                return False

    async def increment_download_count(self, file_id: str, file_info: Optional[Dict[str, Any]] = None) -> bool:
        """
        增加下载次数

        Args:
            file_id: 文件ID
            file_info: 文件信息（可选，如果提供则避免重复查询）

        Returns:
            更新成功返回True（如果字段不存在，返回True但不报错）
        """
        if not self.is_available():
            return False

        try:
            # 如果未提供file_info，则查询
            if file_info is None:
                file_info = await self.get_file_info(file_id)
                if not file_info:
                    return False

            current_count = file_info.get('download_count', 0)
            
            # 更新下载次数
            response = await run_supabase_query(
                lambda: self.service.client.table('files').update({
                    'download_count': current_count + 1
                }).eq('id', file_id).execute()
            )

            return bool(response.data)

        except Exception as e:
            error_str = str(e)
            # 如果字段不存在，记录调试信息但不报错
            if "download_count" in error_str and ("not find" in error_str.lower() or "PGRST204" in error_str):
                logger.debug(f"download_count字段不存在，跳过更新下载次数: {file_id}")
                return True  # 字段不存在不算错误，返回True
            else:
                logger.warning(f"更新下载次数失败: {e}")
                return False

    async def get_files_by_project(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取项目的所有文件

        Args:
            project_id: 项目ID

        Returns:
            文件列表
        """
        if not self.is_available():
            return []

        try:
            # 规范化项目ID（如果是时间戳，尝试查找对应的UUID）
            normalized_id = await normalize_project_id(project_id)
            if normalized_id:
                response = await run_supabase_query(
                    lambda: self.service.client.table('files').select('*').eq('project_id', normalized_id).execute()
                )
            else:
                logger.warning(f"无法规范化 project_id: {project_id}，返回空列表")
                return []
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取项目文件失败: {e}")
            return []

    async def get_all_files(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        获取所有文件（使用直接HTTP查询优化）

        Returns:
            文件列表
        """
        if not self.is_available():
            return []

        try:
            # 使用直接 HTTP 查询，绕过 SDK
            return await direct_supabase_query(
                table="files",
                select="*",
                limit=min(limit, 100),  # 限制最大100条
                use_service_key=True
            )

        except Exception as e:
            logger.error(f"获取所有文件失败: {e}")
            return []

    async def get_file_stats_all(self) -> Dict[str, Any]:
        """
        获取所有文件统计信息（管理员使用，使用直接HTTP查询优化）

        Returns:
            统计信息字典
        """
        if not self.is_available():
            return {
                "total_files": 0,
                "total_size": 0,
                "files_by_stage": {},
                "files_by_type": {},
                "recent_uploads": [],
                "popular_files": []
            }

        try:
            # 使用直接 HTTP 查询，绕过 SDK
            all_files = await direct_supabase_query(
                table="files",
                select="id,file_size,file_type",
                limit=100,
                use_service_key=True
            )

            total_files = len(all_files)
            total_size = sum(f.get('file_size', 0) for f in all_files)

            # 按类型统计（移除了 stage 统计，因为列不存在）
            files_by_stage = {}  # 保留空字典以兼容
            files_by_type = {}
            for f in all_files:
                file_type = f.get('file_type', 'unknown')
                files_by_type[file_type] = files_by_type.get(file_type, 0) + 1

            # 简化：不再查询最近上传和热门文件（这些可以单独的API提供）
            return {
                "total_files": total_files,
                "total_size": total_size,
                "files_by_stage": files_by_stage,
                "files_by_type": files_by_type,
                "recent_uploads": [],
                "popular_files": []
            }

        except Exception as e:
            logger.error(f"获取文件统计失败: {e}")
            return {
                "total_files": 0,
                "total_size": 0,
                "files_by_stage": {},
                "files_by_type": {},
                "recent_uploads": [],
                "popular_files": []
            }


# 全局服务实例
supabase_file_service = SupabaseFileService()

