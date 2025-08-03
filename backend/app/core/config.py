from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
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
    BACKEND_PORT: int = 8000
    
    # ========================================
    # 安全配置
    # ========================================
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ========================================
    # CORS配置
    # ========================================
    BACKEND_CORS_ORIGINS: List[str] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if not v or v.strip() == "[]":
                return []
            if v.startswith("[") and v.endswith("]"):
                # 处理JSON格式的字符串
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    return []
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []
    
    # ========================================
    # 数据库配置
    # ========================================
    DATABASE_URL: Optional[str] = None
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> Any:
        if isinstance(v, str):
            return v
        # 使用SQLite进行开发测试
        return "sqlite:///./test.db"
    
    # ========================================
    # Redis配置
    # ========================================
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    
    # ========================================
    # 本地文件存储配置
    # ========================================
    UPLOAD_DIR: Path = Path("../uploads")  # 使用项目根目录
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "docx", "xlsx", "pptx", "txt", "md",
        "jpg", "jpeg", "png", "gif", "bmp",
        "mp4", "avi", "mov", "wmv",
        "mp3", "wav", "flac"
    ]
    
    # ========================================
    # ChromaDB配置
    # ========================================
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "project_documents"
    
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
    # 文件存储路径
    # ========================================
    TEMP_DIR: Path = Path("../temp")  # 使用项目根目录
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)
        Path(self.LOG_FILE).parent.mkdir(exist_ok=True)
    
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