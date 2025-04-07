"""
餐厅服务示例脚本
"""

import os
import sys
try:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
except Exception as e:
    pass

import pandas as pd

from app.services.functions import GetRestaurantsService
from app.services.instances import Restaurant, RestaurantsGroup
from app.utils.logger import setup_logger
from app.utils.file_io import rp

# 设置日志
logger = setup_logger("moco.log")

def test_example():
    """
    手动创建餐厅示例
    """
    # 创建一个餐厅信息字典
    restaurant_info = {
        'rest_chinese_name': '鱼拿酸菜鱼(江北店)',
        'rest_city': '惠州',
        'rest_chinese_address': '惠州大道中路38号地下层1-BF12',
        'rest_belonged_cp': 'CP001',
        'rest_contact_phone': '18948223006', 
        'rest_location': '114.419921,23.122502'
    }

    restaurant_info2 = {
        'rest_chinese_name': '柠檬鱼御厨房',
        'rest_city': '惠州',
        'rest_chinese_address': '东平大道50号122',
        'rest_belonged_cp': 'CP001',
        'rest_contact_phone': '0752-2476929', 
        'rest_location': '114.428450,23.086066',
        'rest_district': '惠城区'
    }
    
    # 创建餐厅实体
    restaurant = Restaurant(restaurant_info)
    restaurant2 = Restaurant(restaurant_info2)
    # 生成缺失字段
    success = restaurant.generate()
    success2 = restaurant2.generate()

    restaurants = RestaurantsGroup([restaurant, restaurant2], group_type='example')

    rest = restaurants.filter_by_cp('CP001')
    rest = restaurants.filter_by_district('惠城区')
    rest = restaurants.get_by_name('鱼拿酸菜鱼(江北店)')
    restaurants.save_to_excel(rp("example_restaurant.xlsx", folder="assets"))

    return restaurant


if __name__ == "__main__":
    print("运行餐厅示例...")
    
    # 手动创建餐厅
    print("\n1. 手动创建餐厅:")
    restaurant = test_example()
    
    print("\n示例运行完成!") 