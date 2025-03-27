import os
import logging
from logging.handlers import RotatingFileHandler
import datetime

class LogConfig:
    @staticmethod
    def setup_logger(logger_name, log_file=None):
        """
        设置日志记录器
        
        :param logger_name: 日志记录器名称
        :param log_file: 日志文件名（可选，如果不提供则根据logger_name自动生成）
        :return: 配置好的日志记录器
        """
        # 创建日志记录器
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

        # 如果logger已经有处理器，说明已经被配置过，直接返回
        if logger.handlers:
            return logger

        # 获取MoCo项目根目录路径
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 创建主日志目录
        main_log_dir = os.path.join(current_dir, 'logs')
        os.makedirs(main_log_dir, exist_ok=True)
        
        # 创建服务特定的日志目录
        service_log_dir = os.path.join(main_log_dir, logger_name)
        try:
            os.makedirs(service_log_dir, exist_ok=True)
            print(f"Created or verified service log directory at: {service_log_dir}")
        except Exception as e:
            print(f"Error creating service log directory: {str(e)}")
            # 如果创建服务目录失败，使用主日志目录
            service_log_dir = main_log_dir

        # 如果没有提供日志文件名，则根据logger_name生成
        if log_file is None:
            current_date = datetime.datetime.now().strftime('%Y%m%d')
            log_file = f"{logger_name}_{current_date}.log"

        # 创建文件处理器（限制单个文件大小为10MB，最多保留10个文件）
        log_file_path = os.path.join(service_log_dir, log_file)
        file_handler = RotatingFileHandler(
            log_file_path,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器到日志记录器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # 记录日志创建信息
        logger.info(f"Logger initialized. Log file: {log_file_path}")

        return logger