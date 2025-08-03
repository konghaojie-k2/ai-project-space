from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, Boolean, BigInteger
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional
import uuid

from app.core.database import Base

class FileRecord(Base):
    """文件记录模型"""
    __tablename__ = "files"
    
    # 基本信息
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_name = Column(String, nullable=False, comment="原始文件名")
    stored_name = Column(String, nullable=False, comment="存储文件名")
    file_path = Column(String, nullable=False, comment="文件路径")
    
    # 文件属性
    file_size = Column(BigInteger, nullable=False, comment="文件大小（字节）")
    file_type = Column(String, nullable=False, comment="文件类型")
    file_extension = Column(String, comment="文件扩展名")
    
    # 项目相关
    project_id = Column(String, comment="项目ID")
    stage = Column(String, nullable=False, comment="项目阶段")
    tags = Column(JSON, default=list, comment="标签列表")
    description = Column(Text, comment="文件描述")
    
    # 内容信息
    content = Column(Text, comment="提取的文件内容")
    content_type = Column(String, comment="内容类型")
    content_length = Column(Integer, comment="内容长度")
    
    # 统计信息
    view_count = Column(Integer, default=0, comment="查看次数")
    download_count = Column(Integer, default=0, comment="下载次数")
    like_count = Column(Integer, default=0, comment="点赞次数")
    
    # 状态信息
    is_public = Column(Boolean, default=False, comment="是否公开")
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    is_processed = Column(Boolean, default=False, comment="是否已处理")
    
    # 用户信息
    uploaded_by = Column(String, nullable=False, comment="上传者")
    updated_by = Column(String, comment="更新者")
    
    # 时间信息
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 版本信息
    version = Column(Integer, default=1, comment="版本号")
    parent_id = Column(String, comment="父文件ID")
    
    # 元数据
    file_metadata = Column(JSON, default=lambda: {}, comment="额外元数据")
    
    def __repr__(self):
        return f"<FileRecord(id={self.id}, name={self.original_name})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "original_name": self.original_name,
            "stored_name": self.stored_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "file_extension": self.file_extension,
            "stage": self.stage,
            "tags": self.tags,
            "description": self.description,
            "content_length": self.content_length,
            "view_count": self.view_count,
            "download_count": self.download_count,
            "like_count": self.like_count,
            "is_public": self.is_public,
            "is_deleted": self.is_deleted,
            "is_processed": self.is_processed,
            "uploaded_by": self.uploaded_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "parent_id": self.parent_id,
            "file_metadata": self.file_metadata
        }

class FileVersion(Base):
    """文件版本模型"""
    __tablename__ = "file_versions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, nullable=False, comment="文件ID")
    version = Column(Integer, nullable=False, comment="版本号")
    
    # 版本信息
    stored_name = Column(String, nullable=False, comment="存储文件名")
    file_path = Column(String, nullable=False, comment="文件路径")
    file_size = Column(BigInteger, nullable=False, comment="文件大小")
    
    # 变更信息
    change_description = Column(Text, comment="变更描述")
    changed_by = Column(String, nullable=False, comment="变更者")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    def __repr__(self):
        return f"<FileVersion(id={self.id}, file_id={self.file_id}, version={self.version})>"

class FileShare(Base):
    """文件分享模型"""
    __tablename__ = "file_shares"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, nullable=False, comment="文件ID")
    
    # 分享信息
    share_token = Column(String, nullable=False, unique=True, comment="分享令牌")
    share_type = Column(String, nullable=False, comment="分享类型")  # public, private, password
    password = Column(String, comment="分享密码")
    
    # 权限控制
    can_download = Column(Boolean, default=True, comment="允许下载")
    can_preview = Column(Boolean, default=True, comment="允许预览")
    
    # 时间控制
    expires_at = Column(DateTime, comment="过期时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    
    # 统计信息
    access_count = Column(Integer, default=0, comment="访问次数")
    
    # 创建者
    created_by = Column(String, nullable=False, comment="创建者")
    
    def __repr__(self):
        return f"<FileShare(id={self.id}, file_id={self.file_id})>"
    
    def is_expired(self):
        """检查是否过期"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

class FileComment(Base):
    """文件评论模型"""
    __tablename__ = "file_comments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_id = Column(String, nullable=False, comment="文件ID")
    
    # 评论内容
    content = Column(Text, nullable=False, comment="评论内容")
    
    # 评论层级
    parent_id = Column(String, comment="父评论ID")
    level = Column(Integer, default=0, comment="评论层级")
    
    # 评论者信息
    author = Column(String, nullable=False, comment="评论者")
    
    # 时间信息
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 状态信息
    is_deleted = Column(Boolean, default=False, comment="是否删除")
    
    def __repr__(self):
        return f"<FileComment(id={self.id}, file_id={self.file_id})>" 