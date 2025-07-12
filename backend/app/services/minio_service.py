import asyncio
import io
from typing import Optional, AsyncIterator
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException
from loguru import logger

from app.core.config import settings

class MinIOService:
    """MinIO对象存储服务"""
    
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"创建MinIO存储桶: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"创建MinIO存储桶失败: {e}")
            raise
    
    async def upload_file(
        self, 
        file: UploadFile, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> str:
        """
        上传文件到MinIO
        
        Args:
            file: 上传的文件
            object_name: 对象名称
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            str: 上传后的对象路径
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            # 读取文件内容
            file_content = await file.read()
            file_size = len(file_content)
            
            # 重置文件指针
            await file.seek(0)
            
            # 上传文件
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=io.BytesIO(file_content),
                length=file_size,
                content_type=file.content_type
            )
            
            logger.info(f"文件上传成功: {object_name} -> {bucket}")
            return f"{bucket}/{object_name}"
            
        except S3Error as e:
            logger.error(f"MinIO上传失败: {e}")
            raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")
        except Exception as e:
            logger.error(f"上传文件时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"上传文件失败: {str(e)}")
    
    async def download_file(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        从MinIO下载文件
        
        Args:
            object_name: 对象名称
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Yields:
            bytes: 文件内容的字节流
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            # 获取文件对象
            response = self.client.get_object(bucket, object_name)
            
            # 分块读取文件内容
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
            raise HTTPException(status_code=404, detail=f"文件不存在: {object_name}")
        except Exception as e:
            logger.error(f"下载文件时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")
    
    async def delete_file(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        从MinIO删除文件
        
        Args:
            object_name: 对象名称
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            bool: 删除是否成功
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            # 删除文件
            self.client.remove_object(bucket, object_name)
            
            logger.info(f"文件删除成功: {object_name} from {bucket}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO删除失败: {e}")
            # 如果文件不存在，也认为删除成功
            if "NoSuchKey" in str(e):
                logger.warning(f"文件不存在，忽略删除: {object_name}")
                return True
            raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")
        except Exception as e:
            logger.error(f"删除文件时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")
    
    async def file_exists(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        检查文件是否存在
        
        Args:
            object_name: 对象名称
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            bool: 文件是否存在
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            # 尝试获取文件信息
            self.client.stat_object(bucket, object_name)
            return True
            
        except S3Error as e:
            if "NoSuchKey" in str(e):
                return False
            logger.error(f"检查文件存在性失败: {e}")
            raise HTTPException(status_code=500, detail=f"检查文件失败: {str(e)}")
        except Exception as e:
            logger.error(f"检查文件时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"检查文件失败: {str(e)}")
    
    async def get_file_info(
        self, 
        object_name: str, 
        bucket_name: Optional[str] = None
    ) -> dict:
        """
        获取文件信息
        
        Args:
            object_name: 对象名称
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            dict: 文件信息
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            # 获取文件统计信息
            stat = self.client.stat_object(bucket, object_name)
            
            return {
                "object_name": object_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
            
        except S3Error as e:
            logger.error(f"获取文件信息失败: {e}")
            raise HTTPException(status_code=404, detail=f"文件不存在: {object_name}")
        except Exception as e:
            logger.error(f"获取文件信息时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"获取文件信息失败: {str(e)}")
    
    async def list_objects(
        self, 
        prefix: Optional[str] = None,
        bucket_name: Optional[str] = None
    ) -> list:
        """
        列出存储桶中的对象
        
        Args:
            prefix: 对象名称前缀
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            list: 对象列表
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            objects = []
            for obj in self.client.list_objects(bucket, prefix=prefix):
                objects.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified,
                    "content_type": obj.content_type
                })
            
            return objects
            
        except S3Error as e:
            logger.error(f"列出对象失败: {e}")
            raise HTTPException(status_code=500, detail=f"列出对象失败: {str(e)}")
        except Exception as e:
            logger.error(f"列出对象时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"列出对象失败: {str(e)}")
    
    async def generate_presigned_url(
        self, 
        object_name: str, 
        expires_in: int = 3600,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        生成预签名URL
        
        Args:
            object_name: 对象名称
            expires_in: 过期时间（秒），默认1小时
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            str: 预签名URL
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            # 生成预签名URL
            url = self.client.presigned_get_object(
                bucket_name=bucket,
                object_name=object_name,
                expires=expires_in
            )
            
            return url
            
        except S3Error as e:
            logger.error(f"生成预签名URL失败: {e}")
            raise HTTPException(status_code=500, detail=f"生成预签名URL失败: {str(e)}")
        except Exception as e:
            logger.error(f"生成预签名URL时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"生成预签名URL失败: {str(e)}")
    
    async def copy_object(
        self, 
        source_object: str, 
        dest_object: str,
        source_bucket: Optional[str] = None,
        dest_bucket: Optional[str] = None
    ) -> bool:
        """
        复制对象
        
        Args:
            source_object: 源对象名称
            dest_object: 目标对象名称
            source_bucket: 源存储桶名称
            dest_bucket: 目标存储桶名称
            
        Returns:
            bool: 复制是否成功
        """
        try:
            src_bucket = source_bucket or self.bucket_name
            dst_bucket = dest_bucket or self.bucket_name
            
            # 复制对象
            self.client.copy_object(
                bucket_name=dst_bucket,
                object_name=dest_object,
                object_source=f"{src_bucket}/{source_object}"
            )
            
            logger.info(f"对象复制成功: {src_bucket}/{source_object} -> {dst_bucket}/{dest_object}")
            return True
            
        except S3Error as e:
            logger.error(f"复制对象失败: {e}")
            raise HTTPException(status_code=500, detail=f"复制对象失败: {str(e)}")
        except Exception as e:
            logger.error(f"复制对象时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"复制对象失败: {str(e)}")
    
    async def get_bucket_stats(self, bucket_name: Optional[str] = None) -> dict:
        """
        获取存储桶统计信息
        
        Args:
            bucket_name: 存储桶名称，默认使用配置的存储桶
            
        Returns:
            dict: 存储桶统计信息
        """
        try:
            bucket = bucket_name or self.bucket_name
            
            total_objects = 0
            total_size = 0
            
            # 遍历所有对象
            for obj in self.client.list_objects(bucket):
                total_objects += 1
                total_size += obj.size
            
            return {
                "bucket_name": bucket,
                "total_objects": total_objects,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
            
        except S3Error as e:
            logger.error(f"获取存储桶统计失败: {e}")
            raise HTTPException(status_code=500, detail=f"获取存储桶统计失败: {str(e)}")
        except Exception as e:
            logger.error(f"获取存储桶统计时发生错误: {e}")
            raise HTTPException(status_code=500, detail=f"获取存储桶统计失败: {str(e)}") 