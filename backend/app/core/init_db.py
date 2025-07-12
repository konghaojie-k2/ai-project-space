from loguru import logger
from sqlalchemy.orm import Session

from app.core.database import engine, SessionLocal
from app.models.file import FileRecord, FileVersion, FileShare, FileComment


def init_db() -> None:
    """初始化数据库"""
    try:
        # 创建所有表
        from app.models.file import Base
        Base.metadata.create_all(bind=engine)
        
        logger.info("数据库表创建成功")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


def create_sample_data() -> None:
    """创建示例数据"""
    try:
        db = SessionLocal()
        
        # 检查是否已有数据
        existing_files = db.query(FileRecord).first()
        if existing_files:
            logger.info("数据库已有数据，跳过示例数据创建")
            return
        
        # 创建示例文件记录
        sample_files = [
            FileRecord(
                original_name="项目需求文档.pdf",
                stored_name="sample_requirement.pdf",
                file_path="ai-project-files/sample_requirement.pdf",
                file_size=2048000,
                file_type="application/pdf",
                file_extension=".pdf",
                stage="售前阶段",
                tags=["需求", "重要"],
                description="AI项目管理系统的需求文档",
                uploaded_by="admin",
                is_public=True
            ),
            FileRecord(
                original_name="用户调研报告.docx",
                stored_name="sample_research.docx",
                file_path="ai-project-files/sample_research.docx",
                file_size=1536000,
                file_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                file_extension=".docx",
                stage="业务调研",
                tags=["调研", "用户"],
                description="用户需求调研报告",
                uploaded_by="admin",
                is_public=True
            ),
            FileRecord(
                original_name="数据分析图表.png",
                stored_name="sample_chart.png",
                file_path="ai-project-files/sample_chart.png",
                file_size=512000,
                file_type="image/png",
                file_extension=".png",
                stage="数据理解",
                tags=["图表", "分析"],
                description="数据分析可视化图表",
                uploaded_by="admin",
                is_public=True
            )
        ]
        
        for file_record in sample_files:
            db.add(file_record)
        
        db.commit()
        logger.info("示例数据创建成功")
        
    except Exception as e:
        logger.error(f"创建示例数据失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    create_sample_data() 