import logging
from logging.handlers import RotatingFileHandler
from app.utils import rp
import os

# 全局日志对象
GLOBAL_LOGGER = None

class MessageLogHandler(logging.Handler):
    """自定义日志处理器，将日志消息转发到MessageManager"""
    
    def __init__(self):
        super().__init__()
        # 在实际使用时动态导入MessageManager避免循环导入
        self.message_manager = None
    
    def emit(self, record):
        try:
            # 延迟导入，避免循环导入问题
            if self.message_manager is None:
                from app.views.components.message_console import MessageManager
                self.message_manager = MessageManager()
            
            # 获取消息和级别
            msg = self.format(record)
            log_level = record.levelname.lower()
            
            # 根据日志级别映射消息类型
            msg_type = "info"
            if log_level == "error":
                msg_type = "error"
            elif log_level == "warning":
                msg_type = "warning"
            elif log_level == "critical":
                msg_type = "error"
            elif log_level == "debug":
                msg_type = "info"
            
            # 发送消息到控制台
            self.message_manager.send_message(msg, msg_type)
        except Exception:
            self.handleError(record)

def setup_logger(log_file="moco.log", max_size=5 * 1024 * 1024, backup_count=3):
    """
    设置日志系统，支持文件大小控制和日志轮转。
    
    :param log_file: 日志文件路径
    :param max_size: 单个日志文件的最大大小（单位：字节）
    :param backup_count: 备份的旧日志文件数量
    :return: 配置好的 logger 对象
    """
    global GLOBAL_LOGGER
    
    # 如果已经存在全局日志对象，直接返回
    if GLOBAL_LOGGER is not None:
        return GLOBAL_LOGGER
    
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
        
        # 创建消息中继处理器
        message_handler = MessageLogHandler()
        message_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        message_handler.setFormatter(formatter)

        # 将处理器添加到 logger
        logger.addHandler(handler)
        logger.addHandler(console_handler)
        logger.addHandler(message_handler)
    
    # 保存为全局对象
    GLOBAL_LOGGER = logger
    return logger

# 提供一个获取全局logger的函数
def get_logger():
    """获取全局日志对象"""
    global GLOBAL_LOGGER
    if GLOBAL_LOGGER is None:
        GLOBAL_LOGGER = setup_logger()
    return GLOBAL_LOGGER
