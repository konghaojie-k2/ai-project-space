"""
AI模型配置文件
管理各种AI模型的云端API配置
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pathlib import Path
import os

class ModelConfig(BaseModel):
    """模型配置基类"""
    model_name: str
    provider: str = "openai"  # openai, anthropic, azure, local
    description: str = ""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 1.0
    enabled: bool = True

class EmbeddingModelConfig(ModelConfig):
    """嵌入模型配置"""
    embedding_size: int = 1536
    max_input_tokens: int = 8192
    
class LLMModelConfig(ModelConfig):
    """大语言模型配置"""
    context_length: int = 4096
    supports_streaming: bool = True
    supports_functions: bool = False

class MultimodalModelConfig(ModelConfig):
    """多模态模型配置"""
    supported_formats: List[str] = ["image", "text"]
    max_image_size: int = 20  # MB
    supports_vision: bool = True

class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.embedding_models = {
            "text-embedding-ada-002": EmbeddingModelConfig(
                model_name="text-embedding-ada-002",
                provider="openai",
                description="OpenAI嵌入模型，适用于文本相似度和搜索",
                embedding_size=1536,
                max_input_tokens=8192
            ),
            "text-embedding-3-small": EmbeddingModelConfig(
                model_name="text-embedding-3-small",
                provider="openai", 
                description="OpenAI第三代小型嵌入模型",
                embedding_size=1536,
                max_input_tokens=8192
            ),
            "text-embedding-3-large": EmbeddingModelConfig(
                model_name="text-embedding-3-large",
                provider="openai",
                description="OpenAI第三代大型嵌入模型",
                embedding_size=3072,
                max_input_tokens=8192
            )
        }
        
        self.llm_models = {
            "gpt-3.5-turbo": LLMModelConfig(
                model_name="gpt-3.5-turbo",
                provider="openai",
                description="OpenAI GPT-3.5 Turbo模型",
                max_tokens=4096,
                context_length=16385,
                supports_streaming=True,
                supports_functions=True
            ),
            "gpt-4": LLMModelConfig(
                model_name="gpt-4",
                provider="openai",
                description="OpenAI GPT-4模型",
                max_tokens=8192,
                context_length=8192,
                supports_streaming=True,
                supports_functions=True
            ),
            "gpt-4-turbo": LLMModelConfig(
                model_name="gpt-4-turbo",
                provider="openai",
                description="OpenAI GPT-4 Turbo模型",
                max_tokens=4096,
                context_length=128000,
                supports_streaming=True,
                supports_functions=True
            ),
            "claude-3-sonnet": LLMModelConfig(
                model_name="claude-3-sonnet-20240229",
                provider="anthropic",
                description="Anthropic Claude 3 Sonnet模型",
                max_tokens=4096,
                context_length=200000,
                supports_streaming=True,
                supports_functions=False
            ),
            "claude-3-haiku": LLMModelConfig(
                model_name="claude-3-haiku-20240307",
                provider="anthropic",
                description="Anthropic Claude 3 Haiku模型",
                max_tokens=4096,
                context_length=200000,
                supports_streaming=True,
                supports_functions=False
            )
        }
        
        self.multimodal_models = {
            "gpt-4-vision-preview": MultimodalModelConfig(
                model_name="gpt-4-vision-preview",
                provider="openai",
                description="OpenAI GPT-4 Vision模型，支持图像理解",
                max_tokens=4096,
                context_length=128000,
                supported_formats=["image", "text"],
                max_image_size=20,
                supports_vision=True
            ),
            "gpt-4o": MultimodalModelConfig(
                model_name="gpt-4o",
                provider="openai",
                description="OpenAI GPT-4 Omni多模态模型",
                max_tokens=4096,
                context_length=128000,
                supported_formats=["image", "text", "audio"],
                max_image_size=20,
                supports_vision=True
            ),
            "claude-3-opus": MultimodalModelConfig(
                model_name="claude-3-opus-20240229",
                provider="anthropic",
                description="Anthropic Claude 3 Opus多模态模型",
                max_tokens=4096,
                context_length=200000,
                supported_formats=["image", "text"],
                max_image_size=25,
                supports_vision=True
            )
        }
        
        self.global_config = {
            "cache_enabled": True,
            "cache_ttl": 3600,
            "max_concurrent_requests": 10,
            "retry_attempts": 3,
            "timeout": 30,
            "default_embedding_model": "text-embedding-ada-002",
            "default_llm_model": "gpt-3.5-turbo",
            "default_multimodal_model": "gpt-4-vision-preview"
        }
    
    def get_embedding_model(self, model_name: Optional[str] = None) -> EmbeddingModelConfig:
        """获取嵌入模型配置"""
        if model_name is None:
            model_name = self.global_config["default_embedding_model"]
        
        if model_name not in self.embedding_models:
            raise ValueError(f"嵌入模型 {model_name} 不存在")
        
        return self.embedding_models[model_name]
    
    def get_llm_model(self, model_name: Optional[str] = None) -> LLMModelConfig:
        """获取LLM模型配置"""
        if model_name is None:
            model_name = self.global_config["default_llm_model"]
        
        if model_name not in self.llm_models:
            raise ValueError(f"LLM模型 {model_name} 不存在")
        
        return self.llm_models[model_name]
    
    def get_multimodal_model(self, model_name: Optional[str] = None) -> MultimodalModelConfig:
        """获取多模态模型配置"""
        if model_name is None:
            model_name = self.global_config["default_multimodal_model"]
        
        if model_name not in self.multimodal_models:
            raise ValueError(f"多模态模型 {model_name} 不存在")
        
        return self.multimodal_models[model_name]
    
    def list_models(self, model_type: Optional[str] = None) -> Dict[str, Any]:
        """列出所有模型"""
        if model_type == "embedding":
            return {name: config.model_dump() for name, config in self.embedding_models.items()}
        elif model_type == "llm":
            return {name: config.model_dump() for name, config in self.llm_models.items()}
        elif model_type == "multimodal":
            return {name: config.model_dump() for name, config in self.multimodal_models.items()}
        else:
            return {
                "embedding": {name: config.model_dump() for name, config in self.embedding_models.items()},
                "llm": {name: config.model_dump() for name, config in self.llm_models.items()},
                "multimodal": {name: config.model_dump() for name, config in self.multimodal_models.items()}
            }
    
    def add_model(self, model_type: str, model_name: str, config: ModelConfig):
        """添加新模型"""
        if model_type == "embedding" and isinstance(config, EmbeddingModelConfig):
            self.embedding_models[model_name] = config
        elif model_type == "llm" and isinstance(config, LLMModelConfig):
            self.llm_models[model_name] = config
        elif model_type == "multimodal" and isinstance(config, MultimodalModelConfig):
            self.multimodal_models[model_name] = config
        else:
            raise ValueError(f"无效的模型类型或配置: {model_type}")
    
    def remove_model(self, model_type: str, model_name: str):
        """移除模型"""
        if model_type == "embedding" and model_name in self.embedding_models:
            del self.embedding_models[model_name]
        elif model_type == "llm" and model_name in self.llm_models:
            del self.llm_models[model_name]
        elif model_type == "multimodal" and model_name in self.multimodal_models:
            del self.multimodal_models[model_name]
        else:
            raise ValueError(f"模型不存在: {model_type}/{model_name}")
    
    def update_global_config(self, **kwargs):
        """更新全局配置"""
        self.global_config.update(kwargs)
    
    def get_global_config(self) -> Dict[str, Any]:
        """获取全局配置"""
        return self.global_config.copy()

# 全局模型管理器实例
model_manager = ModelManager() 