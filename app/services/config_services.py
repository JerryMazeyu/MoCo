import yaml
import os
from typing import Union
from app.utils import setup_logger

logger = setup_logger()

class ConfigValidator:


    @staticmethod
    def validate_yaml_format(file_path: str) -> dict:
        """验证 YAML 文件格式是否正确"""
        logger.info(f"[CONFIG] 正在验证配置文件格式: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"[CONFIG] 配置文件格式验证成功。")
            return config
        except yaml.YAMLError as e:
            logger.error(f"[CONFIG] YAML 文件格式错误: {str(e)}")
            raise ValueError(f"YAML 文件格式错误: {str(e)}")

    @staticmethod
    def validate_amount_mapping(amount_mapping: dict):
        """验证 收油关系映射 中的值是否为整数或用逗号分隔的整数"""
        logger.info(f"[CONFIG] 正在验证收油关系映射字段。")
        for key, value in amount_mapping.items():
            values = str(value).split(",")
            if not all(val.strip().isdigit() for val in values):
                logger.error(f"[CONFIG] 收油关系映射 中的 '{key}' 值 '{value}' 无效，必须是整数或用逗号分隔的整数。")
                raise ValueError(f"收油关系映射 中的 '{key}' 值 '{value}' 无效，必须是整数或用逗号分隔的整数。")
        logger.info(f"[CONFIG] 收油关系映射字段验证成功。")


    @staticmethod
    def validate_car_section(car_section: dict):
        """验证 CAR 中所有值是否为 int 或 float"""
        logger.info(f"[CONFIG] 正在验证 CAR 字段。")
        for key, value in car_section.items():
            if not isinstance(value, (int, float)):
                logger.error(f"[CONFIG] CAR 中的 '{key}' 值 '{value}' 无效，必须是 int 或 float。")
                raise ValueError(f"CAR 中的 '{key}' 值 '{value}' 无效，必须是 int 或 float。")
        logger.info(f"[CONFIG] CAR 字段验证成功。")

    @staticmethod
    def validate_last_directory(path: str):
        """验证 last_dir 是否是有效路径"""
        logger.info(f"[CONFIG] 正在验证 last_dir 路径。")
        if not os.path.exists(path):
            logger.error(f"[CONFIG] last_dir '{path}' 不是有效路径。")
            raise ValueError(f"last_dir '{path}' 不是有效路径。")
        logger.info(f"[CONFIG] last_dir 路径验证成功。")

    @staticmethod
    def validate_config(file_path: Union[str, dict]):
        """执行所有验证步骤"""
        if isinstance(file_path, str):
            # 1. 验证 YAML 文件格式
            config = ConfigValidator.validate_yaml_format(file_path)
        else:
            config = file_path

        # 2. 验证 amount_mapping 字段
        try:
            amount_mapping = config["BUSINESS"]["RESTAURANT"]["收油关系映射"]
            ConfigValidator.validate_amount_mapping(amount_mapping)
        except KeyError:
            logger.error(f"[CONFIG] 配置文件缺少 收油关系映射 字段。")
            raise ValueError("配置文件缺少 收油关系映射 字段。")

        # 3. 验证 CAR 字段
        try:
            car_section = config["BUSINESS"]["CAR"]
            ConfigValidator.validate_car_section(car_section)
        except KeyError:
            logger.error(f"[CONFIG] 配置文件缺少 CAR 字段。")
            raise ValueError("配置文件缺少 CAR 字段。")

        # 4. 验证 Tab1 的 last_dir 路径
        if "Tab1" in config and "last_dir" in config["Tab1"]:
            last_dir = config["Tab1"]["last_dir"]
            ConfigValidator.validate_last_directory(last_dir)
        
        logger.info(f"[CONFIG] *配置文件格式和数据验证成功。")
        print("配置文件格式和数据验证成功。")
