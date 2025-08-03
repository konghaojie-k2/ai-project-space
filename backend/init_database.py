#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from app.models.file import Base
from app.models.chat import Base as ChatBase
from app.core.config import settings

def init_database():
    """初始化数据库"""
    try:
        # 创建数据库引擎
        engine = create_engine(str(settings.DATABASE_URL), echo=True)
        
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        ChatBase.metadata.create_all(bind=engine)
        
        print("✅ 数据库表创建成功")
        print(f"📍 数据库位置: {settings.DATABASE_URL}")
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    init_database() 