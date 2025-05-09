import random
import datetime
import uuid
from typing import Dict, Any, List, Optional, Union
from app.services.instances.base import BaseInstance, BaseGroup
from app.utils.hash import hash_text
from app.utils.logger import setup_logger
from app.utils.file_io import rp
import pandas as pd
from app.models import VehicleModel
# 设置日志
LOGGER = setup_logger("moco.log")

class Vehicle(BaseInstance):
    """
    车辆实体类，表示一个油品运输车辆
    """
    def __init__(
        self, 
        info: Dict[str, Any],
        model: Optional[Any] = VehicleModel,
        conf: Optional[Dict[str, Any]] = None
    ):
        """
        初始化车辆实例
        
        Args:
            info: 车辆信息字典
            model: 模型实例
            conf: 配置信息
        """
        super().__init__(model)
        
        # 必要字段检查
        assert "vehicle_license_plate" in info, "车牌号码必须存在"
        
        self.info = info

        # 设置默认值
        # if "vehicle_id" not in info:
        #     self.info["vehicle_id"] = self._generate_id()
        
        if "vehicle_belonged_cp" not in info:
            self.info["vehicle_belonged_cp"] = None
            
        if "vehicle_driver_name" not in info:
            self.info["vehicle_driver_name"] = ""
            
        if "vehicle_type" not in info:
            self.info["vehicle_type"] = "to_rest"  # 默认为收油车
            
        if "vehicle_status" not in info:
            self.info["vehicle_status"] = "available"  # 默认为可用状态
        
        if "vehicle_cooldown_days" not in info or pd.isna(self.info["vehicle_cooldown_days"]):
            self.info["vehicle_cooldown_days"] = 3
        
        self.inst = model(**info)
            
        # print(f"Initialized vehicle with info: {self.info}")
        
        # if "driver_name" not in info:
        #     self.info["driver_name"] = ""
            
        # if "driver_phone" not in info:
        #     self.info["driver_phone"] = ""
            
        # if "type" not in info:
        #     self.info["type"] = "oil_truck"  # 默认为油罐车
            
        # if "capacity" not in info:
        #     self.info["capacity"] = 0  # 默认运力为0
            
        # if "status" not in info:
        #     self.info["status"] = "active"  # 默认为激活状态
    
    def _generate_id(self) -> bool:
        """生成唯一车辆ID"""
        # 使用车牌号和司机姓名生成哈希
        plate = self.inst.vehicle_license_plate
        driver = self.inst.vehicle_driver_name if hasattr(self.inst, 'vehicle_driver_name') and self.inst.vehicle_driver_name else ""
        
        # 组合车牌号和司机姓名
        combine_str = f"{plate}_{driver}"
        
        # 使用工具函数生成哈希
        hash_value = hash_text(combine_str)
        
        # 设置车辆ID
        self.inst.vehicle_id = f"V-{hash_value[:8]}"
        
        LOGGER.info(f"已为车辆生成ID: {self.inst.vehicle_id}")
        return True
    
    # def update_driver_info(self, name: str, phone: str) -> None:
    #     """
    #     更新司机信息
        
    #     Args:
    #         name: 司机姓名
    #         phone: 司机电话
    #     """
    #     self.info["driver_name"] = name
    #     self.info["driver_phone"] = phone
        
    # def update_capacity(self, capacity: float) -> None:
    #     """
    #     更新车辆容量
        
    #     Args:
    #         capacity: 容量（单位：吨）
    #     """
    #     if capacity < 0:
    #         LOGGER.warning(f"车辆容量不能为负数: {capacity}")
    #         return
            
    #     self.info["capacity"] = capacity
    
    def _generate_weights(self) -> bool:
        """
        生成车辆的重量信息
        
        :return: 是否生成成功
        """
        try:
            # 检查车辆类型
            if not hasattr(self.inst, 'vehicle_type'):
                # 默认为收集车
                self.inst.vehicle_type = "to_rest"
                LOGGER.info(f"未指定车辆类型，设置为默认类型: {self.inst.vehicle_type}")
            
            # 生成原始皮重
            if not hasattr(self.inst, 'vehicle_tare_weight') or not self.inst.vehicle_tare_weight:
                # 根据车辆类型计算原始皮重
                if self.inst.vehicle_type == "to_rest":
                    # 收集车公式：RANDBETWEEN(43,46)*100+RANDBETWEEN(1,9)*10
                    base = random.randint(43, 46) * 100
                    offset = random.randint(1, 9) * 10
                    self.inst.vehicle_tare_weight = base + offset
                elif self.inst.vehicle_type == "to_sale":
                    # 销售车公式：RANDBETWEEN(145,159)*100+RANDBETWEEN(1,9)*10
                    base = random.randint(145, 159) * 100
                    offset = random.randint(1, 9) * 10
                    self.inst.vehicle_tare_weight = base + offset
                else:
                    # 未知类型，使用默认范围
                    self.inst.vehicle_tare_weight = random.randint(4300, 4690)
                
                LOGGER.info(f"已为车辆生成皮重: {self.inst.vehicle_tare_weight}kg")
            
            # 生成临时毛重
            if not hasattr(self.inst, 'vehicle_rough_weight') or not self.inst.vehicle_rough_weight:
                # 在原始皮重的基础上增加随机值
                if self.inst.vehicle_type == "to_rest":
                    # 收集车增加10~90的随机值
                    offset = random.randint(10, 90)
                    self.inst.vehicle_rough_weight = self.inst.vehicle_tare_weight + offset
                elif self.inst.vehicle_type == "to_sale":
                    # 销售车增加10~130的随机值
                    offset = random.randint(10, 130)
                    self.inst.vehicle_rough_weight = self.inst.vehicle_tare_weight + offset
                else:
                    # 未知类型，增加10~100的随机值
                    self.inst.vehicle_rough_weight = self.inst.vehicle_tare_weight + random.randint(10, 100)
                
                LOGGER.info(f"已为车辆生成毛重: {self.inst.vehicle_rough_weight}kg")
            
            # 计算净重
            if not hasattr(self.inst, 'vehicle_net_weight') or not self.inst.vehicle_net_weight:
                self.inst.vehicle_net_weight = self.inst.vehicle_rough_weight - self.inst.vehicle_tare_weight
                LOGGER.info(f"已为车辆计算净重: {self.inst.vehicle_net_weight}kg")
            
            return True
        except Exception as e:
            LOGGER.error(f"生成车辆重量失败: {e}")
            return False
    
    def _initialize_history(self) -> bool:
        """
        初始化车辆历史记录
        
        :return: 是否初始化成功
        """
        try:
            if not hasattr(self.inst, 'vehicle_historys') or self.inst.vehicle_historys is None:
                self.inst.vehicle_historys = []
                LOGGER.info("已初始化车辆历史记录")
            return True
        except Exception as e:
            LOGGER.error(f"初始化车辆历史记录失败: {e}")
            return False
    
    def _set_default_status(self) -> bool:
        """
        设置默认状态
        
        :return: 是否设置成功
        """
        try:
            if not hasattr(self.inst, 'vehicle_status') or not self.inst.vehicle_status:
                self.inst.vehicle_status = "available"
                LOGGER.info(f"已为车辆设置默认状态: {self.inst.vehicle_status}")
            
            if not hasattr(self.inst, 'vehicle_last_use') or not self.inst.vehicle_last_use:
                # 设置上次使用时间为现在
                self.inst.vehicle_last_use = '1900-01-01'
                LOGGER.info(f"已为车辆设置上次使用时间: {self.inst.vehicle_last_use}")
            
            if not hasattr(self.inst, 'vehicle_cooldown_days') or not self.inst.vehicle_cooldown_days:
                self.inst.vehicle_cooldown_days = 3
                LOGGER.info(f"已为车辆设置冷却天数: {self.inst.vehicle_cooldown_days}")
            

            return True
        except Exception as e:
            LOGGER.error(f"设置车辆默认状态失败: {e}")
            return False
    
    def _set_other_info(self) -> bool:
        """
        设置其他信息
        
        :return: 是否设置成功
        """
        try:
            if not hasattr(self.inst, 'vehicle_other_info') or self.inst.vehicle_other_info is None:
                self.inst.vehicle_other_info = {}
                LOGGER.info("已初始化车辆其他信息")
            return True
        except Exception as e:
            LOGGER.error(f"设置车辆其他信息失败: {e}")
            return False
    
    def generate(self) -> bool:
        """
        生成车辆的所有缺失字段
        
        :return: 是否全部生成成功
        """
        success = True
        
        # 生成ID（如果尚未生成）
        if not hasattr(self.inst, 'vehicle_id') or not self.inst.vehicle_id:
            success &= self._generate_id()
        
        # 生成重量信息
        success &= self._generate_weights()
        
        # 初始化历史记录
        success &= self._initialize_history()
        
        # 设置默认状态
        success &= self._set_default_status()
        
        # 设置其他信息
        success &= self._set_other_info()
        
        # 如果全部成功，更新状态为就绪
        if success:
            # self.info["status"] = "active"
            LOGGER.info(f"车辆 '{self.info['vehicle_license_plate']}' 的所有字段已生成完成")
        
        return success
    
    def is_available(self, date=None) -> bool:
        """
        检查车辆在指定日期是否可用
        
        :param date: 日期字符串，格式为 'YYYY-MM-DD'，默认为当前日期
        :return: 是否可用
        """
        # 使用字典的 get 方法或 in 操作符检查键是否存在
        if 'vehicle_status' not in self.info:
            return False
        
        if self.info['vehicle_status'] != "available":
            return False
        
        # 如果没有指定日期，使用当前日期
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 同样使用字典的方法检查 last_use
        if 'vehicle_last_use' in self.info and self.info['vehicle_last_use']:
            last_use = self.info['vehicle_last_use']
            
            # 确保 last_use 是字符串或 Timestamp
            if isinstance(last_use, pd.Timestamp):
                last_use = last_use.strftime("%Y-%m-%d")  # 转换为字符串
            elif not isinstance(last_use, str):
                raise ValueError("vehicle_last_use 必须是字符串或 Timestamp 类型")
            
            last_use_date = datetime.datetime.strptime(last_use, "%Y-%m-%d")
            current_date = datetime.datetime.strptime(date, "%Y-%m-%d")
            
            # 简单示例：3天冷却期
            cooldown_days = self.info["vehicle_cooldown_days"]
            if (current_date - last_use_date).days < cooldown_days:
                return False
    
        return True
    
    def go(self, date, payload=None) -> bool:
        """
        执行车辆运送动作
        
        :param date: 日期字符串，格式为 'YYYY-MM-DD'
        :param payload: 运送的负载信息，可选
        :return: 是否运送成功
        """
        try:
            # 检查车辆是否可用
            if not self.is_available(date):
                LOGGER.warning(f"车辆 '{self.info['plate_number']}' 在 {date} 不可用")
                return False
            
            # 准备历史记录
            history_record = {
                'date': date,
                'payload': payload or {}
            }
            
            # 添加历史记录
            if not hasattr(self.inst, 'vehicle_historys'):
                self.inst.vehicle_historys = []
            
            # 添加新记录，并保持最多5条记录
            self.inst.vehicle_historys.append(history_record)
            if len(self.inst.vehicle_historys) > 5:
                self.inst.vehicle_historys = self.inst.vehicle_historys[-5:]
            
            # 更新状态
            self.inst.vehicle_status = "unavailable"
            self.inst.vehicle_last_use = date
            
            LOGGER.info(f"车辆 '{self.info['plate_number']}' 在 {date} 完成运送任务")
            return True
        except Exception as e:
            LOGGER.error(f"车辆运送失败: {e}")
            return False
    
    def __str__(self) -> str:
        """
        返回车辆的字符串表示
        
        :return: 字符串表示
        """
        if hasattr(self.inst, 'vehicle_license_plate') and hasattr(self.inst, 'vehicle_id'):
            return f"Vehicle(id={self.inst.vehicle_id}, plate={self.inst.vehicle_license_plate}, type={self.inst.vehicle_type}, status={self.inst.vehicle_status})"
        return f"Vehicle(未完成初始化, plate={self.inst.vehicle_license_plate})"

    def to_dict(self) -> Dict[str, Any]:
        """
        将车辆实例转换为字典
        
        Returns:
            包含车辆信息的字典
        """
        return dict(self.inst)
    
    @staticmethod
    def batch_validate(records: List[Dict[str, Any]], cp_id: str, existing_vehicles: Optional[pd.DataFrame] = None) -> tuple:
        """
        批量验证车辆数据
        
        Args:
            records: 待验证的车辆数据列表
            cp_id: 所属CP的ID
            existing_vehicles: 现有车辆数据，用于检查ID和车牌号是否重复
            
        Returns:
            (valid_records, invalid_records): 有效记录和无效记录的元组
        """
        valid_records = []
        invalid_records = []
        
        # 记录已存在的车牌号和ID集合
        existing_plates = set()
        existing_ids = set()
        
        # 如果提供了现有车辆数据，提取车牌号和ID
        if existing_vehicles is not None and not existing_vehicles.empty:
            if 'vehicle_license_plate' in existing_vehicles.columns:
                existing_plates.update(existing_vehicles['vehicle_license_plate'].dropna().unique())
            if 'vehicle_id' in existing_vehicles.columns:
                existing_ids.update(existing_vehicles['vehicle_id'].dropna().unique())
        
        # 记录此批次中已验证的车牌号，用于检查批次内重复
        batch_plates = set()
        
        for record in records:
            # 验证车牌号是否存在
            if "vehicle_license_plate" not in record or not record["vehicle_license_plate"]:
                invalid_records.append((record, "车牌号不能为空"))
                continue
            
            # 检查车牌号是否重复（与现有数据比较）
            plate = record["vehicle_license_plate"]
            if plate in existing_plates:
                invalid_records.append((record, f"车牌号 '{plate}' 已存在"))
                continue
            
            # 检查车牌号是否在当前批次中重复
            if plate in batch_plates:
                invalid_records.append((record, f"车牌号 '{plate}' 在上传文件中重复"))
                continue
            
            # 添加到批次车牌集合
            batch_plates.add(plate)
                
            # 验证车辆类型是否合法
            if "vehicle_type" not in record:
                record["vehicle_type"] = "to_rest"  # 默认为收油车
            elif record["vehicle_type"] not in ["to_rest", "to_sale"]:
                invalid_records.append((record, f"车辆类型 '{record['vehicle_type']}' 无效，必须是 'to_rest' 或 'to_sale'"))
                continue
            
            # 验证冷却天数
            if "vehicle_cooldown_days" not in record or pd.isna(record["vehicle_cooldown_days"]):
                record["vehicle_cooldown_days"] = 3  # 默认为3天
            else:
                try:
                    # 尝试将冷却天数转换为整数
                    record["vehicle_cooldown_days"] = int(record["vehicle_cooldown_days"])
                    if record["vehicle_cooldown_days"] <= 0:
                        record["vehicle_cooldown_days"] = 3  # 如果小于等于0，使用默认值
                except (ValueError, TypeError):
                    record["vehicle_cooldown_days"] = 3  # 如果转换失败，使用默认值
            
            # 设置其他必要字段的默认值
            if "vehicle_driver_name" not in record:
                record["vehicle_driver_name"] = ""
                
            # 设置所属CP
            record["vehicle_belonged_cp"] = cp_id
            
            # 预生成ID并检查是否重复
            try:
                # 组合车牌号和司机姓名
                driver = record.get("vehicle_driver_name", "")
                combine_str = f"{plate}_{driver}"
                
                # 使用工具函数生成哈希
                hash_value = hash_text(combine_str)
                
                # 设置车辆ID
                vehicle_id = f"V-{hash_value[:8]}"
                
                # 检查ID是否重复
                if vehicle_id in existing_ids:
                    invalid_records.append((record, f"生成的车辆ID '{vehicle_id}' 已存在"))
                    continue
                
                # 将ID添加到记录中
                record["vehicle_id"] = vehicle_id
                
                # 添加到已存在ID集合，避免批次内重复
                existing_ids.add(vehicle_id)
            except Exception as e:
                invalid_records.append((record, f"生成车辆ID时出错: {str(e)}"))
                continue
            
            # 添加到有效记录列表
            valid_records.append(record)
            
        LOGGER.info(f"批量验证车辆数据：共 {len(records)} 条，有效 {len(valid_records)} 条，无效 {len(invalid_records)} 条")
        return valid_records, invalid_records


