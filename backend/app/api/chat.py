"""
AI聊天API路由 - 数据库持久化版本
提供聊天会话管理、消息发送、文档搜索等功能
使用SQLAlchemy进行数据持久化
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

from ..services.ai_service import ai_service
from ..services.supabase_client import supabase_service
from typing import Dict, Any
from ..models.chat import (
    ChatRequest, 
    ChatResponse, 
    MessageResponse, 
    ConversationCreate,
    ConversationResponse,
    StreamEvent,
    DocumentSearchRequest,
    DocumentSearchResponse,
    ProcessDocumentsRequest
)

router = APIRouter(tags=["chat"])

# 导入认证依赖
from ..dependencies.auth import get_current_user

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate, 
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """创建新会话（已迁移到 Supabase）"""
    try:
        # TODO: 使用 Supabase 创建会话
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        
        # 使用 Supabase 创建会话
        session_data = {
            'id': conversation_id,
            'title': request.title,
            'project_id': request.project_id,
            'user_id': str(current_user.get('id')),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        db_conversation = await supabase_service.create_chat_session(session_data)
        
        if not db_conversation:
            raise HTTPException(status_code=500, detail="创建会话失败")
        
        logger.info(f"创建新会话: {conversation_id}, 标题: {request.title}")
        
        return ConversationResponse(
            id=db_conversation.get('id'),
            title=db_conversation.get('title'),
            project_id=db_conversation.get('project_id'),
            project_name=None,
            last_message=None,
            message_count=0,
            created_at=db_conversation.get('created_at'),
            updated_at=db_conversation.get('updated_at')
        )
        
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail="创建会话失败")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取会话列表（已迁移到 Supabase）"""
    try:
        # 使用 Supabase 获取会话列表
        user_id = str(current_user.get('id'))
        conversations = await supabase_service.get_user_chat_sessions(user_id)
        
        result = []
        for conv in conversations:
            # 获取最后一条消息
            session_id = conv.get('id')
            messages = await supabase_service.get_chat_session_messages(session_id)
            last_message = messages[-1] if messages else None
            
            result.append(ConversationResponse(
                id=conv.get('id'),
                title=conv.get('title'),
                project_id=conv.get('project_id'),
                project_name=None,
                last_message=last_message.get('content', '')[:100] + "..." if last_message else None,
                message_count=len(messages),
                created_at=conv.get('created_at'),
                updated_at=conv.get('updated_at')
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str, 
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取会话详情（已迁移到 Supabase）"""
    try:
        conversation = await supabase_service.get_chat_session(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取最后一条消息和消息数量
        messages = await supabase_service.get_chat_session_messages(conversation_id)
        last_message = messages[-1] if messages else None
        
        return ConversationResponse(
            id=conversation.get('id'),
            title=conversation.get('title'),
            project_id=conversation.get('project_id'),
            project_name=None,
            last_message=last_message.get('content', '')[:100] + "..." if last_message else None,
            message_count=len(messages),
            created_at=conversation.get('created_at'),
            updated_at=conversation.get('updated_at')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话详情失败")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str, 
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """删除会话（已迁移到 Supabase）"""
    try:
        # 检查会话是否存在
        conversation = await supabase_service.get_chat_session(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 使用 Supabase 删除会话
        deleted = await supabase_service.delete_chat_session(conversation_id)
        
        if not deleted:
            raise HTTPException(status_code=500, detail="删除会话失败")
        
        logger.info(f"删除会话: {conversation_id}")
        
        return {"message": "会话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail="删除会话失败")

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str, 
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """获取会话消息（已迁移到 Supabase）"""
    try:
        # 验证会话存在
        conversation = await supabase_service.get_chat_session(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 使用 Supabase 获取消息，按时间顺序排序
        messages = await supabase_service.get_chat_session_messages(conversation_id)
        
        return [
            MessageResponse(
                id=msg.get('id'),
                role=msg.get('role'),
                content=msg.get('content'),
                timestamp=msg.get('created_at'),
                conversation_id=conversation_id,
                model=msg.get('metadata', {}).get("model") if msg.get('metadata') else None
            )
            for msg in messages
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息失败: {e}")
        raise HTTPException(status_code=500, detail="获取消息失败")

@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: str, 
    request: ChatRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """发送消息（非流式，已迁移到 Supabase）"""
    try:
        # 验证会话存在
        conversation = await supabase_service.get_chat_session(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息到 Supabase
        user_message_data = {
            'id': f"msg_{uuid.uuid4().hex[:8]}",
            'session_id': conversation_id,
            'role': 'user',
            'content': request.messages[-1]["content"],
            'created_at': datetime.utcnow().isoformat()
        }
        await supabase_service.create_chat_message(user_message_data)
        
        # 调用AI服务（带权限过滤）
        ai_response = await ai_service.chat_completion(
            messages=request.messages,
            project_context=request.project_id,
            model_name=request.model or "gpt-3.5-turbo",
            user_id=str(current_user.get('id')),
            is_admin=current_user.get('is_superuser', False)
        )
        
        # 保存AI回复到 Supabase
        ai_message_data = {
            'id': f"msg_{uuid.uuid4().hex[:8]}",
            'session_id': conversation_id,
            'role': 'assistant',
            'content': ai_response.content,
            'created_at': datetime.utcnow().isoformat(),
            'metadata': {"model": ai_response.model} if hasattr(ai_response, 'model') else {"model": "Claude-3.5"}
        }
        await supabase_service.create_chat_message(ai_message_data)
        
        # 更新会话信息
        await supabase_service.update_chat_session(conversation_id, {
            'updated_at': datetime.utcnow().isoformat()
        })
        
        logger.info(f"消息发送成功，会话: {conversation_id}")
        
        return ai_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送消息失败")

@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str, 
    request: ChatRequest, 
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """发送消息（流式响应，已迁移到 Supabase）"""
    try:
        # 验证会话存在
        conversation = await supabase_service.get_chat_session(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息到 Supabase
        user_message_data = {
            'id': f"msg_{uuid.uuid4().hex[:8]}",
            'session_id': conversation_id,
            'role': 'user',
            'content': request.messages[-1]["content"],
            'created_at': datetime.utcnow().isoformat()
        }
        await supabase_service.create_chat_message(user_message_data)
        
        # 生成AI消息ID
        ai_message_id = f"msg_{uuid.uuid4().hex[:8]}"
        ai_content = ""
        
        # 在异步生成器外部提取需要的值，避免数据库会话问题
        user_id = str(current_user.get('id'))
        is_admin = current_user.get('is_superuser', False)
        
        async def generate_stream():
            nonlocal ai_content
            
            try:
                # 发送开始事件
                start_event = {
                    "message_id": ai_message_id, 
                    "type": "start",
                    "timestamp": datetime.utcnow().isoformat(),
                    "conversation_id": conversation_id
                }
                yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"
                
                buffer = ""  # 用于缓冲不完整的chunks
                
                # 调用AI服务获取流式回复（带权限过滤）
                async for chunk in ai_service.chat_completion_stream(
                    messages=request.messages,
                    project_context=request.project_id,
                    model_name=request.model or "gpt-3.5-turbo",
                    user_id=user_id,
                    is_admin=is_admin
                ):
                    if not chunk:  # 跳过空chunks
                        continue
                        
                    buffer += chunk
                    ai_content += chunk
                    
                    # 检查是否是完整的词汇或句子边界
                    should_send = (
                        chunk.endswith(' ') or 
                        chunk.endswith('\n') or 
                        chunk.endswith('。') or 
                        chunk.endswith('！') or 
                        chunk.endswith('？') or
                        chunk.endswith('.') or
                        chunk.endswith('!') or
                        chunk.endswith('?') or
                        chunk.endswith('```') or
                        len(buffer) > 50  # 防止缓冲区过大
                    )
                    
                    if should_send:
                        # 发送缓冲的内容
                        content_event = {
                            "id": ai_message_id,
                            "role": "assistant", 
                            "content": buffer,
                            "type": "content",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        yield f"data: {json.dumps(content_event, ensure_ascii=False)}\n\n"
                        buffer = ""  # 清空缓冲区
                
                # 发送剩余缓冲内容
                if buffer:
                    content_event = {
                        "id": ai_message_id,
                        "role": "assistant", 
                        "content": buffer,
                        "type": "content",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    yield f"data: {json.dumps(content_event, ensure_ascii=False)}\n\n"
                
                # 获取真实的模型名称
                from app.services.volcengine_client import volcengine_client
                model_name = volcengine_client.llm_model
                
                # 保存完整的AI回复到 Supabase
                ai_message_data = {
                    'id': ai_message_id,
                    'session_id': conversation_id,
                    'role': 'assistant',
                    'content': ai_content,
                    'created_at': datetime.utcnow().isoformat(),
                    'metadata': {"model": model_name}
                }
                await supabase_service.create_chat_message(ai_message_data)
                
                # 更新会话信息
                await supabase_service.update_chat_session(conversation_id, {
                    'updated_at': datetime.utcnow().isoformat()
                })
                
                # 发送完成信号
                end_event = {
                    "message_id": ai_message_id,
                    "role": "assistant", 
                    "content": ai_content,
                    "type": "end",
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_tokens": len(ai_content.split()),  # 简单的token计数
                    "model": model_name  # 包含真实的模型名称
                }
                yield f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"
                
                # 发送完成标识
                yield f"data: [DONE]\n\n"
                
            except Exception as ai_error:
                logger.error(f"AI流式服务调用失败: {ai_error}")
                # 发送错误信息
                error_event = {
                    "id": ai_message_id,
                    "role": "assistant", 
                    "content": f"抱歉，AI服务暂时不可用。您的问题：{request.messages[-1]['content']}",
                    "type": "error",
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
                "X-Accel-Buffering": "no"  # 禁用nginx缓冲
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送流式消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送流式消息失败")

@router.post("/search", response_model=List[DocumentSearchResponse])
async def search_documents(
    request: DocumentSearchRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """搜索相关文档"""
    try:
        results = await ai_service.search_similar_documents(
            query=request.query,
            top_k=request.n_results,
            user_id=str(current_user.get('id')),
            is_admin=current_user.get('is_superuser', False)
        )
        
        return [
            DocumentSearchResponse(
                content=result.get("content", ""),
                file_id=result.get("file_id", ""),
                file_name=result.get("file_name", ""),
                similarity=result.get("similarity", 0.0),
                metadata=result.get("metadata", {})
            )
            for result in results
        ]
        
    except Exception as e:
        logger.error(f"文档搜索失败: {e}")
        raise HTTPException(status_code=500, detail="文档搜索失败")

@router.post("/documents/process")
async def process_documents(request: ProcessDocumentsRequest, background_tasks: BackgroundTasks):
    """处理项目文档"""
    try:
        # 添加后台任务来处理文档
        background_tasks.add_task(
            ai_service.process_project_documents,
            project_id=request.project_id,
            file_paths=request.file_paths
        )
        
        return {"message": "文档处理任务已启动"}
        
    except Exception as e:
        logger.error(f"文档处理失败: {e}")
        raise HTTPException(status_code=500, detail="文档处理失败")

@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查AI服务状态
        ai_status = await ai_service.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "ai_service": ai_status,
                "database": "connected"
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/stats")
async def get_chat_stats(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取聊天统计信息（使用Supabase）
    """
    try:
        # 使用Supabase获取统计信息
        user_id = str(current_user.get('id'))
        stats = await supabase_service.get_chat_stats(user_id=user_id)
        
        logger.info(f"聊天统计: 对话数={stats['total_conversations']}, 消息数={stats['total_messages']}, AI消息数={stats['ai_messages']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"获取聊天统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取聊天统计失败: {str(e)}")

@router.get("/debug/model-info")
async def get_model_info():
    """
    获取当前模型配置信息（调试用）
    """
    try:
        from app.services.volcengine_client import volcengine_client
        return {
            "llm_model": volcengine_client.llm_model,
            "embedding_model": volcengine_client.embedding_model,
            "base_url": volcengine_client.base_url,
            "api_key_configured": bool(volcengine_client.api_key and volcengine_client.api_key != "dummy_key")
        }
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型信息失败: {str(e)}")

@router.post("/debug/fix-old-messages")
async def fix_old_messages(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    修复旧消息的模型信息（调试用，已迁移到 Supabase）
    """
    try:
        from app.services.volcengine_client import volcengine_client
        
        # TODO: 实现 Supabase 版本的修复逻辑
        # 需要查询所有没有模型信息的AI消息并更新
        logger.warning("⚠️ fix_old_messages 端点需要迁移到 Supabase")
        
        return {
            "message": "此功能需要迁移到 Supabase",
            "model_used": volcengine_client.llm_model
        }
        
    except Exception as e:
        logger.error(f"修复旧消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"修复旧消息失败: {str(e)}")