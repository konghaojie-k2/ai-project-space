from sqlalchemy import Boolean, Column, String, Text, Integer, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class QASession(Base):
    """问答会话模型"""
    
    __tablename__ = "qa_session"
    
    # 基本信息
    title = Column(String(200), nullable=True)  # 会话标题
    question = Column(Text, nullable=False)     # 用户问题
    answer = Column(Text, nullable=True)        # AI回答
    
    # 上下文信息
    context_files = Column(JSON, nullable=True)  # 相关文件ID列表
    context_text = Column(Text, nullable=True)   # 检索到的上下文文本
    
    # 质量评估
    rating = Column(Integer, nullable=True)      # 用户评分 (1-5)
    is_helpful = Column(Boolean, nullable=True)  # 是否有帮助
    feedback = Column(Text, nullable=True)       # 用户反馈
    
    # AI模型信息
    model_name = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    response_time = Column(Float, nullable=True)  # 响应时间（秒）
    
    # 关联信息
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # 是否已转为笔记
    is_saved_as_note = Column(Boolean, default=False, nullable=False)
    note_id = Column(Integer, ForeignKey("note.id"), nullable=True)
    
    # 关联关系
    project = relationship("Project", back_populates="qa_sessions")
    user = relationship("User", back_populates="qa_sessions")
    note = relationship("Note", back_populates="qa_session", uselist=False)
    
    def __repr__(self) -> str:
        return f"<QASession(id={self.id}, question='{self.question[:50]}...', rating={self.rating})>"


class Note(Base):
    """笔记模型"""
    
    __tablename__ = "note"
    
    # 基本信息
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # 分类和标签
    category = Column(String(100), nullable=True)
    tags = Column(String(500), nullable=True)  # 逗号分隔的标签
    
    # 来源信息
    source_type = Column(String(50), nullable=True)  # qa_session, manual, imported
    source_files = Column(JSON, nullable=True)       # 相关文件ID列表
    
    # 访问控制
    is_public = Column(Boolean, default=False, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    
    # 协作信息
    view_count = Column(Integer, default=0, nullable=False)
    like_count = Column(Integer, default=0, nullable=False)
    
    # 关联信息
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # 关联关系
    project = relationship("Project", back_populates="notes")
    author = relationship("User", back_populates="notes")
    qa_session = relationship("QASession", back_populates="note", uselist=False)
    
    def __repr__(self) -> str:
        return f"<Note(id={self.id}, title='{self.title}', author_id={self.author_id})>"


class NoteLike(Base):
    """笔记点赞模型"""
    
    __tablename__ = "note_like"
    
    note_id = Column(Integer, ForeignKey("note.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # 关联关系
    note = relationship("Note")
    user = relationship("User")
    
    def __repr__(self) -> str:
        return f"<NoteLike(note_id={self.note_id}, user_id={self.user_id})>" 