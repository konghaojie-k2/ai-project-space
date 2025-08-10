"""
AI聊天API路由
提供聊天会话管理、消息发送、文档搜索等功能
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from loguru import logger

from ..core.database import get_db
from ..services.ai_service import ai_service
from ..models.chat import (
    ChatMessage, 
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

# 模拟数据存储（实际项目中应该使用数据库）
conversations_db = {}
messages_db = {}

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreate):
    """创建新会话"""
    try:
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        
        conversation = {
            "id": conversation_id,
            "title": request.title,
            "project_id": request.project_id,
            "project_name": None,  # 这里可以从项目数据库获取
            "last_message": None,
            "message_count": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        conversations_db[conversation_id] = conversation
        messages_db[conversation_id] = []
        
        logger.info(f"创建会话: {conversation_id}")
        return ConversationResponse(**conversation)
        
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail="创建会话失败")

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations():
    """获取会话列表"""
    try:
        conversations = []
        for conv in conversations_db.values():
            conversations.append(ConversationResponse(**conv))
        
        # 按更新时间排序
        conversations.sort(key=lambda x: x.updated_at, reverse=True)
        return conversations
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")

@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """获取会话详情"""
    try:
        if conversation_id not in conversations_db:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return ConversationResponse(**conversations_db[conversation_id])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话详情失败")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除会话"""
    try:
        if conversation_id not in conversations_db:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 删除会话和相关消息
        del conversations_db[conversation_id]
        del messages_db[conversation_id]
        
        logger.info(f"删除会话: {conversation_id}")
        return {"message": "会话删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail="删除会话失败")

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(conversation_id: str):
    """获取会话消息"""
    try:
        if conversation_id not in conversations_db:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        messages = messages_db.get(conversation_id, [])
        return [MessageResponse(**msg) for msg in messages]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话消息失败")

@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(conversation_id: str, request: ChatRequest):
    """发送消息"""
    try:
        if conversation_id not in conversations_db:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息
        user_message = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "user",
            "content": request.messages[-1]["content"],
            "timestamp": datetime.now(),
            "conversation_id": conversation_id
        }
        
        messages_db[conversation_id].append(user_message)
        
        # 调用AI服务获取回复
        try:
            ai_response = await ai_service.chat_completion(
                messages=request.messages,
                project_context=request.project_id,  # 将project_id作为project_context传递
                model_name=request.model or "gpt-3.5-turbo"
            )
            
            # 保存AI回复
            ai_message = {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": "assistant",
                "content": ai_response.content,
                "timestamp": datetime.now(),
                "conversation_id": conversation_id
            }
            
            messages_db[conversation_id].append(ai_message)
            
            # 更新会话信息
            conversations_db[conversation_id]["last_message"] = ai_response.content[:100] + "..."
            conversations_db[conversation_id]["message_count"] = len(messages_db[conversation_id])
            conversations_db[conversation_id]["updated_at"] = datetime.now()
            
            return ai_response
            
        except Exception as ai_error:
            logger.error(f"AI服务调用失败: {ai_error}")
            # 返回降级响应
            fallback_content = f"抱歉，AI服务暂时不可用。您的问题：{request.messages[-1]['content']}"
            
            ai_message = {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": "assistant", 
                "content": fallback_content,
                "timestamp": datetime.now(),
                "conversation_id": conversation_id
            }
            
            messages_db[conversation_id].append(ai_message)
            
            return ChatResponse(
                content=fallback_content,
                model="fallback",
                sources=[],
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送消息失败")

@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(conversation_id: str, request: ChatRequest):
    """发送消息（流式响应）- 参考DeerFlow优化实现"""
    try:
        if conversation_id not in conversations_db:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 保存用户消息
        user_message = {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "user",
            "content": request.messages[-1]["content"],
            "timestamp": datetime.now(),
            "conversation_id": conversation_id
        }
        
        messages_db[conversation_id].append(user_message)
        
        # 生成AI消息ID
        ai_message_id = f"msg_{uuid.uuid4().hex[:8]}"
        ai_content = ""
        
        async def generate_stream():
            nonlocal ai_content
            try:
                # 发送开始事件 - 添加更多元数据
                start_event = {
                    "message_id": ai_message_id, 
                    "type": "start",
                    "timestamp": datetime.now().isoformat(),
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
                    # 这样可以避免在markdown语法中间断开
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
                            "timestamp": datetime.now().isoformat()
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
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(content_event, ensure_ascii=False)}\n\n"
                
                # 保存完整的AI回复
                ai_message = {
                    "id": ai_message_id,
                    "role": "assistant",
                    "content": ai_content,
                    "timestamp": datetime.now(),
                    "conversation_id": conversation_id
                }
                
                messages_db[conversation_id].append(ai_message)
                
                # 更新会话信息
                conversations_db[conversation_id]["last_message"] = ai_content[:100] + "..."
                conversations_db[conversation_id]["message_count"] = len(messages_db[conversation_id])
                conversations_db[conversation_id]["updated_at"] = datetime.now()
                
                # 发送完成信号 - 包含完整内容和元数据
                end_event = {
                    "message_id": ai_message_id,
                    "role": "assistant", 
                    "content": ai_content,
                    "type": "end",
                    "timestamp": datetime.now().isoformat(),
                    "total_tokens": len(ai_content.split())  # 简单的token计数
                }
                yield f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"
                
                # 发送完成标识
                yield f"data: [DONE]\n\n"
                
            except Exception as ai_error:
                logger.error(f"AI流式服务调用失败: {ai_error}")
                # 发送错误信息
                error_content = f"抱歉，AI服务暂时不可用。您的问题：{request.messages[-1]['content']}"
                yield f"data: {json.dumps({'id': ai_message_id, 'role': 'assistant', 'content': error_content, 'type': 'error'}, ensure_ascii=False)}\n\n"
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送流式消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送流式消息失败")


        
        async def generate_stream():
            try:
                message_id = f"msg_{uuid.uuid4().hex[:8]}"
                
                # 发送开始事件
                start_event = StreamEvent(type="start", message_id=message_id)
                yield f"data: {start_event.model_dump_json()}\n\n"
                
                # 调用AI服务获取流式回复
                content_buffer = ""
                async for chunk in ai_service.chat_completion_stream(
                    messages=request.messages,
                    project_context=request.project_id,  # 将project_id作为project_context传递
                    model_name=request.model or "gpt-3.5-turbo"
                ):
                    content_buffer += chunk
                    content_event = StreamEvent(type="content", content=chunk)
                    yield f"data: {content_event.model_dump_json()}\n\n"
                
                # 保存AI回复
                ai_message = {
                    "id": message_id,
                    "role": "assistant",
                    "content": content_buffer,
                    "timestamp": datetime.now(),
                    "conversation_id": conversation_id
                }
                
                messages_db[conversation_id].append(ai_message)
                
                # 更新会话信息
                conversations_db[conversation_id]["last_message"] = content_buffer[:100] + "..."
                conversations_db[conversation_id]["message_count"] = len(messages_db[conversation_id])
                conversations_db[conversation_id]["updated_at"] = datetime.now()
                
                # 发送结束事件
                end_event = StreamEvent(type="end", message_id=message_id)
                yield f"data: {end_event.model_dump_json()}\n\n"
                
            except Exception as e:
                logger.error(f"流式响应失败: {e}")
                error_event = StreamEvent(type="error", error=str(e))
                yield f"data: {error_event.model_dump_json()}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式发送消息失败: {e}")
        raise HTTPException(status_code=500, detail="流式发送消息失败")

@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(request: DocumentSearchRequest):
    """搜索相关文档"""
    try:
        # 调用AI服务进行文档搜索
        results = await ai_service.search_documents(
            query=request.query,
            n_results=request.n_results,
            project_id=request.project_id
        )
        
        return DocumentSearchResponse(**results)
        
    except Exception as e:
        logger.error(f"文档搜索失败: {e}")
        raise HTTPException(status_code=500, detail="文档搜索失败")

@router.post("/documents/process")
async def process_documents(request: ProcessDocumentsRequest, background_tasks: BackgroundTasks):
    """处理项目文档"""
    try:
        # 在后台处理文档
        background_tasks.add_task(
            ai_service.process_project_files,
            project_id=request.project_id,
            file_paths=request.file_paths
        )
        
        return {"message": "文档处理任务已启动"}
        
    except Exception as e:
        logger.error(f"处理文档失败: {e}")
        raise HTTPException(status_code=500, detail="处理文档失败")

@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查AI服务状态
        ai_status = await ai_service.health_check()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "services": {
                "ai_service": ai_status
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(),
            "error": str(e)
        } 