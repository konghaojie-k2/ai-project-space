"""
AI服务模块
使用外部RAG服务提供完整的问答和文档搜索功能
外部RAG服务已集成RAG检索+LLM生成，无需本地LLM
"""

import os
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from loguru import logger
from pydantic import BaseModel

from .rag_client import rag_client

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

class AIService:
    """AI服务类 - 使用外部RAG服务（已集成RAG检索+LLM生成）"""
    
    def __init__(self):
        """初始化AI服务"""
        # 检查外部RAG服务可用性
        if rag_client.is_available():
            logger.info("✅ 外部RAG服务可用")
        else:
            logger.warning("⚠️ 外部RAG服务不可用")
    
    async def search_similar_documents(
        self, 
        query: str, 
        project_id: Optional[str] = None,
        top_k: int = 3,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> List[DocumentSearchResult]:
        """
        搜索相似文档 - 使用外部RAG服务
        
        Args:
            query: 搜索查询
            project_id: 项目ID
            top_k: 返回结果数量
            user_id: 用户ID（用于权限过滤）
            is_admin: 是否为管理员
            
        Returns:
            文档搜索结果列表
        """
        try:
            if not query.strip():
                logger.warning("查询为空")
                return []
            
            if not rag_client.is_available():
                logger.warning("外部RAG服务不可用")
                return []
            
            # 确定collection名称
            collection_name = f"project_{project_id}" if project_id else rag_client.config.collection_name
            
            # 使用外部RAG服务查询
            rag_result = await rag_client.query(
                query_text=query,
                collection_name=collection_name,
                top_k=top_k,
                similarity_threshold=0.7
            )
            
            # 转换RAG响应为DocumentSearchResult格式
            results = []
            for i, source in enumerate(rag_result.sources or []):
                # 从source中提取信息
                file_id = source.get("file_id") or source.get("document_id", f"doc_{i}")
                file_name = source.get("file_name") or source.get("filename", "Unknown")
                content = source.get("content") or source.get("text", "")
                relevance_score = source.get("score", source.get("similarity", 0.8))
                
                # 权限过滤（如果提供了user_id）
                if user_id is not None:
                    from app.services.supabase_file_service import supabase_file_service
                    if not await supabase_file_service.user_can_access_file(file_id, str(user_id), is_admin):
                        continue  # 跳过无权限的文件
                
                results.append(DocumentSearchResult(
                    document_id=file_id,
                    file_name=file_name,
                    content=content[:500] + "..." if len(content) > 500 else content,
                    relevance_score=float(relevance_score),
                    metadata=source.get("metadata", {})
                ))
            
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
        model_name: Optional[str] = None,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ) -> ChatResponse:
        """
        聊天完成 - 使用外部RAG服务
        
        外部RAG服务已集成RAG检索+LLM生成，直接返回完整答案
        """
        try:
            if not rag_client.is_available():
                return ChatResponse(
                    content="抱歉，RAG服务暂时不可用，请稍后重试。",
                    model="rag_service",
                    usage={}
                )
            
            # 提取最后一条用户消息作为查询
            query_text = ""
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                else:
                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", "")
                
                if role == "user" and content.strip():
                    query_text = content
                    break
            
            if not query_text:
                return ChatResponse(
                    content="请提供您的问题。",
                    model="rag_service",
                    usage={}
                )
            
            # 确定collection名称
            project_id = None
            if project_context:
                if isinstance(project_context, str):
                    if project_context.startswith("project_"):
                        project_id = project_context.replace("project_", "")
                    elif project_context.startswith("project-"):
                        project_id = project_context.replace("project-", "")
                    else:
                        project_id = project_context
            
            collection_name = f"project_{project_id}" if project_id else rag_client.config.collection_name
            
            # 使用外部RAG服务查询（已包含RAG检索+LLM生成）
            rag_result = await rag_client.query(
                query_text=query_text,
                collection_name=collection_name,
                top_k=5,
                similarity_threshold=0.7
            )
            
            # 权限过滤sources（如果提供了user_id）
            filtered_sources = []
            if user_id is not None and rag_result.sources:
                from app.services.supabase_file_service import supabase_file_service
                for source in rag_result.sources:
                    file_id = source.get("file_id") or source.get("document_id")
                    if file_id:
                        if await supabase_file_service.user_can_access_file(file_id, str(user_id), is_admin):
                            filtered_sources.append(source)
                    else:
                        # 如果没有file_id，保留source
                        filtered_sources.append(source)
            else:
                filtered_sources = rag_result.sources or []
            
            return ChatResponse(
                content=rag_result.answer,
                sources=filtered_sources,
                model="rag_service",
                usage={
                    "processing_time": rag_result.processing_time,
                    "sources_count": len(filtered_sources)
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
        model_name: Optional[str] = None,
        user_id: Optional[int] = None,
        is_admin: bool = False
    ):
        """
        聊天完成 - 流式响应
        使用外部RAG服务的流式查询（如果支持），否则使用非流式查询+模拟流式输出
        """
        try:
            logger.info(f"🔥 开始流式聊天完成，消息数量: {len(messages)}")
            
            if not rag_client.is_available():
                error_msg = "抱歉，RAG服务暂时不可用，请稍后重试。"
                words = error_msg.split()
                for i, word in enumerate(words):
                    yield word if i == 0 else f" {word}"
                    await asyncio.sleep(0.1)
                return
            
            # 提取最后一条用户消息作为查询
            query_text = ""
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                else:
                    role = getattr(msg, "role", "user")
                    content = getattr(msg, "content", "")
                
                if role == "user" and content.strip():
                    query_text = content
                    break
            
            if not query_text:
                error_msg = "请提供您的问题。"
                words = error_msg.split()
                for i, word in enumerate(words):
                    yield word if i == 0 else f" {word}"
                    await asyncio.sleep(0.1)
                return
            
            # 确定collection名称
            project_id = None
            if project_context:
                if isinstance(project_context, str):
                    if project_context.startswith("project_"):
                        project_id = project_context.replace("project_", "")
                    elif project_context.startswith("project-"):
                        project_id = project_context.replace("project-", "")
                    else:
                        project_id = project_context
            
            collection_name = f"project_{project_id}" if project_id else rag_client.config.collection_name
            
            # 尝试使用流式查询
            try:
                async for chunk in rag_client.stream_query(
                    query_text=query_text,
                    collection_name=collection_name,
                    top_k=5,
                    similarity_threshold=0.7
                ):
                    if chunk:
                        yield chunk
                return
            except Exception as stream_error:
                logger.warning(f"流式查询失败，使用非流式降级: {stream_error}")
            
            # 降级：使用非流式查询，然后模拟流式输出
            rag_result = await rag_client.query(
                query_text=query_text,
                collection_name=collection_name,
                top_k=5,
                similarity_threshold=0.7
            )
            
            # 权限过滤sources（如果提供了user_id）
            if user_id is not None and rag_result.sources:
                from app.services.supabase_file_service import supabase_file_service
                filtered_sources = []
                for source in rag_result.sources:
                    file_id = source.get("file_id") or source.get("document_id")
                    if file_id:
                        if await supabase_file_service.user_can_access_file(file_id, str(user_id), is_admin):
                            filtered_sources.append(source)
                    else:
                        filtered_sources.append(source)
            
            # 智能的流式输出：按句子和代码块分割
            import re
            
            answer = rag_result.answer
            chunks = []
            
            # 首先处理代码块
            parts = re.split(r'(```[\s\S]*?```)', answer)
            for part in parts:
                if part.startswith('```'):
                    # 代码块整体输出
                    chunks.append(part)
                else:
                    # 普通文本按句子分割
                    sentences = re.split(r'([.!?。！？\n]+)', part)
                    for i in range(0, len(sentences), 2):
                        if i < len(sentences):
                            sentence = sentences[i]
                            if i + 1 < len(sentences):
                                sentence += sentences[i + 1]
                            if sentence.strip():
                                chunks.append(sentence)
            
            # 流式输出chunks
            for chunk in chunks:
                if chunk.strip():
                    yield chunk
                    await asyncio.sleep(0.05)  # 适当的延时
                    
        except Exception as e:
            logger.error(f"流式聊天完成失败: {e}")
            import traceback
            logger.error(f"完整堆栈: {traceback.format_exc()}")
            
            # 发送友好的错误回复
            friendly_response = "抱歉，AI服务暂时遇到问题。请稍后重试。"
            words = friendly_response.split()
            for i, word in enumerate(words):
                yield word if i == 0 else f" {word}"
                await asyncio.sleep(0.1)
    
    async def _build_enhanced_context(self, messages: List[ChatMessage], project_context: Optional[str] = None, user_id: Optional[int] = None, is_admin: bool = False) -> str:
        """
        构建增强上下文 - 已废弃
        
        外部RAG服务已自动处理上下文检索，此方法不再需要
        保留用于兼容性
        """
        # 外部RAG服务会自动处理上下文检索，直接返回项目上下文即可
        return project_context or ""
    
    def _generate_markdown_fallback_response(self, question: str, project_context: Optional[str] = None) -> str:
        """生成Markdown格式的降级回复 - 用于测试流式渲染"""
        
        # 基于问题内容生成相应的Markdown回复
        question_lower = question.lower()
        
        if any(keyword in question_lower for keyword in ['代码', 'code', '编程', 'programming', '函数', 'function']):
            return f"""# 代码相关问题解答

感谢您关于 **{question}** 的提问！

## 解决方案

根据您的问题，我为您提供以下建议：

### 1. 代码示例

```python
def example_function():
    \"\"\"
    这是一个示例函数
    \"\"\"
    print("Hello, World!")
    return True

# 调用函数
result = example_function()
```

### 2. 最佳实践

- **代码规范**：遵循PEP 8标准
- **注释说明**：为复杂逻辑添加注释
- **错误处理**：使用适当的异常处理

### 3. 相关资源

- [Python官方文档](https://docs.python.org)
- [代码规范指南](https://pep8.org)

> 💡 **提示**: 实践是学习编程的最好方法！

希望这个回答对您有帮助！如果您有更多问题，请随时提问。"""

        elif any(keyword in question_lower for keyword in ['什么', 'what', '如何', 'how', '为什么', 'why']):
            return f"""# 关于 "{question}" 的详细解答

## 概述

您询问的是一个很好的问题。让我为您详细解释：

## 主要内容

### 🔍 核心要点

1. **第一点**: 这是重要的基础概念
2. **第二点**: 这涉及到实际应用
3. **第三点**: 这关系到最佳实践

### 📝 详细说明

对于您的问题，主要有以下几个方面需要考虑：

- **技术层面**: 需要掌握相关的技术栈
- **实践层面**: 需要进行实际操作练习  
- **理论层面**: 需要理解underlying原理

### 💡 示例代码

```javascript
// 示例代码
function handleQuestion(question) {{
    console.log(`处理问题: ${{question}}`);
    
    // 分析问题类型
    const type = analyzeQuestionType(question);
    
    // 生成回答
    return generateAnswer(type, question);
}}
```

## 总结

通过以上分析，我们可以得出结论：理解 + 实践 = 掌握。

如果您还有其他问题，欢迎继续提问！"""

        else:
            return f"""# AI助手回复

您好！感谢您的提问：**{question}**

## 回答

我很乐意为您解答这个问题。

### 📋 分析

基于您的问题，我认为可以从以下几个角度来考虑：

1. **背景信息**: 首先需要了解相关背景
2. **核心问题**: 明确问题的关键点  
3. **解决方案**: 提供可行的解决方案

### 🛠️ 建议

```text
这里是一些具体的建议和步骤：

1. 仔细分析需求
2. 制定实施计划
3. 逐步执行方案
4. 验证结果效果
```

### 📊 总结表格

| 方面 | 重要性 | 说明 |
|------|--------|------|
| 理论基础 | ⭐⭐⭐⭐⭐ | 扎实的理论基础很重要 |
| 实践经验 | ⭐⭐⭐⭐ | 通过实践加深理解 |
| 持续学习 | ⭐⭐⭐ | 保持学习的态度 |

> 🎯 **温馨提示**: 如果您需要更具体的帮助，请提供更多详细信息。

希望我的回答对您有所帮助！"""

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
- 考虑项目的技术栈和约束条件

📝 **回复格式要求**：
- 请使用标准的Markdown格式回复
- 使用合适的标题层级（# ## ###）来组织内容结构
- 代码示例请使用代码块包围，并标明语言类型
- 列表使用 - 或 1. 的格式
- 重要内容使用 **粗体** 强调
- 补充说明使用 *斜体*
- 确保段落之间有适当的空行分隔"""
        
        if project_context:
            base_prompt += f"""

🔍 **当前项目上下文**：{project_context}

请基于以上项目背景，结合你的专业知识，为用户提供有针对性的建议和解决方案。如果用户的问题涉及具体的技术细节，请尽可能提供详细的实施步骤和注意事项。"""
        
        return base_prompt
    
    async def process_project_files(self, project_id: str, file_paths: List[str]) -> bool:
        """
        处理项目文件 - 已废弃，文件处理由外部RAG服务完成
        此方法保留用于兼容性
        """
        logger.warning("process_project_files 已废弃，文件处理应由外部RAG服务完成")
        return False
    
    async def _read_file_content(self, file_path) -> Optional[str]:
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
            "service_type": "外部RAG服务（已集成RAG检索+LLM生成）",
            "rag_service_available": rag_client.is_available(),
            "rag_endpoint": rag_client.base_url if rag_client.is_available() else None,
            "collection_name": rag_client.config.collection_name if rag_client.is_available() else None
        }

    async def health_check(self) -> dict:
        """健康检查"""
        try:
            # 检查外部RAG服务
            rag_healthy = rag_client.is_available()
            
            if rag_healthy:
                # 尝试执行健康检查
                try:
                    health_info = await rag_client.health_check()
                    status = health_info.get("status", "healthy") if isinstance(health_info, dict) else "healthy"
                except:
                    status = "healthy"  # 如果健康检查失败，但服务可用，仍标记为healthy
            else:
                status = "unhealthy"
                
            return {
                "status": status,
                "message": "AI服务运行正常" if status == "healthy" else "RAG服务不可用",
                "components": {
                    "rag_service": "healthy" if rag_healthy else "unhealthy"
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"AI服务异常: {str(e)}",
                "components": {
                    "rag_service": "unknown"
                }
            }

# 创建全局AI服务实例
ai_service = AIService() 