#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件工具函数
提供文件类型验证、大小验证等基础功能
注意：文件内容提取功能已由外部RAG服务处理，不再需要本地提取库
"""

import mimetypes
from typing import Optional
from pathlib import Path
from loguru import logger

# 支持的文件类型
SUPPORTED_FILE_TYPES = {
    # 文档类型
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'text/plain': ['.txt'],
    'text/markdown': ['.md'],
    'text/csv': ['.csv'],
    'application/json': ['.json'],
    'application/xml': ['.xml'],
    'text/html': ['.html', '.htm'],
    
    # 图片类型
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'image/gif': ['.gif'],
    'image/bmp': ['.bmp'],
    'image/tiff': ['.tiff', '.tif'],
    'image/webp': ['.webp'],
    
    # 音频类型
    'audio/mpeg': ['.mp3'],
    'audio/wav': ['.wav'],
    'audio/ogg': ['.ogg'],
    'audio/flac': ['.flac'],
    
    # 视频类型
    'video/mp4': ['.mp4'],
    'video/avi': ['.avi'],
    'video/mov': ['.mov'],
    'video/wmv': ['.wmv'],
    'video/flv': ['.flv'],
    
    # 压缩文件
    'application/zip': ['.zip'],
    'application/x-rar-compressed': ['.rar'],
    'application/x-7z-compressed': ['.7z'],
    'application/x-tar': ['.tar'],
    'application/gzip': ['.gz'],
    
    # 代码文件
    'text/x-python': ['.py'],
    'text/javascript': ['.js'],
    'text/x-java-source': ['.java'],
    'text/x-c': ['.c'],
    'text/x-c++': ['.cpp', '.cxx'],
    'text/x-csharp': ['.cs'],
    'text/x-php': ['.php'],
    'text/x-ruby': ['.rb'],
    'text/x-go': ['.go'],
    'text/x-rust': ['.rs'],
    'text/x-sql': ['.sql'],
    'text/css': ['.css'],
    'text/x-scss': ['.scss'],
    'text/x-less': ['.less'],
}

# 文件大小限制（字节）
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10MB
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500MB


def get_file_type(filename: str) -> Optional[str]:
    """
    根据文件名获取MIME类型
    
    Args:
        filename: 文件名
        
    Returns:
        Optional[str]: MIME类型
    """
    try:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type
    except Exception as e:
        logger.error(f"获取文件类型失败: {e}")
        return None


def validate_file_type(filename: str) -> bool:
    """
    验证文件类型是否支持
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否支持
    """
    try:
        file_extension = Path(filename).suffix.lower()
        
        # 检查扩展名是否在支持列表中
        for mime_type, extensions in SUPPORTED_FILE_TYPES.items():
            if file_extension in extensions:
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"验证文件类型失败: {e}")
        return False


def validate_file_size(file_size: int, file_type: Optional[str] = None) -> bool:
    """
    验证文件大小是否符合限制
    
    Args:
        file_size: 文件大小（字节）
        file_type: 文件类型
        
    Returns:
        bool: 是否符合限制
    """
    try:
        if file_type:
            if file_type.startswith('image/'):
                return file_size <= MAX_IMAGE_SIZE
            elif file_type.startswith('video/'):
                return file_size <= MAX_VIDEO_SIZE
        
        return file_size <= MAX_FILE_SIZE
        
    except Exception as e:
        logger.error(f"验证文件大小失败: {e}")
        return False


def generate_file_hash(file_content: bytes) -> str:
    """
    生成文件哈希值
    
    Args:
        file_content: 文件内容
        
    Returns:
        str: 文件哈希值
    """
    try:
        import hashlib
        return hashlib.md5(file_content).hexdigest()
    except Exception as e:
        logger.error(f"生成文件哈希失败: {e}")
        return ""


def get_file_category(file_type: str) -> str:
    """
    根据文件类型获取文件分类
    
    Args:
        file_type: MIME类型
        
    Returns:
        str: 文件分类
    """
    try:
        if file_type.startswith('image/'):
            return 'image'
        elif file_type.startswith('video/'):
            return 'video'
        elif file_type.startswith('audio/'):
            return 'audio'
        elif file_type in ['application/pdf', 'application/msword', 
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
            return 'document'
        elif file_type in ['application/vnd.ms-excel', 
                          'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            return 'spreadsheet'
        elif file_type.startswith('text/'):
            return 'text'
        elif 'zip' in file_type or 'rar' in file_type or 'tar' in file_type:
            return 'archive'
        else:
            return 'other'
            
    except Exception as e:
        logger.error(f"获取文件分类失败: {e}")
        return 'other'


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小
    """
    try:
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
        
    except Exception as e:
        logger.error(f"格式化文件大小失败: {e}")
        return f"{size_bytes} B"


def is_safe_filename(filename: str) -> bool:
    """
    检查文件名是否安全
    
    Args:
        filename: 文件名
        
    Returns:
        bool: 是否安全
    """
    try:
        # 检查危险字符
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                return False
        
        # 检查文件名长度
        if len(filename) > 255:
            return False
        
        # 检查是否为空
        if not filename.strip():
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"检查文件名安全性失败: {e}")
        return False


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，使其安全
    
    Args:
        filename: 原始文件名
        
    Returns:
        str: 清理后的文件名
    """
    try:
        import re
        
        # 移除危险字符
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # 移除连续的点
        filename = re.sub(r'\.{2,}', '.', filename)
        
        # 限制长度
        if len(filename) > 255:
            name, ext = Path(filename).stem, Path(filename).suffix
            max_name_len = 255 - len(ext)
            filename = name[:max_name_len] + ext
        
        # 确保不为空
        if not filename.strip():
            filename = "unnamed_file"
        
        return filename
        
    except Exception as e:
        logger.error(f"清理文件名失败: {e}")
        return "unnamed_file"
