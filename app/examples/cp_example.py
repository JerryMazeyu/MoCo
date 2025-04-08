#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CP类测试示例脚本
演示如何创建、注册和查询CP
"""

import os
import sys

try:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
except Exception as e:
    pass

from app.services.instances.cp import CP, CPsGroup
from app.config.config import CONF
from app.utils.logger import setup_logger

# 设置日志
LOGGER = setup_logger()

def test_create_cp():
    """测试创建CP实例"""
    # 创建CP信息
    cp_info = {
        "cp_name": "测试CP",
        "cp_province": "广东省",
        "cp_city": "广州市",
        "cp_location": "23.129163,113.264435",  # 广州坐标
        "cp_barrels_per_day": 100,
        "cp_capacity": 1000
    }
    
    # 创建CP实例
    cp = CP(cp_info)
    LOGGER.info(f"创建CP实例: {cp}")
    
    # 生成ID
    cp._generate_id()
    LOGGER.info(f"生成ID后: {cp.inst.cp_id}")
    
    return cp

def test_register_cp(cp):
    """测试注册CP到OSS"""
    success = cp.register()
    if success:
        LOGGER.info(f"CP注册成功: {cp}")
    else:
        LOGGER.error(f"CP注册失败: {cp}")
    return success

def test_list_cps():
    """测试获取所有CP列表"""
    cp_list = CP.list()
    LOGGER.info(f"获取到{len(cp_list)}个CP")
    for i, cp_data in enumerate(cp_list):
        LOGGER.info(f"CP {i+1}: {cp_data.get('cp_name')} (ID: {cp_data.get('cp_id')})")
    return cp_list

def test_get_cp_by_id(cp_id):
    """测试通过ID获取CP"""
    cp = CP.get_by_id(cp_id)
    if cp:
        LOGGER.info(f"成功获取CP: {cp}")
    else:
        LOGGER.error(f"获取CP失败, ID: {cp_id}")
    return cp

def test_cp_group():
    """测试CP组合功能"""
    # 获取所有CP
    cp_list = CP.list()
    
    # 创建CP实例列表
    cps = []
    for cp_data in cp_list:
        cp = CP(cp_data)
        cps.append(cp)
    
    # 创建CP组合
    cp_group = CPsGroup(cps, "all")
    LOGGER.info(f"创建CP组合: {cp_group}")
    
    return cp_group

def main():
    """主函数"""
    try:
        # 创建测试CP
        cp = test_create_cp()
        
        # 注册CP
        test_register_cp(cp)
        
        # 获取CP列表
        cp_list = test_list_cps()
        
        # 如果有CP，则测试通过ID获取
        if cp_list:
            cp_id = cp_list[0].get('cp_id')
            test_get_cp_by_id(cp_id)
        
        # 测试CP组合
        test_cp_group()
        
        LOGGER.info("测试完成")
        
    except Exception as e:
        LOGGER.error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    main() 