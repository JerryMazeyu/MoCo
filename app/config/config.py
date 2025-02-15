import yaml
from app.utils import rp

class ConfigService:
    def __init__(self, config_path: str=rp("default.yaml", folder="config")):
        """初始化配置服务，加载 YAML 文件"""
        with open(config_path, "r", encoding="utf-8") as file:
            self._config = yaml.safe_load(file)
            self._config_path = config_path
        
        self._special = {}
        self.special_list = self._config.pop("SPECIAL", [])
        if not isinstance(self.special_list, list):
            self.special_list = []
            
        for sp_path in self.special_list:
            val = self._get_value_by_path(sp_path, self._config)
            if val is not None:
                self._set_value_by_path(sp_path, val, self._special)

        self.special = ConfigWrapper(self._special)
        self.common = ConfigWrapper(self._config)

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
    
    def _get_value_by_path(self, path: str, data: dict):
        keys = path.split(".")
        current = data
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
        return current

    def _set_value_by_path(self, path: str, value, data: dict):
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
    
    def get_special_yaml(self) -> str:
        """
        将当前 self._special 序列化为 YAML 文本。
        这样 UI 只需要把这个文本放到编辑器里展示即可。
        """
        return yaml.dump(self._special, allow_unicode=True)
    
    def update_special_yaml(self, yaml_text: str):
        """
        接收用户改好的 YAML 文本，解析后更新到 self._special，
        同时把修改同步回 self._config (如果你需要双向联动)。
        """
        new_special = yaml.safe_load(yaml_text)
        if not isinstance(new_special, dict):
            raise ValueError("special 配置必须是字典结构")

        # 1) 更新 self._special
        self._special.clear()
        self._special.update(new_special)
        self._sync_special_to_config()
    
    def _sync_special_to_config(self):
        """
        将 self._special 的内容写回 self._config.
        如果你想保留 [SPECIAL] 列表中各个 path 指向的内容，一种简易做法是直接整块替换
        或者遍历自定义。
        这里的做法要根据你实际 'special 只是指针' 的逻辑来决定。
        """
        for key, val in self._special.items():
            # 简化示例：把每个顶级key都放到 _config 里
            self._config[key] = val



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