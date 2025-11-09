"""
API v1 主路由
"""

from fastapi import APIRouter
from ..chat import router as chat_router
from ..models import router as models_router
from .endpoints.files import router as files_router
from .endpoints.files_enhanced import router as files_enhanced_router
from .endpoints.files_rag import router as files_rag_router
from .endpoints.chat_rag import router as chat_rag_router
from .endpoints.auth import router as auth_router
from .endpoints.projects import router as projects_router
from .endpoints.project_members import router as project_members_router

api_router = APIRouter()

# 包含认证路由
api_router.include_router(auth_router, prefix="/auth", tags=["认证"])

# 包含聊天路由
api_router.include_router(chat_router, prefix="/chat")

# 包含模型管理路由
api_router.include_router(models_router, prefix="/models")

# 包含文件管理路由
api_router.include_router(files_router, prefix="/files")

# 包含增强文件管理路由
api_router.include_router(files_enhanced_router, prefix="/files-enhanced", tags=["增强文件管理"])

# 包含RAG文件管理路由
api_router.include_router(files_rag_router, prefix="/files", tags=["RAG文件管理"])

# 包含RAG聊天路由
api_router.include_router(chat_rag_router, prefix="/chat-rag", tags=["RAG智能问答"])

# 包含项目管理路由
api_router.include_router(projects_router, prefix="/projects", tags=["项目管理"])

# 包含项目成员管理路由
api_router.include_router(project_members_router, prefix="", tags=["项目成员管理"]) 