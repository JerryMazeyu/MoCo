import datetime
import random
import uuid
from typing import Dict, Any, List, Optional, Union
from app.services.instances.base import BaseInstance, BaseGroup
from app.utils.hash import hash_text
from app.utils.logger import setup_logger
from app.utils.file_io import rp
import numpy as np

# 设置日志
LOGGER = setup_logger("moco.log")

class ReceiveRecord(BaseInstance):
    """
    收油记录实体类，处理从餐厅到CP的收油记录
    """
    def __init__(self, info: Dict[str, Any], model=None, conf=None):
        """
        初始化收油记录实体
        
        :param info: 收油记录信息字典
        :param model: 收油记录模型类，可选
        :param conf: 配置服务，可选
        """
        super().__init__(model)
        self.conf = conf
        
        # 基本校验，确保必要字段存在
        if model:
            # 创建模型实例
            self.inst = model(**info)
        else:
            # 如果没有提供模型类，直接存储info
            self.inst = type('DynamicModel', (), info)
        
        self.status = 'pending'  # 初始状态为待处理
    
    def _generate_id(self) -> bool:
        """
        生成记录ID
        
        :return: 是否生成成功
        """
        try:
            if not hasattr(self.inst, 'rr_id') or not self.inst.rr_id:
                # 生成唯一ID
                # 使用UUID作为基础，保证唯一性
                uid = str(uuid.uuid4())
                
                # 如果有日期信息，添加到ID前缀
                date_prefix = ""
                if hasattr(self.inst, 'rr_date') and self.inst.rr_date:
                    try:
                        date_obj = datetime.datetime.strptime(self.inst.rr_date, '%Y-%m-%d')
                        date_prefix = date_obj.strftime('%Y%m%d')
                    except:
                        # 如果日期格式不正确，使用今天的日期
                        date_prefix = datetime.datetime.now().strftime('%Y%m%d')
                else:
                    # 如果没有日期信息，使用今天的日期
                    date_prefix = datetime.datetime.now().strftime('%Y%m%d')
                
                # 生成合约编号，格式为：日期-CP编号-随机数
                cp_code = ""
                if hasattr(self.inst, 'rr_cp') and self.inst.rr_cp:
                    cp_code = self.inst.rr_cp
                else:
                    cp_code = "CP000"
                
                # 生成唯一的合约编号
                self.inst.rr_id = f"RR-{date_prefix}-{cp_code}-{uid[:8].upper()}"
                # LOGGER.info(f"已生成收油记录ID: {self.inst.rr_id}")
            
            return True
        except Exception as e:
            LOGGER.error(f"生成收油记录ID失败: {e}")
            return False
    
    def _set_defaults(self) -> bool:
        """
        设置默认值
        
        :return: 是否设置成功
        """
        ## 读取配置文件收油关系映射
        # 根据餐厅类型分配收油量
        def oil_determine_collection_amount(restaurant_type: str, oil_mapping: dict) -> int:
            
            # 如果餐厅类型为空，则使用默认值
            if not restaurant_type:
                return np.random.choice([1, 2])
            # 遍历映射关系，找到对应的收油量
            for key, value in oil_mapping.items():
                if restaurant_type == key or any(type_keyword in restaurant_type for type_keyword in key.split('/')):
                    if isinstance(value, list):
                        return np.random.choice(value)
                    else:
                        return value
            return np.random.choice([1, 2])  # 默认值
            
            # Jerry Modified
            # for key, value in oil_mapping.items():
            #     if ',' in str(value):
            #         try:
            #             allocate_value =  [int(item.strip()) for item in str(value).split(',')]
            #         except:
            #             allocate_value = [int(item.strip()) for item in value]
            #     else:
            #         allocate_value = [int(value)]
            #     if any(type_keyword in restaurant_type for type_keyword in key.split('/')):
            #         return np.random.choice(allocate_value)
            # return np.random.choice([1, 2])  # 默认值
        try:
            # 1、设置数据生成日期
            if not hasattr(self.inst, 'rr_create_date') or not self.inst.rr_date:
                self.inst.rr_date = datetime.datetime.now().strftime('%Y-%m-%d')
                # LOGGER.info(f"已设置默认收油数据生成日期: {self.inst.rr_date}")
            
            # 如果没有收油量，生成一个合理的默认值
            # 获取收油关系表映射
            self.oil_mapping = self.conf.get("BUSINESS.RESTAURANT.收油关系映射", default={})

            # 2、设置默认收油桶数
            if not hasattr(self.inst, 'rr_amount') or not self.inst.rr_amount:
                # 根据所属餐厅类型生成收油量，先按照180KG却ing桶数，最后生成完了再分配180KG和55KG的桶
                self.inst.rr_amount = oil_determine_collection_amount(self.inst.rest_type, self.oil_mapping)
                # LOGGER.info(f"已生成默认收油桶数: {self.inst.rr_amount}桶")
            
            
            return True
        except Exception as e:
            LOGGER.error(f"设置收油记录默认值失败: {e}")
            return False
    
    def generate(self) -> bool:
        """
        生成收油记录的所有缺失字段
        
        :return: 是否全部生成成功
        """
        success = True
        
        # 生成ID
        success &= self._generate_id()
        
        # 设置默认值
        success &= self._set_defaults()
        
        # 如果全部成功，更新状态为就绪
        if success:
            self.status = 'ready'
            # LOGGER.info(f"收油记录 '{self.inst.rr_id}' 的所有字段已生成完成")
        
        return success
    
    def __str__(self) -> str:
        """
        返回收油记录的字符串表示
        
        :return: 字符串表示
        """
        if hasattr(self.inst, 'rr_id'):
            restaurant_info = ""
            if hasattr(self.inst, 'rr_restaurant'):
                if hasattr(self.inst.rr_restaurant, 'rest_chinese_name'):
                    restaurant_info = f", 餐厅={self.inst.rr_restaurant.rest_chinese_name}"
                elif hasattr(self.inst.rr_restaurant, 'rest_id'):
                    restaurant_info = f", 餐厅ID={self.inst.rr_restaurant.rest_id}"
            
            return f"ReceiveRecord(id={self.inst.rr_id}, 日期={getattr(self.inst, 'rr_date', 'unknown')}, 数量={getattr(self.inst, 'rr_amount', 'unknown')}{restaurant_info})"
        return f"ReceiveRecord(未完成初始化, status={self.status})"


