import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time
import traceback

from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging, app_logger
from app.api.api_v1.api import api_router
from app.services.ai_service import ai_service


# 配置matplotlib中文显示 - 暂时注释掉
# matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
# matplotlib.rcParams['axes.unicode_minus'] = False
# plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
# plt.rcParams['axes.unicode_minus'] = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        app_logger.info("🚀 AI项目管理系统 v0.1.0 启动中...")
        app_logger.info("✅ 应用启动完成")
        yield
    except Exception as e:
        app_logger.error(f"❌ 应用启动失败: {e}")
        raise
    finally:
        app_logger.info("🛑 应用正在关闭...")


def create_application() -> FastAPI:
    """创建FastAPI应用"""
    
    app = FastAPI(
        title="AI项目管理系统",
        description="AI加持的项目管理系统，支持多模态内容和智能问答",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/api/v1/openapi.json",
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
    
    # 添加请求日志中间件
    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        start_time = time.time()
        
        # 只对文件上传请求记录关键信息
        if request.url.path == "/api/v1/files/upload":
            app_logger.info(f"文件上传请求 - Content-Type: {request.headers.get('content-type')}")
            app_logger.info(f"文件上传请求 - Content-Length: {request.headers.get('content-length')}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 只对错误状态码或慢请求记录日志
            if response.status_code >= 400 or process_time > 1.0:
                app_logger.warning(f"请求异常: {request.method} {request.url} - {response.status_code}, 耗时: {process_time:.4f}s")
            
            return response
        except Exception as e:
            process_time = time.time() - start_time
            app_logger.error(f"🔥🔥 请求处理异常: {str(e)}")
            app_logger.error(f"🔥🔥 异常堆栈: {traceback.format_exc()}")
            raise

    # 添加422错误处理器
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        app_logger.error(f"🔥🔥 422验证错误 - 请求路径: {request.url}")
        app_logger.error(f"🔥🔥 422验证错误 - 错误详情: {exc.errors()}")
        app_logger.error(f"🔥🔥 422验证错误 - 错误消息: {str(exc)}")
        
        # 对于文件上传的特殊处理
        if request.url.path == "/api/v1/files/upload":
            app_logger.error(f"🔥🔥 文件上传422错误 - Content-Type: {request.headers.get('content-type')}")
            try:
                form_data = await request.form()
                app_logger.error(f"🔥🔥 文件上传422错误 - 表单数据: {dict(form_data)}")
            except Exception as form_e:
                app_logger.error(f"🔥🔥 无法读取表单数据: {str(form_e)}")
        
        # 清理错误信息，确保可以JSON序列化
        cleaned_errors = []
        for error in exc.errors():
            cleaned_error = {
                "type": error.get("type"),
                "loc": error.get("loc"),
                "msg": error.get("msg"),
                "input": str(error.get("input", "")) if error.get("input") is not None else "",
                "ctx": {k: str(v) for k, v in error.get("ctx", {}).items()} if error.get("ctx") else {}
            }
            cleaned_errors.append(cleaned_error)
        
        return JSONResponse(
            status_code=422,
            content={"detail": cleaned_errors}
        )
    
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


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 启动AI项目管理系统后端服务...")
    print(f"📍 API文档: http://localhost:{settings.BACKEND_PORT}/docs")
    print(f"🔗 健康检查: http://localhost:{settings.BACKEND_PORT}/health")
    print(f"🌐 API基础路径: http://localhost:{settings.BACKEND_PORT}{settings.API_V1_STR}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
        access_log=True
    ) 