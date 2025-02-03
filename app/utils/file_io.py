import os
from typing import Union


def rp(file_name, folder:Union[str, list]="assets"):
    """
    获取位于 assets 目录下的文件的完整路径，适配不同操作系统。
    
    参数:
        file_name (str): 文件名，例如 "config.json" 或 "restaurant_data.xlsx"。

    返回:
        str: assets 目录下的完整文件路径。
    """
    # 获取当前脚本所在目录的绝对路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    if isinstance(folder, str):
        # 确定 assets 目录的路径
        assets_dir = os.path.join(current_dir, "..", folder)
    elif isinstance(folder, list):
        # 支持多级目录
        assets_dir = os.path.join(current_dir, "..", *folder)
        
    # 构造完整的文件路径
    full_path = os.path.join(assets_dir, file_name)
    
    # 返回标准化的路径（适配操作系统路径分隔符）
    return os.path.normpath(full_path)



if __name__ == "__main__":
    # 测试获取 config.json 文件路径
    config_path = rp("config.json")
    print(f"config.json 文件路径: {config_path}")