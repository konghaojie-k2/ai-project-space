from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

from app.core.config import settings

# 创建数据库引擎
if str(settings.DATABASE_URL).startswith("sqlite"):
    # SQLite配置（开发环境）
    engine = create_engine(
        str(settings.DATABASE_URL),
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL配置（生产环境）
    engine = create_engine(
        str(settings.DATABASE_URL),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建数据库表"""
    Base.metadata.create_all(bind=engine)

def drop_tables():
    """删除数据库表"""
    Base.metadata.drop_all(bind=engine) 