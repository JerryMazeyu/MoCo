"""
配置服务测试示例
"""
import os
import yaml

from app.config.config import CONF


def test_config_runtime():
    """测试runtime属性"""
    print("测试runtime属性...")
    
    # 设置runtime属性
    CONF.runtime.test_value = "这是一个测试值"
    CONF.runtime.test_dict = {"key": "value"}
    
    # 读取runtime属性
    print(f"runtime.test_value = {CONF.runtime.test_value}")
    print(f"runtime.test_dict = {CONF.runtime.test_dict}")
    
    # 修改runtime属性
    CONF.runtime.test_value = "修改后的值"
    print(f"修改后的runtime.test_value = {CONF.runtime.test_value}")


def test_config_save():
    """测试配置保存功能"""
    print("\n测试配置保存功能...")
    
    # 添加一些测试配置
    if "TEST" not in CONF._config_dict:
        CONF._config_dict["TEST"] = {}
    
    CONF._config_dict["TEST"]["test_key"] = "test_value"
    CONF._config_dict["TEST"]["test_number"] = 123
    CONF._config_dict["TEST"]["test_list"] = [1, 2, 3]
    
    setattr(CONF.runtime, "test_value", "test_value")
    
    # 保存配置
    result = CONF.save()
    CONF.refresh()
    print(f"保存配置结果: {'成功' if result else '失败'}")
    
    # 显示保存的文件路径
    temp_file_path = os.path.join("config", f"{CONF.username}_temp.yaml")
    if os.path.exists(temp_file_path):
        print(f"配置已保存到: {temp_file_path}")
        
        # 读取保存的文件内容并显示
        try:
            with open(temp_file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            print("\n保存的配置内容:")
            print(f"TEST.test_key = {content.get('TEST', {}).get('test_key')}")
            print(f"TEST.test_number = {content.get('TEST', {}).get('test_number')}")
            print(f"TEST.test_list = {content.get('TEST', {}).get('test_list')}")
        except Exception as e:
            print(f"读取保存的配置失败: {e}")
    else:
        print(f"配置文件不存在: {temp_file_path}")





def main():
    """主函数"""
    print("配置服务测试示例")
    print("=" * 50)
    
    # 测试runtime属性
    test_config_runtime()
    
    # 测试配置保存功能
    test_config_save()
    


if __name__ == "__main__":
    main()

