"""
AI服务模块
优先使用火山引擎API，集成RAG系统
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger
import numpy as np
from pydantic import BaseModel

import chromadb
from chromadb.config import Settings

from .volcengine_client import volcengine_client
from ..core.model_config import model_manager

# 配置日志
logger.add("logs/ai_service.log", rotation="1 day", retention="7 days")

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: Optional[str] = None

class ChatResponse(BaseModel):
    """聊天响应模型"""
    content: str
    sources: List[Dict[str, Any]] = []
    model: str
    usage: Dict[str, int] = {}

class AIService:
    """AI服务类"""
    
    def __init__(self):
        """初始化AI服务"""
        self.vector_db = None
        self.initialize_models()
        self.initialize_vector_db()
    
    def initialize_models(self):
        """初始化模型 - 使用火山引擎"""
        try:
            # 测试火山引擎连接
            if volcengine_client.test_connection():
                logger.info("✅ 火山引擎模型初始化成功")
            else:
                logger.warning("⚠️ 火山引擎连接失败，将使用模拟模式")
                
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
    
    def initialize_vector_db(self):
        """初始化向量数据库 - 支持多人协作的持久化"""
        try:
            # 创建ChromaDB客户端 - 使用持久化配置
            chroma_client = chromadb.PersistentClient(
                path="./data/chromadb",  # 使用项目根目录下的data/chromadb
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            
            # 获取或创建集合 - 支持多人协作
            self.vector_db = chroma_client.get_or_create_collection(
                name="project_documents",
                metadata={
                    "hnsw:space": "cosine",
                    "hnsw:construction_ef": 100,
                    "hnsw:search_ef": 50,
                    "description": "AI项目管理系统文档向量数据库",
                    "version": "1.0.0",
                    "created_by": "ai_project_manager",
                    "supports_multi_user": True
                }
            )
            
            # 记录数据库信息
            logger.info(f"向量数据库初始化成功")
            logger.info(f"  路径: ./data/chromadb")
            logger.info(f"  集合: project_documents")
            logger.info(f"  支持多人协作: 是")
            
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {e}")
            self.vector_db = None
    
    async def chat_completion(
        self, 
        messages: List[ChatMessage], 
        project_context: Optional[str] = None,
        stream: bool = False,
        model_name: Optional[str] = None
    ) -> ChatResponse:
        """聊天完成"""
        try:
            # 构建系统提示
            system_prompt = self._build_system_prompt(project_context)
            
            # 构建消息列表
            api_messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            for msg in messages:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # 使用火山引擎生成回复
            response_content = volcengine_client.chat_completion(api_messages)
            
            return ChatResponse(
                content=response_content,
                model=volcengine_client.llm_model,
                usage={
                    "prompt_tokens": len(str(api_messages)),
                    "completion_tokens": len(response_content),
                    "total_tokens": len(str(api_messages)) + len(response_content)
                }
            )
                
        except Exception as e:
            logger.error(f"聊天完成失败: {e}")
            return ChatResponse(
                content="抱歉，AI服务暂时不可用，请稍后重试。",
                model="error",
                usage={}
            )
    
    def _build_system_prompt(self, project_context: Optional[str] = None) -> str:
        """构建系统提示"""
        base_prompt = """你是一个专业的AI助手，专门帮助用户解决技术问题。请提供准确、有用的回答。"""
        
        if project_context:
            base_prompt += f"\n\n当前项目上下文：{project_context}\n请基于项目背景提供相关建议。"
        
        return base_prompt
    
    async def add_document_to_vector_db(
        self, 
        content: str, 
        metadata: Dict[str, Any],
        document_id: str,
        embedding_model_name: Optional[str] = None
    ) -> bool:
        """添加文档到向量数据库"""
        try:
            if not self.vector_db:
                logger.error("向量数据库未初始化")
                return False
            
            # 使用火山引擎获取嵌入向量
            embedding = volcengine_client.get_embedding(content)
            
            # 添加到向量数据库
            self.vector_db.add(
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata],
                ids=[document_id]
            )
            
            logger.info(f"文档已添加到向量数据库: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加文档到向量数据库失败: {e}")
            return False
    
    async def search_similar_documents(
        self, 
        query: str, 
        n_results: int = 5,
        embedding_model_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        try:
            if not self.vector_db:
                logger.error("向量数据库未初始化")
                return []
            
            # 使用火山引擎获取查询的嵌入向量
            query_embedding = volcengine_client.get_embedding(query)
            
            # 搜索相似文档
            results = self.vector_db.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            # 格式化结果
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"搜索相似文档失败: {e}")
            return []
    
    async def process_project_files(self, project_id: str, file_paths: List[str]) -> bool:
        """处理项目文件"""
        try:
            for file_path in file_paths:
                content = await self._read_file_content(Path(file_path))
                if content:
                    metadata = {
                        "project_id": project_id,
                        "file_path": file_path,
                        "file_type": Path(file_path).suffix,
                        "processed_at": str(asyncio.get_event_loop().time())
                    }
                    
                    document_id = f"{project_id}_{Path(file_path).name}"
                    await self.add_document_to_vector_db(content, metadata, document_id)
            
            logger.info(f"项目文件处理完成: {project_id}")
            return True
            
        except Exception as e:
            logger.error(f"处理项目文件失败: {e}")
            return False
    
    async def _read_file_content(self, file_path: Path) -> Optional[str]:
        """读取文件内容"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            return None
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return None
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "llm_model": volcengine_client.llm_model,
            "embedding_model": volcengine_client.embedding_model,
            "api_url": volcengine_client.base_url,
            "vector_db": "ChromaDB" if self.vector_db else "未初始化"
        }

# 创建全局AI服务实例
ai_service = AIService() 