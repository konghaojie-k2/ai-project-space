from contextlib import asynccontextmanager
# import matplotlib
# import matplotlib.pyplot as plt

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging, app_logger
from app.api.api_v1.api import api_router


# 配置matplotlib中文显示 - 暂时注释掉
# matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
# matplotlib.rcParams['axes.unicode_minus'] = False
# plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
# plt.rcParams['axes.unicode_minus'] = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    setup_logging()
    app_logger.info(f"🚀 {settings.PROJECT_NAME} v{settings.VERSION} 启动中...")
    
    # 确保必要的目录存在
    settings.UPLOAD_DIR.mkdir(exist_ok=True)
    settings.TEMP_DIR.mkdir(exist_ok=True)
    
    app_logger.info("✅ 应用启动完成")
    
    yield
    
    # 关闭时执行
    app_logger.info("🛑 应用正在关闭...")


def create_application() -> FastAPI:
    """创建FastAPI应用"""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="AI加持的项目管理系统，支持多模态内容和智能问答",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # 设置CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # 开发环境允许所有来源
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # 注册API路由
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # 静态文件服务
    # app.mount("/static", StaticFiles(directory="static"), name="static")
    # app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")
    
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": f"欢迎使用 {settings.PROJECT_NAME}",
            "version": settings.VERSION,
            "docs": "/docs",
            "api": settings.API_V1_STR
        }
    
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "healthy", "version": settings.VERSION}
    
    return app


# 创建应用实例
app = create_application() 