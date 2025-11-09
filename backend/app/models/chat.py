"""
聊天相关数据模型
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .base import Base


class Conversation(Base):
    """会话模型 - 对应数据库表 chat_sessions"""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)  # 数据库中是nullable
    project_id = Column(String, nullable=True)
    user_id = Column(String, nullable=False)  # 数据库中是not null
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联消息
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    """聊天消息模型 - 对应数据库表 chat_messages"""
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)  # 使用session_id
    content = Column(Text, nullable=False)
    role = Column(String, nullable=False)  # 'user' 或 'assistant'
    created_at = Column(DateTime, default=datetime.utcnow)  # 数据库中使用created_at
    # Python属性名为message_metadata，数据库列名为metadata（避免metadata保留字冲突）
    message_metadata = Column("metadata", JSON, nullable=True)
    
    # 关联会话
    conversation = relationship("Conversation", back_populates="messages")
    
    # 向后兼容属性
    @property
    def conversation_id(self):
        """向后兼容：返回session_id"""
        return self.session_id
    
    @property
    def timestamp(self):
        """向后兼容：返回created_at"""
        return self.created_at
    
    @property
    def meta_data(self):
        """向后兼容：返回message_metadata（避免与SQLAlchemy Base.metadata冲突）"""
        return self.message_metadata


# Pydantic模型用于API序列化

class ChatMessageBase(BaseModel):
    """聊天消息基础模型"""
    content: str
    role: str
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatMessageCreate(ChatMessageBase):
    """创建聊天消息请求"""
    conversation_id: str


class ChatMessageResponse(ChatMessageBase):
    """聊天消息响应"""
    id: str
    conversation_id: str
    timestamp: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """单个消息响应"""
    id: str
    content: str
    role: str
    timestamp: datetime
    conversation_id: str
    model: Optional[str] = None  # AI模型名称

    class Config:
        from_attributes = True


class ConversationBase(BaseModel):
    """会话基础模型"""
    title: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None


class ConversationCreate(ConversationBase):
    """创建会话请求"""
    pass


class ConversationResponse(ConversationBase):
    """会话响应"""
    id: str
    message_count: int = 0
    last_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[Dict[str, str]]
    project_id: Optional[str] = None
    stream: bool = False
    model: Optional[str] = "gpt-3.5-turbo"
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000


class ChatResponse(BaseModel):
    """聊天响应"""
    content: str
    role: str = "assistant"
    model: str
    sources: List[Dict[str, Any]] = []
    usage: Optional[Dict[str, int]] = None
    message_id: Optional[str] = None


class StreamEvent(BaseModel):
    """流式响应事件"""
    type: str  # 'start', 'content', 'end', 'error'
    content: Optional[str] = None
    message_id: Optional[str] = None
    error: Optional[str] = None


class DocumentSearchRequest(BaseModel):
    """文档搜索请求"""
    query: str
    n_results: int = Field(default=5, ge=1, le=20)
    project_id: Optional[str] = None


class DocumentSearchResponse(BaseModel):
    """文档搜索响应"""
    documents: List[Dict[str, Any]]
    distances: List[float]
    metadatas: List[Dict[str, Any]]


class ProcessDocumentsRequest(BaseModel):
    """处理文档请求"""
    project_id: str
    file_paths: List[str]
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000) 