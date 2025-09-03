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
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel
from loguru import logger

from ..core.database import get_db
from ..services.ai_service import ai_service
from ..models.user import User
from ..models.chat import (
    Conversation as ConversationModel,
    ChatMessage as ChatMessageModel,
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
from .api_v1.endpoints.auth import get_current_user

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新会话"""
    try:
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        
        # 创建数据库记录
        db_conversation = ConversationModel(
            id=conversation_id,
            title=request.title,
            project_id=request.project_id,
            project_name=None,  # 这里可以从项目数据库获取
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        
        logger.info(f"创建新会话: {conversation_id}, 标题: {request.title}")
        
        return ConversationResponse(
            id=db_conversation.id,
            title=db_conversation.title,
            project_id=db_conversation.project_id,
            project_name=db_conversation.project_name,
            last_message=None,
            message_count=0,
            created_at=db_conversation.created_at.isoformat(),
            updated_at=db_conversation.updated_at.isoformat()
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail="创建会话失败")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(db: Session = Depends(get_db)):
    """获取会话列表"""
    try:
        # 从数据库获取会话，按更新时间排序
        conversations = db.query(ConversationModel).order_by(desc(ConversationModel.updated_at)).all()
        
        result = []
        for conv in conversations:
            # 获取最后一条消息
            last_message = db.query(ChatMessageModel).filter(
                ChatMessageModel.conversation_id == conv.id
            ).order_by(desc(ChatMessageModel.timestamp)).first()
            
            # 获取消息数量
            message_count = db.query(ChatMessageModel).filter(
                ChatMessageModel.conversation_id == conv.id
            ).count()
            
            result.append(ConversationResponse(
                id=conv.id,
                title=conv.title,
                project_id=conv.project_id,
                project_name=conv.project_name,
                last_message=last_message.content[:100] + "..." if last_message else None,
                message_count=message_count,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat()
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """获取会话详情"""
    try:
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取最后一条消息和消息数量
        last_message = db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation_id
        ).order_by(desc(ChatMessageModel.timestamp)).first()
        
        message_count = db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation_id
        ).count()
        
        return ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            project_id=conversation.project_id,
            project_name=conversation.project_name,
            last_message=last_message.content[:100] + "..." if last_message else None,
            message_count=message_count,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话详情失败")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """删除会话"""
    try:
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 删除会话（消息会通过cascade自动删除）
        db.delete(conversation)
        db.commit()
        
        logger.info(f"删除会话: {conversation_id}")
        
        return {"message": "会话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail="删除会话失败")

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(conversation_id: str, db: Session = Depends(get_db)):
    """获取会话消息"""
    try:
        # 验证会话存在
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取消息，按时间顺序排序
        messages = db.query(ChatMessageModel).filter(
            ChatMessageModel.conversation_id == conversation_id
        ).order_by(ChatMessageModel.timestamp).all()
        
        return [
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                conversation_id=msg.conversation_id,
                model=msg.meta_data.get("model") if msg.meta_data else None
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送消息（非流式）"""
    try:
        # 验证会话存在
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息到数据库
        user_message = ChatMessageModel(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            role="user",
            content=request.messages[-1]["content"],
            timestamp=datetime.utcnow()
        )
        
        db.add(user_message)
        db.commit()
        
        # 调用AI服务
        ai_response = await ai_service.chat_completion(
            messages=request.messages,
            project_context=request.project_id,
            model_name=request.model or "gpt-3.5-turbo"
        )
        
        # 保存AI回复到数据库
        ai_message = ChatMessageModel(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            role="assistant",
            content=ai_response.content,
            timestamp=datetime.utcnow(),
            meta_data={"model": ai_response.model} if hasattr(ai_response, 'model') else {"model": "Claude-3.5"}
        )
        
        db.add(ai_message)
        
        # 更新会话信息
        conversation.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"消息发送成功，会话: {conversation_id}")
        
        return ai_response
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送消息失败")

@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str, 
    request: ChatRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """发送消息（流式响应）- 数据库持久化版本"""
    try:
        # 验证会话存在
        conversation = db.query(ConversationModel).filter(
            ConversationModel.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息到数据库
        user_message = ChatMessageModel(
            id=f"msg_{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            role="user",
            content=request.messages[-1]["content"],
            timestamp=datetime.utcnow()
        )
        
        db.add(user_message)
        db.commit()
        
        # 生成AI消息ID
        ai_message_id = f"msg_{uuid.uuid4().hex[:8]}"
        ai_content = ""
        
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
                
                # 调用AI服务获取流式回复
                async for chunk in ai_service.chat_completion_stream(
                    messages=request.messages,
                    project_context=request.project_id,
                    model_name=request.model or "gpt-3.5-turbo"
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
                
                # 保存完整的AI回复到数据库
                ai_message = ChatMessageModel(
                    id=ai_message_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=ai_content,
                    timestamp=datetime.utcnow(),
                    meta_data={"model": model_name}  # 使用真实的模型名称
                )
                
                db.add(ai_message)
                
                # 更新会话信息
                conversation.updated_at = datetime.utcnow()
                
                db.commit()
                
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
        db.rollback()
        logger.error(f"发送流式消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送流式消息失败")

@router.post("/search", response_model=List[DocumentSearchResponse])
async def search_documents(
    request: DocumentSearchRequest,
    current_user: User = Depends(get_current_user)
):
    """搜索相关文档"""
    try:
        results = await ai_service.search_similar_documents(
            query=request.query,
            top_k=request.n_results,
            user_id=current_user.id,
            is_admin=current_user.is_superuser
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
async def get_chat_stats(db: Session = Depends(get_db)):
    """
    获取聊天统计信息
    """
    try:
        # 统计对话总数
        total_conversations = db.query(func.count(ConversationModel.id)).scalar()
        
        # 统计消息总数
        total_messages = db.query(func.count(ChatMessageModel.id)).scalar()
        
        # 统计AI消息数量
        ai_messages = db.query(func.count(ChatMessageModel.id)).filter(
            ChatMessageModel.role == 'assistant'
        ).scalar()
        
        logger.info(f"聊天统计: 对话数={total_conversations}, 消息数={total_messages}, AI消息数={ai_messages}")
        
        return {
            "total_conversations": total_conversations or 0,
            "total_messages": total_messages or 0,
            "ai_messages": ai_messages or 0
        }
        
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
async def fix_old_messages(db: Session = Depends(get_db)):
    """
    修复旧消息的模型信息（调试用）
    """
    try:
        from app.services.volcengine_client import volcengine_client
        
        # 获取所有没有模型信息的AI消息
        messages_to_fix = db.query(ChatMessageModel).filter(
            ChatMessageModel.role == 'assistant',
            ChatMessageModel.meta_data.is_(None)
        ).all()
        
        updated_count = 0
        for message in messages_to_fix:
            message.meta_data = {"model": volcengine_client.llm_model}
            updated_count += 1
        
        db.commit()
        
        return {
            "updated_messages": updated_count,
            "model_used": volcengine_client.llm_model
        }
        
    except Exception as e:
        logger.error(f"修复旧消息失败: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"修复旧消息失败: {str(e)}")