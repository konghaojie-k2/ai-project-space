"""
项目模型
"""

from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import enum

from app.models.base import Base


class ProjectStatus(str, enum.Enum):
    """项目状态枚举"""
    ACTIVE = "active"        # 活跃
    INACTIVE = "inactive"    # 非活跃
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"    # 已归档


class ProjectStage(str, enum.Enum):
    """项目阶段枚举"""
    PRESALE = "售前"
    RESEARCH = "业务调研"
    UNDERSTANDING = "数据理解"
    EXPLORATION = "数据探索"
    DEVELOPMENT = "工程开发"
    DEPLOYMENT = "实施部署"


class Project(Base):
    """项目模型"""
    
    __tablename__ = "project"
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    
    # 状态信息
    status: Mapped[ProjectStatus] = mapped_column(String(20), default=ProjectStatus.ACTIVE, nullable=False)
    current_stage: Mapped[ProjectStage] = mapped_column(String(25), default=ProjectStage.PRESALE, nullable=False)
    
    # 权限设置
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_file_upload: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_ai_chat: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # 创建者
    creator_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, status={self.status})>"
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "stage": self.current_stage.value if isinstance(self.current_stage, ProjectStage) else self.current_stage,
            "is_public": self.is_public,
            "allow_file_upload": self.allow_file_upload,
            "allow_ai_chat": self.allow_ai_chat,
            "creator_id": self.creator_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }