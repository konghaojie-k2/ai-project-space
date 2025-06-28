from fastapi import APIRouter

from app.api.api_v1.endpoints import health

api_router = APIRouter()

# 包含各个端点路由
api_router.include_router(health.router, prefix="/health", tags=["健康检查"]) 