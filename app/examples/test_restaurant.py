#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
餐厅实体服务测试
"""

import sys
import os
from typing import Dict, List, Any, NamedTuple



from app.services.instances.restaurant import Restaurant, youdao_translate, kimi_restaurant_type_analysis


class MockConfig:
    """
    模拟配置对象
    """
    class KeysConfig:
        def __init__(self):
            # 有道翻译API密钥 (格式: 'appKey:appSecret')
            self.youdao_keys = [
                '007cbb450396e84c:O4keGC6lUemzDdYUiGmgVSWrEhUpjirW'
            ]
            # KIMI API密钥
            self.kimi_keys = [
                'sk-BUDGJQ7FPLCKPD9dgTON2LYswQolHPX7XY7JOIQwvOBh1qlr'
            ]
    
    class StreetMaps:
        def __init__(self):
            # 模拟街道地图数据
            self.guangzhou = {
                "天河区": ["天河路", "体育西路", "林和西路"],
                "越秀区": ["北京路", "中山路", "解放路"],
                "海珠区": ["江南大道", "新港西路", "滨江路"]
            }
    
    def __init__(self):
        self.KEYS = self.KeysConfig()
        self.STREETMAPS = self.StreetMaps()


def test_youdao_translate():
    """
    测试有道翻译功能
    """
    print("=== 测试有道翻译 ===")
    
    # 有道API密钥 (格式: 'appKey:appSecret')
    api_key = '007cbb450396e84c:O4keGC6lUemzDdYUiGmgVSWrEhUpjirW'
    
    # 测试数据
    test_texts = [
        "你好，世界",
        "舒心川湘粤菜",
        "惠州市博罗县罗阳镇四角楼塘上村小罗路188号"
    ]
    
    for text in test_texts:
        try:
            result = youdao_translate(text, 'zh', 'en', api_key)
            print(f"源文本: {text}")
            print(f"翻译结果: {result}")
            print("---")
        except Exception as e:
            print(f"翻译 '{text}' 时出错: {e}")
    
    print()


def test_kimi_restaurant_type():
    """
    测试KIMI餐厅类型分析
    """
    print("=== 测试KIMI餐厅类型分析 ===")
    
    # KIMI API密钥
    api_key = 'sk-BUDGJQ7FPLCKPD9dgTON2LYswQolHPX7XY7JOIQwvOBh1qlr'
    
    # 测试数据
    test_restaurants = [
        {
            "name": "舒心川湘粤菜",
            "address": "惠州市博罗县罗阳镇四角楼塘上村小罗路188号"
        },
        {
            "name": "好滋味川菜馆",
            "address": "广州市天河区天河路385号"
        }
    ]
    
    for rest in test_restaurants:
        try:
            result = kimi_restaurant_type_analysis(rest, api_key)
            print(f"餐厅: {rest['name']}")
            print(f"地址: {rest['address']}")
            print(f"类型分析结果: {result}")
            print("---")
        except Exception as e:
            print(f"分析餐厅 '{rest['name']}' 类型时出错: {e}")
    
    print()


def test_restaurant_entity():
    """
    测试餐厅实体类
    """
    print("=== 测试餐厅实体类 ===")
    
    # 创建配置
    conf = MockConfig()
    
    # 测试数据
    test_restaurants = [
        {
            "rest_chinese_name": "舒心川湘粤菜",
            "rest_chinese_address": "惠州市博罗县罗阳镇四角楼塘上村小罗路188号",
            "rest_city": "guangzhou"  # 注意：这里使用的城市与实际地址不符，仅作测试
        },
        {
            "rest_chinese_name": "好滋味川菜馆",
            "rest_chinese_address": "广州市天河区天河路385号",
            "rest_city": "guangzhou"
        }
    ]
    
    for rest_info in test_restaurants:
        try:
            # 创建餐厅实体
            restaurant = Restaurant(rest_info, model=None, conf=conf)
            
            # 生成英文名
            restaurant._generate_english_name()
            
            # 生成英文地址
            restaurant._generate_english_address()
            
            # 生成餐厅类型
            restaurant._generate_type()
            
            # 提取区域和街道
            restaurant._extract_district_and_street()
            
            # 打印结果
            print(f"餐厅: {restaurant.inst.rest_chinese_name}")
            print(f"英文名: {getattr(restaurant.inst, 'rest_english_name', '未生成')}")
            print(f"英文地址: {getattr(restaurant.inst, 'rest_english_address', '未生成')}")
            print(f"餐厅类型: {getattr(restaurant.inst, 'rest_type', '未生成')}")
            print(f"区域: {getattr(restaurant.inst, 'rest_district', '未生成')}")
            print(f"街道: {getattr(restaurant.inst, 'rest_street', '未生成')}")
            print("---")
        except Exception as e:
            print(f"处理餐厅 '{rest_info['rest_chinese_name']}' 时出错: {e}")
    
    print()


if __name__ == "__main__":
    # 测试有道翻译
    test_youdao_translate()
    
    # 测试KIMI餐厅类型分析
    test_kimi_restaurant_type()
    
    # 测试餐厅实体类
    test_restaurant_entity() 