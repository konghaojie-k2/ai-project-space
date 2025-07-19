"""
模型管理API
用于管理ModelScope模型
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
    name: str
    model_id: str
    provider: str
    device: str
    enabled: bool
    dimension: Optional[int] = None
    context_length: Optional[int] = None

class ModelLoadRequest(BaseModel):
    """模型加载请求"""
    model_type: str  # "embedding", "llm", "multimodal"
    model_name: str
    force_reload: bool = False

class ModelUpdateRequest(BaseModel):
    """模型配置更新请求"""
    model_type: str
    model_name: str
    enabled: Optional[bool] = None
    device: Optional[str] = None
    temperature: Optional[float] = None
    max_length: Optional[int] = None

@router.get("/", response_model=Dict[str, Any])
async def list_models():
    """列出所有可用模型"""
    try:
        return {
            "available_models": model_manager.list_available_models(),
            "loaded_models": model_loader.list_loaded_models(),
            "default_models": model_manager.config["default_models"]
        }
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型列表失败")

@router.get("/embedding", response_model=List[ModelInfo])
async def list_embedding_models():
    """列出嵌入模型"""
    try:
        models = []
        for name, config in model_manager.config["embedding_models"].items():
            models.append(ModelInfo(
                name=config.name,
                model_id=config.model_id,
                provider=config.provider,
                device=config.device,
                enabled=config.enabled,
                dimension=config.dimension
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
        for name, config in model_manager.config["llm_models"].items():
            models.append(ModelInfo(
                name=config.name,
                model_id=config.model_id,
                provider=config.provider,
                device=config.device,
                enabled=config.enabled,
                context_length=config.context_length
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
        for name, config in model_manager.config["multimodal_models"].items():
            models.append(ModelInfo(
                name=config.name,
                model_id=config.model_id,
                provider=config.provider,
                device=config.device,
                enabled=config.enabled
            ))
        return models
    except Exception as e:
        logger.error(f"获取多模态模型列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取多模态模型列表失败")

@router.post("/load")
async def load_model(request: ModelLoadRequest):
    """加载模型"""
    try:
        model_key = f"{request.model_type}_{request.model_name}"
        
        if not request.force_reload and model_key in model_loader.models:
            return {"message": f"模型 {request.model_name} 已经加载", "status": "already_loaded"}
        
        # 根据模型类型加载
        if request.model_type == "embedding":
            model_info = model_loader.load_embedding_model(request.model_name)
        elif request.model_type == "llm":
            model_info = model_loader.load_llm_model(request.model_name)
        elif request.model_type == "multimodal":
            model_info = model_loader.load_multimodal_model(request.model_name)
        else:
            raise HTTPException(status_code=400, detail="不支持的模型类型")
        
        if model_info:
            return {
                "message": f"模型 {request.model_name} 加载成功",
                "status": "loaded",
                "model_info": {
                    "name": model_info['config'].name,
                    "provider": model_info['config'].provider,
                    "device": model_info['config'].device
                }
            }
        else:
            raise HTTPException(status_code=500, detail=f"模型 {request.model_name} 加载失败")
            
    except Exception as e:
        logger.error(f"加载模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载模型失败: {str(e)}")

@router.post("/unload/{model_key}")
async def unload_model(model_key: str):
    """卸载模型"""
    try:
        if model_key in model_loader.models:
            model_loader.unload_model(model_key)
            return {"message": f"模型 {model_key} 卸载成功", "status": "unloaded"}
        else:
            return {"message": f"模型 {model_key} 未加载", "status": "not_loaded"}
    except Exception as e:
        logger.error(f"卸载模型失败: {e}")
        raise HTTPException(status_code=500, detail="卸载模型失败")

@router.put("/config")
async def update_model_config(request: ModelUpdateRequest):
    """更新模型配置"""
    try:
        model_manager.update_model_config(
            request.model_type,
            request.model_name,
            **request.dict(exclude_unset=True, exclude={"model_type", "model_name"})
        )
        return {"message": f"模型 {request.model_name} 配置更新成功", "status": "updated"}
    except Exception as e:
        logger.error(f"更新模型配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新模型配置失败")

@router.get("/status")
async def get_model_status():
    """获取模型状态"""
    try:
        return {
            "loaded_models": model_loader.list_loaded_models(),
            "total_models": len(model_loader.models),
            "memory_usage": "N/A",  # 可以添加内存使用统计
            "gpu_usage": "N/A"      # 可以添加GPU使用统计
        }
    except Exception as e:
        logger.error(f"获取模型状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取模型状态失败")

@router.post("/test/{model_type}")
async def test_model(model_type: str, model_name: Optional[str] = None):
    """测试模型"""
    try:
        if model_type == "embedding":
            # 测试嵌入模型
            test_text = "这是一个测试文本"
            embedding = model_loader.get_embedding(test_text, model_name)
            return {
                "message": "嵌入模型测试成功",
                "test_text": test_text,
                "embedding_shape": embedding.shape,
                "embedding_sample": embedding[:5].tolist()
            }
        elif model_type == "llm":
            # 测试LLM模型
            test_prompt = "你好，请简单介绍一下自己。"
            response = model_loader.generate_text(test_prompt, model_name)
            return {
                "message": "LLM模型测试成功",
                "test_prompt": test_prompt,
                "response": response[:200] + "..." if len(response) > 200 else response
            }
        elif model_type == "multimodal":
            # 测试多模态模型
            test_text = "请描述这张图片"
            response = model_loader.process_multimodal(test_text, None, model_name)
            return {
                "message": "多模态模型测试成功",
                "test_text": test_text,
                "response": response
            }
        else:
            raise HTTPException(status_code=400, detail="不支持的模型类型")
            
    except Exception as e:
        logger.error(f"测试模型失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试模型失败: {str(e)}")

@router.delete("/clear")
async def clear_all_models():
    """清除所有模型"""
    try:
        model_loader.clear_all_models()
        return {"message": "所有模型已清除", "status": "cleared"}
    except Exception as e:
        logger.error(f"清除模型失败: {e}")
        raise HTTPException(status_code=500, detail="清除模型失败") 