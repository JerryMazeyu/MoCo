#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
餐厅搜索脚本 - 低资源版本
用于在独立进程中执行餐厅搜索，避免主程序内存压力
"""

import os
import sys
import argparse
import json
import tempfile
import datetime
import pandas as pd
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.instances.restaurant import RestaurantModel, Restaurant, RestaurantsGroup
from app.services.functions.get_restaurant_service import GetRestaurantService
from app.config.config import CONF
from app.utils.logger import get_logger

# 获取日志对象
LOGGER = get_logger()


def load_runtime_config(config_file):
    """加载运行时配置"""
    if config_file and os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                runtime_config = json.load(f)
            
            # 应用运行时配置到CONF
            if not hasattr(CONF, 'runtime'):
                setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
            
            for key, value in runtime_config.items():
                setattr(CONF.runtime, key, value)
            
            LOGGER.info(f"已加载运行时配置: {config_file}")
            return True
        except Exception as e:
            LOGGER.error(f"加载运行时配置失败: {e}")
    return False


def search_restaurants(city, cp_id, use_llm=True, output_dir=None, keyword=None):
    """
    搜索餐厅信息
    
    Args:
        city: 城市名称
        cp_id: CP ID
        use_llm: 是否使用大模型
        output_dir: 输出目录
        keyword: 搜索关键词（可选）
    
    Returns:
        result_file: 结果文件路径
    """
    try:
        LOGGER.info(f"开始搜索餐厅 - 城市: {city}, CP: {cp_id}, 关键词: {keyword}")
        
        # 创建服务实例
        restaurant_service = GetRestaurantService()
        
        # 先加载默认关键词
        restaurant_service.load_keywords()
        restaurant_service.load_blocked_words()
        
        # 如果指定了关键词，需要临时修改服务的关键词列表
        original_keywords = None
        if keyword:
            # 保存原始关键词列表
            if hasattr(restaurant_service, 'keywords_list'):
                original_keywords = restaurant_service.keywords_list.copy()
            # 设置为指定的关键词
            restaurant_service.keywords_list = [keyword]
            LOGGER.info(f"设置搜索关键词为: {keyword}")
        else:
            LOGGER.info(f"使用默认关键词: {restaurant_service.keywords_list}")
        
        # 获取基础餐厅信息
        LOGGER.info("正在从API获取餐厅基础信息...")
        
        # 临时标记，防止run方法重新加载关键词
        restaurant_service._keywords_already_loaded = True
        
        restaurant_service.run(
            cities=city, 
            cp_id=cp_id, 
            model_class=RestaurantModel,
            file_path=None, 
            use_api=True, 
            if_gen_info=False,  # 搜索阶段不生成详细信息
            use_llm=use_llm
        )
        
        # 恢复原始关键词列表
        if original_keywords is not None:
            restaurant_service.keywords_list = original_keywords
        
        # 清除临时标记
        if hasattr(restaurant_service, '_keywords_already_loaded'):
            delattr(restaurant_service, '_keywords_already_loaded')
        
        # 检查是否有餐厅信息
        if not restaurant_service.restaurants:
            LOGGER.warning(f"未找到 {city} 的餐厅信息")
            return None
        
        restaurants_count = len(restaurant_service.restaurants)
        LOGGER.info(f"已找到 {restaurants_count} 家餐厅")
        
        # 获取餐厅组
        restaurant_group = restaurant_service.get_restaurants_group()
        
        # 转换为DataFrame
        restaurant_data = restaurant_group.to_dataframe()
        
        # 生成输出文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if keyword:
            filename = f"restaurants_{city}_{keyword}_{restaurants_count}_{timestamp}.xlsx"
        else:
            filename = f"restaurants_{city}_all_{restaurants_count}_{timestamp}.xlsx"
        
        # 确保输出目录存在
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            result_file = os.path.join(output_dir, filename)
        else:
            result_file = filename
        
        # 保存结果
        restaurant_data.to_excel(result_file, index=False)
        LOGGER.info(f"已将 {len(restaurant_data)} 条记录保存到: {result_file}")
        
        # 保存状态信息
        status_info = {
            "status": "completed",
            "city": city,
            "keyword": keyword,
            "count": restaurants_count,
            "file": result_file,
            "timestamp": timestamp
        }
        
        status_file = os.path.join(os.path.dirname(result_file), f"status_{keyword if keyword else 'all'}_{timestamp}.json")
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_info, f, ensure_ascii=False, indent=2)
        
        return result_file
        
    except Exception as e:
        LOGGER.error(f"搜索餐厅时出错: {str(e)}")
        
        # 保存错误状态
        if output_dir:
            error_info = {
                "status": "failed",
                "city": city,
                "keyword": keyword,
                "error": str(e),
                "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
            error_file = os.path.join(output_dir, f"error_{keyword if keyword else 'all'}.json")
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_info, f, ensure_ascii=False, indent=2)
        
        raise


def check_existing_results(city, temp_base_dir):
    """
    检查是否存在同城市的临时结果
    
    Args:
        city: 城市名称
        temp_base_dir: 临时文件基础目录
    
    Returns:
        existing_dirs: 存在的结果目录列表
    """
    existing_dirs = []
    
    if os.path.exists(temp_base_dir):
        for item in os.listdir(temp_base_dir):
            item_path = os.path.join(temp_base_dir, item)
            if os.path.isdir(item_path) and city in item:
                # 检查目录中是否有状态文件
                status_files = [f for f in os.listdir(item_path) if f.startswith("status_") and f.endswith(".json")]
                if status_files:
                    existing_dirs.append({
                        "path": item_path,
                        "name": item,
                        "status_files": status_files
                    })
    
    return existing_dirs


def merge_results(result_files, output_file):
    """
    合并多个结果文件
    
    Args:
        result_files: 结果文件列表
        output_file: 输出文件路径
    
    Returns:
        merged_count: 合并后的记录数
    """
    all_data = []
    
    for file_path in result_files:
        if os.path.exists(file_path) and file_path.endswith('.xlsx'):
            try:
                data = pd.read_excel(file_path)
                all_data.append(data)
                LOGGER.info(f"已加载 {len(data)} 条记录从: {file_path}")
            except Exception as e:
                LOGGER.error(f"加载文件失败 {file_path}: {e}")
    
    if all_data:
        # 合并所有数据
        merged_data = pd.concat(all_data, ignore_index=True)
        
        # 去重（基于餐厅名称和地址）
        if 'rest_chinese_name' in merged_data.columns and 'rest_chinese_address' in merged_data.columns:
            merged_data = merged_data.drop_duplicates(
                subset=['rest_chinese_name', 'rest_chinese_address'], 
                keep='first'
            )
        
        # 保存合并结果
        merged_data.to_excel(output_file, index=False)
        LOGGER.info(f"已合并 {len(merged_data)} 条记录到: {output_file}")
        
        return len(merged_data)
    
    return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='餐厅搜索脚本（低资源版）')
    parser.add_argument('--city', required=True, help='城市名称')
    parser.add_argument('--cp_id', required=True, help='CP ID')
    parser.add_argument('--use_llm', type=bool, default=True, help='是否使用大模型')
    parser.add_argument('--output_dir', help='输出目录')
    parser.add_argument('--keywords', nargs='*', help='搜索关键词列表')
    parser.add_argument('--config_file', help='运行时配置文件')
    parser.add_argument('--check_existing', action='store_true', help='检查已存在的结果')
    parser.add_argument('--merge_only', action='store_true', help='仅合并结果')
    parser.add_argument('--result_files', nargs='*', help='要合并的结果文件列表')
    
    args = parser.parse_args()
    
    # 加载运行时配置
    if args.config_file:
        load_runtime_config(args.config_file)
    
    # 如果只是合并结果
    if args.merge_only and args.result_files:
        output_file = os.path.join(args.output_dir, f"merged_restaurants_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        count = merge_results(args.result_files, output_file)
        print(f"合并完成: {count} 条记录")
        return
    
    # 检查已存在的结果
    if args.check_existing:
        temp_base_dir = tempfile.gettempdir()
        existing = check_existing_results(args.city, temp_base_dir)
        print(json.dumps(existing, ensure_ascii=False, indent=2))
        return
    
    # 执行搜索
    try:
        result_files = []
        
        if args.keywords:
            # 按关键词搜索
            for keyword in args.keywords:
                LOGGER.info(f"正在搜索关键词: {keyword}")
                result_file = search_restaurants(
                    city=args.city,
                    cp_id=args.cp_id,
                    use_llm=args.use_llm,
                    output_dir=args.output_dir,
                    keyword=keyword
                )
                if result_file:
                    result_files.append(result_file)
        else:
            # 搜索全部
            LOGGER.info("正在搜索全部餐厅")
            result_file = search_restaurants(
                city=args.city,
                cp_id=args.cp_id,
                use_llm=args.use_llm,
                output_dir=args.output_dir,
                keyword=None
            )
            if result_file:
                result_files.append(result_file)
        
        # 合并结果
        if len(result_files) > 1:
            merged_file = os.path.join(args.output_dir, f"merged_restaurants_{args.city}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            merge_results(result_files, merged_file)
            print(f"搜索完成，结果已保存到: {merged_file}")
        elif result_files:
            print(f"搜索完成，结果已保存到: {result_files[0]}")
        else:
            print("搜索完成，但未找到任何餐厅")
        
    except Exception as e:
        LOGGER.error(f"搜索失败: {str(e)}")
        print(f"错误: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 