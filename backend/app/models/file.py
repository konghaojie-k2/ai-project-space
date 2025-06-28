from sqlalchemy import Boolean, Column, String, Text, Integer, ForeignKey, BigInteger, Enum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class FileType(str, enum.Enum):
    """文件类型枚举"""
    DOCUMENT = "document"    # 文档类型 (pdf, docx, txt, md等)
    SPREADSHEET = "spreadsheet"  # 表格类型 (xlsx, csv等)
    PRESENTATION = "presentation"  # 演示文稿 (pptx等)
    IMAGE = "image"         # 图片类型 (jpg, png等)
    VIDEO = "video"         # 视频类型 (mp4, avi等)
    AUDIO = "audio"         # 音频类型 (mp3, wav等)
    ARCHIVE = "archive"     # 压缩文件 (zip, rar等)
    OTHER = "other"         # 其他类型


class ProcessStatus(str, enum.Enum):
    """处理状态枚举"""
    PENDING = "pending"     # 等待处理
    PROCESSING = "processing"  # 处理中
    COMPLETED = "completed"   # 处理完成
    FAILED = "failed"       # 处理失败


class ProjectFile(Base):
    """项目文件模型"""
    
    __tablename__ = "project_file"
    
    # 基本信息
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # 文件大小（字节）
    file_type = Column(Enum(FileType), nullable=False)
    mime_type = Column(String(100), nullable=True)
    
    # 文件元数据
    file_hash = Column(String(64), nullable=True)  # SHA-256哈希
    description = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)  # 逗号分隔的标签
    
    # 处理状态
    process_status = Column(Enum(ProcessStatus), default=ProcessStatus.PENDING, nullable=False)
    process_message = Column(Text, nullable=True)
    
    # 内容提取
    extracted_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    keywords = Column(String(500), nullable=True)
    
    # 向量化信息
    is_vectorized = Column(Boolean, default=False, nullable=False)
    vector_id = Column(String(100), nullable=True)  # ChromaDB中的文档ID
    
    # 关联信息
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    project_stage = Column(String(50), nullable=False)  # 所属项目阶段
    uploader_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # 访问控制
    is_public = Column(Boolean, default=False, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    
    # 关联关系
    project = relationship("Project", back_populates="files")
    uploader = relationship("User", back_populates="uploaded_files")
    
    def __repr__(self) -> str:
        return f"<ProjectFile(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"


class URLContent(Base):
    """网址内容模型"""
    
    __tablename__ = "url_content"
    
    # 基本信息
    url = Column(String(1000), nullable=False, index=True)
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    # 元数据
    content_type = Column(String(100), nullable=True)
    language = Column(String(10), nullable=True)
    author = Column(String(200), nullable=True)
    publish_date = Column(String(50), nullable=True)
    
    # 处理状态
    process_status = Column(Enum(ProcessStatus), default=ProcessStatus.PENDING, nullable=False)
    process_message = Column(Text, nullable=True)
    
    # 向量化信息
    is_vectorized = Column(Boolean, default=False, nullable=False)
    vector_id = Column(String(100), nullable=True)
    
    # 关联信息
    project_id = Column(Integer, ForeignKey("project.id"), nullable=False)
    project_stage = Column(String(50), nullable=False)
    uploader_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    
    # 关联关系
    project = relationship("Project")
    uploader = relationship("User")
    
    def __repr__(self) -> str:
        return f"<URLContent(id={self.id}, url='{self.url}', title='{self.title}')>" 