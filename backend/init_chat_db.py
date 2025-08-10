"""
简化的聊天数据库初始化脚本
只创建聊天相关的表
"""

from loguru import logger
from app.core.database import engine
from app.models.base import Base
from app.models.chat import Conversation, ChatMessage

def init_chat_db():
    """初始化聊天数据库表"""
    try:
        # 只创建聊天相关的表
        Base.metadata.create_all(bind=engine, tables=[
            Conversation.__table__,
            ChatMessage.__table__
        ])
        
        logger.info("聊天数据库表创建成功")
        print("✅ 聊天数据库表创建成功")
        
    except Exception as e:
        logger.error(f"聊天数据库初始化失败: {e}")
        print(f"❌ 聊天数据库初始化失败: {e}")
        raise

if __name__ == "__main__":
    init_chat_db()
