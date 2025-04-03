import os
os.environ["MoCo_USERNAME"] = 'huizhou'


from app.config.config import CONF



# 通过属性访问配置
api_key = CONF.KEYS.kimi_keys[0]

# 通过字典访问配置
api_key = CONF._config_dict["KEYS"]["kimi_keys"][0]
print(api_key)

# 保存配置
CONF.save()

# # 上传配置到OSS
# CONF.upload()

# 从OSS刷新配置
# CONF.refresh()

# 获取特殊配置
special_yaml = CONF.get_special_yaml()
print(special_yaml)

