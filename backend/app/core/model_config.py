"""
模型配置文件
使用ModelScope管理各种AI模型
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path
import os

class ModelConfig(BaseModel):
    """模型配置基类"""
    name: str
    model_id: str
    provider: str = "modelscope"  # modelscope, openai, local
    device: str = "auto"  # auto, cpu, cuda, mps
    max_length: int = 2048
    temperature: float = 0.7
    top_p: float = 1.0
    enabled: bool = True

class EmbeddingModelConfig(ModelConfig):
    """嵌入模型配置"""
    dimension: int = 1024
    max_length: int = 512
    normalize: bool = True

class LLMModelConfig(ModelConfig):
    """大语言模型配置"""
    context_length: int = 4096
    max_new_tokens: int = 1024
    repetition_penalty: float = 1.1
    do_sample: bool = True

class MultimodalModelConfig(ModelConfig):
    """多模态模型配置"""
    vision_model: Optional[str] = None
    audio_model: Optional[str] = None
    max_image_size: int = 1024
    max_audio_length: int = 30  # 秒

class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载模型配置"""
        return {
            "embedding_models": {
                "qwen3_embedding_8b": EmbeddingModelConfig(
                    name="Qwen3-Embedding-8B",
                    model_id="qwen/Qwen3-Embedding-8B",
                    provider="modelscope",
                    device="auto",
                    dimension=1024,
                    max_length=512,
                    normalize=True,
                    enabled=True
                ),
                "bge_large_zh": EmbeddingModelConfig(
                    name="BGE-Large-ZH",
                    model_id="BAAI/bge-large-zh-v1.5",
                    provider="modelscope",
                    device="auto",
                    dimension=1024,
                    max_length=512,
                    normalize=True,
                    enabled=True
                ),
                "text2vec_chinese": EmbeddingModelConfig(
                    name="Text2Vec-Chinese",
                    model_id="shibing624/text2vec-base-chinese",
                    provider="modelscope",
                    device="auto",
                    dimension=768,
                    max_length=512,
                    normalize=True,
                    enabled=True
                )
            },
            "llm_models": {
                "qwen2_7b": LLMModelConfig(
                    name="Qwen2-7B",
                    model_id="qwen/Qwen2-7B-Instruct",
                    provider="modelscope",
                    device="auto",
                    context_length=32768,
                    max_new_tokens=1024,
                    temperature=0.7,
                    top_p=1.0,
                    repetition_penalty=1.1,
                    do_sample=True,
                    enabled=True
                ),
                "qwen2_14b": LLMModelConfig(
                    name="Qwen2-14B",
                    model_id="qwen/Qwen2-14B-Instruct",
                    provider="modelscope",
                    device="auto",
                    context_length=32768,
                    max_new_tokens=1024,
                    temperature=0.7,
                    top_p=1.0,
                    repetition_penalty=1.1,
                    do_sample=True,
                    enabled=False  # 默认禁用，需要更多显存
                ),
                "chatglm3_6b": LLMModelConfig(
                    name="ChatGLM3-6B",
                    model_id="ZhipuAI/chatglm3-6b",
                    provider="modelscope",
                    device="auto",
                    context_length=8192,
                    max_new_tokens=1024,
                    temperature=0.7,
                    top_p=1.0,
                    repetition_penalty=1.1,
                    do_sample=True,
                    enabled=True
                )
            },
            "multimodal_models": {
                "qwen_vl_7b": MultimodalModelConfig(
                    name="Qwen-VL-7B",
                    model_id="qwen/Qwen-VL-Chat",
                    provider="modelscope",
                    device="auto",
                    max_image_size=1024,
                    max_audio_length=30,
                    enabled=True
                ),
                "llava_1_5_7b": MultimodalModelConfig(
                    name="LLaVA-1.5-7B",
                    model_id="llava-hf/llava-1.5-7b-hf",
                    provider="modelscope",
                    device="auto",
                    max_image_size=1024,
                    max_audio_length=30,
                    enabled=True
                )
            },
            "default_models": {
                "embedding": "qwen3_embedding_8b",
                "llm": "qwen2_7b",
                "multimodal": "qwen_vl_7b"
            },
            "model_cache_dir": "./models",
            "download_mirror": "https://modelscope.cn/api/v1/models",
            "enable_hf_mirror": True
        }
    
    def get_embedding_model(self, model_name: Optional[str] = None) -> EmbeddingModelConfig:
        """获取嵌入模型配置"""
        if model_name is None:
            model_name = self.config["default_models"]["embedding"]
        return self.config["embedding_models"][model_name]
    
    def get_llm_model(self, model_name: Optional[str] = None) -> LLMModelConfig:
        """获取大语言模型配置"""
        if model_name is None:
            model_name = self.config["default_models"]["llm"]
        return self.config["llm_models"][model_name]
    
    def get_multimodal_model(self, model_name: Optional[str] = None) -> MultimodalModelConfig:
        """获取多模态模型配置"""
        if model_name is None:
            model_name = self.config["default_models"]["multimodal"]
        return self.config["multimodal_models"][model_name]
    
    def list_available_models(self) -> Dict[str, Any]:
        """列出所有可用模型"""
        return {
            "embedding_models": {
                name: config.dict() 
                for name, config in self.config["embedding_models"].items() 
                if config.enabled
            },
            "llm_models": {
                name: config.dict() 
                for name, config in self.config["llm_models"].items() 
                if config.enabled
            },
            "multimodal_models": {
                name: config.dict() 
                for name, config in self.config["multimodal_models"].items() 
                if config.enabled
            }
        }
    
    def update_model_config(self, model_type: str, model_name: str, **kwargs):
        """更新模型配置"""
        if model_type == "embedding":
            if model_name in self.config["embedding_models"]:
                for key, value in kwargs.items():
                    if hasattr(self.config["embedding_models"][model_name], key):
                        setattr(self.config["embedding_models"][model_name], key, value)
        elif model_type == "llm":
            if model_name in self.config["llm_models"]:
                for key, value in kwargs.items():
                    if hasattr(self.config["llm_models"][model_name], key):
                        setattr(self.config["llm_models"][model_name], key, value)
        elif model_type == "multimodal":
            if model_name in self.config["multimodal_models"]:
                for key, value in kwargs.items():
                    if hasattr(self.config["multimodal_models"][model_name], key):
                        setattr(self.config["multimodal_models"][model_name], key, value)

# 全局模型管理器实例
model_manager = ModelManager() 