import logging
from logging.handlers import RotatingFileHandler
from app.utils import rp
import os

def setup_logger(log_file="moco.log", max_size=5 * 1024 * 1024, backup_count=3):
    """
    设置日志系统，支持文件大小控制和日志轮转。
    
    :param log_file: 日志文件路径
    :param max_size: 单个日志文件的最大大小（单位：字节）
    :param backup_count: 备份的旧日志文件数量
    :return: 配置好的 logger 对象
    """
    log_file = rp(log_file, folder=["var", "log"])
    # 确保 /var/log 目录存在（在非 Linux 环境中测试时，可以更改路径）
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # 创建 logger
    logger = logging.getLogger("moco.log")
    logger.setLevel(logging.INFO)

    
    if not logger.handlers:

        # 配置日志轮转机制
        handler = RotatingFileHandler(
            log_file, 
            maxBytes=max_size,  # 文件最大大小
            backupCount=backup_count,  # 保留旧日志文件的数量
            encoding="utf-8"  # 日志文件编码
        )
        # 配置控制台输出的 StreamHandler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 将处理器添加到 logger
        logger.addHandler(handler)
        logger.addHandler(console_handler)
    
    return logger
