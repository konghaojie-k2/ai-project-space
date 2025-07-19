"""
API v1 主路由
"""

from fastapi import APIRouter
from ..chat import router as chat_router
from ..models import router as models_router

api_router = APIRouter()

# 包含聊天路由
api_router.include_router(chat_router, prefix="/chat")

# 包含模型管理路由
api_router.include_router(models_router, prefix="/models") 