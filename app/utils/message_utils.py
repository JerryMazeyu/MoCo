"""
消息工具模块，提供与消息控制台交互的辅助函数。
"""

def get_message_manager():
    """
    获取全局消息管理器实例。
    
    从app.views.components.message_console导入MessageManager并返回其实例，
    这样可以避免在应用程序初始化时就导入UI相关的模块。
    
    返回:
        MessageManager: 全局消息管理器实例
    """
    from app.views.components.message_console import MessageManager
    return MessageManager()

def print_message(message, msg_type="info"):
    """
    向消息控制台打印消息。
    
    参数:
        message (str): 要打印的消息
        msg_type (str): 消息类型，可选值：info, warning, error, success, debug
    """
    manager = get_message_manager()
    manager.print(message, msg_type)

def print_info(message):
    """打印信息消息"""
    print_message(message, "info")

def print_warning(message):
    """打印警告消息"""
    print_message(message, "warning")

def print_error(message):
    """打印错误消息"""
    print_message(message, "error")

def print_success(message):
    """打印成功消息"""
    print_message(message, "success")

def print_debug(message):
    """打印调试消息"""
    print_message(message, "debug") 