class ReceiveRecordsGroup(BaseGroup):
    """
    收油记录组合类，用于管理多个收油记录实体
    """
    def __init__(self, records: List[ReceiveRecord] = None, group_type: str = None, group_date: str = None):
        """
        初始化收油记录组合
        
        :param records: 收油记录列表
        :param group_type: 组合类型，如'daily'、'cp'等
        :param group_date: 组合日期，格式为'YYYY-MM-DD'
        """
        super().__init__(records, group_type)
        self.group_date = group_date
    
    def filter_by_date(self, date: str) -> 'ReceiveRecordsGroup':
        """
        按日期筛选收油记录
        
        :param date: 日期字符串，格式为'YYYY-MM-DD'
        :return: 筛选后的收油记录组合
        """
        filtered = self.filter(lambda r: hasattr(r.inst, 'rr_date') and r.inst.rr_date == date)
        filtered.group_date = date
        return filtered
    
    def filter_by_cp(self, cp_id: str) -> 'ReceiveRecordsGroup':
        """
        按CP筛选收油记录
        
        :param cp_id: CP ID
        :return: 筛选后的收油记录组合
        """
        return self.filter(lambda r: hasattr(r.inst, 'rr_cp') and r.inst.rr_cp == cp_id)
    
    def filter_by_restaurant(self, rest_id: str) -> 'ReceiveRecordsGroup':
        """
        按餐厅筛选收油记录
        
        :param rest_id: 餐厅ID
        :return: 筛选后的收油记录组合
        """
        return self.filter(lambda r: hasattr(r.inst, 'rr_restaurant') and 
                          ((hasattr(r.inst.rr_restaurant, 'rest_id') and r.inst.rr_restaurant.rest_id == rest_id) or
                           (hasattr(r.inst.rr_restaurant, 'id') and r.inst.rr_restaurant.id == rest_id)))
    
    def get_by_id(self, record_id: str) -> Optional[ReceiveRecord]:
        """
        按ID获取收油记录
        
        :param record_id: 收油记录ID
        :return: 收油记录实体或None
        """
        for record in self.members:
            if hasattr(record.inst, 'rr_id') and record.inst.rr_id == record_id:
                return record
        return None
    
    def get_total_amount(self) -> float:
        """
        获取总收油量
        
        :return: 总收油量（吨）
        """
        total = 0.0
        for record in self.members:
            if hasattr(record.inst, 'rr_amount'):
                total += float(record.inst.rr_amount)
        return total
    
    def get_daily_summary(self) -> Dict[str, float]:
        """
        获取按日期汇总的收油量
        
        :return: 日期到总量的映射字典
        """
        summary = {}
        for record in self.members:
            if hasattr(record.inst, 'rr_date') and hasattr(record.inst, 'rr_amount'):
                date = record.inst.rr_date
                amount = float(record.inst.rr_amount)
                if date in summary:
                    summary[date] += amount
                else:
                    summary[date] = amount
        return summary
    
    def __str__(self) -> str:
        """
        返回收油记录组合的字符串表示
        
        :return: 字符串表示
        """
        date_info = f", 日期={self.group_date}" if self.group_date else ""
        return f"ReceiveRecordsGroup(数量={self.count()}, 类型={self.group_type}{date_info}, 总量={self.get_total_amount()}吨)"




