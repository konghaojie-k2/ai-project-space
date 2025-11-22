#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG服务客户端
连接到独立的Supabase RAG应用API
"""

import os
import json
import httpx
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel
from loguru import logger

from app.core.config import settings


class RAGConfig(BaseModel):
    """RAG配置模型"""
    api_endpoint: str
    api_key: Optional[str] = None
    collection_name: str = "default"
    timeout: int = 30
    max_retries: int = 3


class RAGDocument(BaseModel):
    """RAG文档模型"""
    content: str
    metadata: Dict[str, Any] = {}


class RAGQueryRequest(BaseModel):
    """RAG查询请求模型"""
    query: str
    collection_name: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.7


class RAGQueryResponse(BaseModel):
    """RAG查询响应模型"""
    answer: str
    sources: List[Dict[str, Any]] = []
    query: str
    processing_time: float
    metadata: Dict[str, Any] = {}


class RAGUploadResponse(BaseModel):
    """RAG上传响应模型"""
    success: bool
    document_id: Optional[str] = None
    message: str
    chunk_count: int = 0
    processing_time: float = 0.0


class RAGListResponse(BaseModel):
    """RAG文档列表响应模型"""
    documents: List[Dict[str, Any]]
    total_count: int
    collection_name: str


class RAGServiceClient:
    """RAG服务客户端"""

    def __init__(self, config: RAGConfig):
        """
        初始化RAG服务客户端

        Args:
            config: RAG服务配置
        """
        self.config = config
        self.base_url = config.api_endpoint.rstrip('/')
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Project-Management-RAG-Client/1.0'
        }

        if config.api_key:
            self.headers['Authorization'] = f'Bearer {config.api_key}'

        logger.info(f"RAG服务客户端初始化完成，端点: {self.base_url}")

    async def health_check(self) -> Dict[str, Any]:
        """
        检查RAG服务健康状态

        Returns:
            健康状态信息
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"RAG服务健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def upload_document(
        self,
        content: str,
        filename: str,
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RAGUploadResponse:
        """
        上传文档到RAG服务

        Args:
            content: 文档内容
            filename: 文件名
            collection_name: 知识库名称
            metadata: 文档元数据

        Returns:
            上传响应结果
        """
        try:
            payload = {
                "content": content,
                "filename": filename,
                "collection_name": collection_name or self.config.collection_name,
                "metadata": metadata or {}
            }

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/documents/upload",
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()
                return RAGUploadResponse(**result)

        except httpx.HTTPStatusError as e:
            logger.error(f"RAG文档上传HTTP错误: {e.response.status_code} - {e.response.text}")
            return RAGUploadResponse(
                success=False,
                message=f"HTTP错误: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"RAG文档上传失败: {e}")
            return RAGUploadResponse(
                success=False,
                message=f"上传失败: {str(e)}"
            )

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        collection_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RAGUploadResponse:
        """
        上传文件到RAG服务（用于分块处理，用于RAG查询）

        Args:
            file_content: 文件二进制内容
            filename: 文件名
            collection_name: 知识库名称（如 project_123）
            metadata: 文件元数据

        Returns:
            上传响应结果
        """
        try:
            # 提取知识库名称（kb_name）
            # collection_name格式可能是 "project_123" 或 "default"
            # 如果明确传递了collection_name（即使是空字符串），优先使用传递的值
            # 只有在collection_name为None时才使用默认值
            if collection_name is None:
                kb_name = self.config.collection_name
                logger.warning(f"⚠️ 未指定知识库名称，使用默认知识库: {kb_name}")
            else:
                kb_name = collection_name
                logger.info(f"✅ 使用指定知识库: {kb_name}")
            
            # 使用multipart/form-data上传文件
            # 注意：虽然URL路径中包含了知识库名称，但为了确保RAG服务端正确使用，
            # 我们也在metadata中显式传递知识库名称
            files = {
                'file': (filename, file_content)
            }
            
            # 在metadata中显式添加知识库名称，确保RAG服务端能正确识别
            if metadata is None:
                metadata = {}
            metadata['collection_name'] = kb_name
            metadata['knowledge_base'] = kb_name

            # 不设置Content-Type，让httpx自动设置multipart boundary
            headers = {k: v for k, v in self.headers.items() if k != 'Content-Type'}

            async with httpx.AsyncClient(timeout=self.config.timeout * 2) as client:
                # 使用正确的端点：/api/v1/knowledge-bases/{kb_name}/chunks/upload
                upload_url = f"{self.base_url}/api/v1/knowledge-bases/{kb_name}/chunks/upload"
                logger.info(f"📤 RAG上传请求URL: {upload_url}")
                logger.info(f"📤 知识库名称: {kb_name}, 文件名: {filename}")
                logger.info(f"📤 元数据中包含知识库: {metadata.get('collection_name')}, {metadata.get('knowledge_base')}")
                
                # 注意：httpx的files参数会自动处理multipart/form-data
                # 如果需要传递metadata，可能需要通过data参数传递，但RAG API可能不支持
                # 目前先通过URL路径传递，如果RAG服务端有问题，需要修复服务端代码
                response = await client.post(
                    upload_url,
                    files=files,
                    headers=headers
                )
                response.raise_for_status()
                
                logger.info(f"📥 RAG上传响应状态: {response.status_code}")

                result = response.json()
                logger.info(f"📥 RAG上传响应内容: {result}")
                
                # API返回DocumentUploadResponse格式：{task_id, message, filename}
                # 需要轮询任务状态获取最终结果
                task_id = result.get('task_id')
                if not task_id:
                    logger.error(f"❌ 未获取到任务ID，响应: {result}")
                    return RAGUploadResponse(
                        success=False,
                        message="未获取到任务ID"
                    )
                
                logger.info(f"✅ RAG文件上传任务已创建: {filename}, task_id: {task_id}, 知识库: {kb_name}")
                
                # 轮询任务状态直到完成
                max_wait_time = self.config.timeout * 2  # 最大等待时间
                poll_interval = 1  # 轮询间隔（秒）
                elapsed_time = 0
                
                while elapsed_time < max_wait_time:
                    await asyncio.sleep(poll_interval)
                    elapsed_time += poll_interval
                    
                    # 查询任务状态
                    status_response = await client.get(
                        f"{self.base_url}/api/v1/tasks/{task_id}",
                        headers=self.headers
                    )
                    
                    if status_response.status_code == 404:
                        # 任务不存在，可能已完成并被清理
                        logger.warning(f"任务 {task_id} 不存在，可能已完成")
                        return RAGUploadResponse(
                            success=True,
                            document_id=task_id,  # 使用task_id作为document_id
                            message="任务已完成",
                            chunk_count=0,
                            processing_time=elapsed_time
                        )
                    
                    status_response.raise_for_status()
                    status_data = status_response.json()
                    
                    status = status_data.get('status')
                    progress = status_data.get('progress', 0)
                    
                    logger.debug(f"任务 {task_id} 状态: {status}, 进度: {progress}")
                    
                    if status == 'completed':
                        # 任务完成，获取结果
                        result_data = status_data.get('result', {})
                        chunk_count = result_data.get('chunk_count', 0)
                        
                        return RAGUploadResponse(
                            success=True,
                            document_id=task_id,  # 使用task_id作为document_id
                            message=status_data.get('message', '文件上传成功'),
                            chunk_count=chunk_count,
                            processing_time=elapsed_time
                        )
                    elif status == 'failed':
                        # 任务失败
                        error_msg = status_data.get('error', '未知错误')
                        logger.error(f"RAG文件上传任务失败: {error_msg}")
                        return RAGUploadResponse(
                            success=False,
                            message=f"任务失败: {error_msg}"
                        )
                    # 继续轮询（pending或processing状态）

                # 超时
                logger.warning(f"RAG文件上传任务超时: {task_id}")
                return RAGUploadResponse(
                    success=False,
                    message=f"任务超时，task_id: {task_id}"
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"RAG文件上传HTTP错误: {e.response.status_code} - {e.response.text}")
            return RAGUploadResponse(
                success=False,
                message=f"HTTP错误: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"RAG文件上传失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return RAGUploadResponse(
                success=False,
                message=f"上传失败: {str(e)}"
            )

    async def query(
        self,
        query_text: str,
        collection_name: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> RAGQueryResponse:
        """
        查询RAG知识库

        Args:
            query_text: 查询文本
            collection_name: 知识库名称
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值

        Returns:
            查询响应结果
        """
        try:
            kb_name = collection_name or self.config.collection_name
            
            # 根据RAG API的实际接口格式构建请求
            # RAG API使用: question, knowledge_base, top_k, threshold
            payload = {
                "question": query_text,
                "knowledge_base": kb_name,
                "top_k": top_k,
                "threshold": similarity_threshold
            }

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                # 使用正确的RAG API端点：/api/v1/query
                query_url = f"{self.base_url}/api/v1/query"
                logger.info(f"🔍 RAG查询请求URL: {query_url}")
                logger.info(f"🔍 查询文本: {query_text[:50]}..., 知识库: {kb_name}")
                logger.info(f"🔍 请求参数: {payload}")
                
                response = await client.post(
                    query_url,
                    json=payload,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"✅ RAG查询成功，答案长度: {len(result.get('answer', ''))}")
                
                # 转换响应格式以匹配RAGQueryResponse
                return RAGQueryResponse(
                    answer=result.get('answer', ''),
                    sources=result.get('sources', []),
                    query=query_text,
                    processing_time=result.get('processing_time', 0.0),
                    metadata=result.get('metadata', {})
                )

        except httpx.HTTPStatusError as e:
            logger.error(f"RAG查询HTTP错误: {e.response.status_code} - {e.response.text}")
            return RAGQueryResponse(
                answer=f"查询失败: HTTP错误 {e.response.status_code}",
                query=query_text,
                processing_time=0.0
            )
        except Exception as e:
            logger.error(f"RAG查询失败: {e}")
            return RAGQueryResponse(
                answer=f"查询失败: {str(e)}",
                query=query_text,
                processing_time=0.0
            )

    async def list_documents(
        self,
        collection_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> RAGListResponse:
        """
        获取文档列表

        Args:
            collection_name: 知识库名称
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            文档列表响应
        """
        try:
            params = {
                "collection_name": collection_name or self.config.collection_name,
                "limit": limit,
                "offset": offset
            }

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/documents",
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()
                return RAGListResponse(**result)

        except httpx.HTTPStatusError as e:
            logger.error(f"RAG文档列表HTTP错误: {e.response.status_code} - {e.response.text}")
            return RAGListResponse(
                documents=[],
                total_count=0,
                collection_name=collection_name or self.config.collection_name
            )
        except Exception as e:
            logger.error(f"获取RAG文档列表失败: {e}")
            return RAGListResponse(
                documents=[],
                total_count=0,
                collection_name=collection_name or self.config.collection_name
            )

    async def delete_document(
        self,
        document_id: str,
        collection_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        删除文档及其所有关联的chunks

        Args:
            document_id: 文档ID（RAG服务中的file_id或document_id）
            collection_name: 知识库名称（可选，用于指定知识库）

        Returns:
            删除结果，包含success和message字段
        """
        try:
            kb_name = collection_name or self.config.collection_name
            logger.info(f"🗑️ 准备删除RAG文档: {document_id}, 知识库: {kb_name}")
            
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                # 根据RAG API文档，删除文件及其所有chunks的端点是：
                # DELETE /api/v1/files/{file_id}
                # 这个端点会删除原始文件及其关联的所有分块
                delete_url = f"{self.base_url}/api/v1/files/{document_id}"
                logger.info(f"🗑️ RAG删除请求URL: {delete_url}")
                
                response = await client.delete(
                    delete_url,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"✅ RAG文档删除成功: {document_id}, 响应: {result}")
                
                # 确保返回格式统一
                if isinstance(result, dict):
                    if 'success' not in result:
                        result['success'] = True
                    return result
                else:
                    return {
                        "success": True,
                        "message": result if isinstance(result, str) else "文档删除成功"
                    }

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"❌ RAG文档删除HTTP错误: {e.response.status_code} - {error_text}")
            
            # 如果是404，可能文档已经不存在，也算成功
            if e.response.status_code == 404:
                logger.warning(f"⚠️ RAG文档不存在（可能已删除）: {document_id}")
                return {
                    "success": True,
                    "message": "文档不存在（可能已删除）"
                }
            
            return {
                "success": False,
                "message": f"HTTP错误: {e.response.status_code} - {error_text}"
            }
        except Exception as e:
            logger.error(f"❌ RAG文档删除失败: {e}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }

    async def get_collection_stats(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Args:
            collection_name: 知识库名称

        Returns:
            统计信息
        """
        try:
            params = {}
            if collection_name:
                params["collection_name"] = collection_name

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/collections/stats",
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()

                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"RAG统计信息HTTP错误: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"HTTP错误: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"获取RAG统计信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def stream_query(
        self,
        query_text: str,
        collection_name: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        流式查询RAG知识库

        Args:
            query_text: 查询文本
            collection_name: 知识库名称
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值

        Yields:
            流式响应内容
        """
        try:
            payload = {
                "query": query_text,
                "collection_name": collection_name or self.config.collection_name,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "stream": True
            }

            async with httpx.AsyncClient(timeout=self.config.timeout * 2) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/query/stream",
                    json=payload,
                    headers=self.headers
                ) as response:
                    response.raise_for_status()

                    async for chunk in response.aiter_text():
                        if chunk.strip():
                            yield chunk

        except httpx.HTTPStatusError as e:
            logger.error(f"RAG流式查询HTTP错误: {e.response.status_code} - {e.response.text}")
            yield f"查询失败: HTTP错误 {e.response.status_code}"
        except Exception as e:
            logger.error(f"RAG流式查询失败: {e}")
            yield f"查询失败: {str(e)}"

    async def clear_knowledge_base(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        清空知识库中的所有文档

        Args:
            collection_name: 知识库名称

        Returns:
            清空结果
        """
        try:
            params = {
                "collection_name": collection_name or self.config.collection_name,
                "confirm": True
            }

            async with httpx.AsyncClient(timeout=self.config.timeout * 3) as client:
                response = await client.delete(
                    f"{self.base_url}/collections/clear",
                    params=params,
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()
                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"清空知识库HTTP错误: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "message": f"HTTP错误: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"清空知识库失败: {e}")
            return {
                "success": False,
                "message": f"清空失败: {str(e)}"
            }

    async def create_knowledge_base(
        self,
        name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建新知识库

        Args:
            name: 知识库名称
            description: 知识库描述

        Returns:
            创建结果，包含知识库信息
        """
        try:
            # 使用multipart/form-data格式，因为外部API使用Form参数
            data = {
                "name": name,
                "description": description
            }

            # 不设置Content-Type，让httpx自动设置multipart boundary
            headers = {k: v for k, v in self.headers.items() if k != 'Content-Type'}

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/knowledge-bases",
                    data=data,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"知识库创建成功: {name}")
                return {
                    "success": True,
                    "message": result.get("message", f"知识库 '{name}' 创建成功"),
                    "data": result.get("data", {})
                }

        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.warning(f"创建知识库HTTP错误: {e.response.status_code} - {error_text}")
            
            # 处理知识库已存在的情况（这是正常情况，不算错误）
            if e.response.status_code == 400:
                try:
                    error_json = e.response.json()
                    error_detail = error_json.get('detail', '')
                    # 检查是否是"知识库名称已存在"的错误
                    if "已存在" in error_detail or "duplicate" in error_detail.lower() or "已存在" in error_text:
                        logger.info(f"知识库 '{name}' 已存在，这是正常情况")
                        return {
                            "success": True,  # 已存在也算成功
                            "message": f"知识库 '{name}' 已存在",
                            "data": {}
                        }
                except:
                    # 如果无法解析JSON，检查文本内容
                    if "已存在" in error_text or "duplicate" in error_text.lower():
                        logger.info(f"知识库 '{name}' 已存在（从错误文本判断）")
                        return {
                            "success": True,  # 已存在也算成功
                            "message": f"知识库 '{name}' 已存在",
                            "data": {}
                        }
            
            # 其他400错误或其他错误
            return {
                "success": False,
                "message": f"HTTP错误: {e.response.status_code}",
                "error": error_text
            }
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            return {
                "success": False,
                "message": f"创建失败: {str(e)}",
                "error": str(e)
            }

    async def delete_knowledge_base(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        删除整个知识库（包括所有文档和元数据）

        Args:
            collection_name: 知识库名称

        Returns:
            删除结果
        """
        try:
            kb_name = collection_name or self.config.collection_name

            async with httpx.AsyncClient(timeout=self.config.timeout * 3) as client:
                # 使用正确的端点：/api/v1/knowledge-bases/{kb_name}
                response = await client.delete(
                    f"{self.base_url}/api/v1/knowledge-bases/{kb_name}",
                    headers=self.headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"知识库删除成功: {kb_name}")
                return {
                    "success": True,
                    "message": result.get("message", f"知识库 '{kb_name}' 已删除"),
                    "data": result
                }

        except httpx.HTTPStatusError as e:
            logger.error(f"删除知识库HTTP错误: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "message": f"HTTP错误: {e.response.status_code}"
            }
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            return {
                "success": False,
                "message": f"删除失败: {str(e)}"
            }

    def is_available(self) -> bool:
        """
        检查RAG服务是否可用
        注意：这只是检查配置是否存在，不实际检查服务是否运行

        Returns:
            是否可用
        """
        # 检查配置是否存在
        if not settings.USE_RAG_SERVICE:
            return False
        
        if not self.config.api_endpoint:
            return False
        
        return True

    def get_config(self) -> RAGConfig:
        """
        获取当前配置

        Returns:
            RAG配置
        """
        return self.config


# 创建全局RAG服务客户端实例
def create_rag_client() -> RAGServiceClient:
    """
    创建RAG服务客户端实例

    Returns:
        RAG服务客户端
    """
    config = RAGConfig(
        api_endpoint=settings.RAG_API_ENDPOINT,
        api_key=settings.RAG_API_KEY,
        collection_name=settings.RAG_COLLECTION_NAME,
        timeout=settings.RAG_TIMEOUT,
        max_retries=settings.RAG_MAX_RETRIES
    )

    return RAGServiceClient(config)


# 全局RAG客户端实例
rag_client = create_rag_client()