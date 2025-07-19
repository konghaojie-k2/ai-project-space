"""
火山引擎API客户端
直接使用火山引擎的模型服务
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from loguru import logger
import numpy as np
from pathlib import Path

# 加载环境变量
try:
    from dotenv import load_dotenv
    # 从backend目录向上查找.env文件
    env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"已加载环境变量文件: {env_path}")
    else:
        logger.warning(f"未找到环境变量文件: {env_path}")
except ImportError:
    logger.warning("未安装 python-dotenv")
except Exception as e:
    logger.error(f"加载环境变量失败: {e}")

class VolcengineClient:
    """火山引擎API客户端"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3/")
        self.llm_model = os.getenv("DEFAULT_LLM_MODEL", "deepseek-v3-250324")
        self.embedding_model = os.getenv("DEFAULT_EMBEDDING_MODEL", "doubao-embedding-text-240715")
        
        if not self.api_key:
            logger.error("未配置火山引擎API密钥")
            logger.error("请检查 .env 文件中的 OPENAI_API_KEY 配置")
            # 不抛出异常，允许应用继续运行
            self.api_key = "dummy_key"
        
        logger.info(f"火山引擎客户端初始化成功")
        logger.info(f"  API地址: {self.base_url}")
        logger.info(f"  LLM模型: {self.llm_model}")
        logger.info(f"  嵌入模型: {self.embedding_model}")
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        try:
            if self.api_key == "dummy_key":
                return "抱歉，火山引擎API密钥未配置，无法生成文本。"
            
            url = f"{self.base_url}chat/completions"
            
            data = {
                "model": self.llm_model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"文本生成失败: {e}")
            return f"抱歉，生成失败: {str(e)}"
    
    def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        try:
            if self.api_key == "dummy_key":
                # 返回零向量作为备用
                return [0.0] * 2560  # 火山引擎嵌入向量维度
            
            url = f"{self.base_url}embeddings"
            
            data = {
                "model": self.embedding_model,
                "input": text
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result["data"][0]["embedding"]
            
        except Exception as e:
            logger.error(f"获取嵌入向量失败: {e}")
            # 返回零向量作为备用
            return [0.0] * 2560  # 火山引擎嵌入向量维度
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天完成"""
        try:
            if self.api_key == "dummy_key":
                return "抱歉，火山引擎API密钥未配置，无法进行聊天。"
            
            url = f"{self.base_url}chat/completions"
            
            data = {
                "model": self.llm_model,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 1000),
                "temperature": kwargs.get("temperature", 0.7),
                "stream": False
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"聊天完成失败: {e}")
            return f"抱歉，聊天失败: {str(e)}"
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            if self.api_key == "dummy_key":
                logger.warning("火山引擎API密钥未配置，无法测试连接")
                return False
            
            # 简单的测试请求
            test_prompt = "你好"
            result = self.generate_text(test_prompt, max_tokens=10)
            logger.info(f"火山引擎连接测试成功: {result}")
            return True
        except Exception as e:
            logger.error(f"火山引擎连接测试失败: {e}")
            return False

# 创建全局客户端实例
volcengine_client = VolcengineClient() 