import logging
from logging.handlers import RotatingFileHandler
from app.utils import rp
import os
import threading

# 全局日志对象
GLOBAL_LOGGER = None
# 批处理日志字典
BATCH_LOGGERS = {}
# 线程锁，防止多线程同时创建日志对象
LOGGER_LOCK = threading.RLock()

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

class RealTimeRotatingFileHandler(RotatingFileHandler):
    """确保日志实时写入的RotatingFileHandler子类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def emit(self, record):
        """重写emit方法，确保每次写入后都刷新缓冲区"""
        super().emit(record)
        self.flush()  # 立即刷新缓冲区

def setup_logger(log_file="moco.log", max_size=5 * 1024 * 1024, backup_count=3):
    """
    设置主日志系统
    
    :param log_file: 日志文件路径
    :param max_size: 单个日志文件的最大大小（单位：字节）
    :param backup_count: 备份的旧日志文件数量
    :return: 配置好的 logger 对象
    """
    global GLOBAL_LOGGER
    
    with LOGGER_LOCK:
        # 如果已经存在全局日志对象，直接返回
        if GLOBAL_LOGGER is not None:
            return GLOBAL_LOGGER
        
        log_file = rp(log_file, folder=["var", "log"])
        # 确保日志目录存在
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # 创建 logger
        logger = logging.getLogger("moco.main")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 配置日志轮转机制，使用实时写入版本
            handler = RealTimeRotatingFileHandler(
                log_file, 
                maxBytes=max_size,
                backupCount=backup_count,
                encoding="utf-8"
            )
            
            # 配置控制台输出
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

def setup_batch_logger(batch_id, log_dir=None, log_prefix="batch_", max_size=5 * 1024 * 1024, backup_count=1):
    """
    为特定批次设置独立的日志记录器
    
    :param batch_id: 批次ID
    :param log_dir: 日志目录，默认为临时目录
    :param log_prefix: 日志文件前缀
    :param max_size: 单个日志文件的最大大小
    :param backup_count: 备份数量
    :return: 配置好的 logger 对象
    """
    global BATCH_LOGGERS
    
    with LOGGER_LOCK:
        # 检查是否已存在此批次的日志记录器
        logger_key = f"{log_prefix}{batch_id}"
        if logger_key in BATCH_LOGGERS:
            return BATCH_LOGGERS[logger_key]
        
        # 确定日志文件路径
        if log_dir:
            # 确保日志目录存在
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"{log_prefix}{batch_id}.log")
        else:
            import tempfile
            temp_dir = tempfile.gettempdir()
            log_file = os.path.join(temp_dir, f"{log_prefix}{batch_id}.log")
        
        # 创建 logger
        logger = logging.getLogger(f"moco.batch.{batch_id}")
        logger.setLevel(logging.INFO)
        
        # 清除已有的处理器，防止重复添加
        if logger.handlers:
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
        
        # 配置日志轮转机制，使用实时写入版本
        handler = RealTimeRotatingFileHandler(
            log_file, 
            maxBytes=max_size,
            backupCount=backup_count,
            encoding="utf-8"
        )
        
        # 配置控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - [Batch-%(batch_id)s] - %(message)s",
                                      defaults={'batch_id': batch_id})
        handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 将处理器添加到 logger
        logger.addHandler(handler)
        logger.addHandler(console_handler)
        
        # 保存到批处理日志字典
        BATCH_LOGGERS[logger_key] = logger
        return logger

def get_logger():
    """获取全局日志对象"""
    global GLOBAL_LOGGER
    if GLOBAL_LOGGER is None:
        GLOBAL_LOGGER = setup_logger()
    return GLOBAL_LOGGER

def get_batch_logger(batch_id, log_dir=None):
    """获取批处理专用日志对象"""
    global BATCH_LOGGERS
    logger_key = f"batch_{batch_id}"
    if logger_key in BATCH_LOGGERS:
        return BATCH_LOGGERS[logger_key]
    return setup_batch_logger(batch_id, log_dir)

def write_batch_completion_file(batch_id, output_dir=None):
    """
    创建批处理完成标记文件
    
    :param batch_id: 批次ID
    :param output_dir: 输出目录，默认使用临时目录
    :return: 创建的文件路径
    """
    if output_dir is None:
        import tempfile
        output_dir = tempfile.gettempdir()
    
    # 确保目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建完成标记文件
    completion_file = os.path.join(output_dir, f"batch_{batch_id}_OK")
    with open(completion_file, 'w') as f:
        f.write(f"Batch {batch_id} completed")
    
    return completion_file

def count_completed_batches(output_dir=None, prefix="batch_", suffix="_OK"):
    """
    统计已完成的批处理数量
    
    :param output_dir: 输出目录，默认使用临时目录
    :param prefix: 文件前缀
    :param suffix: 文件后缀
    :return: 已完成的批处理数量
    """
    if output_dir is None:
        import tempfile
        output_dir = tempfile.gettempdir()
    
    # 确保目录存在
    if not os.path.exists(output_dir):
        return 0
    
    # 统计文件数量
    completed_files = [f for f in os.listdir(output_dir) 
                      if f.startswith(prefix) and f.endswith(suffix)]
    
    return len(completed_files)

def shutdown_logger():
    """关闭日志系统，确保所有日志都被写入"""
    global GLOBAL_LOGGER, BATCH_LOGGERS
    
    with LOGGER_LOCK:
        # 关闭全局日志处理器
        if GLOBAL_LOGGER:
            for handler in GLOBAL_LOGGER.handlers:
                try:
                    handler.close()
                    GLOBAL_LOGGER.removeHandler(handler)
                except:
                    pass
            GLOBAL_LOGGER = None
        
        # 关闭所有批处理日志处理器
        for logger_key, logger in BATCH_LOGGERS.items():
            for handler in logger.handlers:
                try:
                    handler.close()
                    logger.removeHandler(handler)
                except:
                    pass
        
        BATCH_LOGGERS.clear()
