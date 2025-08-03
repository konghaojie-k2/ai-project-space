import asyncio
import io
from typing import Optional, AsyncIterator
from pathlib import Path
import shutil
import uuid

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException
from loguru import logger

from app.core.config import settings

class MinIOService:
    """MinIO对象存储服务，支持降级到本地存储"""
    
    def __init__(self):
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self.fallback_mode = False
        self.local_storage_path = Path("uploads")
        
        try:
            self.client = Minio(
                endpoint=settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            self._ensure_bucket_exists()
            logger.info("MinIO服务连接成功")
        except Exception as e:
            logger.warning(f"MinIO服务不可用，降级到本地文件存储: {e}")
            self.fallback_mode = True
            self._ensure_local_storage()
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"创建MinIO存储桶: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"创建MinIO存储桶失败: {e}")
            self.fallback_mode = True
            self._ensure_local_storage()
    
    def _ensure_local_storage(self):
        """确保本地存储目录存在"""
        self.local_storage_path.mkdir(exist_ok=True)
        logger.info(f"使用本地存储目录: {self.local_storage_path}")
    
    async def upload_file(
        self, 
        file: UploadFile, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> str:
        """
        上传文件到MinIO或本地存储
        
        Args:
            file: 上传的文件
            object_name: 对象名称
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            str: 文件存储路径
        """
        if self.fallback_mode:
            return await self._upload_to_local(file, object_name)
        else:
            return await self._upload_to_minio(file, object_name, bucket_name)
    
    async def _upload_to_local(self, file: UploadFile, object_name: str) -> str:
        """上传文件到本地存储"""
        try:
            file_path = self.local_storage_path / object_name
            
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            content = await file.read()
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"文件保存到本地: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"本地文件上传失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
    
    async def _upload_to_minio(
        self, 
        file: UploadFile, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> str:
        """上传文件到MinIO"""
        try:
            bucket = bucket_name or self.bucket_name
            
            # 重置文件指针
            await file.seek(0)
            content = await file.read()
            
            # 上传到MinIO
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type=file.content_type
            )
            
            logger.info(f"文件上传到MinIO成功: {object_name}")
            return f"{bucket}/{object_name}"
            
        except S3Error as e:
            logger.error(f"MinIO上传失败: {e}")
            # 降级到本地存储
            self.fallback_mode = True
            self._ensure_local_storage()
            return await self._upload_to_local(file, object_name)
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

    async def download_file(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        从MinIO或本地存储下载文件
        
        Args:
            object_name: 对象名称
            bucket_name: 存储桶名称
            
        Yields:
            bytes: 文件内容
        """
        if self.fallback_mode:
            async for chunk in self._download_from_local(object_name):
                yield chunk
        else:
            async for chunk in self._download_from_minio(object_name, bucket_name):
                yield chunk
    
    async def _download_from_local(self, object_name: str) -> AsyncIterator[bytes]:
        """从本地存储下载文件"""
        try:
            file_path = self.local_storage_path / object_name
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk
                    
        except Exception as e:
            logger.error(f"本地文件下载失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")
    
    async def _download_from_minio(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """从MinIO下载文件"""
        try:
            bucket = bucket_name or self.bucket_name
            
            response = self.client.get_object(bucket, object_name)
            
            try:
                while True:
                    chunk = response.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk
            finally:
                response.close()
                response.release_conn()
                
        except S3Error as e:
            logger.error(f"MinIO下载失败: {e}")
            raise HTTPException(status_code=404, detail="文件不存在")
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
            bucket_name: 存储桶名称
            
        Returns:
            bool: 删除是否成功
        """
        if self.fallback_mode:
            return await self._delete_from_local(object_name)
        else:
            return await self._delete_from_minio(object_name, bucket_name)
    
    async def _delete_from_local(self, object_name: str) -> bool:
        """从本地存储删除文件"""
        try:
            file_path = self.local_storage_path / object_name
            if file_path.exists():
                file_path.unlink()
                logger.info(f"本地文件删除成功: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"本地文件删除失败: {e}")
            return False
    
    async def _delete_from_minio(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> bool:
        """从MinIO删除文件"""
        try:
            bucket = bucket_name or self.bucket_name
            self.client.remove_object(bucket, object_name)
            logger.info(f"MinIO文件删除成功: {object_name}")
            return True
        except S3Error as e:
            logger.error(f"MinIO文件删除失败: {e}")
            return False
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
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
            bucket_name: 存储桶名称
            expires: 过期时间（秒）
            
        Returns:
            str: 文件访问URL
        """
        if self.fallback_mode:
            # 本地文件返回相对路径
            return f"/uploads/{object_name}"
        else:
            try:
                bucket = bucket_name or self.bucket_name
                return self.client.presigned_get_object(bucket, object_name, expires=expires)
            except Exception as e:
                logger.error(f"获取文件URL失败: {e}")
                return f"/uploads/{object_name}"  # 降级到本地路径

    @property
    def is_available(self) -> bool:
        """检查MinIO服务是否可用"""
        return not self.fallback_mode
    
    @property
    def storage_info(self) -> dict:
        """获取存储信息"""
        return {
            "type": "minio" if not self.fallback_mode else "local",
            "available": self.is_available,
            "bucket_name": self.bucket_name,
            "endpoint": settings.MINIO_ENDPOINT if not self.fallback_mode else str(self.local_storage_path)
        } 