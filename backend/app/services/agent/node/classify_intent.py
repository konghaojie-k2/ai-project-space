#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图分类节点
使用LLM进行智能意图识别和置信度评估
"""

import json
import re
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from loguru import logger

from ..state.types import AgentState


def classify_intent_node(state: AgentState) -> Dict[str, Any]:
    """
    意图分类节点：使用LLM分析用户查询意图

    Args:
        state: Agent状态，包含用户查询

    Returns:
        更新后的状态，包含意图分类结果
    """
    logger.info(f"📍 [节点] 意图分类开始: {state.get('user_query', '')[:50]}...")

    try:
        # 初始化LLM
        llm = ChatOpenAI(
            model="deepseek-v3-250324",
            base_url="https://ark.cn-beijing.volces.com/api/v3/",
            api_key="0cd502d8-9f14-4b45-a445-6e9fe70ddabf",
            temperature=0.1
        )

        # 构建意图分类提示
        prompt = f"""
作为一个智能意图分类助手，请分析用户的查询并返回JSON格式的分类结果。

用户查询："{state['user_query']}"

请严格按照以下JSON格式返回，不要添加任何其他文本：
{{
    "intent": "qa|summary|project_info|document_analysis|research",
    "confidence": 0.1-1.0之间的数值,
    "clarity": "clear|unclear",
    "topics": ["topic1", "topic2"],
    "ambiguities": ["ambiguity1", "ambiguity2"],
    "clarifying_questions": ["问题1", "问题2", "问题3"],
    "reasoning": "分析过程和理由"
}}

意图类型说明：
- qa: 基础问答，寻求具体信息或解释
- summary: 文档总结、归纳、概要
- project_info: 项目状态、进度、成员等信息查询
- document_analysis: 文档内容分析、理解
- research: 需要深入研究和分析的复杂查询

只返回JSON，不要其他解释文本。
"""

        # 调用LLM进行意图分类
        response = llm.invoke([
            HumanMessage(content=prompt)
        ])

        # 解析LLM响应
        try:
            # 提取JSON内容（处理可能的格式问题）
            content = response.content.strip()
            if content.startswith('```json'):
                content = content[7:-3].strip()
            elif content.startswith('```'):
                content = content[3:-3].strip()

            classification = json.loads(content)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}, 使用备用分类")
            # 备用分类
            classification = {
                "intent": "qa",
                "confidence": 0.6,
                "clarity": "unclear",
                "topics": ["general"],
                "ambiguities": ["查询不够具体"],
                "clarifying_questions": ["能否提供更多细节？"],
                "reasoning": "解析失败，使用默认分类"
            }

        # 标准化分类结果
        intent = classification.get("intent", "qa")
        confidence = float(classification.get("confidence", 0.5))
        clarity = classification.get("clarity", "unclear")

        # 判断是否需要澄清（基于置信度和清晰度）
        needs_clarification = (
            confidence < 0.7 or
            clarity == "unclear" or
            classification.get("ambiguities") or
            classification.get("clarifying_questions")
        )

        logger.info(f"  意图: {intent}")
        logger.info(f"  置信度: {confidence:.2f}")
        logger.info(f"  清晰度: {clarity}")
        logger.info(f"  需要澄清: {needs_clarification}")

        # 构建状态更新
        state_update = {
            "intent_classification": classification,
            "confidence": confidence,
            "needs_clarification": needs_clarification,
            "clarifying_questions": classification.get("clarifying_questions", []),
            "messages": [
                AIMessage(
                    content=f"意图识别：{intent} (置信度: {confidence:.2f}, 清晰度: {clarity})"
                )
            ]
        }

        logger.info(f"📍 [节点] 意图分类完成")
        return state_update

    except Exception as e:
        logger.error(f"意图分类失败: {e}")
        # 错误处理：返回默认分类
        return {
            "intent_classification": {
                "intent": "qa",
                "confidence": 0.5,
                "clarity": "unclear",
                "topics": ["general"],
                "ambiguities": ["分类失败"],
                "clarifying_questions": ["请重新表述您的问题"],
                "reasoning": f"分类失败: {str(e)}"
            },
            "confidence": 0.5,
            "needs_clarification": True,
            "clarifying_questions": ["请重新表述您的问题"],
            "messages": [
                AIMessage(content="意图分类遇到问题，需要澄清")
            ]
        }