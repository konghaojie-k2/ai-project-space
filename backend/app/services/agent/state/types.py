#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Agent状态类型定义"""

from typing import TypedDict, Annotated, Literal, Dict, Any, List, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
import operator


class AgentState(TypedDict):
    """
    Agent状态定义
    使用TypedDict和Annotated类型，符合LangGraph v1最佳实践
    """
    # 消息列表（使用add_messages注解支持消息追加）
    messages: Annotated[List[BaseMessage], add_messages]

    # 用户查询相关信息
    user_query: str
    refined_query: Optional[str]  # 澄清后的查询

    # 意图分类结果
    intent_classification: Dict[str, Any]
    confidence: float
    needs_clarification: bool

    # 澄清相关
    clarification_responses: Dict[str, Any]  # 用户澄清回复
    clarifying_questions: List[str]  # 需要澄清的问题

    # 会话和用户信息
    conversation_id: Optional[str]
    project_id: Optional[str]
    user_id: str
    is_admin: bool

    # 工具执行结果
    rag_result: Optional[Dict[str, Any]]
    project_context: Optional[Dict[str, Any]]
    sources: List[Dict[str, Any]]

    # 最终响应
    final_response: Optional[str]