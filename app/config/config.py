import os
import yaml
import logging
from typing import Optional, Dict, Any, List, Union
import oss2  # 阿里云OSS SDK

from app.utils import rp, oss_get_yaml_file

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOGGER = logging.getLogger("moco.log")

class ConfigWrapper:
    """
    配置包装器，支持以属性方式访问配置
    """
    def __init__(self, config_dict: Dict[str, Any]):
        self._config_dict = config_dict

    def __getattr__(self, item):
        if item in self._config_dict:
            value = self._config_dict[item]
            if isinstance(value, dict):
                return ConfigWrapper(value)
            return value
        raise AttributeError(f"配置项 {item} 不存在")
    
    def __getitem__(self, key):
        """支持以字典方式访问配置"""
        if isinstance(key, str) and key in self._config_dict:
            value = self._config_dict[key]
            if isinstance(value, dict):
                return ConfigWrapper(value)
            return value
        raise KeyError(f"配置项 {key} 不存在")
    
    def __setattr__(self, key, value):
        if key == "_config_dict":
            super().__setattr__(key, value)
        else:
            self._config_dict[key] = value

    def __delattr__(self, key):
        if key in self._config_dict:
            del self._config_dict[key]
        else:
            raise AttributeError(f"配置项 {key} 不存在")
    
    def keys(self):
        """返回配置的所有键"""
        return self._config_dict.keys()
    
    def get(self, key, default=None):
        """获取指定键的值，如果不存在返回默认值"""
        return self._config_dict.get(key, default)


