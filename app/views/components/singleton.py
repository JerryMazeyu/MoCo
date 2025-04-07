# singleton.py
class GlobalContext:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalContext, cls).__new__(cls)
            cls._instance.data = {}  # 初始化变量
        return cls._instance

global_context = GlobalContext()