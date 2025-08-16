#!/usr/bin/env python3
"""
修复数据库中文件名编码问题的脚本
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.file import FileRecord

def fix_file_names():
    """修复数据库中文件名编码问题"""
    print("开始修复文件名编码问题...")
    
    # 获取数据库会话
    db = SessionLocal()
    
    try:
        # 查询所有文件记录
        files = db.query(FileRecord).filter(FileRecord.is_deleted == False).all()
        
        fixed_count = 0
        for file_record in files:
            original_name = file_record.original_name
            
            # 检查是否包含乱码字符
            if '?' in original_name or len(original_name.encode('utf-8', errors='ignore')) < len(original_name):
                print(f"发现乱码文件名: {original_name}")
                
                # 尝试根据存储文件名和扩展名重建文件名
                stored_name = file_record.stored_name
                file_extension = file_record.file_extension or ''
                
                # 生成一个清晰的文件名
                if file_extension:
                    new_name = f"文件_{file_record.id[:8]}{file_extension}"
                else:
                    new_name = f"文件_{file_record.id[:8]}"
                
                print(f"修复为: {new_name}")
                
                # 更新数据库
                file_record.original_name = new_name
                fixed_count += 1
        
        # 提交更改
        db.commit()
        print(f"修复完成！共修复 {fixed_count} 个文件名")
        
    except Exception as e:
        print(f"修复失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_file_names()
