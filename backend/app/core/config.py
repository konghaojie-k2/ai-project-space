from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    
    # 项目基础配置
    PROJECT_NAME: str = "AI项目管理系统"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # 服务器配置
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # 数据库配置
    DATABASE_URL: Optional[str] = None
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> Any:
        if isinstance(v, str):
            return v
        # 使用SQLite进行开发测试
        return "sqlite:///./test.db"
    
    # Redis配置
    REDIS_URL: str = "redis://:redis123@localhost:6379/0"
    
    # MinIO配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_NAME: str = "ai-project-files"
    
    # ChromaDB配置
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION_NAME: str = "project_documents"
    
    # AI模型配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_LLM_MODEL: str = "gpt-3.5-turbo"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    # 文件上传配置
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_FILE_TYPES: List[str] = [
        "pdf", "docx", "xlsx", "pptx", "txt", "md",
        "jpg", "jpeg", "png", "gif", "bmp",
        "mp4", "avi", "mov", "wmv",
        "mp3", "wav", "flac"
    ]
    
    # JWT配置
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # 邮件配置
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # 项目阶段配置
    PROJECT_STAGES: List[str] = [
        "售前",
        "业务调研", 
        "数据理解",
        "数据探索",
        "工程开发",
        "实施部署"
    ]
    
    # 用户角色配置
    USER_ROLES: List[str] = [
        "admin",      # 系统管理员
        "manager",    # 项目管理员
        "member",     # 项目成员
        "viewer"      # 访客
    ]
    
    # 文件存储路径
    UPLOAD_DIR: Path = Path("uploads")
    TEMP_DIR: Path = Path("temp")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保目录存在
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)
        Path(self.LOG_FILE).parent.mkdir(exist_ok=True)


settings = Settings() 