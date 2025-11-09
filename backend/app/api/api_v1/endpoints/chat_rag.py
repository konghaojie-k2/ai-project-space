#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG集成聊天API端点
基于外部Supabase RAG服务的智能问答
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

from app.services.rag_client import rag_client, RAGQueryResponse
from app.dependencies.auth import get_current_user

router = APIRouter()


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: Optional[str] = None


class ChatRAGRequest(BaseModel):
    """RAG聊天请求模型"""
    messages: List[ChatMessage]
    collection_name: Optional[str] = None
    project_id: Optional[str] = None
    top_k: int = 5
    similarity_threshold: float = 0.7
    stream: bool = False


class ChatRAGResponse(BaseModel):
    """RAG聊天响应模型"""
    answer: str
    sources: List[Dict[str, Any]] = []
    query: str
    processing_time: float
    collection_name: str
    metadata: Dict[str, Any] = {}


@router.post("/query", response_model=ChatRAGResponse, summary="RAG智能问答")
async def rag_query(
    request: ChatRAGRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    使用RAG服务进行智能问答

    - **messages**: 聊天消息列表
    - **collection_name**: 知识库名称（可选）
    - **project_id**: 项目ID（用于构建collection名称）
    - **top_k**: 返回相关文档数量
    - **similarity_threshold**: 相似度阈值
    - **stream**: 是否流式响应
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用，请检查服务配置"
            )

        # 验证消息列表
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息列表不能为空"
            )

        # 获取最后一条用户消息作为查询
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要一条用户消息"
            )

        last_user_message = user_messages[-1]
        query_text = last_user_message.content

        # 构建知识库名称
        if request.project_id:
            collection_name = f"project_{request.project_id}"
        else:
            collection_name = request.collection_name or rag_client.config.collection_name

        logger.info(f"开始RAG查询，用户: {current_user.get('username')}, 查询: {query_text[:50]}..., 知识库: {collection_name}")

        # 构建完整的查询上下文（包含历史对话）
        if len(user_messages) > 1:
            # 包含历史对话上下文
            context_messages = []
            for msg in request.messages[-5:]:  # 只取最近5条消息
                context_messages.append(f"{msg.role}: {msg.content}")

            full_query = "对话历史:\n" + "\n".join(context_messages) + f"\n\n当前问题: {query_text}"
        else:
            full_query = query_text

        # 调用RAG服务查询
        result = await rag_client.query(
            query_text=full_query,
            collection_name=collection_name,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold
        )

        logger.info(f"RAG查询完成，耗时: {result.processing_time:.2f}秒，找到 {len(result.sources)} 个相关文档")

        # 构建响应
        response = ChatRAGResponse(
            answer=result.answer,
            sources=result.sources,
            query=query_text,
            processing_time=result.processing_time,
            collection_name=collection_name,
            metadata=result.metadata
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG查询异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询过程中发生错误: {str(e)}"
        )


@router.post("/query/stream", summary="RAG流式智能问答")
async def rag_query_stream(
    request: ChatRAGRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    使用RAG服务进行流式智能问答

    - **messages**: 聊天消息列表
    - **collection_name**: 知识库名称（可选）
    - **project_id**: 项目ID（用于构建collection名称）
    - **top_k**: 返回相关文档数量
    - **similarity_threshold**: 相似度阈值
    - **stream**: 是否流式响应（此接口始终为True）
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        # 验证消息列表
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息列表不能为空"
            )

        # 获取最后一条用户消息作为查询
        user_messages = [msg for msg in request.messages if msg.role == "user"]
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要一条用户消息"
            )

        last_user_message = user_messages[-1]
        query_text = last_user_message.content

        # 构建知识库名称
        if request.project_id:
            collection_name = f"project_{request.project_id}"
        else:
            collection_name = request.collection_name or rag_client.config.collection_name

        logger.info(f"开始RAG流式查询，用户: {current_user.get('username')}, 查询: {query_text[:50]}..., 知识库: {collection_name}")

        # 构建完整的查询上下文（包含历史对话）
        if len(user_messages) > 1:
            context_messages = []
            for msg in request.messages[-5:]:
                context_messages.append(f"{msg.role}: {msg.content}")

            full_query = "对话历史:\n" + "\n".join(context_messages) + f"\n\n当前问题: {query_text}"
        else:
            full_query = query_text

        async def generate_stream():
            """生成流式响应"""
            try:
                # 首先发送一个初始响应
                yield f"data: {json.dumps({'type': 'start', 'message': '正在查询知识库...'}, ensure_ascii=False)}\n\n"

                # 流式调用RAG服务
                async for chunk in rag_client.stream_query(
                    query_text=full_query,
                    collection_name=collection_name,
                    top_k=request.top_k,
                    similarity_threshold=request.similarity_threshold
                ):
                    if chunk.strip():
                        # 发送内容块
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"

                # 发送结束标记
                yield f"data: {json.dumps({'type': 'end'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"流式响应生成异常: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG流式查询异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式查询过程中发生错误: {str(e)}"
        )


@router.post("/simple-query", response_model=dict, summary="简单RAG问答")
async def simple_rag_query(
    query: str,
    collection_name: Optional[str] = None,
    project_id: Optional[str] = None,
    top_k: int = 5,
    similarity_threshold: float = 0.7,
    current_user: dict = Depends(get_current_user)
):
    """
    简单的RAG问答接口（不需要完整消息历史）

    - **query**: 查询文本
    - **collection_name**: 知识库名称（可选）
    - **project_id**: 项目ID（用于构建collection名称）
    - **top_k**: 返回相关文档数量
    - **similarity_threshold**: 相似度阈值
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        if not query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="查询文本不能为空"
            )

        # 构建知识库名称
        if project_id:
            kb_name = f"project_{project_id}"
        else:
            kb_name = collection_name or rag_client.config.collection_name

        logger.info(f"简单RAG查询，用户: {current_user.get('username')}, 查询: {query[:50]}..., 知识库: {kb_name}")

        # 调用RAG服务查询
        result = await rag_client.query(
            query_text=query,
            collection_name=kb_name,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )

        logger.info(f"简单RAG查询完成，耗时: {result.processing_time:.2f}秒")

        return {
            "query": query,
            "answer": result.answer,
            "sources": result.sources,
            "processing_time": result.processing_time,
            "collection_name": kb_name,
            "metadata": result.metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"简单RAG查询异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询过程中发生错误: {str(e)}"
        )