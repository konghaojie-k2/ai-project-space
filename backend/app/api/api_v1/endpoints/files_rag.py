#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RAG集成文件管理API端点
基于外部Supabase RAG服务的文件管理
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from pydantic import BaseModel
from loguru import logger

from app.services.rag_client import rag_client, RAGUploadResponse, RAGListResponse
from app.services.rag_mapping_service import rag_mapping_service
from app.dependencies.auth import get_current_user
from app.schemas.file import FileResponse
from app.schemas.auth import MessageResponse

router = APIRouter()


class RAGFileResponse(BaseModel):
    """RAG文件响应模型"""
    success: bool
    document_id: Optional[str] = None
    filename: str
    chunk_count: int = 0
    message: str
    processing_time: float = 0.0


@router.post("/upload-rag", response_model=RAGFileResponse, summary="上传文件到RAG知识库")
async def upload_file_to_rag(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    local_file_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """
    上传文件到外部RAG知识库并创建映射记录

    - **file**: 上传的文件
    - **collection_name**: 知识库名称（可选，默认使用配置的值）
    - **project_id**: 项目ID（用于构建collection名称）
    - **local_file_id**: 本地文件ID（如果文件已存在于files表中）
    - **description**: 文件描述
    - **tags**: 文件标签
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用，请检查服务配置"
            )

        # 构建知识库名称
        if project_id:
            kb_name = f"project_{project_id}"
        else:
            kb_name = collection_name or rag_client.config.collection_name

        # 读取文件内容
        file_content = await file.read()
        filename = file.filename

        logger.info(f"开始上传文件到RAG知识库: {filename}, 知识库: {kb_name}")

        # 构建元数据
        metadata = {
            "uploaded_by": current_user.get("username", "unknown"),
            "user_id": current_user.get("id"),
            "upload_time": str(current_user.get("created_at", "")),
            "description": description,
            "tags": tags.split(',') if tags else [],
            "content_type": file.content_type,
            "file_size": len(file_content)
        }

        # 如果有项目ID，添加到元数据
        if project_id:
            metadata["project_id"] = project_id

        # 上传到RAG服务
        result = await rag_client.upload_file(
            file_content=file_content,
            filename=filename,
            collection_name=kb_name,
            metadata=metadata
        )

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"文件上传到RAG知识库失败: {result.message}"
            )

        logger.info(f"文件成功上传到RAG知识库: {filename}, 文档ID: {result.document_id}")

        # 创建映射记录（如果提供了local_file_id）
        mapping_id = None
        if local_file_id and result.document_id:
            try:
                mapping = await rag_mapping_service.create_mapping(
                    local_file_id=local_file_id,
                    external_document_id=result.document_id,
                    external_collection_name=kb_name,
                    project_id=project_id,
                    chunk_count=result.chunk_count
                )
                if mapping:
                    mapping_id = mapping.get("id")
                    logger.info(f"映射记录创建成功: mapping_id={mapping_id}")
                else:
                    logger.warning(f"映射记录创建失败，但文件已上传到RAG: document_id={result.document_id}")
            except Exception as mapping_error:
                logger.error(f"创建映射记录时发生错误: {mapping_error}")
                # 映射失败不影响上传成功，只记录错误

        return RAGFileResponse(
            success=result.success,
            document_id=result.document_id,
            filename=filename,
            chunk_count=result.chunk_count,
            message=result.message,
            processing_time=result.processing_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG文件上传异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传过程中发生错误: {str(e)}"
        )


@router.get("/rag/documents", response_model=List[dict], summary="获取RAG知识库文档列表")
async def list_rag_documents(
    collection_name: Optional[str] = Query(None, description="知识库名称"),
    project_id: Optional[str] = Query(None, description="项目ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取RAG知识库中的文档列表

    - **collection_name**: 知识库名称
    - **project_id**: 项目ID（用于构建collection名称）
    - **limit**: 返回数量限制
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        # 构建知识库名称
        if project_id:
            kb_name = f"project_{project_id}"
        else:
            kb_name = collection_name or rag_client.config.collection_name

        # 获取文档列表
        result = await rag_client.list_documents(
            collection_name=kb_name,
            limit=limit
        )

        logger.info(f"获取RAG文档列表成功，知识库: {kb_name}, 文档数量: {result.total_count}")

        return result.documents

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取RAG文档列表异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文档列表失败: {str(e)}"
        )


@router.delete("/rag/documents/{document_id}", response_model=MessageResponse, summary="删除RAG知识库文档")
async def delete_rag_document(
    document_id: str,
    collection_name: Optional[str] = Query(None, description="知识库名称"),
    project_id: Optional[str] = Query(None, description="项目ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    从RAG知识库中删除文档并清理映射记录

    - **document_id**: 文档ID
    - **collection_name**: 知识库名称
    - **project_id**: 项目ID（用于构建collection名称）
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        # 构建知识库名称
        if project_id:
            kb_name = f"project_{project_id}"
        else:
            kb_name = collection_name or rag_client.config.collection_name

        # 删除外部RAG文档
        result = await rag_client.delete_document(
            document_id=document_id,
            collection_name=kb_name
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除文档失败: {result.get('message', '未知错误')}"
            )

        logger.info(f"RAG文档删除成功: {document_id}, 知识库: {kb_name}")

        # 删除映射记录
        try:
            await rag_mapping_service.delete_mapping(external_document_id=document_id)
            logger.info(f"映射记录删除成功: external_document_id={document_id}")
        except Exception as mapping_error:
            logger.warning(f"删除映射记录时发生错误（文档已从RAG删除）: {mapping_error}")
            # 映射删除失败不影响文档删除成功

        return MessageResponse(
            message=f"文档 {document_id} 已成功删除"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除RAG文档异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除文档失败: {str(e)}"
        )


@router.get("/rag/stats", summary="获取RAG知识库统计信息")
async def get_rag_stats(
    collection_name: Optional[str] = Query(None, description="知识库名称"),
    project_id: Optional[str] = Query(None, description="项目ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取RAG知识库统计信息

    - **collection_name**: 知识库名称
    - **project_id**: 项目ID（用于构建collection名称）
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        # 构建知识库名称
        if project_id:
            kb_name = f"project_{project_id}"
        else:
            kb_name = collection_name

        # 获取统计信息
        result = await rag_client.get_collection_stats(collection_name=kb_name)

        logger.info(f"获取RAG统计信息成功，知识库: {kb_name}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取RAG统计信息异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.delete("/rag/clear", response_model=MessageResponse, summary="清空RAG知识库")
async def clear_rag_knowledge_base(
    collection_name: Optional[str] = Query(None, description="知识库名称"),
    project_id: Optional[str] = Query(None, description="项目ID"),
    confirm: bool = Query(False, description="确认操作"),
    current_user: dict = Depends(get_current_user)
):
    """
    清空RAG知识库中的所有文档

    - **collection_name**: 知识库名称
    - **project_id**: 项目ID（用于构建collection名称）
    - **confirm**: 确认操作，必须设置为true才能执行清空
    """
    try:
        # 安全检查，需要明确确认
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请设置confirm=true以确认清空知识库操作"
            )

        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        # 构建知识库名称
        if project_id:
            kb_name = f"project_{project_id}"
        else:
            kb_name = collection_name or rag_client.config.collection_name

        # 检查当前用户权限（可以添加额外的权限检查）
        user_role = current_user.get("role", "viewer")
        if user_role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员或经理可以清空知识库"
            )

        # 清空知识库
        result = await rag_client.clear_knowledge_base(collection_name=kb_name)

        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"清空知识库失败: {result.get('message', '未知错误')}"
            )

        logger.info(f"RAG知识库清空成功: {kb_name}")

        return MessageResponse(
            message=f"知识库 {kb_name} 已成功清空"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空RAG知识库异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空知识库失败: {str(e)}"
        )


@router.delete("/rag/delete-collection", response_model=MessageResponse, summary="删除RAG知识库")
async def delete_rag_knowledge_base(
    collection_name: Optional[str] = Query(None, description="知识库名称"),
    project_id: Optional[str] = Query(None, description="项目ID"),
    confirm: bool = Query(False, description="确认操作"),
    current_user: dict = Depends(get_current_user)
):
    """
    删除整个RAG知识库（包括所有文档和元数据）

    - **collection_name**: 知识库名称
    - **project_id**: 项目ID（用于构建collection名称）
    - **confirm**: 确认操作，必须设置为true才能执行删除
    """
    try:
        # 安全检查，需要明确确认
        if not confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请设置confirm=true以确认删除知识库操作"
            )

        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        # 构建知识库名称
        if project_id:
            kb_name = f"project_{project_id}"
        else:
            kb_name = collection_name or rag_client.config.collection_name

        # 检查当前用户权限
        user_role = current_user.get("role", "viewer")
        if user_role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以删除知识库"
            )

        # 删除知识库
        result = await rag_client.delete_knowledge_base(collection_name=kb_name)

        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"删除知识库失败: {result.get('message', '未知错误')}"
            )

        logger.info(f"RAG知识库删除成功: {kb_name}")

        return MessageResponse(
            message=f"知识库 {kb_name} 已成功删除"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除RAG知识库异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除知识库失败: {str(e)}"
        )


@router.post("/rag/knowledge-bases", summary="创建RAG知识库")
async def create_knowledge_base(
    name: str = Form(...),
    description: str = Form(""),
    current_user: dict = Depends(get_current_user)
):
    """
    创建新的RAG知识库

    - **name**: 知识库名称（必需）
    - **description**: 知识库描述（可选）
    """
    try:
        # 检查RAG服务可用性
        if not rag_client.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="RAG服务不可用"
            )

        # 创建知识库
        result = await rag_client.create_knowledge_base(
            name=name,
            description=description
        )

        if not result.get("success", False):
            error_message = result.get("message", "创建知识库失败")
            error_type = result.get("error", "")
            
            # 处理重复名称错误
            if error_type == "duplicate_name":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_message
                )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message
            )

        logger.info(f"知识库创建成功: {name}")

        return {
            "success": True,
            "message": result.get("message", f"知识库 '{name}' 创建成功"),
            "data": result.get("data", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建知识库异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建知识库失败: {str(e)}"
        )


@router.get("/rag/health", summary="检查RAG服务健康状态")
async def check_rag_health():
    """
    检查RAG服务的健康状态
    """
    try:
        result = await rag_client.health_check()
        return {
            "status": "healthy" if result.get("status") == "healthy" else "unhealthy",
            "rag_service": result,
            "client_configured": rag_client.is_available()
        }
    except Exception as e:
        logger.error(f"RAG健康检查异常: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "client_configured": rag_client.is_available()
        }