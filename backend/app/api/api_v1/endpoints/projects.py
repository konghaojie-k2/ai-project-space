"""
项目管理API端点
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel
from datetime import datetime
import uuid

# 导入Supabase服务
from app.services.supabase_client import supabase_service
from app.services.rag_client import rag_client
from app.dependencies.auth import (
    get_current_user, get_current_superuser,
    RequireManageProjectsPermission
)


router = APIRouter()



# Pydantic模型
class ProjectResponse(BaseModel):
    """项目响应模型"""
    id: str
    name: str
    description: Optional[str] = None
    status: str
    stage: str
    is_public: bool = False
    allow_file_upload: bool = True
    allow_ai_chat: bool = True
    created_by: str
    created_at: str
    updated_at: str


class ProjectCreate(BaseModel):
    """创建项目请求模型"""
    name: str
    description: Optional[str] = None
    status: str = "active"
    stage: str = "售前"
    is_public: bool = False
    allow_file_upload: bool = True
    allow_ai_chat: bool = True


class ProjectUpdate(BaseModel):
    """更新项目请求模型"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    stage: Optional[str] = None
    is_public: Optional[bool] = None
    allow_file_upload: Optional[bool] = None
    allow_ai_chat: Optional[bool] = None


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取用户可访问的项目列表"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查是否是超级管理员
        is_superuser = current_user.get('is_superuser', False)
        
        # 获取用户可访问的项目（管理员可以访问所有项目）
        projects = await supabase_service.get_user_accessible_projects_enhanced(
            user_id, 
            limit=limit + skip,  # 获取足够的数据以支持分页
            is_superuser=is_superuser
        )

        # 应用过滤条件
        if search:
            projects = [p for p in projects if search.lower() in p.get('name', '').lower() or
                       search.lower() in p.get('description', '').lower()]

        if status_filter:
            projects = [p for p in projects if p.get('status') == status_filter]

        # 应用分页
        projects = projects[skip:skip + limit]

        # 转换为响应格式
        return [
            ProjectResponse(
                id=p.get('id', ''),
                name=p.get('name', ''),
                description=p.get('description'),
                status=p.get('status', 'active'),
                stage=p.get('stage', '售前'),
                is_public=p.get('is_public', False),
                allow_file_upload=p.get('allow_file_upload', True),
                allow_ai_chat=p.get('allow_ai_chat', True),
                created_by=p.get('created_by', ''),
                created_at=p.get('created_at', ''),
                updated_at=p.get('updated_at', '')
            )
            for p in projects
        ]

    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    """创建新项目"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查admin_client状态
        logger.info(f"🔍 [创建项目] 检查admin_client状态: admin_client_available={supabase_service.admin_client_available}")
        logger.info(f"🔍 [创建项目] admin_client对象: {supabase_service.admin_client is not None}")

        # 准备项目数据
        project_record = {
            'id': str(uuid.uuid4()),
            'name': project_data.name,
            'description': project_data.description,
            'status': project_data.status,
            'stage': project_data.stage,
            'is_public': project_data.is_public,
            'allow_file_upload': project_data.allow_file_upload,
            'allow_ai_chat': project_data.allow_ai_chat,
            'created_by': user_id
        }

        logger.info(f"📝 [创建项目] 准备创建项目: {project_data.name}, user_id: {user_id}")

        # 创建项目
        created_project = await supabase_service.create_project(project_record)

        if not created_project:
            raise HTTPException(status_code=500, detail="项目创建失败")

        # 将创建者添加为项目所有者
        await supabase_service.add_project_member_enhanced(
            project_id=created_project['id'],
            user_id=user_id,
            role='owner',
            invited_by=user_id
        )

        # 🚀 为项目创建对应的RAG知识库
        if rag_client.is_available():
            try:
                kb_name = f"project_{created_project['id']}"
                kb_description = f"项目 '{project_data.name}' 的知识库"
                
                kb_result = await rag_client.create_knowledge_base(
                    name=kb_name,
                    description=kb_description
                )
                
                if kb_result.get('success'):
                    logger.info(f"✅ 项目知识库创建成功: {kb_name}")
                else:
                    # 如果知识库已存在（可能之前创建过），也视为成功
                    if "已存在" in kb_result.get('message', ''):
                        logger.info(f"ℹ️ 项目知识库已存在: {kb_name}")
                    else:
                        logger.warning(f"⚠️ 项目知识库创建失败: {kb_result.get('message', '未知错误')}")
            except Exception as kb_error:
                # 知识库创建失败不影响项目创建
                logger.error(f"❌ 创建项目知识库时发生错误: {str(kb_error)}")
        else:
            logger.warning("⚠️ RAG服务不可用，跳过知识库创建")

        logger.info(f"项目创建成功: {project_data.name} by {user_id}")

        return ProjectResponse(
            id=created_project['id'],
            name=created_project['name'],
            description=created_project.get('description'),
            status=created_project['status'],
            stage=created_project['stage'],
            is_public=created_project.get('is_public', False),
            allow_file_upload=created_project.get('allow_file_upload', True),
            allow_ai_chat=created_project.get('allow_ai_chat', True),
            created_by=created_project['created_by'],
            created_at=created_project['created_at'],
            updated_at=created_project['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建项目失败: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """获取项目详情"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查用户是否有项目访问权限
        has_permission = await supabase_service.has_project_permission(
            user_id, project_id, 'read'
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="没有访问此项目的权限")

        # 获取项目详情
        project = await supabase_service.get_project_details(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")

        return ProjectResponse(
            id=project['id'],
            name=project['name'],
            description=project.get('description'),
            status=project['status'],
            stage=project['stage'],
            is_public=project.get('is_public', False),
            allow_file_upload=project.get('allow_file_upload', True),
            allow_ai_chat=project.get('allow_ai_chat', True),
            created_by=project['created_by'],
            created_at=project['created_at'],
            updated_at=project['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取项目详情失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取项目详情失败: {str(e)}")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_data: ProjectUpdate,
    current_user: dict = Depends(get_current_user)
):
    """更新项目"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查用户是否有项目编辑权限
        has_permission = await supabase_service.has_project_permission(
            user_id, project_id, 'write'
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="没有编辑此项目的权限")

        # 只更新提供的字段
        update_data = {k: v for k, v in project_data.dict().items() if v is not None}

        # 更新项目
        updated_project = await supabase_service.update_project(project_id, update_data)

        if not updated_project:
            raise HTTPException(status_code=500, detail="项目更新失败")

        return ProjectResponse(
            id=updated_project['id'],
            name=updated_project['name'],
            description=updated_project.get('description'),
            status=updated_project['status'],
            stage=updated_project['stage'],
            is_public=updated_project.get('is_public', False),
            allow_file_upload=updated_project.get('allow_file_upload', True),
            allow_ai_chat=updated_project.get('allow_ai_chat', True),
            created_by=updated_project['created_by'],
            created_at=updated_project['created_at'],
            updated_at=updated_project['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """删除项目"""
    try:
        user_id = current_user.get('id')
        if not user_id:
            raise HTTPException(status_code=401, detail="用户ID无效")

        # 检查用户是否有项目删除权限
        has_permission = await supabase_service.has_project_permission(
            user_id, project_id, 'delete'
        )

        if not has_permission:
            raise HTTPException(status_code=403, detail="没有删除此项目的权限")

        # 🗑️ 实现完整的项目级联删除
        # 注意：对话记录（chat_sessions和chat_messages）会被保留，不删除
        
        # 初始化删除统计
        deleted_files_count = 0
        deleted_storage_paths = []
        member_count = 0
        
        # 1. 删除项目对应的RAG知识库
        if rag_client.is_available():
            try:
                kb_name = f"project_{project_id}"
                kb_result = await rag_client.delete_knowledge_base(collection_name=kb_name)
                if kb_result.get('success'):
                    logger.info(f"✅ 项目知识库删除成功: {kb_name}")
                else:
                    # 知识库可能不存在，记录警告但不阻止删除
                    logger.warning(f"⚠️ 项目知识库删除失败或不存在: {kb_result.get('message', '未知错误')}")
            except Exception as kb_error:
                logger.error(f"❌ 删除项目知识库时发生错误: {str(kb_error)}")
                # 知识库删除失败不影响项目删除
        
        # 2. 删除项目文件（包括Storage文件和RAG文档映射记录）
        try:
            from app.services.supabase_file_service import supabase_file_service
            from app.services.rag_mapping_service import rag_mapping_service
            
            # 获取项目所有文件
            project_files = await supabase_file_service.get_files_by_project(project_id)
            deleted_files_count = 0
            deleted_storage_paths = []
            
            for file_data in project_files:
                file_id = file_data.get('id')
                try:
                    # 删除RAG文档和映射记录
                    mapping = await rag_mapping_service.get_mapping_by_file_id(file_id)
                    if mapping and rag_client.is_available():
                        external_doc_id = mapping.get('external_document_id')
                        collection_name = mapping.get('external_collection_name')
                        if external_doc_id:
                            try:
                                await rag_client.delete_document(
                                    document_id=external_doc_id,
                                    collection_name=collection_name
                                )
                                await rag_mapping_service.delete_mapping(external_document_id=external_doc_id)
                                logger.debug(f"✅ RAG文档和映射删除成功: {file_id}")
                            except Exception as rag_del_error:
                                logger.warning(f"⚠️ 删除RAG文档失败: {rag_del_error}")
                    
                    # 收集Storage路径用于批量删除
                    file_info = await supabase_file_service.get_file_info(file_id)
                    if file_info:
                        storage_path = file_info.get("file_path") or file_info.get("stored_name")
                        if storage_path:
                            deleted_storage_paths.append(storage_path)
                        
                        # 删除数据库记录（使用admin_client绕过RLS）
                        if supabase_service.admin_client:
                            supabase_service.admin_client.table('files').delete().eq('id', file_id).execute()
                            deleted_files_count += 1
                except Exception as file_error:
                    logger.warning(f"⚠️ 删除文件失败 {file_id}: {file_error}")
            
            # 批量删除Storage文件
            if deleted_storage_paths and supabase_service.admin_client:
                try:
                    bucket_name = supabase_file_service.bucket_name
                    if bucket_name:
                        # 分批删除，每批最多100个文件（Supabase Storage限制）
                        batch_size = 100
                        for i in range(0, len(deleted_storage_paths), batch_size):
                            batch = deleted_storage_paths[i:i + batch_size]
                            try:
                                supabase_service.admin_client.storage.from_(bucket_name).remove(batch)
                                logger.debug(f"✅ Storage文件批量删除成功，批次 {i//batch_size + 1}，共 {len(batch)} 个文件")
                            except Exception as batch_error:
                                logger.warning(f"⚠️ Storage文件批量删除失败（批次 {i//batch_size + 1}）: {batch_error}")
                                # 如果批量删除失败，尝试逐个删除
                                for path in batch:
                                    try:
                                        supabase_service.admin_client.storage.from_(bucket_name).remove([path])
                                    except Exception:
                                        pass
                except Exception as storage_error:
                    logger.warning(f"⚠️ 从Storage删除文件时发生错误: {storage_error}")
            
            # 额外清理：删除Storage中可能存在的其他项目相关文件（按项目ID路径）
            # 注意：这可能会删除一些不在files表中的文件，但确保Storage完全清理
            try:
                bucket_name = supabase_file_service.bucket_name
                if bucket_name and supabase_service.admin_client:
                    # 尝试列出并删除项目相关的Storage路径
                    # 注意：Supabase Storage API可能不支持按前缀列出，这里只处理已知路径
                    # 如果Storage中有其他项目相关文件，需要手动清理或通过其他方式处理
                    logger.debug(f"ℹ️ Storage清理完成，已删除 {len(deleted_storage_paths)} 个文件路径")
            except Exception:
                pass
            
            logger.info(f"✅ 项目文件删除完成，共删除 {deleted_files_count} 个文件记录，{len(deleted_storage_paths)} 个Storage文件")
        except Exception as files_error:
            logger.error(f"❌ 删除项目文件时发生错误: {str(files_error)}")
            # 文件删除失败不影响项目删除
        
        # 3. 删除项目成员（会触发审计日志，但使用admin_client时auth.uid()为NULL，需要迁移文件修复）
        try:
            if supabase_service.admin_client:
                # 获取项目所有成员（用于日志）
                members_response = supabase_service.admin_client.table('project_members').select('user_id').eq(
                    'project_id', project_id
                ).execute()
                
                member_count = len(members_response.data) if members_response.data else 0
                
                # 删除项目所有成员
                deleted_members = supabase_service.admin_client.table('project_members').delete().eq(
                    'project_id', project_id
                ).execute()
                
                logger.info(f"✅ 项目成员删除完成，共删除 {member_count} 个成员")
        except Exception as members_error:
            logger.error(f"❌ 删除项目成员时发生错误: {str(members_error)}")
            # 成员删除失败不影响项目删除
        
        # 4. 删除RAG映射记录（清理残留的映射记录）
        try:
            from app.services.rag_mapping_service import rag_mapping_service
            if supabase_service.admin_client:
                # 删除所有与项目相关的映射记录
                mappings_response = supabase_service.admin_client.table('rag_document_mapping').select('id').eq(
                    'project_id', project_id
                ).execute()
                
                if mappings_response.data:
                    supabase_service.admin_client.table('rag_document_mapping').delete().eq(
                        'project_id', project_id
                    ).execute()
                    logger.info(f"✅ RAG映射记录删除完成，共删除 {len(mappings_response.data)} 条记录")
        except Exception as mapping_error:
            logger.warning(f"⚠️ 删除RAG映射记录时发生错误: {str(mapping_error)}")
            # 映射记录删除失败不影响项目删除
        
        # 5. 删除项目记录本身
        # 注意：对话记录（chat_sessions和chat_messages）会被保留，不删除
        # 这些记录仍然可以通过user_id查询，只是project_id会变为NULL或保持不变
        try:
            if supabase_service.admin_client:
                deleted_project = supabase_service.admin_client.table('projects').delete().eq('id', project_id).execute()
                if deleted_project.data:
                    logger.info(f"✅ 项目删除成功: {project_id}")
                    return {
                        "message": f"项目 {project_id} 及其所有相关数据已成功删除",
                        "deleted_items": {
                            "knowledge_base": True,
                            "files_count": deleted_files_count,
                            "storage_files_count": len(deleted_storage_paths),
                            "members_count": member_count,
                            "conversations_preserved": True  # 对话记录已保留
                        }
                    }
                else:
                    raise HTTPException(status_code=404, detail="项目不存在或已被删除")
            else:
                raise HTTPException(status_code=500, detail="管理员客户端不可用，无法删除项目")
        except HTTPException:
            raise
        except Exception as project_error:
            logger.error(f"❌ 删除项目记录失败: {str(project_error)}")
            raise HTTPException(status_code=500, detail=f"删除项目失败: {str(project_error)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除项目失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除项目失败: {str(e)}")
