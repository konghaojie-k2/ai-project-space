import sys
from pathlib import Path
from typing import Dict, Any

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """设置日志配置"""
    
    # 移除默认的logger
    logger.remove()
    
    # 控制台日志格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件日志格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台日志处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # 添加文件日志处理器
    logger.add(
        settings.LOG_FILE,
        format=file_format,
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )
    
    # 添加错误日志文件
    error_log_file = Path(settings.LOG_FILE).parent / "error.log"
    logger.add(
        str(error_log_file),
        format=file_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
    )


def get_logger(name: str = __name__):
    """获取logger实例"""
    return logger.bind(name=name)


# 创建常用的logger实例
app_logger = get_logger("app")
db_logger = get_logger("database")
auth_logger = get_logger("auth")
file_logger = get_logger("file")
ai_logger = get_logger("ai")


class LoggerMixin:
    """Logger混入类，为其他类提供日志功能"""
    
    @property
    def logger(self):
        return get_logger(self.__class__.__name__) 