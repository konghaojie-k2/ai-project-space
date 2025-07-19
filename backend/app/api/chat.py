"""
AI聊天API路由
处理聊天请求和会话管理
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger
from datetime import datetime

from ..services.ai_service import ai_service, ChatMessage, ChatResponse

router = APIRouter(tags=["chat"])

# 请求和响应模型
class ChatRequest(BaseModel):
    """聊天请求模型"""
    messages: List[ChatMessage]
    project_id: Optional[str] = None
    stream: bool = False

class ConversationCreateRequest(BaseModel):
    """创建会话请求模型"""
    title: str
    project_id: Optional[str] = None

class ConversationResponse(BaseModel):
    """会话响应模型"""
    id: str
    title: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    last_message: Optional[str] = None
    message_count: int
    created_at: datetime
    updated_at: datetime

class MessageResponse(BaseModel):
    """消息响应模型"""
    id: str
    role: str
    content: str
    timestamp: datetime
    conversation_id: str

# 模拟数据存储（实际项目中应该使用数据库）
conversations_db = {}
messages_db = {}

@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(request: ConversationCreateRequest):
    """创建新会话"""
    try:
        conversation_id = f"conv_{datetime.now().timestamp()}"
        
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
        
        del conversations_db[conversation_id]
        if conversation_id in messages_db:
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
        
        messages = []
        for msg in messages_db.get(conversation_id, []):
            messages.append(MessageResponse(**msg))
        
        return messages
        
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
        
        # 获取项目上下文
        project_context = None
        if request.project_id:
            # 这里可以从项目数据库获取项目信息
            project_context = f"项目ID: {request.project_id}"
        
        # 调用AI服务
        response = await ai_service.chat_completion(
            messages=request.messages,
            project_context=project_context,
            stream=request.stream
        )
        
        # 保存用户消息
        user_message = {
            "id": f"msg_{datetime.now().timestamp()}_user",
            "role": "user",
            "content": request.messages[-1].content if request.messages else "",
            "timestamp": datetime.now(),
            "conversation_id": conversation_id
        }
        messages_db[conversation_id].append(user_message)
        
        # 保存AI回复
        ai_message = {
            "id": f"msg_{datetime.now().timestamp()}_ai",
            "role": "assistant",
            "content": response.content,
            "timestamp": datetime.now(),
            "conversation_id": conversation_id
        }
        messages_db[conversation_id].append(ai_message)
        
        # 更新会话信息
        conversations_db[conversation_id]["last_message"] = request.messages[-1].content if request.messages else ""
        conversations_db[conversation_id]["message_count"] = len(messages_db[conversation_id])
        conversations_db[conversation_id]["updated_at"] = datetime.now()
        
        logger.info(f"发送消息到会话: {conversation_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail="发送消息失败")

@router.post("/search", response_model=List[dict])
async def search_documents(query: str, n_results: int = 5):
    """搜索相关文档"""
    try:
        documents = await ai_service.search_similar_documents(query, n_results)
        return documents
        
    except Exception as e:
        logger.error(f"搜索文档失败: {e}")
        raise HTTPException(status_code=500, detail="搜索文档失败")

@router.post("/documents/process")
async def process_documents(project_id: str, file_paths: List[str]):
    """处理项目文档"""
    try:
        success = await ai_service.process_project_files(project_id, file_paths)
        if success:
            return {"message": "文档处理成功"}
        else:
            raise HTTPException(status_code=500, detail="文档处理失败")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文档失败: {e}")
        raise HTTPException(status_code=500, detail="处理文档失败")

@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查AI服务状态
        openai_status = "connected" if ai_service.client else "mock_mode"
        embedding_status = "ready" if ai_service.embedding_model else "not_ready"
        vector_db_status = "ready" if ai_service.vector_db else "not_ready"
        
        return {
            "status": "healthy",
            "services": {
                "openai": openai_status,
                "embeddings": embedding_status,
                "vector_db": vector_db_status
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="服务不健康") 