class ReceiveRecordsBalance(BaseGroup):
    """
    收油记录平衡表，用于管理多个日期的收油记录组合
    """
    def __init__(self, record_groups: List[ReceiveRecordsGroup] = None, period: str = None):
        """
        初始化收油记录平衡表
        
        :param record_groups: 收油记录组合列表
        :param period: 周期描述，如'monthly-2023-01'
        """
        super().__init__(record_groups, "balance")
        self.period = period
        self.daily_groups = {}  # 日期到组合的映射
        
        # 初始化日期映射
        if record_groups:
            for group in record_groups:
                if group.group_date:
                    self.daily_groups[group.group_date] = group
    
    def add_daily_group(self, group: ReceiveRecordsGroup) -> None:
        """
        添加日收油记录组合
        
        :param group: 收油记录组合
        """
        super().add(group)
        if group.group_date:
            self.daily_groups[group.group_date] = group
    
    def get_by_date(self, date: str) -> Optional[ReceiveRecordsGroup]:
        """
        按日期获取收油记录组合
        
        :param date: 日期字符串，格式为'YYYY-MM-DD'
        :return: 收油记录组合或None
        """
        return self.daily_groups.get(date)
    
    def get_date_range(self) -> List[str]:
        """
        获取覆盖的日期范围
        
        :return: 日期列表，格式为'YYYY-MM-DD'
        """
        return sorted(self.daily_groups.keys())
    
    def get_total_amount(self) -> float:
        """
        获取总收油量
        
        :return: 总收油量（吨）
        """
        total = 0.0
        for group in self.members:
            total += group.get_total_amount()
        return total
    
    def generate_monthly_report(self) -> Dict[str, Any]:
        """
        生成月度报表
        
        :return: 报表数据字典
        """
        report = {
            'period': self.period,
            'total_amount': self.get_total_amount(),
            'daily_amounts': {},
            'restaurant_amounts': {},
            'vehicle_usage': {}
        }
        
        # 收集日收油量
        for date, group in self.daily_groups.items():
            report['daily_amounts'][date] = group.get_total_amount()
        
        # 收集餐厅收油量（示例，实际实现可能需要更多处理）
        restaurant_amounts = {}
        for group in self.members:
            for record in group.members:
                if hasattr(record.inst, 'rr_restaurant') and hasattr(record.inst, 'rr_amount'):
                    rest_id = getattr(record.inst.rr_restaurant, 'rest_id', None) or getattr(record.inst.rr_restaurant, 'id', None)
                    if rest_id:
                        rest_name = getattr(record.inst.rr_restaurant, 'rest_chinese_name', rest_id)
                        amount = float(record.inst.rr_amount)
                        if rest_id in restaurant_amounts:
                            restaurant_amounts[rest_id]['amount'] += amount
                            restaurant_amounts[rest_id]['count'] += 1
                        else:
                            restaurant_amounts[rest_id] = {
                                'name': rest_name,
                                'amount': amount,
                                'count': 1
                            }
        
        report['restaurant_amounts'] = restaurant_amounts
        
        # 收集车辆使用情况（示例，实际实现可能需要更多处理）
        vehicle_usage = {}
        for group in self.members:
            for record in group.members:
                if hasattr(record.inst, 'rr_vehicle') and hasattr(record.inst, 'rr_amount'):
                    vehicle_id = getattr(record.inst.rr_vehicle, 'vehicle_id', None) or getattr(record.inst.rr_vehicle, 'id', None)
                    if vehicle_id:
                        vehicle_plate = getattr(record.inst.rr_vehicle, 'vehicle_license_plate', vehicle_id)
                        amount = float(record.inst.rr_amount)
                        if vehicle_id in vehicle_usage:
                            vehicle_usage[vehicle_id]['amount'] += amount
                            vehicle_usage[vehicle_id]['usage_days'].add(record.inst.rr_date)
                        else:
                            vehicle_usage[vehicle_id] = {
                                'plate': vehicle_plate,
                                'amount': amount,
                                'usage_days': {record.inst.rr_date}
                            }
        
        # 将集合转换为列表
        for v_id, data in vehicle_usage.items():
            data['usage_days'] = list(data['usage_days'])
            data['usage_count'] = len(data['usage_days'])
        
        report['vehicle_usage'] = vehicle_usage
        
        return report
    
    def save_report(self, file_path: str = None) -> bool:
        """
        保存月度报表
        
        :param file_path: 文件路径，如果为None则使用默认路径
        :return: 是否保存成功
        """
        try:
            if not file_path:
                period_str = self.period or datetime.datetime.now().strftime('%Y-%m')
                file_path = rp(f"receive_report_{period_str}.xlsx", folder="assets")
            
            # 生成报表数据
            report = self.generate_monthly_report()
            
            # 创建Excel工作簿
            import pandas as pd
            
            # 创建一个ExcelWriter对象
            with pd.ExcelWriter(file_path) as writer:
                # 汇总表
                summary_data = {
                    '周期': [report['period']],
                    '总收油量(吨)': [report['total_amount']],
                    '日期范围': [', '.join(self.get_date_range())],
                    '记录数量': [self.count()]
                }
                pd.DataFrame(summary_data).to_excel(writer, sheet_name='汇总', index=False)
                
                # 日收油量表
                daily_data = {
                    '日期': list(report['daily_amounts'].keys()),
                    '收油量(吨)': list(report['daily_amounts'].values())
                }
                pd.DataFrame(daily_data).to_excel(writer, sheet_name='日收油量', index=False)
                
                # 餐厅收油量表
                restaurant_data = []
                for rest_id, data in report['restaurant_amounts'].items():
                    restaurant_data.append({
                        '餐厅ID': rest_id,
                        '餐厅名称': data['name'],
                        '收油量(吨)': data['amount'],
                        '收油次数': data['count'],
                        '平均每次(吨)': data['amount'] / data['count']
                    })
                pd.DataFrame(restaurant_data).to_excel(writer, sheet_name='餐厅收油量', index=False)
                
                # 车辆使用情况表
                vehicle_data = []
                for v_id, data in report['vehicle_usage'].items():
                    vehicle_data.append({
                        '车辆ID': v_id,
                        '车牌号': data['plate'],
                        '收油量(吨)': data['amount'],
                        '使用天数': data['usage_count'],
                        '使用日期': ', '.join(data['usage_days'])
                    })
                pd.DataFrame(vehicle_data).to_excel(writer, sheet_name='车辆使用情况', index=False)
            
            LOGGER.info(f"已保存收油记录报表: {file_path}")
            return True
        except Exception as e:
            LOGGER.error(f"保存收油记录报表失败: {e}")
            return False
    
    def __str__(self) -> str:
        """
        返回收油记录平衡表的字符串表示
        
        :return: 字符串表示
        """
        period_info = f", 周期={self.period}" if self.period else ""
        return f"ReceiveRecordsBalance(日期数={len(self.daily_groups)}, 总量={self.get_total_amount()}吨{period_info})"


