#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
澄清中间件
在Agent调用前后进行澄清上下文注入和置信度检查
"""

import json
from typing import Dict, Any, Optional
from loguru import logger

from ..agent.state.types import AgentState


class ClarificationMiddleware:
    """
    澄清中间件：
    - 在分类后检查是否需要澄清
    - 将澄清历史注入到系统提示中
    - 标记state中的需要澄清标志
    """
    
    def __init__(self, confidence_threshold: float = 0.7):
        """
        初始化澄清中间件
        
        Args:
            confidence_threshold: 置信度阈值，低于此值将触发澄清
        """
        self.confidence_threshold = confidence_threshold
        logger.info(f"✓ 澄清中间件初始化完成，置信度阈值: {confidence_threshold}")
    
    def before_model(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """
        模型调用前：注入澄清历史和上下文
        
        Args:
            state: Agent状态
            
        Returns:
            附加上下文信息，或None
        """
        clarification_responses = state.get("clarification_responses")
        
        if clarification_responses:
            # 构建澄清上下文
            context = self._build_clarification_context(state)
            logger.info(f"✓ 中间件注入澄清上下文")
            return {"additional_context": context}
        
        return None
    
    def after_model(self, state: AgentState, response: Any) -> Optional[Dict[str, Any]]:
        """
        模型调用后：检查是否需要澄清
        
        Args:
            state: Agent状态
            response: 模型响应
            
        Returns:
            状态更新（如需要澄清标志），或None
        """
        confidence = state.get("confidence", 1.0)
        
        if confidence < self.confidence_threshold:
            logger.warning(f"⚠ 中间件检测到需要澄清（置信度: {confidence:.2f} < 阈值: {self.confidence_threshold}）")
            return {"needs_clarification": True}
        
        return None
    
    def _build_clarification_context(self, state: AgentState) -> str:
        """
        构建澄清上下文字符串
        
        Args:
            state: Agent状态
            
        Returns:
            格式化的澄清上下文
        """
        clarification_responses = state.get("clarification_responses", {})
        refined_query = state.get("refined_query", "")
        original_query = state.get("user_query", "")
        
        context_parts = [
            "【澄清上下文】",
            f"原始问题：{original_query}",
            "",
            "用户之前的澄清回复："
        ]
        
        # 添加澄清回复详情
        if isinstance(clarification_responses, dict):
            context_parts.append(json.dumps(clarification_responses, ensure_ascii=False, indent=2))
        elif isinstance(clarification_responses, str):
            context_parts.append(clarification_responses)
        else:
            context_parts.append(str(clarification_responses))
        
        context_parts.append("")
        
        if refined_query:
            context_parts.append(f"精化后的查询：{refined_query}")
        
        return "\n".join(context_parts)


class ContextInjectionMiddleware:
    """
    上下文注入中间件：
    - 在模型调用前注入项目上下文
    - 注入用户权限信息
    """
    
    def __init__(self):
        """初始化上下文注入中间件"""
        logger.info("✓ 上下文注入中间件初始化完成")
    
    def before_model(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """
        模型调用前：注入项目和用户上下文
        
        Args:
            state: Agent状态
            
        Returns:
            附加上下文信息
        """
        project_id = state.get("project_id")
        user_id = state.get("user_id")
        is_admin = state.get("is_admin", False)
        project_context = state.get("project_context")
        
        context_parts = ["【运行上下文】"]
        
        if project_id:
            context_parts.append(f"当前项目ID: {project_id}")
        
        if user_id:
            context_parts.append(f"用户ID: {user_id}")
            context_parts.append(f"管理员权限: {'是' if is_admin else '否'}")
        
        if project_context:
            context_parts.append("")
            context_parts.append("项目上下文信息:")
            if isinstance(project_context, dict):
                context_parts.append(json.dumps(project_context, ensure_ascii=False, indent=2))
            else:
                context_parts.append(str(project_context))
        
        if len(context_parts) > 1:
            logger.debug("✓ 中间件注入运行上下文")
            return {"runtime_context": "\n".join(context_parts)}
        
        return None
    
    def after_model(self, state: AgentState, response: Any) -> Optional[Dict[str, Any]]:
        """
        模型调用后：可用于记录或后处理
        
        Args:
            state: Agent状态
            response: 模型响应
            
        Returns:
            None（当前不做后处理）
        """
        return None


class LoggingMiddleware:
    """
    日志中间件：
    - 记录模型调用前后的关键信息
    - 用于调试和监控
    """
    
    def __init__(self, log_level: str = "INFO"):
        """
        初始化日志中间件
        
        Args:
            log_level: 日志级别
        """
        self.log_level = log_level
        logger.info("✓ 日志中间件初始化完成")
    
    def before_model(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """
        模型调用前：记录输入信息
        """
        user_query = state.get("user_query", "")
        refined_query = state.get("refined_query", "")
        confidence = state.get("confidence", 1.0)
        
        logger.info(f"📥 [中间件] 模型调用开始")
        logger.info(f"  用户查询: {user_query[:50]}...")
        
        if refined_query:
            logger.info(f"  精化查询: {refined_query[:50]}...")
        
        logger.info(f"  当前置信度: {confidence:.2f}")
        
        return None
    
    def after_model(self, state: AgentState, response: Any) -> Optional[Dict[str, Any]]:
        """
        模型调用后：记录输出信息
        """
        logger.info(f"📤 [中间件] 模型调用完成")
        
        if response:
            response_str = str(response)
            logger.info(f"  响应长度: {len(response_str)} 字符")
            logger.debug(f"  响应预览: {response_str[:100]}...")
        
        return None

