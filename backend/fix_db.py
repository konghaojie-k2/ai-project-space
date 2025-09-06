import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.models.project_member import ProjectMember

def main():
    print("开始修复数据库...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        
        # 检查表是否存在
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='project_members'
            """))
            
            if result.fetchone():
                print("project_members 表已存在")
            else:
                print("创建 project_members 表...")
                ProjectMember.__table__.create(engine, checkfirst=True)
                print("✅ project_members 表创建成功")
        
        # 验证表结构
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(project_members)"))
            columns = result.fetchall()
            
            print("表结构:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
        
        print("数据库修复完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