class BalanceRecords(BaseInstance):
    """
    平衡记录实体类，处理餐厅的平衡记录
    """
    def __init__(self, info: Dict[str, Any], model=None, conf=None):
        """
        初始化平衡记录实体
        
        :param info: 平衡记录信息字典
        :param model: 平衡记录模型类，可选
        :param conf: 配置服务，可选
        """
        super().__init__(model)
        self.conf = conf
        
        # 基本校验，确保必要字段存在
        if model:
            # 创建模型实例
            self.inst = model(**info)
        else:
            # 如果没有提供模型类，直接存储info
            self.inst = type('DynamicModel', (), info)
        
        self.status = 'pending'  # 初始状态为待处理

    def generate(self) -> bool:
        """
        生成平衡记录的所有缺失字段
        
        :return: 是否全部生成成功
        """
        # 这里可以添加生成逻辑
        self.status = 'ready'
        return True

    def __str__(self) -> str:
        """
        返回平衡记录的字符串表示
        
        :return: 字符串表示
        """
        return f"BalanceRecords(id={getattr(self.inst, 'balance_id', 'unknown')}, 日期={getattr(self.inst, 'balance_date', 'unknown')})"


class BalanceRecordsGroup(BaseGroup):
    """
    平衡记录组合类，用于管理多个平衡记录实体
    """
    def __init__(self, records: List[BalanceRecords] = None, group_type: str = None, group_date: str = None):
        """
        初始化平衡记录组合
        
        :param records: 平衡记录列表
        :param group_type: 组合类型，如'daily'、'monthly'等
        :param group_date: 组合日期，格式为'YYYY-MM-DD'
        """
        super().__init__(records, group_type)
        self.group_date = group_date

    def filter_by_date(self, date: str) -> 'BalanceRecordsGroup':
        """
        按日期筛选平衡记录
        
        :param date: 日期字符串，格式为'YYYY-MM-DD'
        :return: 筛选后的平衡记录组合
        """
        filtered = self.filter(lambda r: hasattr(r.inst, 'balance_date') and r.inst.balance_date == date)
        filtered.group_date = date
        return filtered

    def get_total_amount(self) -> float:
        """
        获取总平衡量
        
        :return: 总平衡量
        """
        total = 0.0
        for record in self.members:
            if hasattr(record.inst, 'balance_amount'):
                total += float(record.inst.balance_amount)
        return total

    def __str__(self) -> str:
        """
        返回平衡记录组合的字符串表示
        
        :return: 字符串表示
        """
        date_info = f", 日期={self.group_date}" if self.group_date else ""
        return f"BalanceRecordsGroup(数量={self.count()}, 类型={self.group_type}{date_info}, 总量={self.get_total_amount()})"

