"""
餐厅服务示例脚本
"""

import os
import sys
import pandas as pd

from app.services.functions import GetRestaurantsService
from app.services.instances import Restaurant, RestaurantsGroup
from app.utils.logger import setup_logger
from app.utils.file_io import rp

# 设置日志
logger = setup_logger()

def manually_create_restaurant():
    """
    手动创建餐厅示例
    """
    # 创建一个餐厅信息字典
    restaurant_info = {
        'rest_chinese_name': '味道一流饭店',
        'rest_city': '惠州',
        'rest_province': '广东',
        'rest_chinese_address': '广东省惠州市博罗县园洲镇XX路123号',
        'rest_belonged_cp': 'CP001'
    }
    
    # 创建餐厅实体
    restaurant = Restaurant(restaurant_info)
    
    # 生成缺失字段
    success = restaurant.generate()
    
    # 打印结果
    logger.info(f"餐厅生成结果: {'成功' if success else '失败'}")
    logger.info(f"餐厅信息: {restaurant}")
    
    # 保存到Excel
    file_path = rp("example_restaurant.xlsx", folder="assets")
    restaurant.save_to_excel(file_path)
    logger.info(f"已将餐厅信息保存到: {file_path}")
    
    return restaurant

def create_restaurants_group():
    """
    创建餐厅组合示例
    """
    # 创建多个餐厅
    restaurants = []
    
    restaurant_infos = [
        {
            'rest_chinese_name': '味道一流饭店',
            'rest_city': '惠州',
            'rest_province': '广东',
            'rest_chinese_address': '广东省惠州市博罗县园洲镇XX路123号',
            'rest_belonged_cp': 'CP001'
        },
        {
            'rest_chinese_name': '老街烧烤',
            'rest_city': '惠州',
            'rest_province': '广东',
            'rest_chinese_address': '广东省惠州市博罗县园洲镇YY街45号',
            'rest_belonged_cp': 'CP001'
        },
        {
            'rest_chinese_name': '川湘小馆',
            'rest_city': '惠州',
            'rest_province': '广东',
            'rest_chinese_address': '广东省惠州市惠城区ZZ大道67号',
            'rest_belonged_cp': 'CP002'
        }
    ]
    
    for info in restaurant_infos:
        restaurant = Restaurant(info)
        restaurant.generate()
        restaurants.append(restaurant)
    
    # 创建餐厅组合
    group = RestaurantsGroup(restaurants, group_type='example')
    
    # 打印结果
    logger.info(f"餐厅组合: {group}")
    
    # 保存到Excel
    file_path = rp("example_restaurants_group.xlsx", folder="assets")
    group.save_to_excel(file_path)
    logger.info(f"已将餐厅组合保存到: {file_path}")
    
    return group

def use_get_restaurants_service():
    """
    使用餐厅获取服务示例
    """
    # 创建餐厅获取服务实例
    service = GetRestaurantsService()
    
    # 手动添加一些餐厅信息
    service.info = [
        {
            'rest_chinese_name': '味道一流饭店',
            'rest_city': '惠州',
            'rest_province': '广东',
            'rest_chinese_address': '广东省惠州市博罗县园洲镇XX路123号',
            'source': 'manual'
        },
        {
            'rest_chinese_name': '老街烧烤',
            'rest_city': '惠州',
            'rest_province': '广东',
            'rest_chinese_address': '广东省惠州市博罗县园洲镇YY街45号',
            'source': 'manual'
        }
    ]
    
    # 处理餐厅信息
    service._dedup()  # 去重
    service._info_to_restaurant(cp_id='CP001')  # 转换为餐厅实体
    
    # 获取餐厅组合
    group = service.get_restaurants_group()
    
    # 打印结果
    logger.info(f"获取到的餐厅组合: {group}")
    
    # 保存结果
    service.save_results(filename_prefix='example')
    
    return group

def simulate_api_search():
    """
    模拟API搜索餐厅
    
    注意：由于API需要密钥，此函数仅做示例，不会实际调用API
    """
    logger.info("这是一个API搜索模拟示例，不会实际调用API")
    
    # 创建一个伪造的配置对象
    class MockConfig:
        def __init__(self):
            self.KEYS = type('obj', (), {
                'gaode_keys': ['fake_key'],
                'baidu_keys': ['fake_key']
            })
            self.OTHER = type('obj', (), {
                'Tab5': type('obj', (), {
                    '关键词': ['餐厅', '饭店']
                })
            })
    
    mock_config = MockConfig()
    
    # 创建餐厅获取服务
    service = GetRestaurantsService(conf=mock_config)
    
    # 模拟搜索结果
    service.info = [
        {
            'rest_chinese_name': '味道一流饭店',
            'rest_city': '惠州',
            'rest_province': '广东',
            'rest_chinese_address': '广东省惠州市博罗县园洲镇XX路123号',
            'rest_location': '23.123456,114.123456',
            'source': 'gaode'
        },
        {
            'rest_chinese_name': '老街烧烤',
            'rest_city': '惠州',
            'rest_province': '广东',
            'rest_chinese_address': '广东省惠州市博罗县园洲镇YY街45号',
            'rest_location': '23.234567,114.234567',
            'source': 'baidu'
        }
    ]
    
    # 处理餐厅信息
    service._dedup()  # 去重
    service._info_to_restaurant(cp_id='CP001')  # 转换为餐厅实体
    
    # 打印结果
    for restaurant in service.restaurants:
        logger.info(f"餐厅: {restaurant}")
    
    # 保存结果
    service.save_results(filename_prefix='simulation')
    
    return service.get_restaurants_group()

if __name__ == "__main__":
    print("运行餐厅示例...")
    
    # 手动创建餐厅
    print("\n1. 手动创建餐厅:")
    restaurant = manually_create_restaurant()
    
    # 创建餐厅组合
    print("\n2. 创建餐厅组合:")
    group = create_restaurants_group()
    
    # 使用餐厅获取服务
    print("\n3. 使用餐厅获取服务:")
    service_group = use_get_restaurants_service()
    
    # 模拟API搜索
    print("\n4. 模拟API搜索餐厅:")
    api_group = simulate_api_search()
    
    print("\n示例运行完成!") 