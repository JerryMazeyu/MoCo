import os
import yaml
from typing import Dict, Any, Optional, List


def load_yaml(file_path: str) -> Dict[str, Any]:
    """
    加载YAML文件
    
    :param file_path: YAML文件路径
    :return: 加载的配置字典
    """
    if not os.path.exists(file_path):
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"加载YAML文件失败: {e}")
        return {}


def save_yaml(data: Dict[str, Any], file_path: str) -> bool:
    """
    保存数据到YAML文件
    
    :param data: 要保存的数据
    :param file_path: 保存路径
    :return: 是否保存成功
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True)
        return True
    except Exception as e:
        print(f"保存YAML文件失败: {e}")
        return False


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个字典，dict2的值会覆盖dict1中的同名键值
    
    :param dict1: 第一个字典
    :param dict2: 第二个字典
    :return: 合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
            
    return result


def get_value_by_path(data: Dict[str, Any], path: str) -> Optional[Any]:
    """
    通过路径获取字典中的值
    
    :param data: 字典
    :param path: 路径，如 "KEYS.oss.access_key_id"
    :return: 路径对应的值，如果不存在则返回None
    """
    keys = path.split('.')
    current = data
    
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
        
    return current


def set_value_by_path(data: Dict[str, Any], path: str, value: Any) -> None:
    """
    通过路径设置字典中的值
    
    :param data: 字典
    :param path: 路径，如 "KEYS.oss.access_key_id"
    :param value: 要设置的值
    """
    keys = path.split('.')
    current = data
    
    for i, k in enumerate(keys):
        if i == len(keys) - 1:
            current[k] = value
        else:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]


def extract_special_configs(config: Dict[str, Any], special_paths: List[str]) -> Dict[str, Any]:
    """
    从配置中提取特殊配置
    
    :param config: 完整配置
    :param special_paths: 特殊配置路径列表
    :return: 特殊配置字典
    """
    special = {}
    
    for path in special_paths:
        value = get_value_by_path(config, path)
        if value is not None:
            set_value_by_path(special, path, value)
            
    return special


def create_default_configs() -> None:
    """
    创建默认配置文件
    """
    # 检查是否存在默认系统配置文件
    sys_default_path = os.path.join('config', 'SYSCONF_default.yaml')
    if not os.path.exists(sys_default_path):
        # 创建一个基本的默认系统配置
        default_sys = {
            'KEYS': {
                'oss': {
                    'access_key_id': 'exampleAccessKeyId',
                    'access_key_secret': 'exampleAccessKeySecret',
                    'endpoint': 'http://oss-cn-shanghai.aliyuncs.com',
                    'bucket_name': 'moco-data',
                    'region': 'cn-shanghai'
                }
            },
            'SPECIAL': ['KEYS.oss']
        }
        save_yaml(default_sys, sys_default_path)
    
    # 检查是否存在用户配置模板
    user_template_path = os.path.join('config', 'USERCONF_template.yaml')
    if not os.path.exists(user_template_path):
        # 创建一个基本的用户配置模板
        default_user = {
            'USERNAME': 'username',
            'BUSINESS': {
                'CP': {
                    'cp_id': ['id1', 'id2']
                }
            },
            'SPECIAL': ['BUSINESS.CP']
        }
        save_yaml(default_user, user_template_path)


# 导出所有工具函数
__all__ = [
    'load_yaml',
    'save_yaml',
    'deep_merge',
    'get_value_by_path',
    'set_value_by_path',
    'extract_special_configs',
    'create_default_configs'
] 