class BalanceTotal(BaseInstance):
    """
    总表实体类，处理餐厅的总表记录
    """
    def __init__(self, info: Dict[str, Any], model=None, conf=None):
        """
        初始化总表实体
        
        :param info: 总表信息字典
        :param model: 总表模型类，可选
        :param conf: 配置服务，可选
        """
        super().__init__(model)
        self.conf = conf
        
        # 基本校验，确保必要字段存在
        if model:
            # 创建模型实例
            self.inst = model(**info)
        else:
            # 如果没有提供模型类，直接存储info
            self.inst = type('DynamicModel', (), info)
        
        self.status = 'pending'  # 初始状态为待处理

    def generate(self) -> bool:
        """
        生成总表记录的所有缺失字段
        
        :return: 是否全部生成成功
        """
        # 这里可以添加生成逻辑
        self.status = 'ready'
        return True

    def __str__(self) -> str:
        """
        返回总表记录的字符串表示
        
        :return: 字符串表示
        """
        return f"RestaurantTotal(CP={getattr(self.inst, 'total_cp', 'unknown')}, 日期={getattr(self.inst, 'total_supplied_date', 'unknown')}, 产出={getattr(self.inst, 'total_output_quantity', 'unknown')}, 售出={getattr(self.inst, 'total_quantities_sold', 'unknown')}, 库存={getattr(self.inst, 'total_ending_inventory', 'unknown')})"


