import abc
import json
import os
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Type
from abc import abstractmethod
from app.utils.file_io import rp
from app.utils.logger import setup_logger

# 设置日志
logger = setup_logger()

class BaseInstance(abc.ABC):
    """
    所有实体类的基类，提供通用功能
    """
    def __init__(self, model):
        """
        初始化基类
        
        :param model: 实体对应的模型类
        """
        self.inst = None  # 具体的模型实例
        self.model_class = model  # 模型类
        self.status = 'pending'  # 实体状态：pending（待处理）或ready（就绪）
    
    def get_status(self) -> str:
        """
        获取实体状态
        
        :return: 状态字符串
        """
        return self.status
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将实体转换为字典
        
        :return: 字典表示
        """
        # 如果子类实现了自己的to_dict方法，使用子类的实现
        if hasattr(self.__class__, 'to_dict') and self.__class__.to_dict != BaseInstance.to_dict:
            return self.__class__.to_dict(self)
        
        # 如果实例有info属性，返回info
        if hasattr(self, 'info'):
            return self.info.copy() if isinstance(self.info, dict) else dict(self.info)
        
        # 如果inst是pydantic模型，使用其dict方法
        if hasattr(self.inst, 'dict'):
            return self.inst.dict()
        
        # 如果inst有__dict__属性，使用vars
        if hasattr(self.inst, '__dict__'):
            return vars(self.inst)
        
        # 如果以上都不满足，尝试将inst转换为字典
        try:
            return dict(self.inst)
        except (TypeError, ValueError):
            logger.warning(f"无法将{self.__class__.__name__}实例转换为字典")
            return {}
    
    def to_json(self) -> str:
        """
        将实体转换为JSON字符串
        
        :return: JSON字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def save_to_json(self, file_path: str) -> bool:
        """
        将实体保存为JSON文件
        
        :param file_path: 文件路径
        :return: 是否保存成功
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            logger.info(f"已将实体保存到JSON文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            return False
    
    @classmethod
    def load_from_json(cls, file_path: str, model_class=None):
        """
        从JSON文件加载实体
        
        :param file_path: 文件路径
        :param model_class: 模型类，如果为None则使用cls.model_class
        :return: 实体实例
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            model_cls = model_class or cls.model_class
            instance = cls({}, model=model_cls)
            instance.inst = model_cls(**data)
            instance.status = 'ready'
            logger.info(f"已从JSON文件加载实体: {file_path}")
            return instance
        except Exception as e:
            logger.error(f"从JSON文件加载实体失败: {e}")
            return None
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        将实体转换为DataFrame（单行）
        
        :return: DataFrame
        """
        return pd.DataFrame([self.to_dict()])
    
    def save_to_excel(self, file_path: str, sheet_name: str = 'Sheet1') -> bool:
        """
        将实体保存为Excel文件
        
        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :return: 是否保存成功
        """
        try:
            df = self.to_dataframe()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            df.to_excel(file_path, sheet_name=sheet_name, index=False)
            logger.info(f"已将实体保存到Excel文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            return False
    
    @classmethod
    def load_from_excel(cls, file_path: str, sheet_name: str = 'Sheet1', model_class=None):
        """
        从Excel文件加载实体
        
        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :param model_class: 模型类，如果为None则使用cls.model_class
        :return: 实体实例
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            if len(df) > 0:
                data = df.iloc[0].to_dict()
                model_cls = model_class or cls.model_class
                instance = cls(data, model=model_cls)
                instance.status = 'ready'
                logger.info(f"已从Excel文件加载实体: {file_path}")
                return instance
            else:
                logger.error(f"Excel文件中没有数据: {file_path}")
                return None
        except Exception as e:
            logger.error(f"从Excel文件加载实体失败: {e}")
            return None
    
    def __str__(self) -> str:
        """
        返回实体的字符串表示
        
        :return: 字符串表示
        """
        return f"{self.__class__.__name__}({self.to_dict()})"


