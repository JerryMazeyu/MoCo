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
import uuid
import shutil
from datetime import datetime
from pathlib import Path

# 确保可以导入app模块
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

try:
    from app.services.instances.restaurant import Restaurant, RestaurantsGroup
    from app.services.functions.get_restaurant_service import GetRestaurantService
    from app.utils.logger import setup_logger, get_batch_logger, write_batch_completion_file, count_completed_batches
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
        
        # 确保每次运行都创建新的任务ID
        self.task_id = task_id or str(uuid.uuid4())
        self.num_workers = int(num_workers)
        self.batch_size = int(batch_size)
        
        # 创建以task_id为名称的子文件夹
        self.task_dir = os.path.join(self.output_dir, self.task_id)
        os.makedirs(self.task_dir, exist_ok=True)
        
        # 状态文件名 - 存储在顶层目录，以便主程序可以找到
        self.status_file = os.path.join(self.output_dir, f"status_{self.task_id}.json")
        
        # 结果文件 - 同样存储在顶层目录，与状态文件位置一致
        self.task_result_file = os.path.join(self.task_dir, f"result_{self.task_id}.xlsx")
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
            "result_file": self.result_file,  # 使用顶层目录的结果文件路径
            "log_file": self.log_file,  # 添加日志文件路径到状态
            "error": None,
            "task_dir": self.task_dir  # 添加任务目录到状态
        }
        
        # 保存初始状态
        self._save_status()
        self.logger.info(f"初始化完成，任务ID: {self.task_id}")
        self.logger.info(f"输入文件: {self.input_file}")
        self.logger.info(f"输出目录: {self.task_dir}")
        self.logger.info(f"CP位置: {self.cp_location}")
        self.logger.info(f"工作线程数: {self.num_workers}")
        self.logger.info(f"批次大小: {self.batch_size}")
        self.logger.info(f"结果文件将保存到两个位置:")
        self.logger.info(f"1. 工作目录内: {self.task_result_file}")
        self.logger.info(f"2. 主目录: {self.result_file}")
        self.logger.info(f"状态文件位置: {self.status_file}")
        
        # 记录当前已加载的运行时配置
        try:
            from app.config.config import CONF
            if hasattr(CONF, 'runtime'):
                runtime_attrs = {}
                for attr in dir(CONF.runtime):
                    if not attr.startswith('_') and not callable(getattr(CONF.runtime, attr)):
                        runtime_attrs[attr] = getattr(CONF.runtime, attr)
                
                if runtime_attrs:
                    self.logger.info(f"当前运行时配置: {json.dumps(runtime_attrs, ensure_ascii=False)}")
                else:
                    self.logger.info("当前无运行时配置")
        except Exception as e:
            self.logger.warning(f"获取运行时配置信息失败: {e}")
    
    def _setup_logger(self):
        """设置日志记录器"""
        self.logger = setup_logger(self.log_file)
    
    def _flush_log(self):
        """手动刷新日志到磁盘"""
        if hasattr(self, 'file_handler') and self.file_handler:
            self.file_handler.flush()
    
    def _save_status(self):
        """保存当前状态到文件"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())  # 确保写入磁盘
        except Exception as e:
            self.logger.error(f"保存状态文件失败: {e}")
            self._flush_log()
    
    def _update_status(self, **kwargs):
        """更新状态"""
        self.status.update(kwargs)
        self._save_status()
    
    def _log_progress(self, message, progress=None):
        """记录进度"""
        self.logger.info(message)
        self._flush_log()  # 每次记录进度时立即刷新日志
        update_data = {"message": message}
        if progress is not None:
            update_data["progress"] = progress
        self._update_status(**update_data)
    
    def _save_to_both_locations(self, df, message="保存结果"):
        """将结果保存到两个位置，确保UI可以找到文件"""
        try:
            # 保存到任务目录内
            self.logger.info(f"{message}到工作目录: {self.task_result_file}")
            df.to_excel(self.task_result_file, index=False)

            # 保存到主输出目录（UI期望的位置）
            self.logger.info(f"{message}到主目录: {self.result_file}")
            df.to_excel(self.result_file, index=False)
            
            # 验证文件是否存在
            if os.path.exists(self.result_file):
                self.logger.info(f"已确认主目录结果文件存在: {self.result_file}")
            else:
                self.logger.error(f"无法在主目录找到结果文件: {self.result_file}")
                # 尝试再次复制
                if os.path.exists(self.task_result_file):
                    shutil.copy2(self.task_result_file, self.result_file)
                    self.logger.info(f"已从工作目录复制结果文件到主目录")
            
            self._flush_log()
            return True
        except Exception as e:
            self.logger.error(f"{message}失败: {e}")
            self.logger.exception("详细错误信息:")
            self._flush_log()
            return False
        
    def run(self):
        """执行补全过程"""
        try:
            self._update_status(status="running", message="开始处理数据...")
            self._flush_log()
            
            # 检查并输出运行时配置信息
            try:
                from app.config.config import CONF
                if hasattr(CONF, 'runtime'):
                    runtime_attrs = {}
                    for attr in dir(CONF.runtime):
                        if not attr.startswith('_') and not callable(getattr(CONF.runtime, attr)):
                            value = getattr(CONF.runtime, attr)
                            # 仅记录简单类型
                            # if isinstance(value, (int, float, bool, dict, list)) or value is None:
                            runtime_attrs[attr] = value
                    
                    if runtime_attrs:
                        self.logger.info(f"运行时配置详情: {json.dumps(runtime_attrs, ensure_ascii=False)}")
                        
                        # 特别记录重要配置项
                        if hasattr(CONF.runtime, 'STRICT_MODE'):
                            self.logger.info(f"严格模式: {CONF.runtime.STRICT_MODE}")
                        if hasattr(CONF.runtime, 'SEARCH_RADIUS'):
                            self.logger.info(f"搜索半径: {CONF.runtime.SEARCH_RADIUS}")
            except Exception as e:
                self.logger.warning(f"记录运行时配置时出错: {e}")
            
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
                self._flush_log()
                return False
            
            total_restaurants = len(restaurant_data)
            self._update_status(
                total=total_restaurants,
                message=f"已加载 {total_restaurants} 条餐厅数据"
            )
            self.logger.info(f"成功加载 {total_restaurants} 条餐厅数据")
            self._flush_log()
            
            # 2. 分批处理数据
            result = self._process_data(restaurant_data, self.logger)
            
            if result:
                self._update_status(
                    status="completed", 
                    message="处理完成", 
                    progress=100,
                    end_time=datetime.now().isoformat(),
                    result_file=self.result_file  # 确保最终状态使用主目录中的结果文件路径
                )
                self.logger.info(f"所有处理完成，结果保存至 {self.result_file}")
                self._flush_log()
                return True
            else:
                self._update_status(
                    status="failed", 
                    message="处理失败", 
                    end_time=datetime.now().isoformat(),
                    error="处理过程中出现错误"
                )
                self.logger.error("处理过程中出现错误")
                self._flush_log()
                return False
        except Exception as e:
            error_info = traceback.format_exc()
            self.logger.error(f"处理过程中出现异常: {e}\n{error_info}")
            self._flush_log()
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
            self._flush_log()
            if self.input_file.endswith(('.xlsx', '.xls')):
                self.logger.info("检测到Excel文件格式")
                self._flush_log()
                restaurant_data = pd.read_excel(self.input_file)
            elif self.input_file.endswith('.csv'):
                self.logger.info("检测到CSV文件格式")
                self._flush_log()
                restaurant_data = pd.read_csv(self.input_file)
            else:
                self.logger.error(f"不支持的文件类型: {self.input_file}")
                self._flush_log()
                return None
            
            self.logger.info(f"成功加载数据，共 {len(restaurant_data)} 条记录")
            self.logger.debug(f"数据列: {list(restaurant_data.columns)}")
            self._flush_log()
            return restaurant_data
        except Exception as e:
            self.logger.error(f"加载数据失败: {e}")
            self.logger.exception("详细错误信息:")
            self._flush_log()
            return None
    
    def _process_data(self, restaurant_data, logger):
        """处理数据"""
        try:
            total_restaurants = len(restaurant_data)
            batch_size = self.batch_size
            num_workers = self.num_workers
            
            # 计算总批次数
            total_batches = (total_restaurants + batch_size - 1) // batch_size
            self._log_progress(f"共 {total_restaurants} 条数据，分为 {total_batches} 批处理")
            self.logger.info(f"处理配置: 批次大小={batch_size}, 工作线程数={num_workers}")
            self._flush_log()
            
            # 批次索引列表
            batch_indices = list(range(0, total_restaurants, batch_size))
            
            # 所有处理后的记录
            all_processed_records = []
            completed_count = 0
            
            # 创建服务实例
            self.logger.info("创建GetRestaurantService服务实例")
            self._flush_log()
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
                self._flush_log()
                
                try:
                    # 提取批次数据
                    self.logger.debug(f"提取批次数据 {start_idx+1}-{end_idx}")
                    self._flush_log()
                    batch_data = restaurant_data.iloc[start_idx:end_idx].copy()
                    
                    # 获取批次专用日志
                    batch_id = f"{batch_idx+1}"
                    batch_logger = get_batch_logger(batch_id, self.task_dir)
                    batch_logger.info(f"开始处理批次 {batch_idx+1}/{total_batches} ({start_idx+1}-{end_idx})")
                    
                    # 转换为记录
                    batch_records = batch_data.to_dict('records')
                    batch_logger.debug(f"批次数据转换为记录，数量: {len(batch_records)}")
                    
                    # 创建餐厅实例
                    restaurant_instances = []
                    success_count = 0
                    batch_logger.info(f"开始创建餐厅实例...")
                    
                    for idx, restaurant_info in enumerate(batch_records):
                        try:
                            restaurant = Restaurant(restaurant_info, cp_location=self.cp_location, logger=batch_logger)
                            restaurant_instances.append(restaurant)
                            success_count += 1
                            # 每创建5个实例更新一次进度
                            # if idx % 5 == 4 or idx == len(batch_records) - 1:
                            #     batch_logger.debug(f"已创建 {idx+1}/{len(batch_records)} 个餐厅实例")
                        except Exception as e:
                            batch_logger.error(f"创建餐厅实例 {idx} 失败: {e}")
                            continue
                    
                    batch_logger.info(f"成功创建 {success_count}/{len(batch_records)} 个餐厅实例")
                    
                    # 释放批次数据
                    batch_data = None
                    batch_records = None
                    gc.collect()
                    
                    # 创建餐厅组并生成信息
                    if restaurant_instances:
                        # 创建餐厅组
                        batch_logger.info(f"创建餐厅组，成员数: {len(restaurant_instances)}")
                        restaurant_group = RestaurantsGroup(restaurant_instances)
                        restaurant_instances = None
                        
                        # 使用GetRestaurantService补全信息
                        try:
                            batch_logger.info(f"开始补全餐厅信息，使用 {num_workers} 个工作线程")
                            
                            # 调用服务补全信息
                            batch_logger.info(f"开始生成餐厅信息，总计 {len(restaurant_group.members)} 个餐厅")
                            
                            # 调用服务补全信息，使用batch_logger
                            processed_group = service.gen_info_v2(
                                restaurant_group, 
                                num_workers=num_workers,  # PROD
                                # num_workers=1,  # DEBUG
                                logger_file=os.path.join(self.task_dir, f"batch_{batch_id}.log")  # 传递批处理日志文件路径
                            )
                            
                            batch_logger.info(f"补全信息完成")
                        except Exception as e:
                            batch_logger.error(f"补全信息失败: {e}")
                            batch_logger.exception("详细错误信息:")
                            processed_group = restaurant_group
                        
                        restaurant_group = None
                        
                        # 提取结果
                        batch_processed_records = []
                        batch_completed = 0
                        batch_logger.info(f"开始提取处理结果...")
                        
                        for idx, restaurant in enumerate(processed_group.members):
                            if hasattr(restaurant, 'inst') and restaurant.inst:
                                try:
                                    restaurant_dict = restaurant.to_dict()
                                    batch_processed_records.append(restaurant_dict)
                                    batch_completed += 1
                                    
                                    # 每处理5个餐厅记录一次日志
                                    if idx % 5 == 4 or idx == len(processed_group.members) - 1:
                                        batch_logger.debug(f"已提取 {idx+1}/{len(processed_group.members)} 个餐厅数据")
                                except Exception as e:
                                    batch_logger.error(f"提取餐厅数据失败: {e}")
                        
                        # 更新计数
                        completed_count += batch_completed
                        batch_logger.info(f"本批次成功处理 {batch_completed} 条记录")
                        
                        # 添加到总结果
                        all_processed_records.extend(batch_processed_records)
                        
                        # 写入批次完成标记文件
                        completion_file = write_batch_completion_file(batch_id, self.task_dir)
                        batch_logger.info(f"已创建批次完成标记文件: {completion_file}")
                        
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
                        batch_logger.info(f"保存中间结果...")
                        
                        if all_processed_records:
                            try:
                                interim_df = pd.DataFrame(all_processed_records)
                                # 将结果保存到两个位置
                                self._save_to_both_locations(interim_df, "保存中间结果")
                                interim_df = None
                            except Exception as e:
                                batch_logger.error(f"保存中间结果失败: {e}")
                                batch_logger.exception("详细错误信息:")
                        
                        # 更新状态
                        completed_batches = count_completed_batches(self.task_dir)
                        progress_percentage = int((completed_batches / total_batches) * 100)
                        
                        self._update_status(
                            completed=completed_count,
                            progress=progress_percentage,
                            message=f"已完成 {completed_batches}/{total_batches} 批次，共 {completed_count}/{total_restaurants} 条记录"
                        )
                        
                        # 主动调用垃圾回收
                        gc.collect()
                    
                    # 计算批次处理时间
                    batch_time = time.time() - batch_start_time
                    batch_logger.info(f"批次 {batch_idx+1} 处理完成，耗时: {batch_time:.2f}秒")
                    
                    # 计算平均每条记录处理时间
                    avg_time_per_record = batch_time / (end_idx - start_idx) if end_idx > start_idx else 0
                    batch_logger.info(f"平均每条记录处理时间: {avg_time_per_record:.2f}秒")
                    
                    # 预估剩余时间
                    if batch_idx < total_batches - 1:
                        remaining_records = total_restaurants - end_idx
                        estimated_time = remaining_records * avg_time_per_record
                        batch_logger.info(f"预估剩余时间: {estimated_time:.2f}秒 (约 {estimated_time/60:.2f}分钟)")
                        
                        # 更新状态文件添加剩余时间估计
                        self._update_status(
                            estimated_remaining_time=f"{estimated_time/60:.2f}分钟"
                        )
                    
                    # 处理完一批次后暂停一下，让系统喘息
                    if batch_idx % 3 == 2:
                        batch_logger.info("批次间暂停0.5秒...")
                        time.sleep(0.5)
                        
                except Exception as e:
                    self.logger.error(f"处理批次 {batch_idx+1} 失败: {e}")
                    self.logger.exception("详细错误信息:")
                    self._flush_log()
            
            # 计算总处理时间
            total_process_time = time.time() - process_start_time
            self.logger.info(f"所有批次处理完成，总耗时: {total_process_time:.2f}秒 (约 {total_process_time/60:.2f}分钟)")
            self._flush_log()
            
            # 所有批次处理完毕，创建最终结果
            if all_processed_records:
                try:
                    # 创建最终DataFrame
                    self.logger.info(f"创建最终结果DataFrame，共 {len(all_processed_records)} 条记录")
                    self._flush_log()
                    result_df = pd.DataFrame(all_processed_records)
                    
                    # 保存最终结果到两个位置
                    success = self._save_to_both_locations(result_df, "保存最终结果")
                    
                    # 更新状态
                    self._update_status(
                        completed=completed_count,
                        progress=100,
                        message=f"处理完成，共补全 {completed_count}/{total_restaurants} 条记录",
                        result_file=self.result_file,  # 确保使用主目录中的结果文件路径
                        total_process_time=f"{total_process_time/60:.2f}分钟"
                    )
                    
                    self.logger.info(f"处理成功完成，共补全 {completed_count}/{total_restaurants} 条记录")
                    self.logger.info(f"结果文件保存在两个位置:")
                    self.logger.info(f"1. 工作目录: {self.task_result_file}")
                    self.logger.info(f"2. 主目录: {self.result_file} (UI将使用此路径)")
                    self._flush_log()
                    return success
                except Exception as e:
                    self.logger.error(f"创建最终结果失败: {e}")
                    self.logger.exception("详细错误信息:")
                    self._flush_log()
                    return False
            else:
                self.logger.error("没有成功处理任何餐厅记录")
                self._flush_log()
                return False
                
        except Exception as e:
            self.logger.error(f"处理数据失败: {e}")
            self.logger.exception("详细错误信息:")
            self._flush_log()
            self._update_status(
                status="failed", 
                message=f"处理出错: {str(e)}", 
                end_time=datetime.now().isoformat(),
                error=str(e)
            )
            return False

    def check_complete_status(self):
        """检查补全任务状态"""
        try:
            # 如果取消标志被设置，停止轮询
            if hasattr(self, 'cancel_complete_task') and self.cancel_complete_task:
                if hasattr(self, 'monitor_timer'):
                    self.monitor_timer.stop()
                
                # 终止进程
                if hasattr(self, 'complete_process') and self.complete_process:
                    try:
                        self.complete_process.terminate()
                    except:
                        pass
                
                self.complete_task_running = False
                self.complete_info_button.setText("补全餐厅信息")
                if hasattr(self, 'progress_label'):
                    self.progress_label.setText("操作已取消")
                    self.progress_label.setVisible(False)
                
                self.logger.info("补全任务已取消")
                return
            
            # 检查进程是否仍在运行
            if hasattr(self, 'complete_process') and self.complete_process:
                returncode = self.complete_process.poll()
                
                # 检查状态文件和心跳文件
                output_dir = tempfile.gettempdir()
                if hasattr(self, 'current_task') and self.current_task:
                    task_dir = os.path.join(output_dir, self.current_task.get('task_id', ''))
                    if os.path.exists(task_dir):
                        output_dir = task_dir
                
                # 检查心跳文件
                log_file = self.current_task.get('log_file', '') if hasattr(self, 'current_task') and self.current_task else None
                if log_file:
                    heartbeat_file = log_file.replace('.txt', '_heartbeat.txt')
                    status_file = log_file.replace('.txt', '_status.json')
                    
                    # 检查心跳文件是否存在且最近更新
                    if os.path.exists(heartbeat_file):
                        try:
                            with open(heartbeat_file, 'r') as f:
                                heartbeat_time = float(f.read().strip())
                                current_time = time.time()
                                if current_time - heartbeat_time > 30:  # 30秒无更新认为进程卡住
                                    self.logger.warning(f"心跳文件 {heartbeat_file} 超过30秒未更新，进程可能卡住")
                                    # 但不立即终止，继续检查其他状态
                        except Exception as e:
                            self.logger.error(f"读取心跳文件失败: {e}")
                    
                    # 检查状态文件
                    if os.path.exists(status_file):
                        try:
                            with open(status_file, 'r', encoding='utf-8') as f:
                                status_data = json.load(f)
                                
                                # 更新进度信息
                                progress = status_data.get('progress', 0)
                                processed = status_data.get('processed', 0)
                                total = status_data.get('total', 0)
                                success = status_data.get('success', 0)
                                failed = status_data.get('failed', 0)
                                message = status_data.get('message', '')
                                
                                # 显示进度
                                if total > 0:
                                    self.update_progress(f"{message} - 进度: {processed}/{total} ({progress:.1f}%), 成功: {success}, 失败: {failed}")
                                else:
                                    self.update_progress(message)
                                
                                # 检查是否完成
                                if status_data.get('status') == 'completed' or (processed == total and total > 0):
                                    # 任务已完成
                                    result_file = os.path.join(output_dir, f"result_{self.current_task.get('task_id')}.xlsx")
                                    if os.path.exists(result_file):
                                        status_data['result_file'] = result_file
                                        self.on_complete_process_finished(status_data)
                                        return
                                
                                # 检查进程是否还活跃
                                last_update = status_data.get('last_update', 0)
                                current_time = time.time()
                                if current_time - last_update > 60:  # 1分钟无更新认为进程卡住
                                    self.logger.warning(f"状态文件 {status_file} 超过1分钟未更新，进程可能卡住")
                                    # 在这里可以考虑是否要终止进程
                        except Exception as e:
                            self.logger.error(f"读取状态文件失败: {e}")
                
                if hasattr(self, 'complete_start_time'):
                    # 检查是否超时
                    elapsed_time = time.time() - self.complete_start_time
                    if elapsed_time > self.complete_timeout:
                        self.logger.warning("补全任务超时")
                        self.monitor_timer.stop()
                        self.complete_process.terminate()
                        self.complete_task_running = False
                        self.complete_info_button.setText("补全餐厅信息")
                        if hasattr(self, 'progress_label'):
                            self.progress_label.setText("操作已超时")
                            self.progress_label.setVisible(False)
                        QMessageBox.warning(self, "任务超时", "补全餐厅信息任务运行时间过长，已自动终止")
                        return
                
                # 查找标准状态文件，这是原有逻辑的后备
                status_files = [f for f in os.listdir(output_dir) if f.startswith("status_") and f.endswith(".json")]
                
                if status_files:
                    # 找到最新的状态文件
                    status_file = os.path.join(output_dir, sorted(status_files)[-1])
                    
                    try:
                        with open(status_file, 'r', encoding='utf-8') as f:
                            status_data = json.load(f)
                            
                            # 更新进度
                            if 'message' in status_data:
                                self.update_progress(status_data['message'])
                            
                            # 检查任务是否完成
                            if 'status' in status_data:
                                if status_data['status'] == 'completed':
                                    # 任务成功完成
                                    self.on_complete_process_finished(status_data)
                                    return
                                elif status_data['status'] == 'failed':
                                    # 任务失败
                                    error_msg = status_data.get('error', '未知错误')
                                    self.on_complete_process_error(error_msg)
                                    return
                    except Exception as e:
                        self.logger.error(f"读取状态文件失败: {e}")
                
                # 如果进程已结束但未找到状态文件或状态不是成功/失败
                if returncode is not None:
                    if returncode == 0:
                        # 进程正常结束，但可能没有状态文件
                        # 尝试查找结果文件
                        result_files = [f for f in os.listdir(output_dir) if f.startswith("result_") and f.endswith(".xlsx")]
                        if result_files:
                            result_file = os.path.join(output_dir, sorted(result_files)[-1])
                            status_data = {
                                "status": "completed",
                                "result_file": result_file,
                                "message": "处理完成",
                                "progress": 100
                            }
                            self.on_complete_process_finished(status_data)
                        else:
                            # 没有找到结果文件，认为失败
                            self.on_complete_process_error("处理完成，但未找到结果文件")
                    else:
                        # 进程异常结束
                        stderr_output = self.complete_process.stderr.read().decode('utf-8', errors='ignore') if self.complete_process.stderr else "未知错误"
                        self.on_complete_process_error(f"进程异常结束，返回码: {returncode}\n{stderr_output[:500]}")
                    
                    # 停止计时器
                    self.monitor_timer.stop()
                    return
            else:
                # 没有进程对象，停止计时器
                self.monitor_timer.stop()
                self.complete_task_running = False
                self.complete_info_button.setText("补全餐厅信息")
                if hasattr(self, 'progress_label'):
                    self.progress_label.setVisible(False)
                
        except Exception as e:
            self.logger.error(f"检查补全任务状态时出错: {str(e)}")
            # 出错时停止计时器
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()
            
            self.complete_task_running = False
            self.complete_info_button.setText("补全餐厅信息")
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)

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
    parser.add_argument('--config_file', help='运行时配置文件路径，JSON格式')
    return parser.parse_args()

def main():
    """主函数"""
    # 解析命令行参数
    args = parse_args()
    
    # 如果提供了配置文件，加载运行时配置
    if args.config_file:
        try:
            from app.config.config import CONF
            
            # 加载配置文件
            with open(args.config_file, 'r', encoding='utf-8') as f:
                runtime_config = json.load(f)
            
            # 将配置应用到CONF.runtime
            for key, value in runtime_config.items():
                # 确保runtime属性存在
                if not hasattr(CONF, 'runtime'):
                    setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                
                # 设置属性
                setattr(CONF.runtime, key, value)
            
            # print(f"已加载运行时配置")
        except Exception as e:
            pass
    
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