class BalanceTotalGroup(BaseGroup):
    """
    总表组合类，用于管理多个总表记录实体
    """
    def __init__(self, instances: List[BalanceTotal] = None, group_type: str = None, group_date: str = None):
        """
        初始化总表组合
        
        :param instances: 总表记录列表
        :param group_type: 组合类型，如'daily'、'monthly'等
        :param group_date: 组合日期，格式为'YYYY-MM-DD'
        """
        super().__init__(instances=instances, group_type=group_type)
        self.group_date = group_date

    def filter_by_date(self, date: str) -> 'BalanceTotalGroup':
        """
        按日期筛选总表记录
        
        :param date: 日期字符串，格式为'YYYY-MM-DD'
        :return: 筛选后的总表记录组合
        """
        filtered = self.filter(lambda r: hasattr(r.inst, 'total_supplied_date') and r.inst.total_supplied_date == date)
        filtered.group_date = date
        return filtered

    def filter_by_cp(self, cp_id: str) -> 'BalanceTotalGroup':
        """
        按CP筛选总表记录
        
        :param cp_id: CP ID
        :return: 筛选后的总表记录组合
        """
        return self.filter(lambda r: hasattr(r.inst, 'total_cp') and r.inst.total_cp == cp_id)

    def get_total_output(self) -> float:
        """
        获取总产出量
        
        :return: 总产出量
        """
        total = 0.0
        for record in self.members:
            if hasattr(record.inst, 'total_output_quantity'):
                total += float(record.inst.total_output_quantity)
        return total

    def get_total_sold(self) -> float:
        """
        获取总售出量
        
        :return: 总售出量
        """
        total = 0.0
        for record in self.members:
            if hasattr(record.inst, 'total_quantities_sold'):
                total += float(record.inst.total_quantities_sold)
        return total

    def get_total_inventory(self) -> float:
        """
        获取总库存量
        
        :return: 总库存量
        """
        total = 0.0
        for record in self.members:
            if hasattr(record.inst, 'total_ending_inventory'):
                total += float(record.inst.total_ending_inventory)
        return total

    def __str__(self) -> str:
        """
        返回总表组合的字符串表示
        
        :return: 字符串表示
        """
        date_info = f", 日期={self.group_date}" if self.group_date else ""
        return f"RestaurantTotalGroup(数量={self.count()}, 类型={self.group_type}{date_info}, 总产出={self.get_total_output()}, 总售出={self.get_total_sold()}, 总库存={self.get_total_inventory()})"


