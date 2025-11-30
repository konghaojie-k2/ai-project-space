from typing import List, Optional
from pathlib import Path
import uuid
from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import StreamingResponse
from app.core.logging import app_logger
from typing import Dict, Any
from app.schemas.file import FileResponse, FileUpdate
from app.services.supabase_file_service import supabase_file_service
from app.services.rag_client import rag_client
from app.utils.file_utils import validate_file_size, validate_file_type

router = APIRouter()

# 简单的内存缓存，用于统计API（5秒缓存）
_stats_cache = {
    "data": None,
    "timestamp": 0,
    "user_id": None
}

# 导入认证依赖
from app.dependencies.auth import get_current_user, get_current_active_user, get_current_user_token, get_current_user_tokens

@router.post("/upload", response_model=List[FileResponse])
async def upload_files(
    files: List[UploadFile] = File(...),
    stage: str = Form(...),
    project_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    access_level: str = Form("all_users"),  # 访问级别，默认全员
    uploaded_by: Optional[str] = Form(None),  # 添加上传者参数
    current_user: Dict[str, Any] = Depends(get_current_user),
    token: str = Depends(get_current_user_token)  # 获取access_token用于设置认证上下文
):
    """
    上传文件到Supabase Storage并记录到数据库
    如果指定了project_id，同时上传到外部RAG知识库
    """
    try:
        uploaded_files = []

        # 注意：文件记录创建现在使用admin_client（Service Key）绕过RLS限制
        # 因此不需要设置认证上下文
        
        tags_list = tags.split(",") if tags else []
        
        # 权限检查：如果指定了project_id，验证用户是否有权限访问此项目
        user_id = str(current_user.get('id'))
        if project_id:
            from app.dependencies.auth import validate_user_project_access
            has_access = await validate_user_project_access(
                user_id=user_id,
                project_id=project_id,
                required_role='member'  # 至少需要member角色才能上传文件
            )
            if not has_access:
                app_logger.warning(f"用户 {user_id} 尝试上传文件到无权访问的项目 {project_id}")
                raise HTTPException(
                    status_code=403,
                    detail="无权限上传文件到此项目，您需要是项目成员才能上传文件"
                )
            app_logger.info(f"✅ 用户 {user_id} 有权限上传文件到项目 {project_id}")
        
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
            
            # 读取文件内容
            await file.seek(0)
            file_content = await file.read()
            
            # 上传到Supabase Storage（文件名会在supabase_file_service中生成）
            app_logger.info(f"🔥 开始上传文件到Supabase Storage: {file.filename}")
            try:
                # 构建存储路径
                username = current_user.get('username') or current_user.get('email', 'user').split('@')[0]
                file_path = f"uploads/{username}"
                
                # 使用supabase_file_service上传（user_id已在上面定义）
                file_record_data = await supabase_file_service.upload_file(
                    file_path=file_path,
                    file_content=file_content,
                    filename=file.filename,
                    user_id=user_id,
                    project_id=project_id,
                    access_level=access_level,
                    description=description,
                    tags=tags_list,
                    access_token=token  # 传递access_token用于设置认证上下文
                )
                
                if not file_record_data:
                    raise HTTPException(status_code=500, detail="文件上传到Supabase Storage失败")
                
                app_logger.info(f"🔥 文件存储成功: {file_record_data.get('file_path')}")
                
                # 转换为FileResponse格式
                file_record = FileResponse(
                    id=file_record_data.get('id'),
                    original_name=file_record_data.get('original_name'),
                    stored_name=file_record_data.get('stored_name'),
                    file_path=file_record_data.get('file_path'),
                    file_size=file_record_data.get('file_size'),
                    file_type=file_record_data.get('file_type'),
                    project_id=file_record_data.get('project_id'),
                    stage=stage,  # 注意：Supabase Storage可能没有stage字段
                    tags=file_record_data.get('tags', []),
                    description=file_record_data.get('description'),
                    uploaded_by=file_record_data.get('uploaded_by'),
                    user_id=file_record_data.get('uploaded_by'),
                    access_level=file_record_data.get('access_level', 'all_users'),
                    is_public=file_record_data.get('is_public', False),
                    created_at=file_record_data.get('created_at'),
                    updated_at=file_record_data.get('updated_at')
                )
                
                app_logger.info(f"🔥 数据库记录创建成功: {file_record.id}")
                
                uploaded_files.append(file_record)
                
                # 使用数据库返回的实际文件名
                app_logger.info(f"🔥 文件上传成功: {file.filename} -> {file_record.stored_name} (ID: {file_record.id})")
                
                # 🚀 如果指定了project_id，上传到外部RAG知识库（8002端口）
                if project_id:
                    if rag_client.is_available():
                        try:
                            app_logger.info(f"🤖 开始上传文件到外部RAG知识库（8002端口）: {file.filename}")
                            
                            # 确保项目知识库存在（如果不存在则创建）
                            kb_name = f"project_{project_id}"
                            app_logger.info(f"🔍 检查/创建项目知识库: {kb_name}")
                            try:
                                # 尝试创建知识库（如果已存在会返回相应消息）
                                kb_result = await rag_client.create_knowledge_base(
                                    name=kb_name,
                                    description=f"项目 {project_id} 的知识库"
                                )
                                app_logger.info(f"📋 知识库创建结果: {kb_result}")
                                if kb_result.get('success') or "已存在" in kb_result.get('message', ''):
                                    app_logger.info(f"✅ 项目知识库已就绪: {kb_name}")
                                else:
                                    app_logger.warning(f"⚠️ 项目知识库创建可能失败: {kb_result.get('message', '未知错误')}")
                            except Exception as kb_error:
                                # 知识库创建失败不影响文件上传
                                app_logger.error(f"❌ 检查/创建项目知识库时出错: {kb_error}，继续上传文件")
                                import traceback
                                app_logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
                            
                            # 重新读取文件数据用于RAG上传
                            await file.seek(0)
                            file_data = await file.read()
                            
                            # 构建元数据
                            username = current_user.get('username') or current_user.get('email', 'user').split('@')[0]
                            metadata = {
                                "uploaded_by": username or user_id,
                                "user_id": user_id,
                                "upload_time": datetime.now().isoformat(),
                                "description": description,
                                "tags": tags_list,
                                "content_type": file.content_type,
                                "file_size": len(file_data),
                                "stage": stage
                            }
                            
                            # 上传到外部RAG服务（8002端口，使用项目知识库）
                            app_logger.info(f"🤖 准备上传到RAG知识库（8002端口）: {kb_name}, 文件: {file.filename}")
                            rag_result = await rag_client.upload_file(
                                file_content=file_data,
                                filename=file.filename,
                                collection_name=kb_name,  # 使用项目知识库
                                metadata=metadata
                            )
                            
                            if rag_result.success:
                                app_logger.info(f"🤖 文件已成功上传到RAG知识库（8002端口）: {file.filename}, 文档ID: {rag_result.document_id}")
                                # 创建映射记录
                                from app.services.rag_mapping_service import rag_mapping_service
                                try:
                                    await rag_mapping_service.create_mapping(
                                        local_file_id=file_record.id,
                                        external_document_id=rag_result.document_id,
                                        external_collection_name=kb_name,  # 使用项目知识库名称
                                        project_id=project_id,
                                        chunk_count=rag_result.chunk_count
                                    )
                                    app_logger.info(f"✅ RAG映射记录创建成功")
                                except Exception as mapping_error:
                                    app_logger.warning(f"⚠️ RAG映射记录创建失败: {mapping_error}")
                            else:
                                app_logger.warning(f"🤖 文件上传到RAG知识库失败: {file.filename}, 原因: {rag_result.message}")
                        except Exception as rag_error:
                            app_logger.error(f"🤖 RAG上传失败: {file.filename}, 错误: {str(rag_error)}")
                            # RAG上传失败不影响文件上传成功
                    else:
                        app_logger.warning(f"⚠️ RAG服务（8002端口）不可用，跳过文件上传到RAG知识库")
                        app_logger.warning(f"⚠️ 提示：请检查RAG服务是否运行在8002端口，或检查RAG_API_ENDPOINT配置")
                
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
    size: int = Query(50, ge=1, le=100, description="每页数量"),  # 默认50，最大100
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取文件列表 - 基于用户权限
    """
    try:
        tags_list = tags.split(",") if tags else None
        
        # 管理员可以查看所有文件，普通用户只能查看自己的文件
        is_superuser = current_user.get('is_superuser', False)
        user_id = current_user.get('id')
        
        if is_superuser:
            # 管理员：获取所有文件
            files_data = await supabase_file_service.get_files(
                project_id=project_id,
                stage=stage,
                tags=tags_list,
                search=search,
                page=page,
                size=size
            )
        else:
            # 普通用户：只获取自己可访问的文件
            files_data = await supabase_file_service.get_files_by_user(
                user_id=str(user_id),
                project_id=project_id,
                stage=stage,
                tags=tags_list,
                search=search,
                page=page,
                size=size
            )
        
        # 转换为FileResponse格式，确保所有必需字段都有值
        files = []
        for file_data in files_data:
            # 确保必需字段有默认值
            if 'stage' not in file_data or file_data.get('stage') is None:
                file_data['stage'] = None  # 允许为None
            # 确保其他字段有默认值
            if 'tags' not in file_data or file_data.get('tags') is None:
                file_data['tags'] = []
            if 'is_public' not in file_data:
                file_data['is_public'] = False
            if 'access_level' not in file_data:
                file_data['access_level'] = 'all_users'
            if 'view_count' not in file_data:
                file_data['view_count'] = 0
            if 'download_count' not in file_data:
                file_data['download_count'] = 0
            if 'like_count' not in file_data:
                file_data['like_count'] = 0
            if 'version' not in file_data:
                file_data['version'] = 1
            if 'file_metadata' not in file_data:
                file_data['file_metadata'] = {}
            
            try:
                files.append(FileResponse(**file_data))
            except Exception as e:
                app_logger.warning(f"文件数据转换失败，跳过该文件: {file_data.get('id', 'unknown')}, 错误: {str(e)}")
                continue
        
        return files
        
    except Exception as e:
        app_logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取文件详情 - 基于用户权限
    """
    try:
        file_data = await supabase_file_service.get_file_info(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 权限检查：基于新的访问级别系统
        user_id = current_user.get('id')
        is_superuser = current_user.get('is_superuser', False)
        if not await supabase_file_service.user_can_access_file(file_id, str(user_id), is_superuser):
            raise HTTPException(status_code=403, detail="无权限访问此文件")
        
        # 确保所有必需字段都有默认值
        if 'stage' not in file_data or file_data.get('stage') is None:
            file_data['stage'] = None
        if 'tags' not in file_data or file_data.get('tags') is None:
            file_data['tags'] = []
        if 'is_public' not in file_data:
            file_data['is_public'] = False
        if 'access_level' not in file_data:
            file_data['access_level'] = 'all_users'
        if 'view_count' not in file_data:
            file_data['view_count'] = 0
        if 'download_count' not in file_data:
            file_data['download_count'] = 0
        if 'like_count' not in file_data:
            file_data['like_count'] = 0
        if 'version' not in file_data:
            file_data['version'] = 1
        if 'file_metadata' not in file_data:
            file_data['file_metadata'] = {}
        
        return FileResponse(**file_data)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"获取文件详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件详情失败: {str(e)}")