class VehicleGroup(BaseGroup):
    """
    车辆组，用于管理多个车辆实体
    """
    def __init__(
        self, 
        vehicles: Optional[List[Vehicle]] = None,
        model: Optional[Any] = None,
        conf: Optional[Dict[str, Any]] = None,
        group_type: Optional[str] = None
    ):
        """
        初始化车辆组
        
        Args:
            vehicles: 车辆实例列表
            model: 模型实例
            conf: 配置信息
            group_type: 组合类型
        """
        vehicles = vehicles if vehicles is not None else []
        super().__init__(vehicles, group_type)
        self.model = model
        self.conf = conf
        print(f"Initialized VehicleGroup with {len(self.members)} vehicles.")
    
    def add_vehicle(self, vehicle: Vehicle) -> None:
        """
        添加车辆到组
        
        Args:
            vehicle: 车辆实例
        """
        self.instances.append(vehicle)
    
    def get_by_plate_number(self, plate_number: str) -> Optional[Vehicle]:
        """
        根据车牌号获取车辆
        
        Args:
            plate_number: 车牌号
            
        Returns:
            匹配的车辆实例，未找到则返回None
        """
        for vehicle in self.instances:
            if vehicle.info.get("vehicle_license_plate") == plate_number:
                return vehicle
        return None
    
    # def get_active_vehicles(self) -> List[Vehicle]:
    #     """
    #     获取所有激活状态的车辆
        
    #     Returns:
    #         激活状态的车辆列表
    #     """
    #     return [v for v in self.instances if v.info.get("status") == "active"]
    
    def get_by_type(self, vehicle_type: str) -> List[Vehicle]:
        """
        根据车辆类型筛选车辆
        
        Args:
            vehicle_type: 车辆类型
            
        Returns:
            匹配类型的车辆列表
        """
        return [v for v in self.instances if v.info.get("type") == vehicle_type]
    
    # def get_total_capacity(self) -> float:
    #     """
    #     计算所有激活车辆的总容量
        
    #     Returns:
    #         总容量
    #     """
    #     active_vehicles = self.get_active_vehicles()
    #     return sum(v.info.get("capacity", 0) for v in active_vehicles)
    
    def filter_by_type(self, vehicle_type: str) -> 'VehicleGroup':
        """
        按类型筛选车辆
        
        :param vehicle_type: 车辆类型
        :return: 筛选后的车辆组合
        """
        print(f"Filtering vehicles by type: {vehicle_type}")
        print(f"Total vehicles before filtering: {len(self.members)}")
        
        filtered_vehicles = []
        for v in self.members:
            if 'vehicle_type' in v.info and v.info['vehicle_type'] == vehicle_type:
                filtered_vehicles.append(v)
                print(f"Vehicle {v.info['vehicle_license_plate']} matched type {vehicle_type}")
        
        filtered_group = VehicleGroup(
            vehicles=filtered_vehicles,
            model=self.model,
            conf=self.conf,
            group_type=self.group_type
        )
        
        print(f"Total vehicles after filtering: {len(filtered_group.members)}")
        return filtered_group
    
    def filter_by_cp(self, cp_id: str) -> 'VehicleGroup':
        """
        按所属CP筛选车辆
        
        :param cp_id: CP ID
        :return: 筛选后的车辆组合
        """
        print(f"Filtering vehicles for CP ID: {cp_id}")
        print(f"Total vehicles before filtering: {len(self.members)}")
        
        filtered_vehicles = []
        for v in self.members:
            if 'vehicle_belonged_cp' in v.info and v.info['vehicle_belonged_cp'] == cp_id:
                filtered_vehicles.append(v)
                print(f"Vehicle {v.info['vehicle_license_plate']} matched CP {cp_id}")
        
        filtered_group = VehicleGroup(
            vehicles=filtered_vehicles,
            model=self.model,
            conf=self.conf,
            group_type=self.group_type
        )
        
        print(f"Total vehicles after filtering: {len(filtered_group.members)}")
        return filtered_group
    
    def filter_available(self, date=None) -> 'VehicleGroup':
        """
        筛选可用车辆
        
        :param date: 日期字符串，格式为 'YYYY-MM-DD'，默认为当前日期
        :return: 筛选后的车辆组合
        """
        filtered_vehicles = self.filter(lambda v: v.is_available(date))
        return filtered_vehicles
    
    def get_by_id(self, vehicle_id: str) -> Optional[Vehicle]:
        """
        按ID获取车辆
        
        :param vehicle_id: 车辆ID
        :return: 车辆实体或None
        """
        for vehicle in self.members:
            if hasattr(vehicle.inst, 'vehicle_id') and vehicle.inst.vehicle_id == vehicle_id:
                return vehicle
        return None
    
    def get_by_license_plate(self, license_plate: str) -> Optional[Vehicle]:
        """
        按车牌号获取车辆
        
        :param license_plate: 车牌号
        :return: 车辆实体或None
        """
        for vehicle in self.members:
            if hasattr(vehicle.inst, 'vehicle_license_plate') and vehicle.inst.vehicle_license_plate == license_plate:
                return vehicle
        return None
    
    def allocate(self, date=None, min_payload=0) -> Optional[Vehicle]:
        """
        分配一辆可用车辆
        
        :param date: 日期字符串，格式为 'YYYY-MM-DD'，默认为当前日期
        :param min_payload: 最小负载要求
        :return: 分配的车辆或None
        """
        # 获取可用车辆
        available_vehicles = self.filter_available(date)
        
        if available_vehicles.count() == 0:
            LOGGER.warning(f"没有可用车辆分配")
            return None
        
        # 随机选择一辆车辆
        selected_index = random.randint(0, available_vehicles.count() - 1)
        selected_vehicle = available_vehicles[selected_index]
        
        LOGGER.info(f"已分配车辆: {selected_vehicle}")
        return selected_vehicle
    
    def __str__(self) -> str:
        """
        返回车辆组合的字符串表示
        
        :return: 字符串表示
        """
        return f"VehicleGroup(数量={self.count()}, 类型={self.group_type})" 
    
    def update_vehicle_info(self, vehicle_id: str, update_fields: dict):
        """
        更新车辆信息
        
        :param vehicle_id: 车辆ID
        :param update_fields: 更新字段
        :return: 是否更新成功
        """
        for vehicle in self.members:
            if vehicle.info['vehicle_id'] == vehicle_id:
                vehicle.info.update(update_fields)
                # 同时更新 inst
                for key, value in update_fields.items():
                    setattr(vehicle.inst, key, value)
                print(f"Updated vehicle {vehicle_id} with fields: {update_fields}")
                return True
        print(f"Vehicle {vehicle_id} not found")
        return False