class ConfigService:
    """配置服务，负责加载、保存和管理配置"""
    
    def __init__(self, username: str):
        """
        初始化配置服务
        
        :param username: 用户名，用于加载用户特定配置
        """
        self.username = username
        self._config_dict = {}
        self.special_list = []
        self._special = {}
        
        # 初始化runtime属性，用于存储运行时的临时配置
        self.runtime = type('RuntimeConfig', (), {})()
        
        # 加载系统配置
        self._load_sys_config()
        
        # 加载用户配置
        self._load_user_config()
        
        # 合并配置
        self._merge_configs()
        
        # 初始化特殊配置
        self._init_special_configs()
        
    def _load_sys_config(self):
        """加载系统配置"""
        # 首先尝试加载本地 SYSCONF.yaml
        sys_conf_path = rp("SYSCONF.yaml", folder="config")
        default_sys_conf_path = rp("SYSCONF_default.yaml", folder="config")
        
        self.sys_config = {}
        if os.path.exists(sys_conf_path):
            try:
                with open(sys_conf_path, "r", encoding="utf-8") as f:
                    self.sys_config = yaml.safe_load(f) or {}
                LOGGER.info(f"已从本地加载系统配置: {sys_conf_path}")
            except Exception as e:
                LOGGER.error(f"加载系统配置失败: {e}")
                
                # 如果本地配置加载失败，尝试加载默认配置
                if os.path.exists(default_sys_conf_path):
                    try:
                        with open(default_sys_conf_path, "r", encoding="utf-8") as f:
                            self.sys_config = yaml.safe_load(f) or {}
                        LOGGER.info(f"已从默认配置加载系统配置: {default_sys_conf_path}")
                    except Exception as e:
                        LOGGER.error(f"加载默认系统配置失败: {e}")
        elif os.path.exists(default_sys_conf_path):
            # 如果本地配置不存在，尝试加载默认配置
            try:
                with open(default_sys_conf_path, "r", encoding="utf-8") as f:
                    self.sys_config = yaml.safe_load(f) or {}
                LOGGER.info(f"已从默认配置加载系统配置: {default_sys_conf_path}")
            except Exception as e:
                LOGGER.error(f"加载默认系统配置失败: {e}")
    
    def _load_user_config(self):
        """加载用户配置"""
        # 首先检查是否存在临时用户配置
        user_temp_conf_path = rp(f"{self.username}_temp.yaml", folder="config")
        user_conf_path = rp(f"{self.username}.yaml", folder="config")
        
        self.user_config = {}
        if os.path.exists(user_temp_conf_path):
            # 如果存在临时配置，优先加载
            try:
                with open(user_temp_conf_path, "r", encoding="utf-8") as f:
                    self.user_config = yaml.safe_load(f) or {}
                LOGGER.info(f"已从临时配置加载用户配置: {user_temp_conf_path}")
            except Exception as e:
                LOGGER.error(f"加载临时用户配置失败: {e}")
        elif self.sys_config.get("KEYS", {}).get("oss"):
            # 如果没有临时配置且系统配置中包含OSS配置，尝试从OSS下载
            try:
                self._download_from_oss()
                
                # 下载完成后，检查是否已经生成了用户配置文件
                if os.path.exists(user_conf_path):
                    with open(user_conf_path, "r", encoding="utf-8") as f:
                        self.user_config = yaml.safe_load(f) or {}
                    LOGGER.info(f"已从OSS下载并加载用户配置: {user_conf_path}")
            except Exception as e:
                LOGGER.error(f"从OSS加载用户配置失败: {e}")
        elif os.path.exists(user_conf_path):
            # 如果OSS下载失败但本地存在用户配置，直接加载
            try:
                with open(user_conf_path, "r", encoding="utf-8") as f:
                    self.user_config = yaml.safe_load(f) or {}
                LOGGER.info(f"已从本地加载用户配置: {user_conf_path}")
            except Exception as e:
                LOGGER.error(f"加载本地用户配置失败: {e}")
    
    def _merge_configs(self):
        """合并系统配置和用户配置"""
        # 深度合并两个配置字典，用户配置优先级更高
        self._config_dict = self._deep_merge(self.sys_config, self.user_config)
        
        # 将合并后的配置放入ConfigWrapper
        self.config = ConfigWrapper(self._config_dict)
    
    def _deep_merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """深度合并两个字典，dict2的值会覆盖dict1的值"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result
    
    def _init_special_configs(self):
        """初始化特殊配置"""
        # 获取特殊配置列表
        self.special_list = self._config_dict.get("SPECIAL", [])
        if not isinstance(self.special_list, list):
            self.special_list = []
        
        # 提取特殊配置
        for sp_path in self.special_list:
            val = self._get_value_by_path(sp_path, self._config_dict)
            if val is not None:
                self._set_value_by_path(sp_path, val, self._special)
        
        # 将特殊配置放入ConfigWrapper
        self.special = ConfigWrapper(self._special)
    
    def _get_value_by_path(self, path: str, data: dict) -> Any:
        """通过路径获取字典中的值"""
        keys = path.split(".")
        current = data
        
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
            
        return current
    
    def _set_value_by_path(self, path: str, value: Any, data: dict) -> None:
        """通过路径设置字典中的值"""
        if isinstance(data, ConfigWrapper):
            data = data._config_dict
            
        keys = path.split(".")
        current = data
        
        for i, k in enumerate(keys):
            if isinstance(current, ConfigWrapper):
                current = current._config_dict
                
            if i == len(keys) - 1:
                current[k] = value
            else:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]
    
    def __getattr__(self, item):
        """支持以属性方式访问配置"""
        if item in self._config_dict:
            value = self._config_dict[item]
            if isinstance(value, dict):
                return ConfigWrapper(value)
            return value
        raise AttributeError(f"配置项 {item} 不存在")
    
    def __getitem__(self, key):
        """支持以字典方式访问配置"""
        return self.__getattr__(key)
    
    def get(self, key_path: str, default=None):
        """
        通过路径访问配置，例如 "SYSTEM.database.host"
        
        :param key_path: 点分隔的路径字符串，例如 "SYSTEM.database.host"
        :param default: 如果路径不存在，返回的默认值
        :return: 对应配置值或默认值
        """
        return self._get_value_by_path(key_path, self._config_dict) or default
    
    def save(self):
        """保存配置"""
        # 将用户配置保存为临时文件
        user_temp_conf_path = rp(f"{self.username}_temp.yaml", folder="config")
        
        # 确保user_config包含最新的合并配置
        self.user_config = self._config_dict.copy()
        
        try:
            # 确保config目录存在
            os.makedirs(os.path.dirname(user_temp_conf_path), exist_ok=True)
            
            # 保存用户配置
            with open(user_temp_conf_path, "w", encoding="utf-8") as f:
                yaml.dump(self.user_config, f, allow_unicode=True)
            LOGGER.info(f"用户配置已保存至: {user_temp_conf_path}")
            return True
        except Exception as e:
            LOGGER.error(f"保存用户配置失败: {e}")
            return False
    
    def upload(self):
        """将配置上传到OSS"""
        # 首先检查是否已配置OSS
        oss_config = self.sys_config.get("KEYS", {}).get("oss")
        if not oss_config:
            LOGGER.error("未配置OSS，无法上传配置")
            return False
        
        try:
            # 创建OSS客户端
            auth = oss2.Auth(oss_config["access_key_id"], oss_config["access_key_secret"])
            bucket = oss2.Bucket(auth, oss_config["endpoint"], oss_config["bucket_name"])
            
            # 上传用户配置
            user_temp_conf_path = rp(f"{self.username}_temp.yaml", folder="config")
            if os.path.exists(user_temp_conf_path):
                # 读取配置文件内容
                with open(user_temp_conf_path, "rb") as f:
                    content = f.read()
                
                # 上传到OSS
                remote_path = f"configs/{self.username}.yaml"
                bucket.put_object(remote_path, content)
                LOGGER.info(f"用户配置已上传至OSS: {remote_path}")
                return True
            else:
                LOGGER.error(f"用户临时配置文件不存在: {user_temp_conf_path}")
                return False
        except Exception as e:
            LOGGER.error(f"上传配置到OSS失败: {e}")
            return False
    
    def refresh(self):
        """刷新配置，从OSS重新下载"""
        # 删除临时配置文件
        user_temp_conf_path = rp(f"{self.username}_temp.yaml", folder="config")
        if os.path.exists(user_temp_conf_path):
            try:
                os.remove(user_temp_conf_path)
                LOGGER.info(f"已删除临时配置文件: {user_temp_conf_path}")
            except Exception as e:
                LOGGER.error(f"删除临时配置文件失败: {e}")
        
        # 重新从OSS下载配置
        self._download_from_oss()
        
        # 重新加载配置
        self._load_user_config()
        self._merge_configs()
        self._init_special_configs()
        
        return True
    
    def _download_from_oss(self):
        """从OSS下载用户配置"""
        info = oss_get_yaml_file(f"configs/{self.username}.yaml")
        if info:
            with open(rp(f"{self.username}_temp.yaml", folder="config"), "w", encoding="utf-8") as f:
                yaml.dump(info, f, allow_unicode=True)
            LOGGER.info(f"已从OSS下载用户配置: {rp(f'{self.username}.yaml', folder='config')}")
            return True
        else:
            LOGGER.error(f"从OSS下载用户配置失败")
            return False
    
    def get_special_yaml(self) -> str:
        """
        将当前特殊配置序列化为YAML文本
        
        :return: YAML格式的特殊配置
        """
        return yaml.dump(self._special, allow_unicode=True)
    
    def update_special_yaml(self, yaml_text: str):
        """
        更新特殊配置
        
        :param yaml_text: YAML格式的特殊配置
        """
        try:
            new_special = yaml.safe_load(yaml_text)
            if not isinstance(new_special, dict):
                raise ValueError("特殊配置必须是字典结构")
            
            # 更新特殊配置
            self._special.clear()
            self._special.update(new_special)
            
            # 同步回主配置
            self._sync_special_to_config()
            
            # 更新包装器
            self.special = ConfigWrapper(self._special)
            
            LOGGER.info("特殊配置已更新")
            return True
        except Exception as e:
            LOGGER.error(f"更新特殊配置失败: {e}")
            return False
    
    def _sync_special_to_config(self):
        """将特殊配置同步回主配置"""
        for sp_path in self.special_list:
            # 从special中获取值
            val = self._get_value_by_path(sp_path.split(".")[-1], self._special)
            if val is not None:
                # 设置到主配置中
                self._set_value_by_path(sp_path, val, self._config_dict)


# 初始化配置服务
try:
    # 获取用户名，如果未指定则使用默认用户名
    username = os.environ.get("MoCo_USERNAME", "huizhou")
    CONF = ConfigService(username)
except Exception as e:
    LOGGER.error(f"初始化配置服务失败: {e}")
    # 使用空配置作为后备
    CONF = ConfigService("default")

# 导出配置服务和配置实例
__all__ = ["CONF"]