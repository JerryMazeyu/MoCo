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


def test_config_save_with_content():
    """测试使用content参数的配置保存功能"""
    print("\n测试使用content参数的配置保存功能...")
    
    # 创建一个新的配置字典
    new_config = {
        "TEST": {
            "new_key": "新的值",
            "new_number": 456,
            "new_list": [4, 5, 6]
        },
        "NEW_SECTION": {
            "item1": "值11",
            "item2": "值22"
        },
        "runtime": {
            "test_value": "test222_value",}
    }
    
    # 保存前打印当前配置
    print("保存前的配置:")
    if "TEST" in CONF._config_dict:
        print(f"TEST.test_key = {CONF._config_dict.get('TEST', {}).get('test_key')}")
    if "NEW_SECTION" in CONF._config_dict:
        print(f"NEW_SECTION存在: {bool('NEW_SECTION' in CONF._config_dict)}")
    
    # 使用新配置保存
    result = CONF.save(new_config)
    print(f"使用content参数保存配置结果: {'成功' if result else '失败'}")
    
    # 验证CONF对象是否已更新
    print("\n保存后CONF对象的配置内容:")
    print(f"TEST.new_key = {CONF._config_dict.get('TEST', {}).get('new_key')}")
    print(f"TEST.new_number = {CONF._config_dict.get('TEST', {}).get('new_number')}")
    print(f"TEST.new_list = {CONF._config_dict.get('TEST', {}).get('new_list')}")
    print(f"NEW_SECTION.item1 = {CONF._config_dict.get('NEW_SECTION', {}).get('item1')}")
    
    # 测试通过ConfigWrapper访问新配置
    print("\n通过ConfigWrapper访问新配置:")
    print(f"CONF.TEST.new_key = {CONF.TEST.new_key}")
    print(f"CONF.NEW_SECTION.item1 = {CONF.NEW_SECTION.item1}")
    
    # # 显示保存的文件路径
    # temp_file_path = os.path.join(f"{CONF.username}_temp.yaml")
    # if os.path.exists(temp_file_path):
    #     print(f"\n配置已保存到: {temp_file_path}")
        
    #     # 读取保存的文件内容并显示
    #     try:
    #         with open(temp_file_path, "r", encoding="utf-8") as f:
    #             content = yaml.safe_load(f)
    #         print("\n保存的配置文件内容:")
    #         print(f"TEST.new_key = {content.get('TEST', {}).get('new_key')}")
    #         print(f"NEW_SECTION.item1 = {content.get('NEW_SECTION', {}).get('item1')}")
    #     except Exception as e:
    #         print(f"读取保存的配置失败: {e}")
    # else:
    #     print(f"配置文件不存在: {temp_file_path}")


def main():
    # """主函数"""
    # print("配置服务测试示例")
    # print("=" * 50)
    
    # # 测试runtime属性
    # test_config_runtime()
    
    # # 测试配置保存功能
    # test_config_save()
    
    # 测试使用content参数的配置保存功能
    test_config_save_with_content()


if __name__ == "__main__":
    main()

