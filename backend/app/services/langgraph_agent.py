#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph Agent主服务
基于现代LangGraph v1架构的智能问答Agent
"""

import asyncio
import time
from typing import Dict, Any, Optional, AsyncGenerator
from loguru import logger
from langgraph.types import Command

from .agent.graph.builder import build_agent_workflow
from .agent.state.types import AgentState
from ..core.langgraph_config import langgraph_config


class LangGraphAgent:
    """基于现代LangGraph v1架构的智能问答Agent"""

    def __init__(self):
        """初始化LangGraph Agent"""
        self.config = langgraph_config

        # 构建Agent工作流
        self.workflow = build_agent_workflow()

        logger.info("✅ LangGraph v1 Agent 初始化完成（现代架构）")
        logger.info(f"🔧 配置: 启用={self.config.enabled}, 降级={self.config.fallback_enabled}")

    async def process_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: str = "",
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """处理单条消息"""
        start_time = time.time()

        try:
            # 检查是否启用
            if not self.config.enabled:
                return {
                    'response': 'LangGraph功能未启用',
                    'sources': [],
                    'intent_type': 'disabled',
                    'confidence': 0.0,
                    'processing_time': 0.0,
                    'error': 'Feature disabled'
                }

            # 初始化状态
            initial_state = AgentState(
                messages=[],
                user_query=message,
                refined_query=None,
                intent_classification={},
                confidence=0.0,
                needs_clarification=False,
                clarification_responses={},
                clarifying_questions=[],
                conversation_id=conversation_id,
                project_id=project_id,
                user_id=user_id,
                is_admin=is_admin,
                rag_result=None,
                project_context=None,
                sources=[],
                final_response=None
            )

            # 配置thread_id用于状态持久化
            config = {"configurable": {"thread_id": conversation_id or "default"}}

            # 执行工作流（使用异步调用以支持异步节点）
            result = await self.workflow.ainvoke(initial_state, config=config)

            processing_time = time.time() - start_time

            # 检查是否有中断（需要澄清）
            if "__interrupt__" in result:
                # 有中断，说明需要用户澄清
                interrupt_value = result["__interrupt__"][0].value
                logger.info(f"🔴 检测到中断点，需要澄清: {interrupt_value.get('type')}")

                return {
                    'response': self._build_clarification_response(interrupt_value),
                    'sources': [],
                    'intent_type': 'clarification_needed',
                    'confidence': result.get('confidence', 0.0),
                    'processing_time': processing_time,
                    'status': 'clarification_required',
                    'clarification_request': interrupt_value
                }

            # 正常完成
            final_response = result.get('final_response', '抱歉，无法处理您的请求')

            return {
                'response': final_response,
                'sources': result.get('sources', []),
                'intent_type': result.get('intent_classification', {}).get('intent', 'unknown'),
                'confidence': result.get('confidence', 0.0),
                'processing_time': processing_time,
                'status': 'success',
                'clarification_responses': result.get('clarification_responses', {})
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"消息处理失败: {e}")

            # 如果启用降级，返回降级响应
            if self.config.fallback_enabled:
                return {
                    'response': f'Agent处理失败，已降级到基础服务。错误: {str(e)}',
                    'sources': [],
                    'intent_type': 'error',
                    'confidence': 0.0,
                    'processing_time': processing_time,
                    'status': 'fallback'
                }

            return {
                'response': f'处理失败: {str(e)}',
                'sources': [],
                'intent_type': 'error',
                'confidence': 0.0,
                'processing_time': processing_time,
                'status': 'error',
                'error': str(e)
            }

    async def process_message_with_clarification(
        self,
        message: str,
        clarification_responses: Dict[str, Any],
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: str = "",
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        处理带有澄清回复的消息
        使用Command(resume=...)恢复中断的执行
        """
        start_time = time.time()

        try:
            # 配置thread_id用于状态持久化（必须与之前一致）
            config = {"configurable": {"thread_id": conversation_id or "default"}}

            # 🔴 关键：使用Command恢复执行
            logger.info(f"🔧 使用澄清回复恢复执行: {clarification_responses}")

            # 构建恢复命令
            resume_command = Command(resume=clarification_responses)

            # 恢复执行（使用异步调用）
            result = await self.workflow.ainvoke(resume_command, config=config)

            processing_time = time.time() - start_time

            # 提取最终回复
            final_response = result.get('final_response', '抱歉，无法处理您的请求')

            return {
                'response': final_response,
                'sources': result.get('sources', []),
                'intent_type': result.get('intent_classification', {}).get('intent', 'unknown'),
                'confidence': result.get('confidence', 0.0),
                'processing_time': processing_time,
                'status': 'success',
                'clarification_responses': result.get('clarification_responses', {})
            }

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"澄清处理失败: {e}")

            return {
                'response': f'澄清处理失败: {str(e)}',
                'sources': [],
                'intent_type': 'error',
                'confidence': 0.0,
                'processing_time': processing_time,
                'status': 'error',
                'error': str(e)
            }

    async def process_message_stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: str = "",
        is_admin: bool = False
    ) -> AsyncGenerator[str, None]:
        """流式处理消息"""
        # 对于现代架构，流式处理需要更复杂的实现
        # 暂时使用非流式方式
        result = await self.process_message(
            message, conversation_id, project_id, user_id, is_admin
        )
        yield result['response']

    def _build_clarification_response(self, clarification_request: Dict[str, Any]) -> str:
        """构建澄清响应消息"""
        response_parts = [
            "为了更好地回答您的问题，我需要一些澄清：",
            "",
        ]

        # 添加原始问题
        if clarification_request.get("original_query"):
            response_parts.append(f"您的原始问题：{clarification_request['original_query']}")
            response_parts.append("")

        # 添加检测到的意图
        if clarification_request.get("detected_intent"):
            response_parts.append(f"我理解您可能想了解：{clarification_request['detected_intent']}")
            response_parts.append("")

        # 添加澄清问题
        questions = clarification_request.get("questions", [])
        if questions:
            response_parts.append("请您帮助澄清以下问题：")
            for i, q in enumerate(questions, 1):
                response_parts.append(f"{i}. {q}")
            response_parts.append("")

        response_parts.append("请提供澄清信息，以便我能为您提供更准确的回答。")

        return "\n".join(response_parts)

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            return {
                'status': 'healthy',
                'enabled': self.config.enabled,
                'architecture': 'modern_langgraph_v1',
                'components': {
                    'workflow': 'compiled',
                    'nodes': ['classify', 'clarification', 'agent_executor'],
                    'tools': ['rag_query', 'project_info', 'project_stats', 'project_members']
                },
                'config': {
                    'confidence_threshold': self.config.confidence_threshold,
                    'enable_streaming': self.config.enable_streaming,
                    'fallback_enabled': self.config.fallback_enabled
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'components': {}
            }


# 创建全局Agent实例
langgraph_agent = LangGraphAgent()