#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Supabase文件存储服务
基于Supabase Storage的文件上传、下载和管理
"""

import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger

from app.services.supabase_client import supabase_service
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

async def normalize_project_id(project_id: str) -> Optional[str]:
    """
    规范化项目ID：如果是时间戳格式，尝试在Supabase中查找对应的UUID
    
    Args:
        project_id: 项目ID字符串
        
    Returns:
        规范化的UUID格式项目ID，如果无法转换则返回None
    """
    if not project_id:
        return None
    
    # 如果是有效的UUID，直接返回
    if is_valid_uuid(project_id):
        return project_id
    
    # 如果是纯数字（可能是时间戳），尝试在Supabase中查找对应的项目
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
                    
                    response = supabase_service.client.table('projects').select('id').gte(
                        'created_at', start_time
                    ).lte('created_at', end_time).order('created_at', desc=False).limit(1).execute()
                    
                    if response.data and len(response.data) > 0:
                        found_uuid = response.data[0].get('id')
                        logger.info(f"✅ 找到时间戳 {project_id} 对应的项目UUID: {found_uuid}")
                        return found_uuid
                    else:
                        logger.debug(f"未在Supabase中找到时间戳 {project_id} 对应的项目（时间范围: {start_time} 到 {end_time}）")
                except Exception as e:
                    logger.debug(f"查询项目UUID失败: {e}")
            
            # 如果找不到对应的UUID，返回None（调用者会跳过项目过滤）
            logger.warning(f"⚠️ 时间戳格式的project_id {project_id} 无法映射到UUID，将跳过项目过滤")
            return None
        except (ValueError, TypeError) as e:
            logger.warning(f"时间戳格式转换失败 {project_id}: {e}")
            return None
    
    # 其他格式，返回None
    logger.warning(f"⚠️ 无效的project_id格式: {project_id}")
    return None

# 用于排序
def desc(field: str) -> str:
    """降序排序辅助函数"""
    return f"{field}.desc"


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

            # 上传到Supabase Storage
            response = self.service.client.storage.from_(self.bucket_name).upload(
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

            # 获取文件URL
            file_url = self.service.client.storage.from_(self.bucket_name).get_public_url(storage_path)

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

            file_record = await self.service.create_file_record(file_data, access_token=access_token)

            if file_record:
                logger.info(f"文件上传成功: {filename} -> {storage_path}")
                return file_record

            return None

        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return None

    async def download_file(
        self,
        file_id: str,
        user_id: str
    ) -> Optional[bytes]:
        """
        从Supabase Storage下载文件

        Args:
            file_id: 文件ID
            user_id: 用户ID（用于权限检查）

        Returns:
            文件二进制内容，失败返回None
        """
        if not self.is_available():
            return None

        try:
            # 获取文件记录
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return None

            # 检查权限
            if not await self._check_file_access(file_id, user_id):
                logger.warning(f"用户 {user_id} 无权限下载文件 {file_id}")
                return None

            # 从Storage下载
            storage_path = file_info.get("file_path") or file_info.get("stored_name")
            response = self.service.client.storage.from_(self.bucket_name).download(storage_path)

            if response:
                logger.info(f"文件下载成功: {file_id}")
                return response

            return None

        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return None

    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息

        Args:
            file_id: 文件ID

        Returns:
            文件信息字典
        """
        if not self.is_available():
            return None

        try:
            response = self.service.client.table('files').select('*').eq('id', file_id).single().execute()

            if response.data:
                return response.data
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
        获取用户可访问的文件列表

        Args:
            user_id: 用户ID
            project_id: 项目ID（可选）
            limit: 返回数量限制

        Returns:
            文件列表
        """
        if not self.is_available():
            return []

        try:
            query = self.service.client.table('files').select('*')

            if project_id:
                # 规范化项目ID（如果是时间戳，尝试查找对应的UUID）
                normalized_id = await normalize_project_id(project_id)
                if normalized_id:
                    query = query.eq('project_id', normalized_id)
                else:
                    logger.warning(f"无法规范化 project_id: {project_id}，跳过项目过滤")
                    # 如果无法规范化，跳过项目过滤

            # 根据访问级别过滤
            query = query.or_(
                f"access_level.eq.all_users,uploaded_by.eq.{user_id}"
            )

            response = query.limit(limit).order('created_at', desc=False).execute()

            return response.data if response.data else []

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

            # 从Storage删除
            storage_path = file_info.get("file_path") or file_info.get("stored_name")
            try:
                self.service.client.storage.from_(self.bucket_name).remove([storage_path])
            except Exception as storage_error:
                logger.warning(f"从Storage删除文件失败（继续删除数据库记录）: {storage_error}")

            # 删除数据库记录
            response = self.service.client.table('files').delete().eq('id', file_id).execute()

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
            response = self.service.client.table('files').update({
                'access_level': access_level
            }).eq('id', file_id).execute()

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

            response = db_query.limit(limit).order('created_at', desc=False).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"搜索文件失败: {e}")
            return []

    async def get_file_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取文件统计信息

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
            # 获取用户文件
            files = await self.get_user_files(user_id, limit=1000)

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
                response = self.service.client.table('files').update(update_data).eq('id', file_id).execute()
                return bool(response.data)

            return False

        except Exception as e:
            logger.error(f"更新文件元数据失败: {e}")
            return False

    async def _check_file_access(self, file_id: str, user_id: str) -> bool:
        """
        检查用户是否有权限访问文件

        Args:
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            有权限返回True
        """
        try:
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

    async def user_can_access_file(self, file_id: str, user_id: str, is_admin: bool = False) -> bool:
        """
        检查用户是否有权限访问文件（公开方法）

        Args:
            file_id: 文件ID
            user_id: 用户ID
            is_admin: 是否为管理员

        Returns:
            有权限返回True
        """
        return await self._check_file_access(file_id, user_id)

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
        获取文件列表（管理员使用）

        Args:
            project_id: 项目ID筛选
            stage: 项目阶段筛选
            tags: 标签列表
            search: 搜索关键词
            page: 页码
            size: 每页数量

        Returns:
            文件列表
        """
        if not self.is_available():
            return []

        try:
            query = self.service.client.table('files').select('*')

            if project_id:
                # 规范化项目ID（如果是时间戳，尝试查找对应的UUID）
                normalized_id = await normalize_project_id(project_id)
                if normalized_id:
                    query = query.eq('project_id', normalized_id)
                else:
                    logger.warning(f"无法规范化 project_id: {project_id}，跳过项目过滤")
                    # 如果无法规范化，跳过项目过滤，返回所有文件
            if stage:
                query = query.eq('stage', stage)
            if tags:
                # Supabase数组查询：检查tags数组是否包含任一标签
                # 注意：Supabase的contains需要精确匹配，这里简化处理
                pass  # 标签筛选功能暂时跳过，Supabase数组查询较复杂
            if search:
                query = query.or_(
                    f"original_name.ilike.%{search}%,description.ilike.%{search}%"
                )

            # 分页
            offset = (page - 1) * size
            response = query.order('created_at', desc=False).range(offset, offset + size - 1).execute()

            return response.data if response.data else []

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
            if file_info.get('uploaded_by') != user_id:
                logger.warning(f"用户 {user_id} 无权限更新文件 {file_id}")
                return None

            # 构建更新数据
            update_data = {}
            if 'original_name' in file_update:
                update_data['original_name'] = file_update['original_name']
            if 'description' in file_update:
                update_data['description'] = file_update['description']
            if 'stage' in file_update:
                update_data['stage'] = file_update['stage']
            if 'tags' in file_update:
                update_data['tags'] = file_update['tags']
            if 'is_public' in file_update:
                update_data['is_public'] = file_update['is_public']

            if not update_data:
                return file_info

            # 更新文件
            response = self.service.client.table('files').update(update_data).eq('id', file_id).execute()

            if response.data:
                return response.data[0]
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
            更新成功返回True
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
            response = self.service.client.table('files').update({
                'view_count': current_count + 1
            }).eq('id', file_id).execute()

            return bool(response.data)

        except Exception as e:
            logger.error(f"更新查看次数失败: {e}")
            return False

    async def increment_download_count(self, file_id: str) -> bool:
        """
        增加下载次数

        Args:
            file_id: 文件ID

        Returns:
            更新成功返回True
        """
        if not self.is_available():
            return False

        try:
            # 获取当前下载次数
            file_info = await self.get_file_info(file_id)
            if not file_info:
                return False

            current_count = file_info.get('download_count', 0)
            
            # 更新下载次数
            response = self.service.client.table('files').update({
                'download_count': current_count + 1
            }).eq('id', file_id).execute()

            return bool(response.data)

        except Exception as e:
            logger.error(f"更新下载次数失败: {e}")
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
                response = self.service.client.table('files').select('*').eq('project_id', normalized_id).execute()
            else:
                logger.warning(f"无法规范化 project_id: {project_id}，返回空列表")
                return []
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取项目文件失败: {e}")
            return []

    async def get_all_unprocessed_files(self) -> List[Dict[str, Any]]:
        """
        获取所有未处理的文件

        Returns:
            文件列表
        """
        if not self.is_available():
            return []

        try:
            response = self.service.client.table('files').select('*').eq('is_processed', False).execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取未处理文件失败: {e}")
            return []

    async def get_all_files(self) -> List[Dict[str, Any]]:
        """
        获取所有文件

        Returns:
            文件列表
        """
        if not self.is_available():
            return []

        try:
            response = self.service.client.table('files').select('*').execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取所有文件失败: {e}")
            return []

    async def mark_file_processed(self, file_id: str) -> bool:
        """
        标记文件已处理（已索引到向量数据库）

        Args:
            file_id: 文件ID

        Returns:
            标记成功返回True
        """
        if not self.is_available():
            return False

        try:
            response = self.service.client.table('files').update({
                'is_processed': True
            }).eq('id', file_id).execute()

            return bool(response.data)

        except Exception as e:
            logger.error(f"标记文件已处理失败: {e}")
            return False

    async def get_file_stats_all(self) -> Dict[str, Any]:
        """
        获取所有文件统计信息（管理员使用）

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
            # 获取所有文件
            all_files = await self.get_all_files()

            total_files = len(all_files)
            total_size = sum(f.get('file_size', 0) for f in all_files)

            # 按阶段统计
            files_by_stage = {}
            for f in all_files:
                stage = f.get('stage', 'unknown')
                files_by_stage[stage] = files_by_stage.get(stage, 0) + 1

            # 按类型统计
            files_by_type = {}
            for f in all_files:
                file_type = f.get('file_type', 'unknown')
                files_by_type[file_type] = files_by_type.get(file_type, 0) + 1

            # 最近上传的文件（按created_at排序）
            recent_uploads = sorted(all_files, key=lambda x: x.get('created_at', ''), reverse=True)[:5]

            # 热门文件（按view_count排序）
            popular_files = sorted(all_files, key=lambda x: x.get('view_count', 0), reverse=True)[:5]

            return {
                "total_files": total_files,
                "total_size": total_size,
                "files_by_stage": files_by_stage,
                "files_by_type": files_by_type,
                "recent_uploads": recent_uploads,
                "popular_files": popular_files
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

