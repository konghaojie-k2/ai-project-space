from sqlalchemy import Boolean, Column, String, Text, Table, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


# 用户-项目关联表
user_project_association = Table(
    'user_project_association',
    Base.metadata,
    Column('user_id', ForeignKey('user.id'), primary_key=True),
    Column('project_id', ForeignKey('project.id'), primary_key=True),
    Column('role', String(50), default='member')  # admin, manager, member, viewer
)


class User(Base):
    """用户模型"""
    
    __tablename__ = "user"
    
    # 基本信息
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # 认证信息
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # 个人设置
    bio = Column(Text, nullable=True)
    phone = Column(String(20), nullable=True)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    
    # 关联关系
    projects = relationship(
        "Project",
        secondary=user_project_association,
        back_populates="members"
    )
    
    created_projects = relationship(
        "Project",
        back_populates="creator",
        foreign_keys="Project.creator_id"
    )
    
    uploaded_files = relationship(
        "ProjectFile",
        back_populates="uploader"
    )
    
    qa_sessions = relationship(
        "QASession",
        back_populates="user"
    )
    
    notes = relationship(
        "Note",
        back_populates="author"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>" 