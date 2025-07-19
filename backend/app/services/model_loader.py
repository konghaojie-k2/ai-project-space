"""
ModelScope模型加载器
用于加载和管理各种AI模型
"""

import os
import torch
from typing import Optional, Dict, Any, List
from pathlib import Path
from loguru import logger
import numpy as np

# ModelScope相关代码已注释 - 本机不具备使用本地大模型的条件
# try:
#     from modelscope import snapshot_download, AutoTokenizer, AutoModel, AutoModelForCausalLM
#     from modelscope.outputs import OutputKeys
#     from modelscope.pipelines import pipeline
#     from modelscope.utils.constant import Tasks
#     from transformers import AutoTokenizer as HFAutoTokenizer
#     from transformers import AutoModelForCausalLM as HFAutoModelForCausalLM
#     from transformers import AutoModel as HFAutoModel
#     MODELSCOPE_AVAILABLE = True
# except ImportError:
#     MODELSCOPE_AVAILABLE = False
#     logger.warning("ModelScope未安装，将使用备用方案")

# 禁用ModelScope功能
MODELSCOPE_AVAILABLE = False

from ..core.model_config import model_manager, EmbeddingModelConfig, LLMModelConfig, MultimodalModelConfig

class ModelLoader:
    """模型加载器"""
    
    def __init__(self):
        self.models = {}
        self.model_cache_dir = Path("./models")
        self.model_cache_dir.mkdir(exist_ok=True)
        
        # 设置ModelScope环境
        self._setup_modelscope()
    
    def _setup_modelscope(self):
        """设置ModelScope环境 - 已禁用"""
        logger.info("ModelScope功能已禁用，将使用云端API服务")
    
    def load_embedding_model(self, model_name: Optional[str] = None) -> Any:
        """加载嵌入模型"""
        try:
            if not MODELSCOPE_AVAILABLE:
                logger.warning("ModelScope不可用，使用备用嵌入模型")
                return self._load_fallback_embedding_model()
            
            config = model_manager.get_embedding_model(model_name)
            model_key = f"embedding_{model_name or 'default'}"
            
            if model_key in self.models:
                return self.models[model_key]
            
            logger.info(f"加载嵌入模型: {config.name}")
            
            # 下载模型
            model_dir = snapshot_download(
                model_id=config.model_id,
                cache_dir=self.model_cache_dir
            )
            
            # 加载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(model_dir)
            model = AutoModel.from_pretrained(
                model_dir,
                device_map=config.device,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            
            if config.normalize:
                model.eval()
            
            self.models[model_key] = {
                'model': model,
                'tokenizer': tokenizer,
                'config': config
            }
            
            logger.success(f"嵌入模型 {config.name} 加载成功")
            return self.models[model_key]
            
        except Exception as e:
            logger.error(f"加载嵌入模型失败: {e}")
            return self._load_fallback_embedding_model()
    
    def load_llm_model(self, model_name: Optional[str] = None) -> Any:
        """加载大语言模型"""
        try:
            if not MODELSCOPE_AVAILABLE:
                logger.warning("ModelScope不可用，使用备用LLM模型")
                return self._load_fallback_llm_model()
            
            config = model_manager.get_llm_model(model_name)
            model_key = f"llm_{model_name or 'default'}"
            
            if model_key in self.models:
                return self.models[model_key]
            
            logger.info(f"加载LLM模型: {config.name}")
            
            # 下载模型
            model_dir = snapshot_download(
                model_id=config.model_id,
                cache_dir=self.model_cache_dir
            )
            
            # 加载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(
                model_dir,
                trust_remote_code=True
            )
            
            model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                device_map=config.device,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                trust_remote_code=True
            )
            
            self.models[model_key] = {
                'model': model,
                'tokenizer': tokenizer,
                'config': config
            }
            
            logger.success(f"LLM模型 {config.name} 加载成功")
            return self.models[model_key]
            
        except Exception as e:
            logger.error(f"加载LLM模型失败: {e}")
            return self._load_fallback_llm_model()
    
    def load_multimodal_model(self, model_name: Optional[str] = None) -> Any:
        """加载多模态模型"""
        try:
            if not MODELSCOPE_AVAILABLE:
                logger.warning("ModelScope不可用，使用备用多模态模型")
                return self._load_fallback_multimodal_model()
            
            config = model_manager.get_multimodal_model(model_name)
            model_key = f"multimodal_{model_name or 'default'}"
            
            if model_key in self.models:
                return self.models[model_key]
            
            logger.info(f"加载多模态模型: {config.name}")
            
            # 下载模型
            model_dir = snapshot_download(
                model_id=config.model_id,
                cache_dir=self.model_cache_dir
            )
            
            # 加载tokenizer和模型
            tokenizer = AutoTokenizer.from_pretrained(
                model_dir,
                trust_remote_code=True
            )
            
            model = AutoModelForCausalLM.from_pretrained(
                model_dir,
                device_map=config.device,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                trust_remote_code=True
            )
            
            self.models[model_key] = {
                'model': model,
                'tokenizer': tokenizer,
                'config': config
            }
            
            logger.success(f"多模态模型 {config.name} 加载成功")
            return self.models[model_key]
            
        except Exception as e:
            logger.error(f"加载多模态模型失败: {e}")
            return self._load_fallback_multimodal_model()
    
    def _load_fallback_embedding_model(self) -> Any:
        """加载备用嵌入模型（sentence-transformers）"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            config = EmbeddingModelConfig(
                name="all-MiniLM-L6-v2",
                model_id="all-MiniLM-L6-v2",
                provider="sentence-transformers",
                dimension=384,
                max_length=512,
                normalize=True
            )
            
            return {
                'model': model,
                'tokenizer': None,
                'config': config
            }
        except Exception as e:
            logger.error(f"加载备用嵌入模型失败: {e}")
            return None
    
    def _load_fallback_llm_model(self) -> Any:
        """加载备用LLM模型"""
        # 这里可以实现备用LLM模型加载
        # 比如使用OpenAI API或其他本地模型
        logger.warning("备用LLM模型未实现")
        return None
    
    def _load_fallback_multimodal_model(self) -> Any:
        """加载备用多模态模型"""
        # 这里可以实现备用多模态模型加载
        logger.warning("备用多模态模型未实现")
        return None
    
    def get_embedding(self, text: str, model_name: Optional[str] = None) -> np.ndarray:
        """获取文本嵌入向量"""
        model_info = self.load_embedding_model(model_name)
        if model_info is None:
            raise ValueError("无法加载嵌入模型")
        
        model = model_info['model']
        config = model_info['config']
        
        if hasattr(model, 'encode'):
            # sentence-transformers
            embedding = model.encode(text, normalize_embeddings=config.normalize)
        else:
            # ModelScope模型
            tokenizer = model_info['tokenizer']
            inputs = tokenizer(
                text,
                max_length=config.max_length,
                padding=True,
                truncation=True,
                return_tensors='pt'
            )
            
            with torch.no_grad():
                outputs = model(**inputs)
                embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
                
                if config.normalize:
                    embedding = embedding / np.linalg.norm(embedding, axis=1, keepdims=True)
        
        return embedding
    
    def generate_text(self, prompt: str, model_name: Optional[str] = None, **kwargs) -> str:
        """生成文本"""
        model_info = self.load_llm_model(model_name)
        if model_info is None:
            raise ValueError("无法加载LLM模型")
        
        model = model_info['model']
        tokenizer = model_info['tokenizer']
        config = model_info['config']
        
        # 合并配置参数
        generation_config = {
            'max_new_tokens': config.max_new_tokens,
            'temperature': config.temperature,
            'top_p': config.top_p,
            'repetition_penalty': config.repetition_penalty,
            'do_sample': config.do_sample,
            **kwargs
        }
        
        inputs = tokenizer(prompt, return_tensors='pt')
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                **generation_config
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response[len(prompt):]  # 移除输入部分
    
    def process_multimodal(self, text: str, image_path: Optional[str] = None, model_name: Optional[str] = None) -> str:
        """处理多模态输入"""
        model_info = self.load_multimodal_model(model_name)
        if model_info is None:
            raise ValueError("无法加载多模态模型")
        
        model = model_info['model']
        tokenizer = model_info['tokenizer']
        config = model_info['config']
        
        # 这里实现多模态处理逻辑
        # 具体实现取决于模型类型
        logger.info(f"处理多模态输入: 文本={text[:50]}..., 图片={image_path}")
        
        # 临时返回
        return f"多模态处理结果: {text}"
    
    def list_loaded_models(self) -> Dict[str, Any]:
        """列出已加载的模型"""
        loaded_models = {}
        for key, model_info in self.models.items():
            loaded_models[key] = {
                'name': model_info['config'].name,
                'provider': model_info['config'].provider,
                'device': model_info['config'].device
            }
        return loaded_models
    
    def unload_model(self, model_key: str):
        """卸载模型"""
        if model_key in self.models:
            del self.models[model_key]
            logger.info(f"模型 {model_key} 已卸载")
    
    def clear_all_models(self):
        """清除所有模型"""
        self.models.clear()
        logger.info("所有模型已清除")

# 全局模型加载器实例
model_loader = ModelLoader() 