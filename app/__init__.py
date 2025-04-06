# app/__init__.py
# 应用程序的初始化文件

__version__ = '1.0.0'

# 全局上下文，用于在不同模块间共享数据
global_context = {
    'config': {},  # 配置数据
    'current_cp': None,  # 当前选择的CP
    'user_info': None,  # 用户信息
}

# 导入模块前不导入消息管理器，避免循环导入
# 应用程序启动后，视图模块会初始化消息管理器 