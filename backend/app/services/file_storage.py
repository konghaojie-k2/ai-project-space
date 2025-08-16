import asyncio
import io
from typing import Optional, AsyncIterator
from pathlib import Path
import shutil
import uuid
from loguru import logger

from fastapi import UploadFile, HTTPException

from app.core.config import settings

class LocalFileService:
    """本地文件存储服务"""
    
    def __init__(self):
        # 统一使用backend目录下的uploads文件夹
        # 从当前文件位置向上找到backend目录
        current_file = Path(__file__).resolve()
        # file_storage.py在backend/app/services/下，所以向上3级到backend目录
        backend_dir = current_file.parent.parent.parent
        self.storage_path = backend_dir / "uploads"
        self._ensure_storage_exists()
        logger.info("本地文件存储服务初始化成功")
    
    def _ensure_storage_exists(self):
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"使用本地存储目录: {self.storage_path.absolute()}")
    
    async def upload_file(
        self, 
        file: UploadFile, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> str:
        """
        上传文件到本地存储
        
        Args:
            file: 上传的文件
            object_name: 对象名称
            bucket_name: 兼容参数（忽略）
            
        Returns:
            str: 文件存储路径
        """
        try:
            file_path = self.storage_path / object_name
            
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"文件保存成功: {file_path}")
            return f"uploads/{object_name}"
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

    async def download_file(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        从本地存储下载文件
        
        Args:
            object_name: 对象名称
            bucket_name: 兼容参数（忽略）
            
        Yields:
            bytes: 文件内容
        """
        try:
            file_path = self.storage_path / object_name
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk
                    
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

    async def delete_file(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        删除文件
        
        Args:
            object_name: 对象名称
            bucket_name: 兼容参数（忽略）
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 确保object_name是完整的路径
            file_path = self.storage_path / object_name
            
            # 记录详细的删除信息用于调试
            logger.info(f"尝试删除文件: {file_path.absolute()}")
            logger.info(f"文件是否存在: {file_path.exists()}")
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"✅ 物理文件删除成功: {file_path.absolute()}")
                
                # 双重验证文件是否真的被删除
                if not file_path.exists():
                    logger.info(f"✅ 确认文件已被物理删除: {object_name}")
                    return True
                else:
                    logger.error(f"❌ 文件删除后仍然存在: {file_path.absolute()}")
                    return False
            else:
                logger.warning(f"⚠️ 文件不存在，无需删除: {file_path.absolute()}")
                return True  # 文件不存在也算删除成功
        except Exception as e:
            logger.error(f"❌ 文件删除失败: {object_name}, 错误: {e}")
            return False

    def get_file_url(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None,
        expires: int = 3600
    ) -> str:
        """
        获取文件访问URL
        
        Args:
            object_name: 对象名称
            bucket_name: 兼容参数（忽略）
            expires: 兼容参数（忽略）
            
        Returns:
            str: 文件访问URL
        """
        return f"/uploads/{object_name}"

    @property
    def is_available(self) -> bool:
        """检查存储服务是否可用"""
        return True
    
    @property
    def storage_info(self) -> dict:
        """获取存储信息"""
        return {
            "type": "local",
            "available": True,
            "storage_path": str(self.storage_path.absolute())
        } 