from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class FileAccessLevel(str, Enum):
    """文件访问级别枚举"""
    ALL_USERS = "all_users"      # 全员可见
    ADMINS_ONLY = "admins_only"  # 仅管理员
    OWNER_ONLY = "owner_only"    # 仅上传者

class FileStage(str, Enum):
    """项目阶段枚举"""
    PRESALES = "presales"
    BUSINESS_RESEARCH = "business-research"
    DATA_UNDERSTANDING = "data-understanding"
    DATA_EXPLORATION = "data-exploration"
    ENGINEERING_DEVELOPMENT = "engineering-development"
    IMPLEMENTATION_DEPLOYMENT = "implementation-deployment"

class FileShareType(str, Enum):
    """分享类型枚举"""
    PUBLIC = "public"
    PRIVATE = "private"
    PASSWORD = "password"

class FileBase(BaseModel):
    """文件基础模式"""
    original_name: str = Field(..., description="原始文件名")
    description: Optional[str] = Field(None, description="文件描述")
    project_id: Optional[str] = Field(None, description="项目ID")
    stage: str = Field(..., description="项目阶段")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    is_public: bool = Field(False, description="是否公开")
    access_level: FileAccessLevel = Field(FileAccessLevel.ALL_USERS, description="访问级别")

class FileCreate(FileBase):
    """创建文件模式"""
    stored_name: str = Field(..., description="存储文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小")
    file_type: str = Field(..., description="文件类型")
    uploaded_by: str = Field(..., description="上传者")
    user_id: Optional[int] = Field(None, description="上传用户ID")
    
    @validator('file_size')
    def validate_file_size(cls, v):
        if v <= 0:
            raise ValueError('文件大小必须大于0')
        if v > 100 * 1024 * 1024:  # 100MB
            raise ValueError('文件大小不能超过100MB')
        return v

class FileUpdate(BaseModel):
    """更新文件模式"""
    original_name: Optional[str] = Field(None, description="原始文件名")
    description: Optional[str] = Field(None, description="文件描述")
    stage: Optional[str] = Field(None, description="项目阶段")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    is_public: Optional[bool] = Field(None, description="是否公开")

class FileResponse(FileBase):
    """文件响应模式"""
    id: str = Field(..., description="文件ID")
    stored_name: str = Field(..., description="存储文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小")
    file_type: str = Field(..., description="文件类型")
    file_extension: Optional[str] = Field(None, description="文件扩展名")
    
    # 内容信息
    content_length: Optional[int] = Field(None, description="内容长度")
    
    # 统计信息
    view_count: int = Field(0, description="查看次数")
    download_count: int = Field(0, description="下载次数")
    like_count: int = Field(0, description="点赞次数")
    
    # 状态信息
    is_processed: bool = Field(False, description="是否已处理")
    
    # 访问权限
    access_level: FileAccessLevel = Field(FileAccessLevel.ALL_USERS, description="访问级别")
    
    # 用户信息
    user_id: Optional[int] = Field(None, description="上传用户ID")
    uploaded_by: str = Field(..., description="上传者")
    updated_by: Optional[str] = Field(None, description="更新者")
    
    # 时间信息
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    # 版本信息
    version: int = Field(1, description="版本号")
    parent_id: Optional[str] = Field(None, description="父文件ID")
    
    # 元数据
    file_metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")
    
    class Config:
        from_attributes = True

class FileVersionCreate(BaseModel):
    """创建文件版本模式"""
    file_id: str = Field(..., description="文件ID")
    stored_name: str = Field(..., description="存储文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小")
    change_description: Optional[str] = Field(None, description="变更描述")
    changed_by: str = Field(..., description="变更者")

class FileVersionResponse(BaseModel):
    """文件版本响应模式"""
    id: str = Field(..., description="版本ID")
    file_id: str = Field(..., description="文件ID")
    version: int = Field(..., description="版本号")
    stored_name: str = Field(..., description="存储文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int = Field(..., description="文件大小")
    change_description: Optional[str] = Field(None, description="变更描述")
    changed_by: str = Field(..., description="变更者")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True

class FileShareCreate(BaseModel):
    """创建文件分享模式"""
    file_id: str = Field(..., description="文件ID")
    share_type: FileShareType = Field(..., description="分享类型")
    password: Optional[str] = Field(None, description="分享密码")
    can_download: bool = Field(True, description="允许下载")
    can_preview: bool = Field(True, description="允许预览")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    
    @validator('password')
    def validate_password(cls, v, values):
        if values.get('share_type') == FileShareType.PASSWORD and not v:
            raise ValueError('密码分享必须设置密码')
        return v

class FileShareResponse(BaseModel):
    """文件分享响应模式"""
    id: str = Field(..., description="分享ID")
    file_id: str = Field(..., description="文件ID")
    share_token: str = Field(..., description="分享令牌")
    share_type: FileShareType = Field(..., description="分享类型")
    can_download: bool = Field(..., description="允许下载")
    can_preview: bool = Field(..., description="允许预览")
    expires_at: Optional[datetime] = Field(None, description="过期时间")
    created_at: datetime = Field(..., description="创建时间")
    access_count: int = Field(0, description="访问次数")
    created_by: str = Field(..., description="创建者")
    
    class Config:
        from_attributes = True

class FileCommentCreate(BaseModel):
    """创建文件评论模式"""
    file_id: str = Field(..., description="文件ID")
    content: str = Field(..., min_length=1, max_length=1000, description="评论内容")
    parent_id: Optional[str] = Field(None, description="父评论ID")

class FileCommentResponse(BaseModel):
    """文件评论响应模式"""
    id: str = Field(..., description="评论ID")
    file_id: str = Field(..., description="文件ID")
    content: str = Field(..., description="评论内容")
    parent_id: Optional[str] = Field(None, description="父评论ID")
    level: int = Field(0, description="评论层级")
    author: str = Field(..., description="评论者")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True

class FileStatsResponse(BaseModel):
    """文件统计响应模式"""
    total_files: int = Field(..., description="总文件数")
    total_size: int = Field(..., description="总大小")
    files_by_stage: Dict[str, int] = Field(..., description="按阶段分组的文件数")
    files_by_type: Dict[str, int] = Field(..., description="按类型分组的文件数")
    recent_uploads: List[FileResponse] = Field(..., description="最近上传的文件")
    popular_files: List[FileResponse] = Field(..., description="热门文件")

class FileSearchRequest(BaseModel):
    """文件搜索请求模式"""
    query: Optional[str] = Field(None, description="搜索关键词")
    stage: Optional[str] = Field(None, description="项目阶段")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    file_type: Optional[str] = Field(None, description="文件类型")
    date_from: Optional[datetime] = Field(None, description="开始日期")
    date_to: Optional[datetime] = Field(None, description="结束日期")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=100, description="每页数量")
    sort_by: Optional[str] = Field("created_at", description="排序字段")
    sort_order: Optional[str] = Field("desc", description="排序方向")

class FileSearchResponse(BaseModel):
    """文件搜索响应模式"""
    files: List[FileResponse] = Field(..., description="文件列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")

class FileContentResponse(BaseModel):
    """文件内容响应模式"""
    file_id: str = Field(..., description="文件ID")
    content: str = Field(..., description="提取的内容")
    content_type: str = Field(..., description="内容类型")
    content_length: int = Field(..., description="内容长度")
    extracted_at: datetime = Field(..., description="提取时间") 