class BaseGroup:
    """
    用于组合同类实体的基类
    """
    def __init__(self, instances: List[BaseInstance] = None, group_type: str = None):
        """
        初始化组合
        
        :param instances: 实体列表
        :param group_type: 组合类型
        """
        self.members = instances or []
        self.group_type = group_type
    
    def add(self, instance: BaseInstance) -> None:
        """
        添加实体到组合中
        
        :param instance: 实体
        """
        self.members.append(instance)
    
    def remove(self, instance: BaseInstance) -> bool:
        """
        从组合中移除实体
        
        :param instance: 实体
        :return: 是否移除成功
        """
        if instance in self.members:
            self.members.remove(instance)
            return True
        return False
    
    def count(self) -> int:
        """
        获取组合中实体数量
        
        :return: 实体数量
        """
        return len(self.members)
    
    def to_dicts(self) -> List[Dict[str, Any]]:
        """
        将组合中的所有实体转换为字典列表
        
        :return: 字典列表
        """
        return [member.to_dict() for member in self.members]
    
    def to_json(self) -> str:
        """
        将组合转换为JSON字符串
        
        :return: JSON字符串
        """
        return json.dumps(self.to_dicts(), ensure_ascii=False, indent=2)
    
    def save_to_json(self, file_path: str) -> bool:
        """
        将组合保存为JSON文件
        
        :param file_path: 文件路径
        :return: 是否保存成功
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            logger.info(f"已将组合保存到JSON文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            return False
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        将组合转换为DataFrame
        
        :return: DataFrame
        """
        if not self.members:
            return pd.DataFrame()
        
        data = self.to_dicts()
        return pd.DataFrame(data)
    
    def save_to_excel(self, file_path: str, sheet_name: str = 'Sheet1') -> bool:
        """
        将组合保存为Excel文件
        
        :param file_path: 文件路径
        :param sheet_name: 工作表名称
        :return: 是否保存成功
        """
        try:
            df = self.to_dataframe()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            df.to_excel(file_path, sheet_name=sheet_name, index=False)
            logger.info(f"已将组合保存到Excel文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            return False
    
    @classmethod
    def merge_groups(cls, groups: List['BaseGroup']) -> 'BaseGroup':
        """
        合并多个组合
        
        :param groups: 组合列表
        :return: 合并后的组合
        """
        merged = cls()
        for group in groups:
            for member in group.members:
                merged.add(member)
        return merged
    
    def filter(self, condition_func) -> 'BaseGroup':
        """
        根据条件函数筛选实体
        
        :param condition_func: 条件函数，接收实体并返回布尔值
        :return: 筛选后的组合
        """
        filtered_members = [member for member in self.members if condition_func(member)]
        
        # 根据类名决定参数名
        if self.__class__.__name__ == 'VehicleGroup':
            kwargs = {'vehicles': filtered_members}
        elif self.__class__.__name__ == 'RestaurantsGroup':
            kwargs = {'restaurants': filtered_members}
        else:
            kwargs = {'instances': filtered_members}
        
        kwargs['group_type'] = self.group_type
        
        # 如果类有model和conf属性，也传递它们
        if hasattr(self, 'model'):
            kwargs['model'] = self.model
        if hasattr(self, 'conf'):
            kwargs['conf'] = self.conf
        
        filtered_group = self.__class__(**kwargs)
        return filtered_group
    
    def __str__(self) -> str:
        """
        返回组合的字符串表示
        
        :return: 字符串表示
        """
        return f"{self.__class__.__name__}(数量={self.count()}, 类型={self.group_type})"
    
    def __iter__(self):
        """
        迭代器
        
        :return: 成员迭代器
        """
        return iter(self.members)
    
    def __getitem__(self, index):
        """
        索引访问
        
        :param index: 索引
        :return: 成员
        """
        return self.members[index] 