#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
增强文件管理相关的Pydantic模型
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from .file import FileResponse


class FileShareRequest(BaseModel):
    """文件分享请求"""
    user_email: EmailStr = Field(..., description="目标用户邮箱")
    can_view: bool = Field(default=True, description="是否可以查看")
    can_download: bool = Field(default=False, description="是否可以下载")
    can_edit: bool = Field(default=False, description="是否可以编辑")
    expires_at: Optional[datetime] = Field(None, description="过期时间")


class FileSearchRequest(BaseModel):
    """文件搜索请求"""
    query: str = Field(..., min_length=1, max_length=100, description="搜索关键词")
    project_id: Optional[str] = Field(None, description="项目ID过滤")
    file_type: Optional[str] = Field(None, description="文件类型过滤")
    limit: Optional[int] = Field(20, ge=1, le=100, description="返回数量限制")


class FileStatsResponse(BaseModel):
    """文件统计响应"""
    total_files: int = Field(..., description="文件总数")
    total_size: int = Field(..., description="总大小（字节）")
    by_type: Dict[str, int] = Field(default_factory=dict, description="按类型统计")
    by_project: Dict[str, int] = Field(default_factory=dict, description="按项目统计")


class FileMetadataUpdate(BaseModel):
    """文件元数据更新"""
    description: Optional[str] = Field(None, max_length=500, description="文件描述")
    tags: Optional[List[str]] = Field(None, description="文件标签")
    custom_fields: Optional[Dict[str, Any]] = Field(None, description="自定义字段")


class FileBatchOperation(BaseModel):
    """批量文件操作"""
    file_ids: List[str] = Field(..., min_items=1, max_items=100, description="文件ID列表")
    operation: str = Field(..., regex="^(delete|share|archive|unarchive)$", description="操作类型")
    operation_params: Optional[Dict[str, Any]] = Field(None, description="操作参数")


class FileVersionInfo(BaseModel):
    """文件版本信息"""
    id: str
    file_id: str
    version_number: int
    size: int
    created_by: str
    created_at: datetime
    changes_description: Optional[str] = None


class FileComment(BaseModel):
    """文件评论"""
    id: Optional[str] = None
    file_id: str
    user_id: str
    username: str
    avatar_url: Optional[str] = None
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parent_id: Optional[str] = None


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    success: bool
    message: str
    file_id: Optional[str] = None
    url: Optional[str] = None
    size: Optional[int] = None
    content_type: Optional[str] = None


class FilePreviewRequest(BaseModel):
    """文件预览请求"""
    file_id: str = Field(..., description="文件ID")
    max_width: Optional[int] = Field(800, ge=100, le=2000, description="最大宽度")
    max_height: Optional[int] = Field = Field(600, ge=100, le=2000, description="最大高度")
    page: Optional[int] = Field(1, ge=1, description="PDF页码（仅PDF文件）")
    quality: Optional[int] = Field(90, ge=10, le=100, description="图片质量（10-100）")


class FileAnalysisRequest(BaseModel):
    """文件分析请求"""
    file_id: str = Field(..., description="文件ID")
    analysis_type: str = Field(..., regex="^(text|image|structure|security)$", description="分析类型")
    options: Optional[Dict[str, Any]] = Field(None, description="分析选项")


class FileAnalysisResponse(BaseModel):
    """文件分析响应"""
    file_id: str
    analysis_type: str
    results: Dict[str, Any]
    processing_time: float
    created_at: datetime


class FileAccessLog(BaseModel):
    """文件访问日志"""
    id: str
    file_id: str
    user_id: str
    action: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class FileExportRequest(BaseModel):
    """文件导出请求"""
    file_ids: List[str] = Field(..., min_items=1, description="文件ID列表")
    export_format: str = Field(..., regex="^(zip|pdf|csv|json)$", description="导出格式")
    options: Optional[Dict[str, Any]] = Field(None, description="导出选项")


class FileActivity(BaseModel):
    """文件活动记录"""
    id: str
    file_id: str
    activity_type: str
    description: str
    performed_by: str
    user_avatar: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class FileCategory(BaseModel):
    """文件分类"""
    id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    file_count: int = 0
    total_size: int = 0
    created_at: datetime
    updated_at: datetime


class FileTag(BaseModel):
    """文件标签"""
    id: str
    name: str
    color: Optional[str] = None
    file_count: int = 0
    created_at: datetime
    updated_at: datetime


class FileLink(BaseModel):
    """文件分享链接"""
    id: str
    file_id: str
    token: str
    url: str
    password: Optional[str] = None
    expires_at: Optional[datetime] = None
    download_limit: Optional[int] = None
    view_count: int = 0
    created_at: datetime
    created_by: str


class FileFavorite(BaseModel):
    """文件收藏"""
    id: str
    file_id: str
    user_id: str
    created_at: datetime


class FileRecent(BaseModel):
    """最近访问的文件"""
    id: str
    file_id: str
    user_id: str
    last_accessed: datetime
    access_count: int
    created_at: datetime


# 复合响应模型
class FileDetailResponse(FileResponse):
    """文件详细信息响应"""
    shares: List[Dict[str, Any]] = Field(default_factory=list, description="分享记录")
    versions: List[FileVersionInfo] = Field(default_factory=list, description="版本历史")
    comments: List[FileComment] = Field(default_factory=list, description="评论")
    is_favorited: bool = Field(default=False, description="是否已收藏")
    preview_available: bool = Field(default=False, description="是否可预览")
    access_log_count: int = Field(default=0, description="访问次数")
    created_at: datetime
    updated_at: datetime