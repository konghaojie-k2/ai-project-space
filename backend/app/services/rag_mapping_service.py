#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG文档映射服务
管理本地文件表和外部RAG应用之间的映射关系
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from loguru import logger

from app.services.supabase_client import supabase_service


class RAGMappingService:
    """RAG文档映射服务"""

    def __init__(self):
        """初始化服务"""
        self.table_name = "rag_document_mapping"

    def is_available(self) -> bool:
        """检查服务是否可用"""
        return supabase_service.is_available()

    async def create_mapping(
        self,
        local_file_id: str,
        external_document_id: str,
        external_collection_name: str,
        project_id: Optional[str] = None,
        external_kb_id: Optional[str] = None,
        chunk_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        创建映射记录

        Args:
            local_file_id: 本地文件ID
            external_document_id: 外部RAG文档ID
            external_collection_name: 外部知识库名称
            project_id: 项目ID（可选）
            external_kb_id: 外部知识库ID（可选）
            chunk_count: 文档分块数量

        Returns:
            创建的映射记录，失败返回None
        """
        if not self.is_available():
            logger.error("Supabase服务不可用，无法创建映射记录")
            return None

        try:
            mapping_data = {
                "local_file_id": local_file_id,
                "external_document_id": external_document_id,
                "external_collection_name": external_collection_name,
                "chunk_count": chunk_count
            }

            if project_id:
                mapping_data["project_id"] = project_id
            if external_kb_id:
                mapping_data["external_kb_id"] = external_kb_id

            response = supabase_service.client.table(self.table_name).insert(
                mapping_data
            ).execute()

            if response.data:
                logger.info(
                    f"映射记录创建成功: local_file_id={local_file_id}, "
                    f"external_document_id={external_document_id}"
                )
                return response.data[0]
            else:
                logger.error("映射记录创建失败：响应数据为空")
                return None

        except Exception as e:
            logger.error(f"创建映射记录失败: {e}")
            return None

    async def get_mapping_by_file_id(
        self,
        local_file_id: str,
        collection_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        根据本地文件ID获取映射记录

        Args:
            local_file_id: 本地文件ID
            collection_name: 知识库名称（可选，用于过滤）

        Returns:
            映射记录，不存在返回None
        """
        if not self.is_available():
            return None

        try:
            query = supabase_service.client.table(self.table_name).select("*").eq(
                "local_file_id", local_file_id
            )

            if collection_name:
                query = query.eq("external_collection_name", collection_name)

            response = query.execute()

            if response.data and len(response.data) > 0:
                # 如果指定了collection_name，返回第一个匹配的记录
                # 否则返回第一个记录
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"获取映射记录失败: {e}")
            return None

    async def get_mapping_by_external_id(
        self,
        external_document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        根据外部文档ID获取映射记录

        Args:
            external_document_id: 外部RAG文档ID

        Returns:
            映射记录，不存在返回None
        """
        if not self.is_available():
            return None

        try:
            response = supabase_service.client.table(self.table_name).select("*").eq(
                "external_document_id", external_document_id
            ).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"根据外部ID获取映射记录失败: {e}")
            return None

    async def get_mappings_by_project(
        self,
        project_id: str,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取项目的所有映射记录

        Args:
            project_id: 项目ID
            collection_name: 知识库名称（可选，用于过滤）

        Returns:
            映射记录列表
        """
        if not self.is_available():
            return []

        try:
            query = supabase_service.client.table(self.table_name).select("*").eq(
                "project_id", project_id
            )

            if collection_name:
                query = query.eq("external_collection_name", collection_name)

            response = query.order("created_at", desc=True).execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"获取项目映射记录失败: {e}")
            return []

    async def update_chunk_count(
        self,
        mapping_id: str,
        chunk_count: int
    ) -> bool:
        """
        更新映射记录的chunk_count

        Args:
            mapping_id: 映射记录ID
            chunk_count: 新的chunk_count值

        Returns:
            更新成功返回True，失败返回False
        """
        if not self.is_available():
            return False

        try:
            response = supabase_service.client.table(self.table_name).update({
                "chunk_count": chunk_count
            }).eq("id", mapping_id).execute()

            if response.data:
                logger.info(f"映射记录chunk_count更新成功: mapping_id={mapping_id}, chunk_count={chunk_count}")
                return True
            return False

        except Exception as e:
            logger.error(f"更新chunk_count失败: {e}")
            return False

    async def delete_mapping(
        self,
        mapping_id: Optional[str] = None,
        local_file_id: Optional[str] = None,
        external_document_id: Optional[str] = None
    ) -> bool:
        """
        删除映射记录

        Args:
            mapping_id: 映射记录ID（优先使用）
            local_file_id: 本地文件ID
            external_document_id: 外部文档ID

        Returns:
            删除成功返回True，失败返回False
        """
        if not self.is_available():
            return False

        try:
            query = supabase_service.client.table(self.table_name).delete()

            if mapping_id:
                query = query.eq("id", mapping_id)
            elif local_file_id:
                query = query.eq("local_file_id", local_file_id)
            elif external_document_id:
                query = query.eq("external_document_id", external_document_id)
            else:
                logger.error("删除映射记录失败：必须提供mapping_id、local_file_id或external_document_id之一")
                return False

            response = query.execute()

            logger.info(f"映射记录删除成功: mapping_id={mapping_id}, local_file_id={local_file_id}, external_document_id={external_document_id}")
            return True

        except Exception as e:
            logger.error(f"删除映射记录失败: {e}")
            return False

    async def delete_mappings_by_file(
        self,
        local_file_id: str
    ) -> bool:
        """
        删除文件的所有映射记录

        Args:
            local_file_id: 本地文件ID

        Returns:
            删除成功返回True，失败返回False
        """
        return await self.delete_mapping(local_file_id=local_file_id)

    async def get_collection_stats(
        self,
        collection_name: str
    ) -> Dict[str, Any]:
        """
        获取知识库的统计信息

        Args:
            collection_name: 知识库名称

        Returns:
            统计信息字典，包含document_count等
        """
        if not self.is_available():
            return {
                "document_count": 0,
                "total_chunks": 0
            }

        try:
            response = supabase_service.client.table(self.table_name).select(
                "chunk_count"
            ).eq("external_collection_name", collection_name).execute()

            mappings = response.data if response.data else []
            document_count = len(mappings)
            total_chunks = sum(m.get("chunk_count", 0) for m in mappings)

            return {
                "document_count": document_count,
                "total_chunks": total_chunks,
                "mappings": mappings
            }

        except Exception as e:
            logger.error(f"获取知识库统计信息失败: {e}")
            return {
                "document_count": 0,
                "total_chunks": 0
            }


# 全局映射服务实例
rag_mapping_service = RAGMappingService()

