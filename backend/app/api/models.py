"""
AI模型管理API
管理云端AI模型配置和状态
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from loguru import logger

from ..services.model_loader import model_loader
from ..core.model_config import model_manager

router = APIRouter(prefix="/models", tags=["模型管理"])

class ModelInfo(BaseModel):
    """模型信息"""
    model_name: str
    provider: str
    description: str
    max_tokens: Optional[int] = None
    embedding_size: Optional[int] = None
    context_length: Optional[int] = None
    supported_formats: Optional[List[str]] = None
    enabled: bool = True

class ModelTestRequest(BaseModel):
    """模型测试请求"""
    model_type: str  # "embedding", "llm", "multimodal"
    model_name: Optional[str] = None
    test_input: Optional[str] = None

@router.get("/", response_model=Dict[str, Any])
async def list_all_models():
    """列出所有可用模型"""
    try:
        return {
            "available_models": model_manager.list_models(),
            "loaded_models": model_loader.list_loaded_models(),
            "global_config": model_manager.get_global_config()
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")

@router.get("/embedding", response_model=List[ModelInfo])
async def list_embedding_models():
    """列出嵌入模型"""
    try:
        models = []
        embedding_models = model_manager.list_models("embedding")
        
        for name, config in embedding_models.items():
            models.append(ModelInfo(
                model_name=config["model_name"],
                provider=config["provider"],
                description=config["description"],
                embedding_size=config["embedding_size"],
                max_tokens=config.get("max_input_tokens"),
                enabled=config["enabled"]
            ))
        return models
    except Exception as e:
        logger.error(f"获取嵌入模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取嵌入模型列表失败")

@router.get("/llm", response_model=List[ModelInfo])
async def list_llm_models():
    """列出大语言模型"""
    try:
        models = []
        llm_models = model_manager.list_models("llm")
        
        for name, config in llm_models.items():
            models.append(ModelInfo(
                model_name=config["model_name"],
                provider=config["provider"],
                description=config["description"],
                max_tokens=config["max_tokens"],
                context_length=config["context_length"],
                enabled=config["enabled"]
            ))
        return models
    except Exception as e:
        logger.error(f"获取LLM模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取LLM模型列表失败")

@router.get("/multimodal", response_model=List[ModelInfo])
async def list_multimodal_models():
    """列出多模态模型"""
    try:
        models = []
        multimodal_models = model_manager.list_models("multimodal")
        
        for name, config in multimodal_models.items():
            models.append(ModelInfo(
                model_name=config["model_name"],
                provider=config["provider"],
                description=config["description"],
                max_tokens=config["max_tokens"],
                context_length=config["context_length"],
                supported_formats=config["supported_formats"],
                enabled=config["enabled"]
            ))
        return models
    except Exception as e:
        logger.error(f"获取多模态模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取多模态模型列表失败")

@router.post("/load/{model_type}")
async def load_model(model_type: str, model_name: Optional[str] = None):
    """加载云端模型服务"""
    try:
        if model_type not in ["embedding", "llm", "multimodal"]:
            raise HTTPException(status_code=400, detail="不支持的模型类型")
        
        model = model_loader.get_model(model_type, model_name)
        if model:
            model_info = model_loader.get_model_info(model_type, model_name)
            return {
                "message": f"云端{model_type}模型准备就绪",
                "status": "ready",
                "model_info": model_info
            }
        else:
            raise HTTPException(status_code=500, detail=f"模型初始化失败")
            
    except Exception as e:
        logger.error(f"准备模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"准备模型失败: {str(e)}")

@router.delete("/unload/{model_type}")
async def unload_model(model_type: str, model_name: Optional[str] = None):
    """卸载模型"""
    try:
        model_loader.unload_model(model_type, model_name)
        return {
            "message": f"模型 {model_type}/{model_name} 卸载成功",
            "status": "unloaded"
        }
    except Exception as e:
        logger.error(f"卸载模型失败: {e}")
        raise HTTPException(status_code=500, detail="卸载模型失败")

@router.get("/status")
async def get_model_status():
    """获取模型状态"""
    try:
        health_check = model_loader.health_check()
        return {
            "loaded_models": health_check["model_list"],
            "total_loaded": health_check["loaded_models"],
            "mode": health_check["mode"],
            "status": health_check["status"],
            "cache_dir": health_check["cache_dir"]
        }
    except Exception as e:
        logger.error(f"获取模型状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型状态失败")

@router.post("/test")
async def test_model(request: ModelTestRequest):
    """测试模型功能"""
    try:
        model_type = request.model_type
        model_name = request.model_name
        test_input = request.test_input or "测试输入"
        
        if model_type == "embedding":
            # 测试嵌入模型
            model = model_loader.get_model("embedding", model_name)
            if model:
                # 模拟嵌入测试
                test_texts = [test_input]
                embeddings = model.encode(test_texts)
                return {
                    "message": "嵌入模型测试成功",
                    "model_name": model.model_name,
                    "test_input": test_input,
                    "embedding_shape": embeddings.shape,
                    "embedding_sample": embeddings[0][:5].tolist()
                }
            else:
                raise HTTPException(status_code=404, detail="嵌入模型未找到")
                
        elif model_type == "llm":
            # 测试LLM模型
            model = model_loader.get_model("llm", model_name)
            if model:
                response = model.generate(test_input)
                return {
                    "message": "LLM模型测试成功",
                    "model_name": model.model_name,
                    "test_input": test_input,
                    "response": response[:200] + "..." if len(response) > 200 else response
                }
            else:
                raise HTTPException(status_code=404, detail="LLM模型未找到")
                
        elif model_type == "multimodal":
            # 测试多模态模型
            model = model_loader.get_model("multimodal", model_name)
            if model:
                response = model.process_multimodal({"text": test_input})
                return {
                    "message": "多模态模型测试成功",
                    "model_name": model.model_name,
                    "test_input": test_input,
                    "response": response
                }
            else:
                raise HTTPException(status_code=404, detail="多模态模型未找到")
        else:
            raise HTTPException(status_code=400, detail="不支持的模型类型")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试模型失败: {str(e)}")

@router.get("/info/{model_type}")
async def get_model_info(model_type: str, model_name: Optional[str] = None):
    """获取模型详细信息"""
    try:
        if model_type not in ["embedding", "llm", "multimodal"]:
            raise HTTPException(status_code=400, detail="不支持的模型类型")
        
        model_info = model_loader.get_model_info(model_type, model_name)
        if model_info:
            return model_info
        else:
            raise HTTPException(status_code=404, detail="模型信息未找到")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型信息失败")

@router.put("/config")
async def update_global_config(**config_updates):
    """更新全局配置"""
    try:
        model_manager.update_global_config(**config_updates)
        return {
            "message": "全局配置更新成功",
            "status": "updated",
            "config": model_manager.get_global_config()
        }
    except Exception as e:
        logger.error(f"更新全局配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新全局配置失败")

@router.get("/health")
async def health_check():
    """模型服务健康检查"""
    try:
        return model_loader.health_check()
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败") 