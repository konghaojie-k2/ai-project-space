"""
AI服务模块
使用豆包Embedding + FAISS + LangChain最新架构，提供稳定的RAG系统
参考：https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_agentic_rag/
"""

import os
# 🔧 设置OpenMP环境变量，防止FAISS等库冲突 - 必须在AI库导入之前设置
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import pickle
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from pathlib import Path
from loguru import logger
import numpy as np
from pydantic import BaseModel

# LangChain最新导入
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

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

class DocumentSearchResult(BaseModel):
    """文档搜索结果"""
    document_id: str
    file_name: str
    content: str
    relevance_score: float
    metadata: Dict[str, Any] = {}

class VolcengineEmbeddings(Embeddings):
    """豆包Embedding模型LangChain适配器"""
    
    def __init__(self):
        """初始化豆包Embedding"""
        self.client = volcengine_client
        self.model = self.client.embedding_model
        logger.info(f"✅ 初始化豆包Embedding模型: {self.model}")
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文档"""
        try:
            embeddings = []
            for text in texts:
                embedding = self.client.get_embedding(text)
                embeddings.append(embedding)
            logger.info(f"✅ 成功嵌入 {len(texts)} 个文档")
            return embeddings
        except Exception as e:
            logger.error(f"文档嵌入失败: {e}")
            # 返回零向量作为降级
            return [[0.0] * 2560 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """嵌入查询文本"""
        try:
            embedding = self.client.get_embedding(text)
            logger.info(f"✅ 成功嵌入查询文本")
            return embedding
        except Exception as e:
            logger.error(f"查询嵌入失败: {e}")
            return [0.0] * 2560
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """异步批量嵌入文档"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.embed_documents, texts
        )
    
    async def aembed_query(self, text: str) -> List[float]:
        """异步嵌入查询文本"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.embed_query, text
        )

class AIService:
    """AI服务类 - 基于豆包Embedding + FAISS + LangChain最新架构"""
    
    def __init__(self):
        """初始化AI服务"""
        self.vector_store = None
        self.embeddings_model = None
        self.text_splitter = None
        self.documents_metadata = {}  # 存储文档元数据
        self.faiss_index_path = Path("../vector_storage")
        self.faiss_index_path.mkdir(exist_ok=True)
        
        self.initialize_models()
        self.initialize_vector_store()
    
    def initialize_models(self):
        """初始化模型"""
        try:
            # 测试火山引擎连接
            if volcengine_client.test_connection():
                logger.info("✅ 火山引擎模型初始化成功")
            else:
                logger.warning("⚠️ 火山引擎连接失败，将使用模拟模式")
                
            # 初始化豆包embedding模型
            try:
                logger.info("🤖 正在初始化豆包Embedding模型...")
                self.embeddings_model = VolcengineEmbeddings()
                logger.info("✅ 豆包Embedding模型初始化成功")
            except Exception as embed_error:
                logger.error(f"豆包Embedding模型初始化失败: {embed_error}")
                logger.warning("使用简单的文本匹配作为降级方案")
                self.embeddings_model = None
            
            # 初始化文本分割器 - 使用最新参数
            try:
                self.text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len,
                    separators=["\n\n", "\n", " ", ""]
                )
                logger.info("✅ 文本分割器初始化成功")
            except Exception as splitter_error:
                logger.error(f"文本分割器初始化失败: {splitter_error}")
                self.text_splitter = None
                
        except Exception as e:
            logger.error(f"模型初始化失败: {e}")
            # 设置为None，后续方法会检查并使用降级方案
            self.embeddings_model = None
            self.text_splitter = None
    
    def initialize_vector_store(self):
        """初始化FAISS向量存储"""
        try:
            # 如果embedding模型未初始化，跳过向量存储初始化
            if not self.embeddings_model:
                logger.warning("⚠️ Embedding模型未初始化，跳过向量存储初始化")
                self.vector_store = None
                return
            
            # 检查是否存在已保存的向量存储
            faiss_file = self.faiss_index_path / "index.faiss"
            pkl_file = self.faiss_index_path / "index.pkl"
            metadata_file = self.faiss_index_path / "metadata.json"
            
            if faiss_file.exists() and pkl_file.exists():
                # 加载现有的向量存储
                try:
                    self.vector_store = FAISS.load_local(
                        str(self.faiss_index_path), 
                        self.embeddings_model,
                        allow_dangerous_deserialization=True
                    )
                    
                    # 加载文档元数据
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            self.documents_metadata = json.load(f)
                    
                    logger.info(f"✅ 从本地加载FAISS向量存储成功")
                    logger.info(f"  文档数量: {len(self.documents_metadata)}")
                except Exception as load_error:
                    logger.error(f"加载向量存储失败: {load_error}")
                    # 创建新的向量存储
                    self._create_new_vector_store()
            else:
                # 创建新的向量存储
                self._create_new_vector_store()
            
            logger.info(f"向量存储路径: {self.faiss_index_path}")
            
        except Exception as e:
            logger.error(f"向量存储初始化失败: {e}")
            self.vector_store = None
    
    def _create_new_vector_store(self):
        """创建新的向量存储"""
        try:
            # 用一个空文档初始化FAISS
            initial_doc = Document(page_content="初始化文档", metadata={"type": "init"})
            self.vector_store = FAISS.from_documents([initial_doc], self.embeddings_model)
            logger.info("✅ 创建新的FAISS向量存储")
        except Exception as e:
            logger.error(f"创建向量存储失败: {e}")
            self.vector_store = None
    
    def save_vector_store(self):
        """保存向量存储到本地"""
        try:
            if self.vector_store:
                self.vector_store.save_local(str(self.faiss_index_path))
                
                # 保存文档元数据
                metadata_file = self.faiss_index_path / "metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(self.documents_metadata, f, ensure_ascii=False, indent=2)
                
                logger.info("✅ 向量存储已保存到本地")
        except Exception as e:
            logger.error(f"保存向量存储失败: {e}")
    
    async def add_document_to_vector_db(
        self, 
        content: str, 
        file_id: str, 
        file_name: str,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """添加文档到向量数据库"""
        try:
            if not self.vector_store or not self.text_splitter or not content.strip():
                logger.warning("向量存储或文本分割器未初始化，跳过文档添加")
                return False
            
            # 分割文档
            chunks = self.text_splitter.split_text(content)
            if not chunks:
                return False
            
            # 为每个chunk创建Document对象
            documents = []
            for i, chunk in enumerate(chunks):
                doc_metadata = {
                    "file_id": file_id,
                    "file_name": file_name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "project_id": project_id or "default"
                }
                if metadata:
                    doc_metadata.update(metadata)
                
                documents.append(Document(page_content=chunk, metadata=doc_metadata))
            
            # 添加文档到向量存储
            self.vector_store.add_documents(documents)
            
            # 保存文档元数据
            self.documents_metadata[file_id] = {
                "file_name": file_name,
                "project_id": project_id,
                "chunks_count": len(chunks),
                "metadata": metadata or {}
            }
            
            # 异步保存
            await asyncio.get_event_loop().run_in_executor(None, self.save_vector_store)
            
            logger.info(f"✅ 文档已添加到向量数据库: {file_name} ({len(chunks)} chunks)")
            return True
            
        except Exception as e:
            logger.error(f"添加文档到向量数据库失败: {e}")
            return False
    
    async def search_similar_documents(
        self, 
        query: str, 
        project_id: Optional[str] = None,
        top_k: int = 3
    ) -> List[DocumentSearchResult]:
        """搜索相似文档 - 使用豆包Embedding"""
        try:
            if not self.vector_store or not query.strip():
                logger.warning("向量存储未初始化或查询为空")
                return []
            
            # 使用FAISS进行相似度搜索
            docs_with_scores = self.vector_store.similarity_search_with_score(
                query, k=top_k * 2  # 获取更多结果以便过滤
            )
            
            results = []
            seen_files = set()
            
            for doc, score in docs_with_scores:
                # 项目过滤
                if project_id and doc.metadata.get("project_id") != project_id:
                    continue
                
                file_id = doc.metadata.get("file_id", "unknown")
                file_name = doc.metadata.get("file_name", "Unknown")
                
                # 避免重复文件，每个文件只取最相关的chunk
                if file_id in seen_files:
                    continue
                seen_files.add(file_id)
                
                # 计算相关性分数 (FAISS返回的是距离，转换为相似度)
                # 豆包embedding使用余弦相似度，距离越小相似度越高
                relevance_score = max(0.0, 1.0 - score / 2.0)
                
                results.append(DocumentSearchResult(
                    document_id=file_id,
                    file_name=file_name,
                    content=doc.page_content[:500] + "..." if len(doc.page_content) > 500 else doc.page_content,
                    relevance_score=relevance_score,
                    metadata=doc.metadata
                ))
                
                if len(results) >= top_k:
                    break
            
            # 按相关性分数排序
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            logger.info(f"🔍 搜索查询: {query[:50]}...")
            logger.info(f"📄 找到 {len(results)} 个相关文档")
            
            return results
            
        except Exception as e:
            logger.error(f"搜索相似文档失败: {e}")
            return []
    
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
            
            # 🤖 智能上下文增强：搜索相关项目文档
            enhanced_context = await self._build_enhanced_context(messages, project_context)
            
            # 构建系统提示
            system_prompt = self._build_system_prompt(enhanced_context)
            
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
    
    async def _build_enhanced_context(self, messages: List[ChatMessage], project_context: Optional[str] = None) -> str:
        """构建增强上下文：基于用户消息搜索相关项目文档"""
        try:
            if not messages:
                return project_context or ""
            
            # 获取最后一条用户消息用于搜索
            last_message = messages[-1] if messages else None
            if not last_message:
                return project_context or ""
            
            # 提取查询内容
            if isinstance(last_message, dict):
                query = last_message.get("content", "")
            else:
                query = getattr(last_message, "content", "")
            
            if not query.strip():
                return project_context or ""
            
            logger.info(f"🤖 开始智能上下文搜索，查询: {query[:100]}...")
            
            # 从project_context中提取项目ID（如果有的话）
            project_id = project_context if project_context and project_context.startswith("project-") else None
            
            # 搜索相关文档
            relevant_docs = await self.search_similar_documents(
                query=query,
                project_id=project_id
            )
            
            # 构建增强上下文
            context_parts = []
            
            if project_context:
                context_parts.append(f"项目背景: {project_context}")
            
            if relevant_docs:
                context_parts.append("📚 相关项目文档:")
                for i, doc in enumerate(relevant_docs[:3], 1):
                    file_name = doc.file_name
                    content_preview = doc.content[:200] + ("..." if len(doc.content) > 200 else "")
                    relevance = doc.relevance_score
                    
                    context_parts.append(f"""
{i}. 文件: {file_name} (相关性: {relevance:.2f})
   内容摘要: {content_preview}""")
                
                logger.info(f"🤖 找到 {len(relevant_docs)} 个相关文档，已添加到上下文")
            else:
                logger.info("🤖 未找到相关项目文档")
            
            enhanced_context = "\n".join(context_parts)
            return enhanced_context
            
        except Exception as e:
            logger.error(f"构建增强上下文失败: {e}")
            return project_context or ""
    
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
        base_prompt = """你是一个专业的AI项目管理助手，具备以下能力：

🎯 **专业领域**：
- AI/机器学习项目管理
- 软件开发架构设计
- 数据科学项目实施
- 技术问题解决和咨询

💡 **回答原则**：
- 基于项目实际情况提供专业建议
- 结合最佳实践和行业标准
- 提供可操作的解决方案
- 保持回答的准确性和实用性

📚 **上下文理解**：
- 会分析项目阶段和具体需求
- 基于已有文档和资料提供建议
- 考虑项目的技术栈和约束条件"""
        
        if project_context:
            base_prompt += f"""

🔍 **当前项目上下文**：{project_context}

请基于以上项目背景，结合你的专业知识，为用户提供有针对性的建议和解决方案。如果用户的问题涉及具体的技术细节，请尽可能提供详细的实施步骤和注意事项。"""
        
        return base_prompt
    
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
                    await self.add_document_to_vector_db(content, document_id, Path(file_path).name, project_id, metadata)
            
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
            "vector_db": "FAISS + 豆包Embedding" if self.vector_store else "未初始化"
        }

# 创建全局AI服务实例
ai_service = AIService() 