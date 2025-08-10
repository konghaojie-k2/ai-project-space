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
from app.core.database import get_db
from app.models.file import FileRecord
from app.schemas.file import FileCreate, FileResponse, FileUpdate
from app.services.file_service import FileService
from app.services.file_storage import LocalFileService
from app.utils.file_utils import get_file_type, validate_file_size, validate_file_type

router = APIRouter()

# 依赖注入
def get_file_service(db: Session = Depends(get_db)):
    return FileService(db)

def get_storage_service():
    return LocalFileService()

@router.post("/upload", response_model=List[FileResponse])
async def upload_files(
    files: List[UploadFile] = File(...),
    stage: str = Form(...),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    file_service: FileService = Depends(get_file_service),
    storage_service: LocalFileService = Depends(get_storage_service)
):
    """
    上传文件到MinIO并记录到数据库
    """
    try:
        uploaded_files = []

        tags_list = tags.split(",") if tags else []
        
        for i, file in enumerate(files):
            app_logger.info(f"🔥 处理第 {i+1} 个文件: {file.filename}, 大小: {file.size}, 类型: {file.content_type}")
            
            # 验证文件
            app_logger.info(f"🔥 开始验证文件: {file.filename}")
            if not validate_file_size(file.size):
                app_logger.error(f"🔥 文件大小验证失败: {file.filename}, 大小: {file.size}")
                raise HTTPException(
                    status_code=400,
                    detail=f"文件 {file.filename} 大小超过限制"
                )
            
            if not validate_file_type(file.filename):
                app_logger.error(f"🔥 文件类型验证失败: {file.filename}")
                raise HTTPException(
                    status_code=400,
                    detail=f"文件 {file.filename} 类型不支持"
                )
            
            app_logger.info(f"🔥 文件验证通过: {file.filename}")
            
            # 生成唯一文件名
            file_id = str(uuid.uuid4())
            file_extension = Path(file.filename).suffix
            stored_filename = f"{file_id}{file_extension}"
            
            app_logger.info(f"🔥 生成存储文件名: {stored_filename}")
            
            # 上传到本地存储
            app_logger.info(f"🔥 开始上传文件到本地存储: {stored_filename}")
            try:
                object_name = await storage_service.upload_file(
                    file=file,
                    object_name=stored_filename
                )
                app_logger.info(f"🔥 文件存储成功: {object_name}")
            except Exception as storage_error:
                app_logger.error(f"🔥 文件存储失败: {str(storage_error)}")
                raise
            
            # 创建文件记录
            app_logger.info(f"🔥 开始创建数据库记录")
            try:
                file_create = FileCreate(
                    original_name=file.filename,
                    stored_name=stored_filename,
                    file_path=object_name,
                    file_size=file.size,
                    file_type=file.content_type,
                    project_id=project_id,
                    stage=stage,
                    tags=tags_list,
                    description=description,
                    uploaded_by="current_user"  # TODO: 从认证中获取
                )
                app_logger.info(f"🔥 FileCreate对象创建成功: {file_create}")
                
                # 保存到数据库
                app_logger.info(f"🔥 开始保存到数据库")
                file_record = file_service.create_file(file_create)
                app_logger.info(f"🔥 数据库记录创建成功: {file_record.id}")
                
                uploaded_files.append(file_record)
                
                app_logger.info(f"🔥 文件上传成功: {file.filename} -> {stored_filename}")
                
                # 🚀 自动提取内容并索引到向量数据库
                try:
                    app_logger.info(f"🤖 开始自动提取文件内容: {file.filename}")
                    
                    # 重新读取文件数据用于内容提取
                    await file.seek(0)  # 重置文件指针
                    file_data = await file.read()
                    
                    # 提取文件内容
                    content = await file_service.extract_content(file_data, file.content_type or "")
                    
                    if content and content.strip():
                        app_logger.info(f"🤖 内容提取成功，长度: {len(content)} 字符")
                        
                        # 更新文件内容到数据库
                        await file_service.update_file_content(file_record.id, content)
                        
                        # 索引到向量数据库
                        if project_id:
                            from app.services.ai_service import ai_service
                            
                            metadata = {
                                "file_id": file_record.id,
                                "project_id": project_id,
                                "file_name": file.filename,
                                "file_type": file.content_type,
                                "stage": stage,
                                "tags": tags_list,
                                "upload_time": datetime.now().isoformat(),
                                "content_length": len(content)
                            }
                            
                            success = await ai_service.add_document_to_vector_db(
                                content=content,
                                file_id=file_record.id,
                                file_name=file.filename,
                                project_id=project_id,
                                metadata=metadata
                            )
                            
                            if success:
                                app_logger.info(f"🤖 文件已成功索引到向量数据库: {file.filename}")
                                # 标记文件已处理
                                file_service.mark_file_processed(file_record.id)
                            else:
                                app_logger.warning(f"🤖 文件索引到向量数据库失败: {file.filename}")
                        else:
                            app_logger.info(f"🤖 无项目ID，跳过向量索引: {file.filename}")
                    else:
                        app_logger.warning(f"🤖 文件内容为空或提取失败: {file.filename}")
                        
                except Exception as index_error:
                    app_logger.error(f"🤖 自动索引失败: {file.filename}, 错误: {str(index_error)}")
                    # 索引失败不影响文件上传成功
                
            except Exception as db_error:
                app_logger.error(f"🔥 数据库操作失败: {str(db_error)}")
                raise
        
        app_logger.info(f"🔥 所有文件上传完成，共 {len(uploaded_files)} 个文件")
        return uploaded_files
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"🔥 文件上传失败: {str(e)}")
        app_logger.error(f"🔥 异常详情: {type(e).__name__}: {str(e)}")
        import traceback
        app_logger.error(f"🔥 异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.get("/", response_model=List[FileResponse])
async def list_files(
    project_id: Optional[str] = Query(None, description="项目ID筛选"),
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
        
        files = file_service.get_files(
            project_id=project_id,
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
        file_record = file_service.get_file_by_id(file_id)
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
    storage_service: LocalFileService = Depends(get_storage_service)
):
    """
    下载文件
    """
    try:
        # 获取文件记录
        file_record = file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从本地存储获取文件 - 注意：这里不要使用await，因为download_file返回的是AsyncIterator
        file_data = storage_service.download_file(
            object_name=file_record.stored_name
        )
        
        # 更新下载次数
        file_service.increment_download_count(file_id)
        
        # 处理文件名编码问题
        import urllib.parse
        encoded_filename = urllib.parse.quote(file_record.original_name.encode('utf-8'))
        
        return StreamingResponse(
            file_data,
            media_type=file_record.file_type,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
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
    storage_service: LocalFileService = Depends(get_storage_service)
):
    """
    预览文件
    """
    try:
        # 获取文件记录
        file_record = await file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从本地存储获取文件
        file_data = await storage_service.download_file(
            object_name=file_record.stored_name
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
        file_record = file_service.update_file(file_id, file_update)
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
    storage_service: LocalFileService = Depends(get_storage_service)
):
    """
    删除文件
    """
    try:
        # 获取文件记录
        file_record = file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从本地存储删除文件
        await storage_service.delete_file(
            object_name=file_record.stored_name
        )
        
        # 从向量数据库删除嵌入向量
        try:
            from app.services.ai_service import ai_service
            vector_deleted = await ai_service.remove_document_from_vector_db(file_id)
            if vector_deleted:
                app_logger.info(f"🤖 文件向量已从向量数据库删除: {file_record.original_name}")
            else:
                app_logger.warning(f"🤖 文件向量删除失败: {file_record.original_name}")
        except Exception as vector_error:
            app_logger.error(f"🤖 删除文件向量时出错: {vector_error}")
        
        # 从数据库删除记录
        file_service.delete_file(file_id)
        
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
    storage_service: LocalFileService = Depends(get_storage_service)
):
    """
    提取文件内容（用于AI分析）
    """
    try:
        # 获取文件记录
        file_record = await file_service.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 从本地存储获取文件
        file_data = await storage_service.download_file(
            object_name=file_record.stored_name
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
        stats = file_service.get_file_stats()
        return {"message": "获取统计信息成功", "data": stats}
        
    except Exception as e:
        app_logger.error(f"获取文件统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件统计失败: {str(e)}")

@router.post("/batch-index")
async def batch_index_files(
    project_id: Optional[str] = None,
    force_reindex: bool = False,
    file_service: FileService = Depends(get_file_service),
    storage_service: LocalFileService = Depends(get_storage_service)
):
    """
    批量索引文件到向量数据库
    
    Args:
        project_id: 项目ID，如果指定则只索引该项目的文件
        force_reindex: 是否强制重新索引已处理的文件
    """
    try:
        from app.services.ai_service import ai_service
        
        # 获取需要索引的文件
        if project_id:
            files = file_service.get_files_by_project(project_id)
        else:
            files = file_service.get_all_unprocessed_files() if not force_reindex else file_service.get_all_files()
        
        app_logger.info(f"🤖 开始批量索引，共 {len(files)} 个文件")
        
        indexed_count = 0
        failed_count = 0
        
        for file_record in files:
            try:
                # 跳过已处理的文件（除非强制重新索引）
                if file_record.is_processed and not force_reindex:
                    continue
                
                app_logger.info(f"🤖 正在索引文件: {file_record.original_name}")
                
                # 从存储获取文件数据
                file_data = await storage_service.download_file(
                    object_name=file_record.stored_name
                )
                
                # 提取文件内容
                content = await file_service.extract_content(file_data, file_record.file_type)
                
                if content and content.strip():
                    # 更新文件内容到数据库
                    await file_service.update_file_content(file_record.id, content)
                    
                    # 索引到向量数据库
                    metadata = {
                        "file_id": file_record.id,
                        "project_id": file_record.project_id,
                        "file_name": file_record.original_name,
                        "file_type": file_record.file_type,
                        "stage": file_record.stage,
                        "tags": file_record.tags or [],
                        "upload_time": file_record.created_at.isoformat() if file_record.created_at else datetime.now().isoformat(),
                        "content_length": len(content)
                    }
                    
                    document_id = f"file_{file_record.id}"
                    success = await ai_service.add_document_to_vector_db(
                        content=content,
                        file_id=file_record.id,
                        file_name=file_record.original_name,
                        project_id=file_record.project_id,
                        metadata=metadata
                    )
                    
                    if success:
                        # 标记文件已处理
                        file_service.mark_file_processed(file_record.id)
                        indexed_count += 1
                        app_logger.info(f"🤖 文件索引成功: {file_record.original_name}")
                    else:
                        failed_count += 1
                        app_logger.warning(f"🤖 文件索引失败: {file_record.original_name}")
                else:
                    app_logger.warning(f"🤖 文件内容为空，跳过索引: {file_record.original_name}")
                    
            except Exception as file_error:
                failed_count += 1
                app_logger.error(f"🤖 处理文件失败: {file_record.original_name}, 错误: {str(file_error)}")
        
        app_logger.info(f"🤖 批量索引完成，成功: {indexed_count}, 失败: {failed_count}")
        
        return {
            "message": "批量索引完成",
            "indexed_count": indexed_count,
            "failed_count": failed_count,
            "total_processed": indexed_count + failed_count
        }
        
    except Exception as e:
        app_logger.error(f"批量索引失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量索引失败: {str(e)}")

@router.get("/search-context")
async def search_file_context(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 5
):
    """
    搜索文件上下文（用于AI问答）
    
    Args:
        query: 搜索查询
        project_id: 项目ID筛选
        limit: 返回结果数量限制
    """
    try:
        from app.services.ai_service import AIService
        ai_service = AIService()
        
        # 搜索相似文档
        results = await ai_service.search_similar_documents(
            query=query,
            n_results=limit
        )
        
        # 过滤项目相关结果
        if project_id:
            results = [
                result for result in results
                if result.get('metadata', {}).get('project_id') == project_id
            ]
        
        return {
            "message": "搜索完成",
            "query": query,
            "project_id": project_id,
            "results": results
        }
        
    except Exception as e:
        app_logger.error(f"搜索文件上下文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索文件上下文失败: {str(e)}") 