from typing import List, Optional
from pathlib import Path
import shutil
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import app_logger
from app.models.file import FileRecord
from app.schemas.file import FileCreate, FileResponse, FileUpdate
from app.services.file_service import FileService
from app.services.minio_service import MinIOService
from app.utils.file_utils import get_file_type, validate_file_size, validate_file_type

router = APIRouter()

# 依赖注入
def get_file_service():
    return FileService()

def get_minio_service():
    return MinIOService()

@router.post("/upload", response_model=List[FileResponse])
async def upload_files(
    files: List[UploadFile] = File(...),
    stage: str = Form(...),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file_service: FileService = Depends(get_file_service),
    minio_service: MinIOService = Depends(get_minio_service)
):
    """
    上传文件到MinIO并记录到数据库
    """
    try:
        uploaded_files = []
        tags_list = tags.split(",") if tags else []
        
        for file in files:
            # 验证文件
            if not validate_file_size(file.size):
                raise HTTPException(
                    status_code=400,
                    detail=f"文件 {file.filename} 大小超过限制"
                )
            
            if not validate_file_type(file.filename):
                raise HTTPException(
                    status_code=400,
                    detail=f"文件 {file.filename} 类型不支持"
                )
            
            # 生成唯一文件名
            file_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix
            stored_filename = f"{file_id}{file_extension}"
            
            # 上传到MinIO
            object_name = await minio_service.upload_file(
                file=file,
                object_name=stored_filename,
                bucket_name=settings.MINIO_BUCKET_NAME
            )
            
            # 创建文件记录
            file_create = FileCreate(
                original_name=file.filename,
                stored_name=stored_filename,
                file_path=object_name,
                file_size=file.size,
                file_type=file.content_type,
                stage=stage,
                tags=tags_list,
                description=description,
                uploaded_by="current_user"  # TODO: 从认证中获取
            )
            
            # 保存到数据库
            file_record = await file_service.create_file(file_create)
            uploaded_files.append(file_record)
            
            app_logger.info(f"文件上传成功: {file.filename} -> {stored_filename}")
        
        return uploaded_files
        
    except Exception as e:
        app_logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.get("/", response_model=List[FileResponse])
async def list_files(
    stage: Optional[str] = Query(None, description="项目阶段筛选"),
    tags: Optional[str] = Query(None, description="标签筛选，逗号分隔"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    file_service: FileService = Depends(get_file_service)
):
    """
    获取文件列表
    """
    try:
        tags_list = tags.split(",") if tags else None
        
        files = await file_service.get_files(
            stage=stage,
            tags=tags_list,
            search=search,
            page=page,
            size=size
        )
        
        return files
        
    except Exception as e:
        app_logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    获取文件详情
    """
    try:
        file_record = await file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return file_record
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取文件详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件详情失败: {str(e)}")

@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    minio_service: MinIOService = Depends(get_minio_service)
):
    """
    下载文件
    """
    try:
        # 获取文件记录
        file_record = await file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从MinIO获取文件
        file_data = await minio_service.download_file(
            object_name=file_record.stored_name,
            bucket_name=settings.MINIO_BUCKET_NAME
        )
        
        # 更新下载次数
        await file_service.increment_download_count(file_id)
        
        return StreamingResponse(
            file_data,
            media_type=file_record.file_type,
            headers={
                "Content-Disposition": f"attachment; filename={file_record.original_name}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"文件下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@router.get("/{file_id}/preview")
async def preview_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    minio_service: MinIOService = Depends(get_minio_service)
):
    """
    预览文件
    """
    try:
        # 获取文件记录
        file_record = await file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从MinIO获取文件
        file_data = await minio_service.download_file(
            object_name=file_record.stored_name,
            bucket_name=settings.MINIO_BUCKET_NAME
        )
        
        # 更新查看次数
        await file_service.increment_view_count(file_id)
        
        return StreamingResponse(
            file_data,
            media_type=file_record.file_type,
            headers={
                "Content-Disposition": f"inline; filename={file_record.original_name}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"文件预览失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件预览失败: {str(e)}")

@router.put("/{file_id}", response_model=FileResponse)
async def update_file(
    file_id: str,
    file_update: FileUpdate,
    file_service: FileService = Depends(get_file_service)
):
    """
    更新文件信息
    """
    try:
        file_record = await file_service.update_file(file_id, file_update)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return file_record
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"更新文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新文件失败: {str(e)}")

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    minio_service: MinIOService = Depends(get_minio_service)
):
    """
    删除文件
    """
    try:
        # 获取文件记录
        file_record = await file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从MinIO删除文件
        await minio_service.delete_file(
            object_name=file_record.stored_name,
            bucket_name=settings.MINIO_BUCKET_NAME
        )
        
        # 从数据库删除记录
        await file_service.delete_file(file_id)
        
        app_logger.info(f"文件删除成功: {file_record.original_name}")
        
        return {"message": "文件删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"文件删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")

@router.post("/{file_id}/extract-content")
async def extract_file_content(
    file_id: str,
    file_service: FileService = Depends(get_file_service),
    minio_service: MinIOService = Depends(get_minio_service)
):
    """
    提取文件内容（用于AI分析）
    """
    try:
        # 获取文件记录
        file_record = await file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从MinIO获取文件
        file_data = await minio_service.download_file(
            object_name=file_record.stored_name,
            bucket_name=settings.MINIO_BUCKET_NAME
        )
        
        # 根据文件类型提取内容
        content = await file_service.extract_content(file_data, file_record.file_type)
        
        # 更新文件内容到数据库
        await file_service.update_file_content(file_id, content)
        
        return {"message": "内容提取成功", "content_length": len(content)}
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"内容提取失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内容提取失败: {str(e)}")

@router.get("/stats/summary")
async def get_file_stats(
    file_service: FileService = Depends(get_file_service)
):
    """
    获取文件统计信息
    """
    try:
        stats = await file_service.get_file_stats()
        return stats
        
    except Exception as e:
        app_logger.error(f"获取文件统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件统计失败: {str(e)}") 