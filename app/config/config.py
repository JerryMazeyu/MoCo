import yaml
from app.utils import rp

class ConfigService:
    def __init__(self, config_path: str=rp("default.yaml", folder="config")):
        """初始化配置服务，加载 YAML 文件"""
        with open(config_path, "r", encoding="utf-8") as file:
            self._config = yaml.safe_load(file)
            self._config_path = config_path

    def get(self, key_path: str, default=None):
        """
        通过路径访问配置，例如 "SYSTEM.database.host"
        :param key_path: 点分隔的路径字符串，例如 "SYSTEM.database.host"
        :param default: 如果路径不存在，返回的默认值
        :return: 对应配置值或默认值
        """
        keys = key_path.split(".")
        value = self._config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def __getattr__(self, item):
        """
        支持通过属性访问配置，例如 config.SYSTEM.database.host
        """
        return self._get_nested_dict(self._config.get(item, {}))

    def _get_nested_dict(self, config_subtree):
        """
        将嵌套字典转化为支持点式访问的对象
        """
        if isinstance(config_subtree, dict):
            return ConfigWrapper(config_subtree)
        return config_subtree

    def save(self, config_path: str=None):
        """
        保存配置到文件
        :param config_path: 保存的配置文件路径
        """
        if not config_path:
            config_path = self._config_path
        with open(config_path, "w", encoding="utf-8") as file:
            yaml.dump(self._config, file, allow_unicode=True)


class ConfigWrapper:
    """
    用于封装嵌套配置字典，支持点式访问
    """
    def __init__(self, config_dict):
        self._config_dict = config_dict

    def __getattr__(self, item):
        if item in self._config_dict:
            value = self._config_dict[item]
            if isinstance(value, dict):
                return ConfigWrapper(value)
            return value
        raise AttributeError(f"配置项 {item} 不存在")

default_config = ConfigService()

def get_config():
    try:
        return ConfigService(config_path=rp("config.yaml", folder="config"))
    except:
        return default_config

try:
    CONF = ConfigService(config_path=rp("config.yaml", folder="config"))
except:
    CONF = default_config

__all__ = ["ConfigService" ,"default_config", "CONF", "get_config"]