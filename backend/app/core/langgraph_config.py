#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LangGraph配置管理
"""

from pydantic_settings import BaseSettings

class LangGraphConfig(BaseSettings):
    """LangGraph配置"""
    enabled: bool = True  # 默认启用LangGraph Agent
    fallback_enabled: bool = True
    confidence_threshold: float = 0.5
    max_execution_time: int = 60  # 最大执行时间（秒）
    enable_streaming: bool = True
    checkpoint_backend: str = "memory"  # memory, sqlite, postgres

    class Config:
        env_prefix = "LANGGRAPH_"

# 创建全局配置实例
langgraph_config = LangGraphConfig()