# 配置模块说明

配置模块用于管理项目的配置信息，包括系统配置和用户配置。

## 配置文件

- `SYSCONF.yaml`：系统配置，包含全局设置
- `SYSCONF_default.yaml`：系统默认配置，当`SYSCONF.yaml`不存在时使用
- `<username>.yaml`：用户配置，从OSS下载
- `<username>_temp.yaml`：临时用户配置，本地修改后保存

## 配置优先级

配置的优先级从高到低为：
1. 用户临时配置（`<username>_temp.yaml`）
2. 用户配置（`<username>.yaml`）
3. 系统配置（`SYSCONF.yaml`）
4. 系统默认配置（`SYSCONF_default.yaml`）

当存在相同配置项时，高优先级的配置会覆盖低优先级的配置。

## 使用方法

```python
from config import CONF

# 通过属性访问配置
api_key = CONF.KEYS.kimi_keys[0]

# 通过路径访问配置
api_key = CONF.get("KEYS.kimi_keys.0")

# 通过字典访问配置
api_key = CONF._config_dict["KEYS"]["kimi_keys"][0]

# 保存配置
CONF.save()

# 上传配置到OSS
CONF.upload()

# 从OSS刷新配置
CONF.refresh()

# 获取特殊配置
special_yaml = CONF.get_special_yaml()

# 更新特殊配置
CONF.update_special_yaml(special_yaml)
```

## 特殊配置

特殊配置是指在配置中标记为需要单独展示或处理的配置项。它们在`SPECIAL`列表中定义，例如：

```yaml
SPECIAL:
  - KEYS.oss
  - BUSINESS.REST2CP
```

这些特殊配置项可以通过`CONF.special`访问，也可以通过`get_special_yaml()`方法获取YAML格式的表示，用于UI展示。

## 目录结构

```
config/
├── __init__.py      # 配置模块入口
├── config.py        # 配置服务实现
├── utils.py         # 工具函数
├── README.md        # 说明文档
├── SYSCONF.yaml     # 系统配置
├── SYSCONF_default.yaml # 系统默认配置
├── <username>.yaml  # 用户配置
└── <username>_temp.yaml # 临时用户配置
``` 