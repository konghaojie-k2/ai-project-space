from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取项目根目录（backend的父目录）
# 如果当前文件在 backend/app/core/config.py，则项目根目录是 backend 的父目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),  # 使用项目根目录的.env文件
        env_file_encoding="utf-8",
        env_ignore_empty=True, 
        extra="ignore",
        case_sensitive=False
    )
    
    # ========================================
    # 项目基础配置
    # ========================================
    PROJECT_NAME: str = "AI项目管理系统"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # ========================================
    # 服务器配置
    # ========================================
    BACKEND_HOST: str = "0.0.0.0"
    FRONTEND_PORT: int = 3000
    BACKEND_PORT: int = 8001

    # ========================================
    # RAG服务配置
    # ========================================
    RAG_API_ENDPOINT: str = "http://localhost:8001"  # 独立RAG服务的API端点
    RAG_API_KEY: Optional[str] = None  # RAG服务的API密钥
    RAG_COLLECTION_NAME: str = "project_management"  # 默认知识库名称
    RAG_TIMEOUT: int = 30  # RAG服务请求超时时间（秒）
    RAG_MAX_RETRIES: int = 3  # RAG服务请求重试次数
    USE_RAG_SERVICE: bool = True  # 是否使用RAG服务
    
    # ========================================
    # 安全配置
    # ========================================
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2小时，适合开发测试
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ========================================
    # CORS配置
    # ========================================
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = Field(
        default=[],
        description="CORS允许的源列表，支持逗号分隔的字符串或JSON数组格式"
    )
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        """处理CORS配置，支持多种格式"""
        if v is None:
            return []
        
        # 如果已经是列表，直接返回
        if isinstance(v, list):
            return v
        
        # 处理字符串格式
        if isinstance(v, str):
            v = v.strip()
            # 处理空字符串
            if not v or v == "[]" or v == "":
                return []
            
            # 尝试解析JSON格式（如果值以[开头和]结尾）
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    result = json.loads(v)
                    return result if isinstance(result, list) else []
                except (json.JSONDecodeError, TypeError, ValueError):
                    # JSON解析失败，尝试作为逗号分隔的字符串处理
                    v = v.strip("[]")
            
            # 作为逗号分隔的字符串处理
            return [i.strip() for i in v.split(",") if i.strip()]
        
        # 其他类型，返回空列表
        return []
    
    # ========================================
    # 数据库配置（已废弃，使用 Supabase）
    # ========================================
    # 注意：项目已完全迁移到 Supabase，不再使用本地数据库
    # DATABASE_URL 保留仅为兼容性，实际不会被使用
    DATABASE_URL: Optional[str] = None

    # ========================================
    # Supabase配置
    # ========================================
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None  # Anon Key (用于客户端操作，如用户登录/注册)
    SUPABASE_ANON_KEY: Optional[str] = None  # Anon Key的别名
    SUPABASE_SERVICE_KEY: Optional[str] = None  # Service Key (用于服务端管理操作)
    
    # ========================================
    # Redis配置
    # ========================================
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    
    # ========================================
    # 本地文件存储配置 (已废弃，使用Supabase Storage)
    # ========================================
    # 注意：项目已完全迁移到 Supabase Storage，不再使用本地存储
    # UPLOAD_DIR 保留仅为兼容性，实际不会被使用
    UPLOAD_DIR: Path = Path("../uploads")  # 已废弃，使用Supabase Storage
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB (Supabase Storage限制)
    ALLOWED_FILE_TYPES: Union[str, List[str]] = Field(
        default=[
            "pdf", "docx", "xlsx", "pptx", "txt", "md",
            "jpg", "jpeg", "png", "gif", "bmp",
            "mp4", "avi", "mov", "wmv",
            "mp3", "wav", "flac"
        ],
        description="允许的文件类型列表，支持逗号分隔的字符串或JSON数组格式"
    )
    
    @field_validator("ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def assemble_file_types(cls, v: Any) -> List[str]:
        """处理文件类型配置，支持多种格式"""
        if v is None:
            return []
        
        # 如果已经是列表，直接返回
        if isinstance(v, list):
            return v
        
        # 处理字符串格式
        if isinstance(v, str):
            v = v.strip()
            # 处理空字符串
            if not v or v == "[]" or v == "":
                return []
            
            # 尝试解析JSON格式（如果值以[开头和]结尾）
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    result = json.loads(v)
                    return result if isinstance(result, list) else []
                except (json.JSONDecodeError, TypeError, ValueError):
                    # JSON解析失败，尝试作为逗号分隔的字符串处理
                    v = v.strip("[]")
            
            # 作为逗号分隔的字符串处理
            return [i.strip() for i in v.split(",") if i.strip()]
        
        # 其他类型，返回空列表
        return []
    
    # ========================================
    # 向量数据库配置 (替换ChromaDB)
    # ========================================
    VECTOR_DIMENSION: int = 1536  # OpenAI embedding维度
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    VECTOR_SIMILARITY_THRESHOLD: float = 0.7

    # ChromaDB配置 (保留向后兼容，将逐步移除)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "project_documents"

    # ========================================
    # Supabase Storage配置 (替换MinIO)
    # ========================================
    STORAGE_BUCKET: str = "project-files"
    STORAGE_MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    
    # ========================================
    # AI模型配置
    # ========================================
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_LLM_MODEL: str = "gpt-3.5-turbo"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # ========================================
    # 邮件配置
    # ========================================
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    # 开发环境邮件验证设置
    DISABLE_EMAIL_VERIFICATION: bool = True  # 开发环境禁用邮件验证
    
    # ========================================
    # 日志配置
    # ========================================
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    LOG_FILE: str = "logs/app.log"
    
    # ========================================
    # 开发工具配置
    # ========================================
    ENABLE_HOT_RELOAD: bool = True
    DEBUG: bool = False
    VERBOSE_LOGGING: bool = False
    
    # ========================================
    # 项目阶段配置
    # ========================================
    PROJECT_STAGES: List[str] = [
        "售前",
        "业务调研", 
        "数据理解",
        "数据探索",
        "工程开发",
        "实施部署"
    ]
    
    # ========================================
    # 用户角色配置
    # ========================================
    USER_ROLES: List[str] = [
        "admin",      # 系统管理员
        "manager",    # 项目管理员
        "member",     # 项目成员
        "viewer"      # 访客
    ]
    
    # ========================================
    # 文件存储路径 (已废弃，使用Supabase Storage)
    # ========================================
    TEMP_DIR: Path = Path("../temp")  # 已废弃，使用Supabase Storage

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 强制设置API_V1_STR为正确的值（防止环境变量干扰）
        if not hasattr(self, 'API_V1_STR') or not self.API_V1_STR.startswith("/"):
            self.API_V1_STR = "/api/v1"

        # 只确保日志目录存在，其他目录已废弃
        Path(self.LOG_FILE).parent.mkdir(exist_ok=True)

        # 注释：不再创建本地存储目录，使用Supabase Storage
        # self.UPLOAD_DIR.mkdir(exist_ok=True)  # 已废弃
        # self.TEMP_DIR.mkdir(exist_ok=True)    # 已废弃
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境"""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """是否为测试环境"""
        return self.ENVIRONMENT.lower() == "testing"

    @property
    def use_supabase(self) -> bool:
        """是否使用Supabase"""
        # 检查必需的Supabase配置：URL和至少一个Key
        # Anon Key用于用户认证操作，Service Key用于管理员操作
        anon_key = self.SUPABASE_ANON_KEY or self.SUPABASE_KEY
        return self.SUPABASE_URL is not None and (anon_key is not None or self.SUPABASE_SERVICE_KEY is not None)
    
    @property
    def supabase_anon_key(self) -> Optional[str]:
        """获取Supabase Anon Key"""
        return self.SUPABASE_ANON_KEY or self.SUPABASE_KEY
    
    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的源"""
        if self.is_development:
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3001"
            ]
        return [str(origin) for origin in self.BACKEND_CORS_ORIGINS]


settings = Settings() 