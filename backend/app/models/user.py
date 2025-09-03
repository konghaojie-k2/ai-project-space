from sqlalchemy import Boolean, String, Text, Table, ForeignKey, Column
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Optional, List

from app.models.base import Base


# 用户-项目关联表 - 暂时注释掉以避免外键关系问题
# user_project_association = Table(
#     'user_project_association',
#     Base.metadata,
#     Column('user_id', ForeignKey('user.id'), primary_key=True),
#     Column('project_id', ForeignKey('project.id'), primary_key=True),
#     Column('role', String(50), default='member')  # admin, manager, member, viewer
# )


class User(Base):
    """用户模型"""
    
    __tablename__ = "user"
    
    # 基本信息
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # 认证信息
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # 个人设置
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # 关联关系 - 暂时注释掉以避免循环导入问题
    # projects = relationship(
    #     "Project",
    #     secondary=user_project_association,
    #     back_populates="members"
    # )
    
    # created_projects = relationship(
    #     "Project",
    #     back_populates="creator",
    #     foreign_keys="Project.creator_id"
    # )
    
    # uploaded_files = relationship(
    #     "FileRecord",
    #     back_populates="uploader"
    # )
    
    # qa_sessions = relationship(
    #     "QASession",
    #     back_populates="user"
    # )
    
    # notes = relationship(
    #     "Note",
    #     back_populates="author"
    # )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>" 