@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    下载文件 - 基于用户权限，从Supabase Storage下载
    """
    try:
        # 获取文件记录
        file_data = await supabase_file_service.get_file_info(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 权限检查：基于新的访问级别系统
        user_id = current_user.get('id')
        is_superuser = current_user.get('is_superuser', False)
        if not await supabase_file_service.user_can_access_file(file_id, str(user_id), is_superuser):
            raise HTTPException(status_code=403, detail="无权限下载此文件")
        
        # 从Supabase Storage下载文件
        file_content = await supabase_file_service.download_file(
            file_id=file_id,
            user_id=str(user_id)
        )
        
        if not file_content:
            raise HTTPException(status_code=500, detail="文件下载失败")
        
        # 更新下载次数
        await supabase_file_service.increment_download_count(file_id)
        
        # 处理文件名编码问题
        import urllib.parse
        encoded_filename = urllib.parse.quote(file_data.get('original_name', 'file').encode('utf-8'))
        
        # 将bytes转换为流
        from io import BytesIO
        file_stream = BytesIO(file_content)
        
        return StreamingResponse(
            file_stream,
            media_type=file_data.get('file_type', 'application/octet-stream'),
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
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    预览文件 - 从Supabase Storage获取
    """
    try:
        # 获取文件记录
        file_data = await supabase_file_service.get_file_info(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 权限检查
        user_id = current_user.get('id')
        is_superuser = current_user.get('is_superuser', False)
        if not await supabase_file_service.user_can_access_file(file_id, str(user_id), is_superuser):
            raise HTTPException(status_code=403, detail="无权限预览此文件")
        
        # 从Supabase Storage下载文件
        file_content = await supabase_file_service.download_file(
            file_id=file_id,
            user_id=str(user_id)
        )
        
        if not file_content:
            raise HTTPException(status_code=500, detail="文件预览失败")
        
        # 更新查看次数
        await supabase_file_service.increment_view_count(file_id)
        
        # 将bytes转换为流
        from io import BytesIO
        file_stream = BytesIO(file_content)
        
        return StreamingResponse(
            file_stream,
            media_type=file_data.get('file_type', 'application/octet-stream'),
            headers={
                "Content-Disposition": f"inline; filename={file_data.get('original_name', 'file')}"
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
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    更新文件信息
    """
    try:
        # 转换为字典格式
        update_dict = file_update.model_dump(exclude_unset=True)
        
        user_id = current_user.get('id')
        file_data = await supabase_file_service.update_file(
            file_id=file_id,
            file_update=update_dict,
            user_id=str(user_id)
        )
        
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在或无权限")
        
        # 确保所有必需字段都有默认值
        if 'stage' not in file_data or file_data.get('stage') is None:
            file_data['stage'] = None
        if 'tags' not in file_data or file_data.get('tags') is None:
            file_data['tags'] = []
        if 'is_public' not in file_data:
            file_data['is_public'] = False
        if 'access_level' not in file_data:
            file_data['access_level'] = 'all_users'
        if 'view_count' not in file_data:
            file_data['view_count'] = 0
        if 'download_count' not in file_data:
            file_data['download_count'] = 0
        if 'like_count' not in file_data:
            file_data['like_count'] = 0
        if 'version' not in file_data:
            file_data['version'] = 1
        if 'file_metadata' not in file_data:
            file_data['file_metadata'] = {}
        
        return FileResponse(**file_data)
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"更新文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新文件失败: {str(e)}")

@router.delete("/{file_id}")
async def delete_file(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    删除文件 - 从Supabase Storage删除，同时删除外部RAG文档
    """
    try:
        # 获取文件记录
        file_data = await supabase_file_service.get_file_info(file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 权限检查
        user_id = current_user.get('id')
        is_superuser = current_user.get('is_superuser', False)
        if not await supabase_file_service.user_can_access_file(file_id, str(user_id), is_superuser):
            raise HTTPException(status_code=403, detail="无权限删除此文件")
        
        # 删除外部RAG文档（如果存在映射）
        try:
            from app.services.rag_mapping_service import rag_mapping_service
            mapping = await rag_mapping_service.get_mapping_by_file_id(file_id)
            if mapping and rag_client.is_available():
                external_doc_id = mapping.get('external_document_id')
                collection_name = mapping.get('external_collection_name')
                if external_doc_id:
                    rag_result = await rag_client.delete_document(
                        document_id=external_doc_id,
                        collection_name=collection_name
                    )
                    if rag_result.get('success'):
                        app_logger.info(f"🤖 RAG文档删除成功: {external_doc_id}")
                    # 删除映射记录
                    await rag_mapping_service.delete_mapping(external_document_id=external_doc_id)
        except Exception as rag_error:
            app_logger.warning(f"⚠️ 删除RAG文档时出错（继续删除文件）: {rag_error}")
        
        # 从Supabase Storage删除文件（这会同时删除数据库记录）
        storage_deleted = await supabase_file_service.delete_file(
            file_id=file_id,
            user_id=str(user_id)
        )
        
        if not storage_deleted:
            app_logger.warning(f"⚠️ 文件删除失败: {file_data.get('original_name')}")
            raise HTTPException(status_code=500, detail="文件删除失败")
        else:
            app_logger.info(f"✅ 文件删除成功: {file_data.get('original_name')}")
        
        return {"message": "文件删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"文件删除失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")

@router.post("/{file_id}/extract-content")
async def extract_file_content(
    file_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    提取文件内容（已废弃）- 内容提取由外部RAG服务处理
    此接口保留用于兼容性，实际应使用外部RAG服务
    """
    raise HTTPException(
        status_code=410,
        detail="内容提取功能已迁移到外部RAG服务，请使用 /api/v1/files/upload-rag 接口上传文件"
    )

@router.get("/stats/summary")
async def get_file_stats(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    获取文件统计信息（性能优化：添加5秒缓存）
    """
    try:
        is_superuser = current_user.get('is_superuser', False)
        user_id = str(current_user.get('id'))
        current_time = asyncio.get_event_loop().time()

        # 检查缓存（5秒有效期）
        cache_key = f"admin_{user_id}" if is_superuser else f"user_{user_id}"
        if (_stats_cache["data"] and
            _stats_cache["user_id"] == cache_key and
            current_time - _stats_cache["timestamp"] < 5.0):
            app_logger.info(f"🚀 使用缓存文件统计 (用户: {cache_key})")
            return {"message": "获取统计信息成功", "data": _stats_cache["data"]}

        # 缓存未命中，重新查询
        if is_superuser:
            stats = await supabase_file_service.get_file_stats_all()
        else:
            stats = await supabase_file_service.get_file_stats(user_id)

        # 更新缓存
        _stats_cache.update({
            "data": stats,
            "timestamp": current_time,
            "user_id": cache_key
        })

        app_logger.info(f"🔄 更新文件统计缓存 (用户: {cache_key})")
        return {"message": "获取统计信息成功", "data": stats}

    except Exception as e:
        app_logger.error(f"获取文件统计失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件统计失败: {str(e)}")

@router.post("/batch-index")
async def batch_index_files(
    project_id: Optional[str] = None,
    force_reindex: bool = False,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    批量上传文件到外部RAG知识库
    
    Args:
        project_id: 项目ID，如果指定则只处理该项目的文件
        force_reindex: 是否强制重新上传已处理的文件
    """
    try:
        if not rag_client.is_available():
            raise HTTPException(status_code=503, detail="RAG服务不可用")
        
        # 获取需要处理的文件
        if project_id:
            files_data = await supabase_file_service.get_files_by_project(project_id)
        else:
            files_data = await supabase_file_service.get_all_files()
        
        app_logger.info(f"🤖 开始批量上传到RAG，共 {len(files_data)} 个文件")
        
        uploaded_count = 0
        failed_count = 0
        
        for file_data in files_data:
            try:
                
                file_id = file_data.get('id')
                file_name = file_data.get('original_name', 'unknown')
                
                app_logger.info(f"🤖 正在上传文件到RAG: {file_name}")
                
                # 从Supabase Storage获取文件数据
                user_id = current_user.get('id')
                file_content = await supabase_file_service.download_file(
                    file_id=file_id,
                    user_id=str(user_id)
                )
                
                if not file_content:
                    app_logger.warning(f"⚠️ 文件下载失败，跳过: {file_name}")
                    failed_count += 1
                    continue
                
                # 构建元数据
                metadata = {
                    "uploaded_by": file_data.get('uploaded_by', str(user_id)),
                    "user_id": file_data.get('uploaded_by', str(user_id)),
                    "upload_time": file_data.get('created_at', datetime.now().isoformat()),
                    "description": file_data.get('description'),
                    "tags": file_data.get('tags', []),
                    "content_type": file_data.get('file_type'),
                    "file_size": file_data.get('file_size'),
                    "stage": file_data.get('stage')
                }
                
                # 确定collection名称
                file_project_id = file_data.get('project_id') or project_id
                collection_name = f"project_{file_project_id}" if file_project_id else rag_client.config.collection_name
                
                # 上传到外部RAG
                rag_result = await rag_client.upload_file(
                    file_content=file_content,
                    filename=file_name,
                    collection_name=collection_name,
                    metadata=metadata
                )
                
                if rag_result.success:
                    # 创建映射记录
                    from app.services.rag_mapping_service import rag_mapping_service
                    try:
                        await rag_mapping_service.create_mapping(
                            local_file_id=file_id,
                            external_document_id=rag_result.document_id,
                            external_collection_name=collection_name,
                            project_id=file_project_id,
                            chunk_count=rag_result.chunk_count
                        )
                    except Exception as mapping_error:
                        app_logger.warning(f"⚠️ 映射记录创建失败: {mapping_error}")
                    
                    uploaded_count += 1
                    app_logger.info(f"🤖 文件上传到RAG成功: {file_name}")
                else:
                    failed_count += 1
                    app_logger.warning(f"🤖 文件上传到RAG失败: {file_name}, 原因: {rag_result.message}")
                    
            except Exception as file_error:
                failed_count += 1
                app_logger.error(f"🤖 处理文件失败: {file_data.get('original_name', 'unknown')}, 错误: {str(file_error)}")
        
        app_logger.info(f"🤖 批量上传完成，成功: {uploaded_count}, 失败: {failed_count}")
        
        return {
            "message": "批量上传完成",
            "uploaded_count": uploaded_count,
            "failed_count": failed_count,
            "total_processed": uploaded_count + failed_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"批量上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")

@router.get("/search-context")
async def search_file_context(
    query: str,
    project_id: Optional[str] = None,
    limit: int = 5,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    搜索文件上下文（用于AI问答）- 使用外部RAG服务
    
    Args:
        query: 搜索查询
        project_id: 项目ID筛选
        limit: 返回结果数量限制
    """
    try:
        if not rag_client.is_available():
            raise HTTPException(status_code=503, detail="RAG服务不可用")
        
        # 确定collection名称
        collection_name = f"project_{project_id}" if project_id else rag_client.config.collection_name
        
        # 使用外部RAG服务查询
        rag_result = await rag_client.query(
            query_text=query,
            collection_name=collection_name,
            top_k=limit,
            similarity_threshold=0.7
        )
        
        return {
            "message": "搜索完成",
            "query": query,
            "project_id": project_id,
            "answer": rag_result.answer,
            "sources": rag_result.sources,
            "processing_time": rag_result.processing_time
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"搜索文件上下文失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索文件上下文失败: {str(e)}") 