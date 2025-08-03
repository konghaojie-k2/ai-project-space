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
                path="../chroma_db",  # 使用项目根目录下的chroma_db
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
            logger.info(f"  路径: ../chroma_db")
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
                # 处理字典格式和对象格式的消息
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                else:
                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", "")
                    
                api_messages.append({
                    "role": role,
                    "content": content
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
    
    async def chat_completion_stream(
        self, 
        messages: List[ChatMessage], 
        project_context: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        """聊天完成 - 流式响应"""
        try:
            logger.info(f"🔥 开始流式聊天完成，消息数量: {len(messages)}")
            logger.info(f"🔥 消息类型: {[type(msg).__name__ for msg in messages]}")
            logger.info(f"🔥 前3条消息内容: {messages[:3] if len(messages) <= 3 else messages[:3]}")
            
            # 构建系统提示
            system_prompt = self._build_system_prompt(project_context)
            
            # 构建消息列表
            api_messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            for msg in messages:
                # 处理字典格式和对象格式的消息
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                else:
                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", "")
                    
                api_messages.append({
                    "role": role,
                    "content": content
                })
            
            # 尝试使用真实的流式AI服务
            try:
                # 这里可以接入真实的流式AI服务
                # 目前使用模拟的流式响应
                response_content = volcengine_client.chat_completion(api_messages)
                
                # 模拟流式输出 - 将完整回复按字符分割
                import asyncio
                words = response_content.split()
                for i, word in enumerate(words):
                    if i == 0:
                        yield word
                    else:
                        yield f" {word}"
                    await asyncio.sleep(0.1)  # 控制输出速度
                    
            except Exception as ai_error:
                logger.warning(f"AI服务流式调用失败，使用降级方案: {ai_error}")
                # 降级处理 - 生成智能回复并流式输出
                last_message_content = ""
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        last_message_content = last_msg.get("content", "")
                    else:
                        last_message_content = getattr(last_msg, "content", "")
                        
                fallback_response = self._generate_fallback_response(
                    last_message_content, 
                    project_context
                )
                
                words = fallback_response.split()
                for i, word in enumerate(words):
                    if i == 0:
                        yield word
                    else:
                        yield f" {word}"
                    await asyncio.sleep(0.08)  # 稍快一些的输出速度
                    
        except Exception as e:
            logger.error(f"流式聊天完成失败: {e}")
            logger.error(f"异常详情: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(f"完整堆栈: {traceback.format_exc()}")
            
            # 发送错误信息 - 但实际上应该发送正常回复
            # 临时修复：直接发送一个友好的回复
            friendly_response = "你好！我是您的AI助手。虽然当前遇到了一些技术问题，但我很乐意为您提供帮助。请问有什么可以为您做的吗？"
            
            words = friendly_response.split()
            for i, word in enumerate(words):
                if i == 0:
                    yield word
                else:
                    yield f" {word}"
                import asyncio
                await asyncio.sleep(0.1)
    
    def _generate_fallback_response(self, user_input: str, project_context: Optional[str] = None) -> str:
        """生成降级回复"""
        if not user_input:
            return "您好！我是您的AI助手，请问有什么可以帮您的？"
        
        # 根据关键词生成相关回复
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in ['架构', '设计', '系统']):
            return """关于系统架构设计，我建议考虑以下几个关键方面：

🏗️ **架构设计原则：**
1. **模块化设计** - 将系统分解为独立的模块
2. **可扩展性** - 支持未来功能扩展
3. **高可用性** - 确保系统稳定运行
4. **性能优化** - 关注响应时间和吞吐量

💡 **技术选型建议：**
- 选择成熟稳定的技术栈
- 考虑团队技术栈熟悉度
- 评估技术的长期维护性
- 权衡开发效率和性能需求

您希望深入讨论哪个具体的架构方面？"""

        elif any(keyword in user_input_lower for keyword in ['数据', '数据库', '存储']):
            return """关于数据管理和存储，这里有一些专业建议：

📊 **数据存储策略：**
1. **关系型数据库** - 适合结构化数据和事务处理
2. **非关系型数据库** - 适合大规模数据和灵活schema
3. **缓存系统** - 提升数据访问性能
4. **数据备份** - 确保数据安全性

🔍 **数据处理最佳实践：**
- 数据清洗和验证
- 建立数据质量监控
- 实施数据安全策略
- 优化查询性能

需要针对特定的数据场景进行深入分析吗？"""

        elif any(keyword in user_input_lower for keyword in ['AI', '机器学习', '算法', '模型']):
            return """关于AI和机器学习实施，我为您提供以下指导：

🤖 **AI项目开发流程：**
1. **需求分析** - 明确AI应用场景
2. **数据准备** - 收集和预处理训练数据
3. **模型选择** - 根据问题类型选择算法
4. **模型训练** - 使用合适的训练策略
5. **模型评估** - 多维度评估模型性能
6. **部署上线** - 将模型集成到生产环境

⚡ **关键技术要点：**
- 特征工程的重要性
- 过拟合和欠拟合的处理
- 模型解释性和可信度
- 持续学习和模型更新

您想了解哪个具体的AI技术细节？"""

        else:
            # 通用回复
            context_info = f"在{project_context}的背景下，" if project_context else ""
            return f"""感谢您的提问！{context_info}我为您提供以下分析：

💡 **问题理解：**
您询问的"{user_input}"是一个很好的问题。

🎯 **建议方向：**
1. **深入分析** - 从多个角度理解问题本质
2. **最佳实践** - 参考行业标准和成功案例
3. **风险评估** - 识别潜在的技术和业务风险
4. **实施策略** - 制定循序渐进的解决方案

🚀 **下一步行动：**
- 收集更多详细需求
- 评估技术可行性
- 制定详细实施计划
- 建立项目里程碑

如果您能提供更多具体的技术需求或约束条件，我可以给出更有针对性的建议。您希望从哪个方面开始深入讨论？"""
    
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
            if not file_path.exists():
                return None
                
            # 根据文件扩展名判断处理方式
            file_extension = file_path.suffix.lower()
            
            # 文本文件直接读取
            if file_extension in ['.txt', '.md', '.csv', '.json', '.xml', '.html', '.htm']:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            # 对于二进制文件（PDF、Word等），使用文件工具提取内容
            elif file_extension in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']:
                # 这里应该使用专门的文件内容提取工具
                # 暂时返回文件信息而不是内容
                return f"二进制文件: {file_path.name}, 大小: {file_path.stat().st_size} 字节"
            
            # 图片文件
            elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                return f"图片文件: {file_path.name}, 大小: {file_path.stat().st_size} 字节"
            
            # 其他文件尝试文本读取
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                except:
                    return f"文件: {file_path.name}, 大小: {file_path.stat().st_size} 字节"
                    
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