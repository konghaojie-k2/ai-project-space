from sqlalchemy import Boolean, Column, String, Text, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base
from app.models.user import user_project_association


class ProjectStage(str, enum.Enum):
    """项目阶段枚举"""
    PRE_SALES = "售前"
    BUSINESS_RESEARCH = "业务调研"
    DATA_UNDERSTANDING = "数据理解"
    DATA_EXPLORATION = "数据探索"
    ENGINEERING_DEVELOPMENT = "工程开发"
    IMPLEMENTATION_DEPLOYMENT = "实施部署"


class ProjectStatus(str, enum.Enum):
    """项目状态枚举"""
    DRAFT = "draft"        # 草稿
    ACTIVE = "active"      # 进行中
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"   # 已归档
    SUSPENDED = "suspended" # 暂停


class Project(Base):
    """项目模型"""
    
    __tablename__ = "project"
    
    # 基本信息
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # 项目状态
    status = Column(Enum(ProjectStatus), default=ProjectStatus.DRAFT, nullable=False)
    current_stage = Column(Enum(ProjectStage), default=ProjectStage.PRE_SALES, nullable=False)
    
    # 项目设置
    is_public = Column(Boolean, default=False, nullable=False)
    allow_file_upload = Column(Boolean, default=True, nullable=False)
    allow_ai_chat = Column(Boolean, default=True, nullable=False)
    
    # 创建者
    creator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # 关联关系
    creator = relationship("User", back_populates="created_projects", foreign_keys=[creator_id])
    
    members = relationship(
        "User",
        secondary=user_project_association,
        back_populates="projects"
    )
    
    files = relationship(
        "ProjectFile",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    qa_sessions = relationship(
        "QASession",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    notes = relationship(
        "Note",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name='{self.name}', status='{self.status}')>" 