class BuyerConfirmation(BaseInstance):
    """
    收货确认书实体类，处理收货确认书记录
    """
    def __init__(self, info: Dict[str, Any], model=None, conf=None):
        """
        初始化收货确认书实体
        
        :param info: 收货确认书信息字典
        :param model: 收货确认书模型类，可选
        :param conf: 配置服务，可选
        """
        super().__init__(model)
        self.conf = conf
        
        # 基本校验，确保必要字段存在
        if model:
            # 创建模型实例
            self.inst = model(**info)
        else:
            # 如果没有提供模型类，直接存储info
            self.inst = type('DynamicModel', (), info)
        
        self.status = 'pending'  # 初始状态为待处理

    def generate(self) -> bool:
        """
        生成收货确认书记录的所有缺失字段
        
        :return: 是否全部生成成功
        """
        # 这里可以添加生成逻辑
        self.status = 'ready'
        return True

    def __str__(self) -> str:
        """
        返回收货确认书记录的字符串表示
        
        :return: 字符串表示
        """
        return f"BuyerConfirmation(CP={getattr(self.inst, 'check_belong_cp', 'unknown')}, 日期={getattr(self.inst, 'check_date', 'unknown')}, 车牌={getattr(self.inst, 'check_truck_plate_no', 'unknown')}, 重量={getattr(self.inst, 'check_weight', 'unknown')})"


class BuyerConfirmationGroup(BaseGroup):
    """
    收货确认书组合类，用于管理多个收货确认书记录实体
    """
    def __init__(self, instances: List[BuyerConfirmation] = None, group_type: str = None, group_date: str = None):
        """
        初始化收货确认书组合
        
        :param records: 收货确认书记录列表
        :param group_type: 组合类型，如'daily'、'monthly'等
        :param group_date: 组合日期，格式为'YYYY-MM-DD'
        """
        super().__init__(instances=instances, group_type=group_type)
        self.group_date = group_date

    def filter_by_date(self, date: str) -> 'BuyerConfirmationGroup':
        """
        按日期筛选收货确认书记录
        
        :param date: 日期字符串，格式为'YYYY-MM-DD'
        :return: 筛选后的收货确认书记录组合
        """
        filtered = self.filter(lambda r: hasattr(r.inst, 'check_date') and r.inst.check_date == date)
        filtered.group_date = date
        return filtered

    def filter_by_cp(self, cp_id: str) -> 'BuyerConfirmationGroup':
        """
        按CP筛选收货确认书记录
        
        :param cp_id: CP ID
        :return: 筛选后的收货确认书记录组合
        """
        return self.filter(lambda r: hasattr(r.inst, 'check_belong_cp') and r.inst.check_belong_cp == cp_id)

    def get_total_weight(self) -> float:
        """
        获取总重量
        
        :return: 总重量
        """
        total = 0.0
        for record in self.members:
            if hasattr(record.inst, 'check_weight'):
                total += float(record.inst.check_weight)
        return total

    def get_vehicle_usage(self) -> Dict[str, List[str]]:
        """
        获取车辆使用情况
        
        :return: 车辆使用情况字典，key为车牌号，value为使用日期列表
        """
        vehicle_usage = {}
        for record in self.members:
            if hasattr(record.inst, 'check_truck_plate_no') and hasattr(record.inst, 'check_date'):
                plate = record.inst.check_truck_plate_no
                date = record.inst.check_date
                if plate in vehicle_usage:
                    vehicle_usage[plate].append(date)
                else:
                    vehicle_usage[plate] = [date]
        return vehicle_usage

    def __str__(self) -> str:
        """
        返回收货确认书组合的字符串表示
        
        :return: 字符串表示
        """
        date_info = f", 日期={self.group_date}" if self.group_date else ""
        return f"BuyerConfirmationGroup(数量={self.count()}, 类型={self.group_type}{date_info}, 总重量={self.get_total_weight()})"



