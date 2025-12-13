#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
澄清节点
处理用户查询的澄清需求
"""

from typing import Dict, Any, List
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt
from loguru import logger

from ..state.types import AgentState


def clarification_node(state: AgentState) -> Dict[str, Any]:
    """
    澄清节点：当用户查询不够清晰时，请求澄清

    使用interrupt实现人机交互，暂停执行等待用户回复

    Args:
        state: Agent状态，包含意图分类和澄清需求

    Returns:
        更新后的状态，包含用户澄清回复
    """
    logger.info(f"📍 [节点] 澄清开始")

    classification = state.get("intent_classification", {})
    original_query = state.get("user_query", "")
    clarifying_questions = state.get("clarifying_questions", [])

    # 构建澄清请求
    clarification_request = {
        "type": "clarification_required",
        "original_query": original_query,
        "detected_intent": classification.get("intent"),
        "confidence": classification.get("confidence"),
        "clarity": classification.get("clarity"),
        "ambiguities": classification.get("ambiguities", []),
        "questions": clarifying_questions,
        "reasoning": classification.get("reasoning", "")
    }

    logger.info(f"  原始问题: {original_query}")
    logger.info(f"  检测意图: {classification.get('intent')}")
    logger.info(f"  不清晰之处: {classification.get('ambiguities', [])}")
    logger.info(f"  澄清问题数量: {len(clarifying_questions)}")

    # 构建澄清消息给用户
    clarification_message = build_clarification_message(clarification_request)

    # 添加澄清消息到消息列表
    messages = state.get("messages", [])
    messages.append(AIMessage(content=clarification_message))

    # 🔴 关键：调用interrupt暂停执行，等待用户输入
    logger.info("  ⏸ 执行暂停，等待用户澄清...")

    try:
        user_response = interrupt(clarification_request)

        # ✅ 用户恢复执行后，会执行到这里
        logger.info(f"  ✓ 收到用户澄清: {user_response}")

        # 处理用户回复
        refined_query = build_refined_query(original_query, user_response)

        return {
            "clarification_responses": user_response,
            "refined_query": refined_query,
            "needs_clarification": False,  # 标记澄清完成
            "messages": messages + [
                AIMessage(content=f"感谢您的澄清。我现在将基于您的补充信息进行处理。")
            ]
        }

    except Exception as e:
        logger.error(f"澄清过程失败: {e}")

        # 错误处理：继续执行原查询
        return {
            "clarification_responses": {},
            "refined_query": original_query,
            "needs_clarification": False,
            "messages": messages + [
                AIMessage(content="澄清过程遇到问题，将使用原始查询继续处理。")
            ]
        }


def build_clarification_message(clarification_request: Dict[str, Any]) -> str:
    """
    构建澄清消息

    Args:
        clarification_request: 澄清请求信息

    Returns:
        格式化的澄清消息
    """
    message_parts = [
        "为了更好地回答您的问题，我需要一些澄清：",
        ""
    ]

    # 添加原始问题
    if clarification_request.get("original_query"):
        message_parts.append(f"您的原始问题：{clarification_request['original_query']}")
        message_parts.append("")

    # 添加检测到的意图
    if clarification_request.get("detected_intent"):
        message_parts.append(f"我理解您可能想了解：{clarification_request['detected_intent']}")
        message_parts.append("")

    # 添加不清晰之处
    ambiguities = clarification_request.get("ambiguities", [])
    if ambiguities:
        message_parts.append("我注意到以下方面可能不够清晰：")
        for amb in ambiguities:
            message_parts.append(f"• {amb}")
        message_parts.append("")

    # 添加澄清问题
    questions = clarification_request.get("questions", [])
    if questions:
        message_parts.append("请您帮助澄清以下问题：")
        for i, q in enumerate(questions, 1):
            message_parts.append(f"{i}. {q}")
        message_parts.append("")

    message_parts.append("您的回复将帮助我提供更准确和有用的回答。")

    return "\n".join(message_parts)


def build_refined_query(original_query: str, user_response: Dict[str, Any]) -> str:
    """
    构建精化后的查询

    Args:
        original_query: 原始查询
        user_response: 用户澄清回复

    Returns:
        精化后的查询
    """
    refined_parts = [
        f"原始问题：{original_query}",
        "",
        "用户澄清："
    ]

    # 处理不同格式的用户回复
    if isinstance(user_response, dict):
        for key, value in user_response.items():
            if value and value.strip():
                refined_parts.append(f"• {key}: {value}")
    elif isinstance(user_response, str):
        refined_parts.append(f"• {user_response}")
    elif isinstance(user_response, list):
        for i, item in enumerate(user_response, 1):
            if item and str(item).strip():
                refined_parts.append(f"• 回复{i}: {item}")

    refined_parts.append("")
    refined_parts.append("请基于以上澄清信息回答用户的问题。")

    return "\n".join(refined_parts)