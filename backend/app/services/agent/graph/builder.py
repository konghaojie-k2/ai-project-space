#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent工作流构建器
使用LangGraph构建完整的Agent工作流
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from ..state.types import AgentState
from ..node import classify_intent_node, clarification_node, agent_executor_node


def route_after_classification(state: AgentState) -> Literal["clarification_node", "agent_executor_node"]:
    """
    分类后的路由函数：根据是否需要澄清决定下一步

    Args:
        state: Agent状态

    Returns:
        下一个节点名称
    """
    needs_clarification = state.get("needs_clarification", False)
    route = "clarification_node" if needs_clarification else "agent_executor_node"

    logger.info(f"🔀 [路由] {route} (需要澄清: {needs_clarification})")
    return route


def build_agent_workflow():
    """
    构建完整的Agent工作流图

    工作流：START → 意图分类 → [澄清/Agent] → END

    Returns:
        编译后的工作流图
    """
    logger.info("🏗️  开始构建Agent工作流")

    # 创建工作流图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("classify", classify_intent_node)
    workflow.add_node("clarification", clarification_node)
    workflow.add_node("agent_executor", agent_executor_node)

    # 定义流程
    workflow.add_edge(START, "classify")

    # 条件路由：根据分类结果决定是否需要澄清
    workflow.add_conditional_edges(
        "classify",
        route_after_classification,
        {
            "clarification_node": "clarification",
            "agent_executor_node": "agent_executor"
        }
    )

    # 澄清后进入Agent执行
    workflow.add_edge("clarification", "agent_executor")

    # Agent执行后结束
    workflow.add_edge("agent_executor", END)

    # 配置检查点存储（支持中断和恢复）
    checkpointer = MemorySaver()

    # 编译工作流
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("✅ Agent工作流构建完成")

    return app