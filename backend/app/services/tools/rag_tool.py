#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG查询工具
封装外部RAG服务，提供文档检索和问答功能
"""

from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from loguru import logger

# 导入现有的RAG客户端
from ...services.rag_client import rag_client
from ...services.supabase_file_service import supabase_file_service

@tool
async def rag_query_tool(
    query: str,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    is_admin: bool = False,
    top_k: int = 5,
    similarity_threshold: float = 0.7
) -> Dict[str, Any]:
    """
    使用外部RAG服务进行文档检索和问答

    Args:
        query: 查询问题
        project_id: 项目ID
        user_id: 用户ID（权限控制）
        is_admin: 是否管理员
        top_k: 返回结果数量
        similarity_threshold: 相似度阈值

    Returns:
        RAG查询结果包含答案和来源
    """
    try:
        if not query.strip():
            logger.warning("RAG查询为空")
            return {
                'answer': '请提供有效的查询问题。',
                'sources': [],
                'error': '查询为空'
            }

        # 检查外部RAG服务可用性
        if not rag_client.is_available():
            logger.warning("外部RAG服务不可用")
            return {
                'answer': 'RAG服务暂时不可用，请稍后重试。',
                'sources': [],
                'error': 'RAG服务不可用'
            }

        # 确定collection名称
        collection_name = f"project_{project_id}" if project_id else rag_client.config.collection_name

        logger.info(f"🔍 开始RAG查询: '{query[:50]}...', collection: {collection_name}")

        # 调用外部RAG服务
        rag_result = await rag_client.query(
            query_text=query,
            collection_name=collection_name,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

        # 权限过滤
        filtered_sources = []
        if user_id and rag_result.sources:
            logger.info(f"🔒 开始权限过滤，用户ID: {user_id}")
            filtered_count = 0

            for source in rag_result.sources:
                file_id = source.get("file_id") or source.get("document_id")
                if file_id:
                    if await supabase_file_service.user_can_access_file(file_id, user_id, is_admin):
                        filtered_sources.append(source)
                    else:
                        filtered_count += 1
                        logger.debug(f"🚫 文件无权限: {file_id}")
                else:
                    # 如果没有file_id，保留source（可能是通用知识）
                    filtered_sources.append(source)

            if filtered_count > 0:
                logger.info(f"🔒 权限过滤完成，过滤掉 {filtered_count} 个无权限文件")
        else:
            filtered_sources = rag_result.sources or []

        # 构建返回结果
        result = {
            'answer': rag_result.answer,
            'sources': filtered_sources,
            'processing_time': getattr(rag_result, 'processing_time', 0),
            'collection_used': collection_name,
            'total_sources': len(rag_result.sources) if rag_result.sources else 0,
            'filtered_sources': len(filtered_sources)
        }

        logger.info(f"✅ RAG查询完成: 返回 {len(filtered_sources)} 个来源")
        return result

    except Exception as e:
        logger.error(f"RAG查询失败: {e}")
        import traceback
        logger.error(f"完整堆栈: {traceback.format_exc()}")

        return {
            'answer': f'RAG查询失败: {str(e)}',
            'sources': [],
            'error': str(e),
            'processing_time': 0
        }

@tool
async def document_search_tool(
    query: str,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    is_admin: bool = False,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    搜索相关文档片段（不生成答案，只返回文档片段）

    Args:
        query: 搜索查询
        project_id: 项目ID
        user_id: 用户ID
        is_admin: 是否管理员
        limit: 返回结果数量限制

    Returns:
        文档片段列表
    """
    try:
        # 调用RAG工具，但只返回文档部分
        rag_result = await rag_query_tool(
            query=query,
            project_id=project_id,
            user_id=user_id,
            is_admin=is_admin,
            top_k=limit,
            similarity_threshold=0.5  # 搜索时使用更低的阈值
        )

        # 返回格式化的文档片段
        documents = []
        for source in rag_result.get('sources', []):
            documents.append({
                'content': source.get('content', ''),
                'file_id': source.get('file_id', ''),
                'file_name': source.get('file_name', 'Unknown'),
                'similarity': source.get('score', source.get('similarity', 0.0)),
                'metadata': source.get('metadata', {})
            })

        return documents

    except Exception as e:
        logger.error(f"文档搜索失败: {e}")
        return []