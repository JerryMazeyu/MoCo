#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
餐厅信息补全脚本
该脚本可以独立运行，用于补全餐厅信息

使用方法：
python complete_restaurants_info.py --input_file=xxx.xlsx --output_dir=/tmp/ --cp_location=xxx,xxx

参数说明：
--input_file: 输入的Excel文件路径
--output_dir: 输出目录
--cp_location: CP的经纬度坐标，格式为"经度,纬度"
--task_id: 任务ID，用于标识当前任务，主程序通过该ID监控任务状态
--num_workers: 工作线程数，默认为2
--batch_size: 批次大小，默认为20
--log_file: 日志文件路径，默认为output_dir中的log_{task_id}.txt
"""

import os
import sys
import time
import json
import argparse
import tempfile
import pandas as pd
import gc
import traceback
import logging
from datetime import datetime
from pathlib import Path

# 确保可以导入app模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

try:
    from app.services.instances.restaurant import Restaurant, RestaurantsGroup
    from app.services.functions.get_restaurant_service import GetRestaurantService
    from app.utils.logger import setup_logger
except ImportError as e:
    print(f"导入模块失败: {e}")
    sys.exit(1)

class RestaurantCompleter:
    """餐厅信息补全器"""
    
    def __init__(self, input_file, output_dir, cp_location=None, task_id=None, 
                 num_workers=2, batch_size=20, log_file=None):
        """
        初始化补全器
        
        Args:
            input_file: 输入文件路径
            output_dir: 输出目录
            cp_location: CP位置坐标
            task_id: 任务ID
            num_workers: 工作线程数
            batch_size: 批次大小
            log_file: 日志文件路径
        """
        self.input_file = input_file
        self.output_dir = output_dir
        self.cp_location = cp_location
        self.task_id = task_id or datetime.now().strftime("%Y%m%d%H%M%S")
        self.num_workers = int(num_workers)
        self.batch_size = int(batch_size)
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 状态文件名
        self.status_file = os.path.join(self.output_dir, f"status_{self.task_id}.json")
        self.result_file = os.path.join(self.output_dir, f"result_{self.task_id}.xlsx")
        
        # 设置日志文件
        self.log_file = log_file or os.path.join(self.output_dir, f"log_{self.task_id}.txt")
        self._setup_logger()
        
        # 初始化状态
        self.status = {
            "task_id": self.task_id,
            "status": "initializing",  # initializing, running, completed, failed
            "progress": 0,
            "total": 0,
            "completed": 0,
            "message": "初始化中...",
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "result_file": None,
            "log_file": self.log_file,  # 添加日志文件路径到状态
            "error": None
        }
        
        # 保存初始状态
        self._save_status()
        self.logger.info(f"初始化完成，任务ID: {self.task_id}")
        self.logger.info(f"输入文件: {self.input_file}")
        self.logger.info(f"输出目录: {self.output_dir}")
        self.logger.info(f"CP位置: {self.cp_location}")
        self.logger.info(f"工作线程数: {self.num_workers}")
        self.logger.info(f"批次大小: {self.batch_size}")
    
    def _setup_logger(self):
        """设置日志记录器"""
        self.logger = logging.getLogger(f"restaurant_completer_{self.task_id}")
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _save_status(self):
        """保存当前状态到文件"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存状态文件失败: {e}")
    
    def _update_status(self, **kwargs):
        """更新状态"""
        self.status.update(kwargs)
        self._save_status()
    
    def _log_progress(self, message, progress=None):
        """记录进度"""
        self.logger.info(message)
        update_data = {"message": message}
        if progress is not None:
            update_data["progress"] = progress
        self._update_status(**update_data)
    
    def run(self):
        """执行补全过程"""
        try:
            self._update_status(status="running", message="开始处理数据...")
            
            # 1. 加载数据
            self._log_progress("正在加载餐厅数据...")
            restaurant_data = self._load_data()
            
            if restaurant_data is None or len(restaurant_data) == 0:
                self._update_status(
                    status="failed", 
                    message="无法加载数据或数据为空", 
                    end_time=datetime.now().isoformat(),
                    error="无法加载数据或数据为空"
                )
                self.logger.error("无法加载数据或数据为空")
                return False
            
            total_restaurants = len(restaurant_data)
            self._update_status(
                total=total_restaurants,
                message=f"已加载 {total_restaurants} 条餐厅数据"
            )
            self.logger.info(f"成功加载 {total_restaurants} 条餐厅数据")
            
            # 2. 分批处理数据
            result = self._process_data(restaurant_data)
            
            if result:
                self._update_status(
                    status="completed", 
                    message="处理完成", 
                    progress=100,
                    end_time=datetime.now().isoformat(),
                    result_file=self.result_file
                )
                self.logger.info(f"所有处理完成，结果保存至 {self.result_file}")
                return True
            else:
                self._update_status(
                    status="failed", 
                    message="处理失败", 
                    end_time=datetime.now().isoformat(),
                    error="处理过程中出现错误"
                )
                self.logger.error("处理过程中出现错误")
                return False
        except Exception as e:
            error_info = traceback.format_exc()
            self.logger.error(f"处理过程中出现异常: {e}\n{error_info}")
            self._update_status(
                status="failed", 
                message=f"处理出错: {str(e)}", 
                end_time=datetime.now().isoformat(),
                error=str(e)
            )
            return False
    
    def _load_data(self):
        """加载数据"""
        try:
            self.logger.info(f"开始加载文件: {self.input_file}")
            if self.input_file.endswith(('.xlsx', '.xls')):
                self.logger.info("检测到Excel文件格式")
                restaurant_data = pd.read_excel(self.input_file)
            elif self.input_file.endswith('.csv'):
                self.logger.info("检测到CSV文件格式")
                restaurant_data = pd.read_csv(self.input_file)
            else:
                self.logger.error(f"不支持的文件类型: {self.input_file}")
                return None
            
            self.logger.info(f"成功加载数据，共 {len(restaurant_data)} 条记录")
            self.logger.debug(f"数据列: {list(restaurant_data.columns)}")
            return restaurant_data
        except Exception as e:
            self.logger.error(f"加载数据失败: {e}")
            self.logger.exception("详细错误信息:")
            return None
    
    def _process_data(self, restaurant_data):
        """处理数据"""
        try:
            total_restaurants = len(restaurant_data)
            batch_size = self.batch_size
            num_workers = self.num_workers
            
            # 计算总批次数
            total_batches = (total_restaurants + batch_size - 1) // batch_size
            self._log_progress(f"共 {total_restaurants} 条数据，分为 {total_batches} 批处理")
            self.logger.info(f"处理配置: 批次大小={batch_size}, 工作线程数={num_workers}")
            
            # 批次索引列表
            batch_indices = list(range(0, total_restaurants, batch_size))
            
            # 所有处理后的记录
            all_processed_records = []
            completed_count = 0
            
            # 创建服务实例
            self.logger.info("创建GetRestaurantService服务实例")
            service = GetRestaurantService()
            
            # 记录处理开始时间
            process_start_time = time.time()
            
            # 逐批处理
            for batch_idx, start_idx in enumerate(batch_indices):
                batch_start_time = time.time()
                
                # 计算批次范围
                end_idx = min(start_idx + batch_size, total_restaurants)
                
                # 更新进度
                progress = int((batch_idx / total_batches) * 100)
                batch_message = f"处理第 {batch_idx+1}/{total_batches} 批 ({start_idx+1}-{end_idx})"
                self._log_progress(batch_message, progress=progress)
                
                self.logger.info(f"===== 开始 {batch_message} =====")
                
                try:
                    # 提取批次数据
                    self.logger.debug(f"提取批次数据 {start_idx+1}-{end_idx}")
                    batch_data = restaurant_data.iloc[start_idx:end_idx].copy()
                    
                    # 转换为记录
                    batch_records = batch_data.to_dict('records')
                    self.logger.debug(f"批次数据转换为记录，数量: {len(batch_records)}")
                    
                    # 创建餐厅实例
                    restaurant_instances = []
                    success_count = 0
                    self.logger.info(f"开始创建餐厅实例...")
                    
                    for idx, restaurant_info in enumerate(batch_records):
                        try:
                            restaurant = Restaurant(restaurant_info, cp_location=self.cp_location)
                            restaurant_instances.append(restaurant)
                            success_count += 1
                        except Exception as e:
                            self.logger.error(f"创建餐厅实例 {idx} 失败: {e}")
                            continue
                    
                    self.logger.info(f"成功创建 {success_count}/{len(batch_records)} 个餐厅实例")
                    
                    # 释放批次数据
                    batch_data = None
                    batch_records = None
                    gc.collect()
                    
                    # 创建餐厅组并生成信息
                    if restaurant_instances:
                        # 创建餐厅组
                        self.logger.info(f"创建餐厅组，成员数: {len(restaurant_instances)}")
                        restaurant_group = RestaurantsGroup(restaurant_instances)
                        restaurant_instances = None
                        
                        # 使用GetRestaurantService补全信息
                        try:
                            self.logger.info(f"开始补全餐厅信息，使用 {num_workers} 个工作线程")
                            processed_group = service.gen_info(restaurant_group, num_workers=num_workers)
                            self.logger.info(f"补全信息完成")
                        except Exception as e:
                            self.logger.error(f"补全信息失败: {e}")
                            self.logger.exception("详细错误信息:")
                            processed_group = restaurant_group
                        
                        restaurant_group = None
                        
                        # 提取结果
                        batch_processed_records = []
                        batch_completed = 0
                        self.logger.info(f"开始提取处理结果...")
                        
                        for restaurant in processed_group.members:
                            if hasattr(restaurant, 'inst') and restaurant.inst:
                                try:
                                    restaurant_dict = restaurant.to_dict()
                                    batch_processed_records.append(restaurant_dict)
                                    batch_completed += 1
                                except Exception as e:
                                    self.logger.error(f"提取餐厅数据失败: {e}")
                        
                        # 更新计数
                        completed_count += batch_completed
                        self.logger.info(f"本批次成功处理 {batch_completed} 条记录")
                        
                        # 添加到总结果
                        all_processed_records.extend(batch_processed_records)
                        
                        # 更新状态文件中的已完成数量
                        self._update_status(
                            completed=completed_count,
                            progress=progress
                        )
                        
                        # 释放资源
                        batch_processed_records = None
                        processed_group = None
                        gc.collect()
                        
                        # 每个批次都保存中间结果，增加实时性
                        # 保存中间结果
                        self.logger.info(f"保存中间结果...")
                        interim_df = pd.DataFrame(all_processed_records)
                        # 保存到临时文件
                        interim_df.to_excel(self.result_file, index=False)
                        interim_df = None
                        
                        # 更新状态
                        self._update_status(
                            completed=completed_count,
                            progress=progress,
                            message=f"已完成 {completed_count}/{total_restaurants} 条记录，保存中间结果"
                        )
                        
                        # 主动调用垃圾回收
                        gc.collect()
                    
                    # 计算批次处理时间
                    batch_time = time.time() - batch_start_time
                    self.logger.info(f"批次 {batch_idx+1} 处理完成，耗时: {batch_time:.2f}秒")
                    
                    # 计算平均每条记录处理时间
                    avg_time_per_record = batch_time / (end_idx - start_idx) if end_idx > start_idx else 0
                    self.logger.info(f"平均每条记录处理时间: {avg_time_per_record:.2f}秒")
                    
                    # 预估剩余时间
                    if batch_idx < total_batches - 1:
                        remaining_records = total_restaurants - end_idx
                        estimated_time = remaining_records * avg_time_per_record
                        self.logger.info(f"预估剩余时间: {estimated_time:.2f}秒 (约 {estimated_time/60:.2f}分钟)")
                        
                        # 更新状态文件添加剩余时间估计
                        self._update_status(
                            estimated_remaining_time=f"{estimated_time/60:.2f}分钟"
                        )
                    
                    # 处理完一批次后暂停一下，让系统喘息
                    if batch_idx % 3 == 2:
                        self.logger.info("批次间暂停0.5秒...")
                        time.sleep(0.5)
                        
                except Exception as e:
                    self.logger.error(f"处理批次 {batch_idx+1} 失败: {e}")
                    self.logger.exception("详细错误信息:")
            
            # 计算总处理时间
            total_process_time = time.time() - process_start_time
            self.logger.info(f"所有批次处理完成，总耗时: {total_process_time:.2f}秒 (约 {total_process_time/60:.2f}分钟)")
            
            # 所有批次处理完毕，创建最终结果
            if all_processed_records:
                try:
                    # 创建最终DataFrame
                    self.logger.info(f"创建最终结果DataFrame，共 {len(all_processed_records)} 条记录")
                    result_df = pd.DataFrame(all_processed_records)
                    
                    # 保存最终结果
                    self.logger.info(f"保存最终结果到 {self.result_file}")
                    result_df.to_excel(self.result_file, index=False)
                    
                    # 更新状态
                    self._update_status(
                        completed=completed_count,
                        progress=100,
                        message=f"处理完成，共补全 {completed_count}/{total_restaurants} 条记录",
                        result_file=self.result_file,
                        total_process_time=f"{total_process_time/60:.2f}分钟"
                    )
                    
                    self.logger.info(f"处理成功完成，共补全 {completed_count}/{total_restaurants} 条记录")
                    return True
                except Exception as e:
                    self.logger.error(f"创建最终结果失败: {e}")
                    self.logger.exception("详细错误信息:")
                    return False
            else:
                self.logger.error("没有成功处理任何餐厅记录")
                return False
                
        except Exception as e:
            self.logger.error(f"处理数据失败: {e}")
            self.logger.exception("详细错误信息:")
            return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='餐厅信息补全脚本')
    parser.add_argument('--input_file', required=True, help='输入文件路径')
    parser.add_argument('--output_dir', default=tempfile.gettempdir(), help='输出目录')
    parser.add_argument('--cp_location', help='CP位置，格式为"经度,纬度"')
    parser.add_argument('--task_id', help='任务ID')
    parser.add_argument('--num_workers', default=2, type=int, help='工作线程数')
    parser.add_argument('--batch_size', default=20, type=int, help='批次大小')
    parser.add_argument('--log_file', help='日志文件路径')
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 创建补全器
    completer = RestaurantCompleter(
        input_file=args.input_file,
        output_dir=args.output_dir,
        cp_location=args.cp_location,
        task_id=args.task_id,
        num_workers=args.num_workers,
        batch_size=args.batch_size,
        log_file=args.log_file
    )
    
    # 执行处理
    success = completer.run()
    
    # 返回结果
    return 0 if success else 1

if __name__ == '__main__':
    # 设置当前工作目录为项目根目录
    os.chdir(project_root)
    sys.exit(main())
