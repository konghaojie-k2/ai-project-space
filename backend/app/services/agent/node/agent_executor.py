#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent执行节点
使用create_agent方法创建智能Agent，自主选择工具
"""

from typing import Dict, Any, Optional
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger

from ..state.types import AgentState
from ...tools.rag_tool import rag_query_tool
from ...tools.project_info_tool import (
    get_project_info_tool,
    get_project_stats_tool,
    get_project_members_tool
)


async def agent_executor_node(state: AgentState) -> Dict[str, Any]:
    """
    Agent执行节点：使用create_agent创建智能Agent

    Agent将根据查询内容和上下文自主选择合适的工具

    Args:
        state: Agent状态，包含用户查询和上下文信息

    Returns:
        更新后的状态，包含最终响应
    """
    logger.info(f"📍 [节点] Agent执行开始")

    try:
        # 使用精化后的查询（如果有的话）
        query = state.get("refined_query") or state.get("user_query", "")
        project_id = state.get("project_id")
        user_id = state.get("user_id", "")
        is_admin = state.get("is_admin", False)

        logger.info(f"  处理查询: {query[:50]}...")
        logger.info(f"  项目ID: {project_id}")

        # 初始化LLM
        llm = ChatOpenAI(
            model="deepseek-v3-250324",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
            api_key="0cd502d8-9f14-4b45-a445-6e9fe70ddabf",
            temperature=0.1,
            max_tokens=2000
        )

        # 可用工具列表
        tools = [
            rag_query_tool,
            get_project_info_tool,
            get_project_stats_tool,
            get_project_members_tool
        ]

        # 构建系统提示
        system_prompt = f"""你是一个智能项目助手，具备以下能力：

🎯 **主要功能**：
1. **知识问答**：使用知识库回答技术问题
2. **项目信息查询**：获取项目状态、进度、成员等信息
3. **文档分析**：深入分析文档内容

🔧 **工具选择指南**：
- **知识库查询 (rag_query_tool)**：用于回答技术问题、查询文档内容
- **项目信息 (get_project_info_tool)**：查询项目基本信息
- **项目统计 (get_project_stats_tool)**：获取项目统计数据和进度
- **项目成员 (get_project_members_tool)**：查询项目团队成员

📋 **当前上下文**：
- 项目ID: {project_id or '未指定'}
- 用户ID: {user_id}
- 管理员权限: {is_admin}

💡 **使用原则**：
1. 根据用户问题选择最合适的工具
2. 如果问题涉及多个方面，可以依次调用相关工具
3. 如果信息不足，明确告诉用户缺少什么
4. 使用清晰的结构化格式回答

请基于用户的问题和可用工具，提供准确、有用的回答。
"""

        # 使用create_agent创建智能Agent
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=InMemorySaver(),
        )

        # 构建用户消息
        user_message = f"用户查询：{query}"

        # 调用Agent处理（使用异步调用以支持异步工具）
        logger.info("  调用Agent处理...")
        result = await agent.ainvoke({
            "messages": [
                HumanMessage(content=user_message)
            ]
        })

        # 提取最终回复
        if result.get("messages"):
            final_message = result["messages"][-1]
            # AIMessage 是 Pydantic 对象，使用 .content 属性而不是 .get() 方法
            if hasattr(final_message, 'content'):
                final_response = final_message.content
            elif isinstance(final_message, dict):
                final_response = final_message.get("content", str(final_message))
            else:
                final_response = str(final_message)
        else:
            final_response = "抱歉，我无法处理您的请求。"

        logger.info(f"  ✓ Agent处理完成")
        logger.info(f"  回复长度: {len(final_response)} 字符")

        # 构建状态更新
        state_update = {
            "final_response": final_response,
            "messages": [
                AIMessage(content=final_response)
            ]
        }

        return state_update

    except Exception as e:
        logger.error(f"Agent执行失败: {e}")

        # 错误处理：返回友好错误信息
        error_response = f"抱歉，处理您的请求时遇到了问题：{str(e)}。请稍后重试或重新表述您的问题。"

        return {
            "final_response": error_response,
            "messages": [
                AIMessage(content=error_response)
            ]
        }