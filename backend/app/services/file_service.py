import asyncio
import io
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
import mimetypes

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from loguru import logger

from app.models.file import FileRecord, FileVersion, FileShare, FileComment
from app.schemas.file import FileCreate, FileUpdate, FileResponse, FileStatsResponse, FileAccessLevel
from app.core.database import get_db
from app.utils.file_utils import extract_text_from_pdf, extract_text_from_docx, extract_text_from_xlsx

def _fix_access_level_enum(file_dict: dict) -> dict:
    """确保access_level字段是有效的字符串值"""
    access_level = file_dict.get('access_level')
    if access_level not in ["all_users", "admins_only", "owner_only"]:
        # 如果不是有效值，使用默认值
        file_dict['access_level'] = "all_users"
    return file_dict

class FileService:
    """文件服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_file(self, file_create: FileCreate) -> FileResponse:
        """
        创建文件记录
        
        Args:
            file_create: 文件创建数据
            
        Returns:
            FileResponse: 创建的文件记录
        """
        try:
            logger.info(f"🔥 FileService.create_file - 开始创建文件记录")
            logger.info(f"🔥 FileCreate数据: {file_create}")
            
            # 创建文件记录
            logger.info(f"🔥 开始创建FileRecord对象")
            file_record = FileRecord(
                original_name=file_create.original_name,
                stored_name=file_create.stored_name,
                file_path=file_create.file_path,
                file_size=file_create.file_size,
                file_type=file_create.file_type,
                file_extension=Path(file_create.original_name).suffix,
                project_id=file_create.project_id,
                stage=file_create.stage,
                tags=file_create.tags,
                description=file_create.description,
                uploaded_by=file_create.uploaded_by,
                user_id=file_create.user_id,
                is_public=file_create.is_public,
                access_level=file_create.access_level
            )
            logger.info(f"🔥 FileRecord对象创建成功: {file_record}")
            
            logger.info(f"🔥 开始添加到数据库会话")
            self.db.add(file_record)
            
            logger.info(f"🔥 开始提交数据库事务")
            self.db.commit()
            
            logger.info(f"🔥 开始刷新文件记录")
            self.db.refresh(file_record)
            
            logger.info(f"🔥 文件记录创建成功: {file_record.id}")
            
            # 确保file_metadata是字典类型
            logger.info(f"🔥 检查file_metadata类型: {type(file_record.file_metadata)}")
            if not isinstance(file_record.file_metadata, dict):
                logger.warning(f"🔥 file_metadata不是字典类型，将设置为空字典")
                file_record.file_metadata = {}
            else:
                logger.info(f"🔥 file_metadata是字典类型: {file_record.file_metadata}")
                
            logger.info(f"🔥 开始创建FileResponse对象")
            # 使用to_dict方法来避免SQLAlchemy MetaData对象的问题
            file_dict = file_record.to_dict()
            response = FileResponse(**file_dict)
            logger.info(f"🔥 FileResponse对象创建成功: {response.id}")
            
            return response
            
        except Exception as e:
            logger.error(f"🔥 FileService.create_file - 创建文件记录失败: {e}")
            logger.error(f"🔥 异常类型: {type(e).__name__}")
            logger.error(f"🔥 异常详情: {str(e)}")
            import traceback
            logger.error(f"🔥 异常堆栈: {traceback.format_exc()}")
            
            self.db.rollback()
            logger.info(f"🔥 数据库事务已回滚")
            raise
    
    def get_file_by_id(self, file_id: str) -> Optional[FileResponse]:
        """
        根据ID获取文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            Optional[FileResponse]: 文件记录
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                FileRecord.id == file_id
            ).first()
            
            if not file_record:
                return None
            
            # 确保file_metadata是字典类型
            if not isinstance(file_record.file_metadata, dict):
                file_record.file_metadata = {}
                
            # 使用to_dict方法来避免SQLAlchemy MetaData对象的问题
            file_dict = file_record.to_dict()
            file_dict = _fix_access_level_enum(file_dict)
            return FileResponse(**file_dict)
            
        except Exception as e:
            logger.error(f"获取文件记录失败: {e}")
            raise
    
    def get_files_by_user(
        self,
        user_id: int,
        project_id: Optional[str] = None,
        stage: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> List[FileResponse]:
        """
        获取用户的文件列表
        """
        try:
            query = self.db.query(FileRecord).filter(
                FileRecord.is_deleted == False,
                or_(
                    FileRecord.access_level == "all_users",  # 全员可见
                    FileRecord.user_id == user_id,  # 用户自己的文件
                    FileRecord.is_public == True     # 或者公开文件（向后兼容）
                )
            )
            
            # 应用筛选条件
            if project_id:
                query = query.filter(FileRecord.project_id == project_id)
            if stage:
                query = query.filter(FileRecord.stage == stage)
            if tags:
                for tag in tags:
                    query = query.filter(FileRecord.tags.contains([tag]))
            if search:
                query = query.filter(
                    or_(
                        FileRecord.original_name.contains(search),
                        FileRecord.description.contains(search)
                    )
                )
            
            # 分页
            offset = (page - 1) * size
            files = query.order_by(desc(FileRecord.created_at)).offset(offset).limit(size).all()
            
            # 使用to_dict方法来避免SQLAlchemy MetaData对象的问题
            result = []
            for file_record in files:
                if not isinstance(file_record.file_metadata, dict):
                    file_record.file_metadata = {}
                file_dict = file_record.to_dict()
                file_dict = _fix_access_level_enum(file_dict)
                result.append(FileResponse(**file_dict))
            return result
            
        except Exception as e:
            logger.error(f"获取用户文件列表失败: {str(e)}")
            raise

    def user_can_access_file(self, user_id: int, file_id: str, is_admin: bool = False) -> bool:
        """
        检查用户是否可以访问指定文件
        基于新的访问级别系统
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                FileRecord.id == file_id,
                FileRecord.is_deleted == False
            ).first()
            
            if not file_record:
                return False
            
            # 根据访问级别判断权限（使用字符串比较）
            if file_record.access_level == "all_users":
                return True  # 全员可见
            elif file_record.access_level == "admins_only":
                return is_admin  # 仅管理员
            elif file_record.access_level == "owner_only":
                return file_record.user_id == user_id  # 仅上传者
            
            # 向后兼容：如果没有设置access_level，使用原来的逻辑
            return file_record.user_id == user_id or file_record.is_public
            
        except Exception as e:
            logger.error(f"检查文件访问权限失败: {str(e)}")
            return False

    def get_files(
        self,
        project_id: Optional[str] = None,
        stage: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20
    ) -> List[FileResponse]:
        """
        获取文件列表
        
        Args:
            project_id: 项目ID筛选
            stage: 项目阶段筛选
            tags: 标签筛选
            search: 搜索关键词
            page: 页码
            size: 每页数量
            
        Returns:
            List[FileResponse]: 文件列表
        """
        try:
            query = self.db.query(FileRecord).filter(FileRecord.is_deleted == False)
            
            # 项目ID筛选
            if project_id:
                query = query.filter(FileRecord.project_id == project_id)
            
            # 阶段筛选
            if stage:
                query = query.filter(FileRecord.stage == stage)
            
            # 标签筛选
            if tags:
                for tag in tags:
                    query = query.filter(FileRecord.tags.contains([tag]))
            
            # 搜索筛选
            if search:
                search_filter = or_(
                    FileRecord.original_name.ilike(f"%{search}%"),
                    FileRecord.description.ilike(f"%{search}%"),
                    FileRecord.content.ilike(f"%{search}%")
                )
                query = query.filter(search_filter)
            
            # 分页
            offset = (page - 1) * size
            files = query.order_by(desc(FileRecord.created_at)).offset(offset).limit(size).all()
            
            # 使用to_dict方法来避免SQLAlchemy MetaData对象的问题
            result = []
            for file_record in files:
                if not isinstance(file_record.file_metadata, dict):
                    file_record.file_metadata = {}
                file_dict = file_record.to_dict()
                file_dict = _fix_access_level_enum(file_dict)
                result.append(FileResponse(**file_dict))
            return result
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {e}")
            raise
    
    def update_file(self, file_id: str, file_update: FileUpdate) -> Optional[FileResponse]:
        """
        更新文件信息
        
        Args:
            file_id: 文件ID
            file_update: 更新数据
            
        Returns:
            Optional[FileResponse]: 更新后的文件记录
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.id == file_id,
                    FileRecord.is_deleted == False
                )
            ).first()
            
            if not file_record:
                return None
            
            # 更新字段
            if file_update.original_name is not None:
                file_record.original_name = file_update.original_name
                # 同时更新文件扩展名
                file_record.file_extension = Path(file_update.original_name).suffix
            if file_update.description is not None:
                file_record.description = file_update.description
            if file_update.stage is not None:
                file_record.stage = file_update.stage
            if file_update.tags is not None:
                file_record.tags = file_update.tags
            if file_update.is_public is not None:
                file_record.is_public = file_update.is_public
            
            file_record.updated_at = datetime.now()
            
            self.db.commit()
            self.db.refresh(file_record)
            
            # 确保file_metadata是字典类型
            if not isinstance(file_record.file_metadata, dict):
                file_record.file_metadata = {}
            
            logger.info(f"文件记录更新成功: {file_id}")
            # 使用to_dict方法来避免SQLAlchemy MetaData对象的问题
            file_dict = file_record.to_dict()
            file_dict = _fix_access_level_enum(file_dict)
            return FileResponse(**file_dict)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新文件记录失败: {e}")
            raise
    
    def delete_file(self, file_id: str) -> bool:
        """
        删除文件（软删除）
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.id == file_id,
                    FileRecord.is_deleted == False
                )
            ).first()
            
            if not file_record:
                return False
            
            file_record.is_deleted = True
            file_record.updated_at = datetime.now()
            
            self.db.commit()
            
            logger.info(f"文件记录删除成功: {file_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除文件记录失败: {e}")
            raise
    
    def increment_view_count(self, file_id: str) -> bool:
        """
        增加查看次数
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.id == file_id,
                    FileRecord.is_deleted == False
                )
            ).first()
            
            if not file_record:
                return False
            
            file_record.view_count += 1
            file_record.updated_at = datetime.now()
            
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新查看次数失败: {e}")
            raise
    
    def increment_download_count(self, file_id: str) -> bool:
        """
        增加下载次数
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.id == file_id,
                    FileRecord.is_deleted == False
                )
            ).first()
            
            if not file_record:
                return False
            
            file_record.download_count += 1
            file_record.updated_at = datetime.now()
            
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新下载次数失败: {e}")
            raise
    
    async def extract_content(self, file_data: bytes, file_type: str) -> str:
        """
        提取文件内容
        
        Args:
            file_data: 文件数据
            file_type: 文件类型
            
        Returns:
            str: 提取的文本内容
        """
        try:
            content = ""
            
            if file_type == "application/pdf":
                content = extract_text_from_pdf(io.BytesIO(file_data))
            elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
                content = extract_text_from_docx(io.BytesIO(file_data))
            elif file_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
                content = extract_text_from_xlsx(io.BytesIO(file_data))
            elif file_type.startswith("text/"):
                content = file_data.decode("utf-8", errors="ignore")
            else:
                logger.warning(f"不支持的文件类型: {file_type}")
                content = ""
            
            return content
            
        except Exception as e:
            logger.error(f"提取文件内容失败: {e}")
            return ""
    
    async def update_file_content(self, file_id: str, content: str) -> bool:
        """
        更新文件内容
        
        Args:
            file_id: 文件ID
            content: 提取的内容
            
        Returns:
            bool: 更新是否成功
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.id == file_id,
                    FileRecord.is_deleted == False
                )
            ).first()
            
            if not file_record:
                return False
            
            file_record.content = content
            file_record.content_length = len(content)
            file_record.is_processed = True
            file_record.updated_at = datetime.now()
            
            self.db.commit()
            
            logger.info(f"文件内容更新成功: {file_id}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新文件内容失败: {e}")
            raise
    
    async def get_file_stats(self) -> FileStatsResponse:
        """
        获取文件统计信息
        
        Returns:
            FileStatsResponse: 文件统计信息
        """
        try:
            # 总文件数和总大小
            total_stats = self.db.query(
                func.count(FileRecord.id).label('total_files'),
                func.sum(FileRecord.file_size).label('total_size')
            ).filter(FileRecord.is_deleted == False).first()
            
            total_files = total_stats.total_files or 0
            total_size = total_stats.total_size or 0
            
            # 按阶段分组
            stage_stats = self.db.query(
                FileRecord.stage,
                func.count(FileRecord.id).label('count')
            ).filter(FileRecord.is_deleted == False).group_by(FileRecord.stage).all()
            
            files_by_stage = {stage: count for stage, count in stage_stats}
            
            # 按类型分组
            type_stats = self.db.query(
                FileRecord.file_type,
                func.count(FileRecord.id).label('count')
            ).filter(FileRecord.is_deleted == False).group_by(FileRecord.file_type).all()
            
            files_by_type = {file_type: count for file_type, count in type_stats}
            
            # 最近上传的文件
            recent_files = self.db.query(FileRecord).filter(
                FileRecord.is_deleted == False
            ).order_by(desc(FileRecord.created_at)).limit(5).all()
            
            # 使用to_dict方法来避免SQLAlchemy MetaData对象的问题
            recent_uploads = []
            for file_record in recent_files:
                if not isinstance(file_record.file_metadata, dict):
                    file_record.file_metadata = {}
                file_dict = file_record.to_dict()
                recent_uploads.append(FileResponse(**file_dict))
            
            # 热门文件（按查看次数排序）
            popular_files = self.db.query(FileRecord).filter(
                FileRecord.is_deleted == False
            ).order_by(desc(FileRecord.view_count)).limit(5).all()
            
            popular_files_list = []
            for file_record in popular_files:
                if not isinstance(file_record.file_metadata, dict):
                    file_record.file_metadata = {}
                file_dict = file_record.to_dict()
                popular_files_list.append(FileResponse(**file_dict))
            
            return FileStatsResponse(
                total_files=total_files,
                total_size=total_size,
                files_by_stage=files_by_stage,
                files_by_type=files_by_type,
                recent_uploads=recent_uploads,
                popular_files=popular_files_list
            )
            
        except Exception as e:
            logger.error(f"获取文件统计失败: {e}")
            raise
    
    async def search_files(
        self,
        query: Optional[str] = None,
        stage: Optional[str] = None,
        tags: Optional[List[str]] = None,
        file_type: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        搜索文件
        
        Args:
            query: 搜索关键词
            stage: 项目阶段
            tags: 标签列表
            file_type: 文件类型
            date_from: 开始日期
            date_to: 结束日期
            page: 页码
            size: 每页数量
            sort_by: 排序字段
            sort_order: 排序方向
            
        Returns:
            Dict[str, Any]: 搜索结果
        """
        try:
            query_obj = self.db.query(FileRecord).filter(FileRecord.is_deleted == False)
            
            # 关键词搜索
            if query:
                search_filter = or_(
                    FileRecord.original_name.ilike(f"%{query}%"),
                    FileRecord.description.ilike(f"%{query}%"),
                    FileRecord.content.ilike(f"%{query}%")
                )
                query_obj = query_obj.filter(search_filter)
            
            # 阶段筛选
            if stage:
                query_obj = query_obj.filter(FileRecord.stage == stage)
            
            # 标签筛选
            if tags:
                for tag in tags:
                    query_obj = query_obj.filter(FileRecord.tags.contains([tag]))
            
            # 文件类型筛选
            if file_type:
                query_obj = query_obj.filter(FileRecord.file_type.ilike(f"%{file_type}%"))
            
            # 日期范围筛选
            if date_from:
                query_obj = query_obj.filter(FileRecord.created_at >= date_from)
            if date_to:
                query_obj = query_obj.filter(FileRecord.created_at <= date_to)
            
            # 排序
            if sort_order.lower() == "desc":
                query_obj = query_obj.order_by(desc(getattr(FileRecord, sort_by)))
            else:
                query_obj = query_obj.order_by(getattr(FileRecord, sort_by))
            
            # 获取总数
            total = query_obj.count()
            
            # 分页
            offset = (page - 1) * size
            files = query_obj.offset(offset).limit(size).all()
            
            # 使用to_dict方法来避免SQLAlchemy MetaData对象的问题
            files_response = []
            for file_record in files:
                if not isinstance(file_record.file_metadata, dict):
                    file_record.file_metadata = {}
                file_dict = file_record.to_dict()
                files_response.append(FileResponse(**file_dict))
            
            return {
                "files": files_response,
                "total": total,
                "page": page,
                "size": size,
                "total_pages": (total + size - 1) // size
            }
            
        except Exception as e:
            logger.error(f"搜索文件失败: {e}")
            raise 
    
    def mark_file_processed(self, file_id: str) -> bool:
        """
        标记文件已处理（已索引到向量数据库）
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 标记是否成功
        """
        try:
            file_record = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.id == file_id,
                    FileRecord.is_deleted == False
                )
            ).first()
            
            if not file_record:
                logger.warning(f"文件不存在或已删除: {file_id}")
                return False
            
            file_record.is_processed = True
            self.db.commit()
            
            logger.info(f"文件已标记为已处理: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"标记文件已处理失败: {e}")
            self.db.rollback()
            return False
    
    def get_files_by_project(self, project_id: str) -> List[FileRecord]:
        """
        获取项目的所有文件
        
        Args:
            project_id: 项目ID
            
        Returns:
            List[FileRecord]: 文件列表
        """
        try:
            files = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.project_id == project_id,
                    FileRecord.is_deleted == False
                )
            ).all()
            
            return files
            
        except Exception as e:
            logger.error(f"获取项目文件失败: {e}")
            return []
    
    def get_all_unprocessed_files(self) -> List[FileRecord]:
        """
        获取所有未处理的文件
        
        Returns:
            List[FileRecord]: 文件列表
        """
        try:
            files = self.db.query(FileRecord).filter(
                and_(
                    FileRecord.is_deleted == False,
                    FileRecord.is_processed == False
                )
            ).all()
            
            return files
            
        except Exception as e:
            logger.error(f"获取未处理文件失败: {e}")
            return []
    
    def get_all_files(self) -> List[FileRecord]:
        """
        获取所有文件
        
        Returns:
            List[FileRecord]: 文件列表
        """
        try:
            files = self.db.query(FileRecord).filter(
                FileRecord.is_deleted == False
            ).all()
            
            return files
            
        except Exception as e:
            logger.error(f"获取所有文件失败: {e}")
            return [] 