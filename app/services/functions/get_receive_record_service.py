"""
收油记录服务模块
"""
import datetime
from datetime import timedelta
from typing import Dict, List, Optional, Any, Union
import sys 
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.services.instances.receive_record import ReceiveRecord, ReceiveRecordsGroup, ReceiveRecordsBalance,BalanceRecords,BalanceRecordsGroup
from app.utils.logger import setup_logger
from app.services.instances.restaurant import Restaurant,RestaurantsGroup
from app.services.instances.vehicle import Vehicle,VehicleGroup
import numpy as np
import pandas as pd
from app.models.receive_record import ReceiveRecordModel,RestaurantBalanceModel,RestaurantTotalModel,BuyerConfirmationModel
from app.models.vehicle_model import VehicleModel
import random
import math

LOGGER = setup_logger("moco.log")

class GetReceiveRecordService:
    """
    获取收油记录的服务
    """
    def __init__(self, model=None, conf=None):
        """
        初始化收油记录服务
        
        Args:
            model: 模型实例
            conf: 配置信息
        """
        self.model = model
        self.conf = conf
        self.records_balance = ReceiveRecordsBalance()
    
    def get_by_date(
        self, 
        date: Optional[str] = None
    ) -> ReceiveRecordsGroup:
        """
        获取指定日期的收油记录
        
        Args:
            date: 日期字符串（YYYY-MM-DD格式），默认为今天
            
        Returns:
            收油记录组
        """
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        # 检查是否已有该日期的记录组
        records_group = self.records_balance.get_records_by_date(date)
        if not records_group:
            # 如果没有找到记录，创建一个新的组
            records_group = ReceiveRecordsGroup(date=date, model=self.model, conf=self.conf)
            self.records_balance.add_daily_group(records_group)
            
        return records_group
    
    def get_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[ReceiveRecordsGroup]:
        """
        获取日期范围内的收油记录
        
        Args:
            start_date: 开始日期（YYYY-MM-DD格式）
            end_date: 结束日期（YYYY-MM-DD格式）
            
        Returns:
            日期范围内的收油记录组列表
        """
        try:
            start = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
            
            if start > end:
                LOGGER.warning(f"开始日期 {start_date} 晚于结束日期 {end_date}")
                return []
                
            result = []
            current = start
            while current <= end:
                date_str = current.strftime("%Y-%m-%d")
                records_group = self.get_by_date(date_str)
                result.append(records_group)
                current += datetime.timedelta(days=1)
                
            return result
        except ValueError as e:
            LOGGER.error(f"日期格式错误: {e}")
            return []
    
    def add_record(
        self, 
        info: Dict[str, Any],
        date: Optional[str] = None
    ) -> Optional[ReceiveRecord]:
        """
        添加收油记录
        
        Args:
            info: 收油记录信息
            date: 指定日期，默认为记录中的日期或今天
            
        Returns:
            创建的收油记录实例，失败则返回None
        """
        try:
            # 使用记录中的日期或今天作为默认值
            record_date = info.get("date") or date or datetime.datetime.now().strftime("%Y-%m-%d")
            
            # 确保record_date在info中
            info["date"] = record_date
            
            # 创建记录实例
            record = ReceiveRecord(info, model=self.model, conf=self.conf)
            
            # 确保所有字段都有值
            record.generate_all_fields()
            
            # 获取对应日期的记录组并添加记录
            records_group = self.get_by_date(record_date)
            records_group.add_record(record)
            
            LOGGER.info(f"成功添加收油记录 {record.info['record_id']} 到 {record_date}")
            return record
        except Exception as e:
            LOGGER.error(f"添加收油记录失败: {e}")
            return None
    
    def get_monthly_report(
        self, 
        year: Optional[int] = None, 
        month: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取月度报表
        
        Args:
            year: 年份，默认为当前年份
            month: 月份，默认为当前月份
            
        Returns:
            月度报表数据
        """
        if year is None or month is None:
            today = datetime.datetime.now()
            year = year or today.year
            month = month or today.month
            
        return self.records_balance.get_monthly_report(year, month)
    
    def get_restaurant_records(
        self, 
        restaurant_id: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[ReceiveRecord]:
        """
        获取餐厅的收油记录
        
        Args:
            restaurant_id: 餐厅ID
            start_date: 开始日期，默认为30天前
            end_date: 结束日期，默认为今天
            
        Returns:
            餐厅的收油记录列表
        """
        # 设置默认日期范围
        if end_date is None:
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        if start_date is None:
            # 默认为30天前
            start = datetime.datetime.now() - datetime.timedelta(days=30)
            start_date = start.strftime("%Y-%m-%d")
            
        # 获取日期范围内的记录组
        daily_groups = self.get_by_date_range(start_date, end_date)
        
        # 提取符合餐厅ID的记录
        result = []
        for group in daily_groups:
            restaurant_records = group.filter_by_restaurant(restaurant_id)
            result.extend(restaurant_records)
            
        return result
    
    def get_cp_records(
        self, 
        cp_id: str, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None
    ) -> List[ReceiveRecord]:
        """
        获取CP的收油记录
        
        Args:
            cp_id: CP ID
            start_date: 开始日期，默认为30天前
            end_date: 结束日期，默认为今天
            
        Returns:
            CP的收油记录列表
        """
        # 设置默认日期范围
        if end_date is None:
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        if start_date is None:
            # 默认为30天前
            start = datetime.datetime.now() - datetime.timedelta(days=30)
            start_date = start.strftime("%Y-%m-%d")
            
        # 获取日期范围内的记录组
        daily_groups = self.get_by_date_range(start_date, end_date)
        
        # 提取符合CP ID的记录
        result = []
        for group in daily_groups:
            cp_records = group.filter_by_cp(cp_id)
            result.extend(cp_records)
            
        return result 

    # 分配车辆号码
    def _oil_assign_vehicle_numbers(self,df_restaurants: pd.DataFrame, df_vehicles: pd.DataFrame, total_barrels: int, min_barrel_per_car: int=35,max_barrel_per_car:int = 44) -> pd.DataFrame:
        """
        根据收油数分配车辆号码，并将结果与原DataFrame合并
        
        :param df_restaurants: 包含'镇/街道', '区域', '餐厅类型', '收油数'的DataFrame
        :param df_vehicles: 包含'车牌号'的DataFrame
        :param total_barrels: 总桶数限制
        :param vehicles_over_distance: 最近3天运输超过600KM的车辆
        :param min_barrel_per_car: 每车收购量最小值
        :param max_barrel_per_car: 每车收购量最大值
        :return: 处理后的DataFrame
        """
        
        # 初始化变量
        ##首先初始化每辆车的收油数
        random_barrel_per_car = random.randint(min_barrel_per_car, max_barrel_per_car)
        ## 乱序排列车牌号
        vehicle_sorted_df = df_vehicles.sample(frac=1, replace=False)
        result_rows = []
        
        total_accumulated = 0  # 所有车辆的累计收油数
        should_break = False  # 控制外层循环的标志
        
        

        # 按区域分组
        grouped = df_restaurants.groupby('rest_district',sort=False)
        
        current_vehicle_index = 0
        for area, group in grouped:
            accumulated_sum = 0
            temp_group = []
            
            for index, row in group.iterrows():
                # 先计算如果加上当前行的桶数会是多少
                potential_sum = accumulated_sum + row['rr_amount']
                
                # 如果加上当前行会超过max_barrel_per_car，先处理当前temp_group
                if potential_sum > max_barrel_per_car:
                    # 只有当accumulated_sum达到min_barrel_per_car才处理
                    if accumulated_sum >= min_barrel_per_car:
                        # 检查添加这组数据是否会超过总桶数限制
                        print(f"当前累计桶数: {total_accumulated}, 目标桶数: {total_barrels}")
                        if isinstance(total_barrels, (int, float)) and not pd.isna(total_barrels):
                            # 先检查加上这组是否会超过目标桶数
                            if total_accumulated + accumulated_sum > total_barrels:
                                should_break = True  # 设置跳出标志
                                break
                        
                        # 分配车牌号
                        total_accumulated += accumulated_sum

                        for temp_row in temp_group:
                            temp_row = temp_row.copy()  # 防止修改原DataFrame
                            temp_row['rr_vehicle_license_plate'] = None
                            temp_row['rr_vehicle'] = None
                            temp_row['rr_amount_of_day'] = accumulated_sum
                            temp_row['temp_vehicle_index'] = current_vehicle_index
                            result_rows.append(temp_row)
                                
                        current_vehicle_index += 1    
                        # 重置累计值和临时组
                        accumulated_sum = 0
                        temp_group = []
                        # 重新生成随机目标桶数
                        random_barrel_per_car = random.randint(min_barrel_per_car, max_barrel_per_car)
                        
                        # 如果加入当前行超过最大的桶数限制，那么之前的先处理，当前行作为下一组的第一条数据
                        temp_group.append(row)
                        accumulated_sum = row['rr_amount']
                    else:
                        # 如果accumulated_sum小于min_barrel_per_car，继续累加即使会超过max_barrel_per_car
                        temp_group.append(row)
                        accumulated_sum = potential_sum
                else:
                    # 如果加上当前行不会超过max_barrel_per_car，继续累加
                    temp_group.append(row)
                    accumulated_sum = potential_sum
                    
                    # 如果累计值在min和max之间，且达到或超过随机目标值，处理当前组
                    if min_barrel_per_car <= accumulated_sum <= max_barrel_per_car and accumulated_sum >= random_barrel_per_car:
                        # 检查添加这组数据是否会超过总桶数限制
                        print(f"当前累计桶数: {total_accumulated}, 目标桶数: {total_barrels}")
                        if isinstance(total_barrels, (int, float)) and not pd.isna(total_barrels):
                            # 先检查加上这组是否会超过目标桶数
                            if total_accumulated + accumulated_sum > total_barrels:
                                should_break = True  # 设置跳出标志
                                break
                        
                        # 分配车牌号
                        total_accumulated += accumulated_sum

                        for temp_row in temp_group:
                            temp_row = temp_row.copy()  # 防止修改原DataFrame
                            temp_row['rr_vehicle_license_plate'] = None
                            temp_row['rr_vehicle'] = None
                            temp_row['rr_amount_of_day'] = accumulated_sum
                            temp_row['temp_vehicle_index'] = current_vehicle_index
                            result_rows.append(temp_row)
                                
                        current_vehicle_index += 1    
                        # 重置累计值和临时组
                        accumulated_sum = 0
                        temp_group = []
                        # 重新生成随机目标桶数
                        random_barrel_per_car = random.randint(min_barrel_per_car, max_barrel_per_car)
            
            # 处理最后一组数据（如果达到最小桶数要求）
            if accumulated_sum >= min_barrel_per_car and not should_break:
                # 检查添加这组数据是否会超过总桶数限制
                print(f"当前累计桶数: {total_accumulated}, 目标桶数: {total_barrels}")
                if isinstance(total_barrels, (int, float)) and not pd.isna(total_barrels):
                    # 先检查加上这组是否会超过目标桶数
                    if total_accumulated + accumulated_sum > total_barrels:
                        break
                
                # 分配车牌号
                total_accumulated += accumulated_sum

                for temp_row in temp_group:
                    temp_row = temp_row.copy()
                    temp_row['rr_vehicle_license_plate'] = None
                    temp_row['rr_vehicle'] = None
                    temp_row['rr_amount_of_day'] = accumulated_sum
                    temp_row['temp_vehicle_index'] = current_vehicle_index
                    result_rows.append(temp_row)
                    
                current_vehicle_index += 1
            
            # 如果外层循环需要跳出，则不处理剩余数据
            if should_break:
                break
                
        # 创建结果DataFrame前检查是否有数据
        if not result_rows:
            raise ValueError("没有符合分配条件的数据，请确保每个区域的收油量达到要求（35-44桶）")
            
            
        # 创建结果DataFrame
        result_df = pd.DataFrame(result_rows)
        
        return result_df
    
    def _allocate_barrels(self, result_df: pd.DataFrame, count_of_barrel_55: int) -> pd.DataFrame:
        """
        分配180KG和55KG桶
        
        Args:
            result_df: 包含餐厅信息的DataFrame
            count_of_barrel_55: 目标55KG桶数
            
        Returns:
            处理后的DataFrame，包含rr_amount_180和rr_amount_55列
        """
        if count_of_barrel_55 is None:
            return result_df
        else:

            # 初始化 rr_amount_180 和 rr_amount_55 列
            result_df['rr_amount_180'] = result_df['rr_amount']
            result_df['rr_amount_55'] = 0

            # 记录所有选择的行的索引
            selected_indices = []

            # 获取所有可用的索引
            available_indices = list(result_df.index)

            # 跟踪55KG桶的总数
            total_55_barrels = 0

            while total_55_barrels < count_of_barrel_55:
                if not available_indices:
                    break  # 如果没有可用的索引，退出循环

                # 随机选择一行
                selected_index = random.choice(available_indices)
                selected_row = result_df.loc[selected_index]
                rr_amount = selected_row['rr_amount']

                # 计算55KG桶的最大可能数量
                max_55_barrels = math.ceil(rr_amount * 180 / 55) + 1

                # 随机选择一个不超过最大值的55KG桶数
                rr_amount_55 = random.randint(1, max_55_barrels)

                # 计算剩余重量
                remaining_weight = 180 * rr_amount - rr_amount_55 * 55

                if remaining_weight < 150:
                    # 如果剩余重量小于150，将剩余重量全部转换为55KG桶
                    additional_55_barrels = math.ceil(remaining_weight / 55)
                    rr_amount_55 += additional_55_barrels
                    # 设置180KG桶数为0
                    result_df.at[selected_index, 'rr_amount_180'] = 0
                else:
                    # 保持原有的180KG桶数，根据剩余重量计算
                    result_df.at[selected_index, 'rr_amount_180'] = math.ceil(remaining_weight/180)

                # 更新55KG桶数
                result_df.at[selected_index, 'rr_amount_55'] = rr_amount_55

                # 验证重量是否满足要求
                new_weight = (result_df.at[selected_index, 'rr_amount_180'] * 180 + 
                            result_df.at[selected_index, 'rr_amount_55'] * 55)
                original_weight = rr_amount * 180

                if new_weight >= original_weight:
                    # 记录选择的行索引
                    selected_indices.append(selected_index)
                    # 更新总55KG桶数
                    total_55_barrels = result_df['rr_amount_55'].sum()
                    print(f"处理行 {selected_index}: 55KG桶数={rr_amount_55}, 总55KG桶数={total_55_barrels}")
                else:
                    # 如果不满足要求，恢复原值
                    result_df.at[selected_index, 'rr_amount_180'] = rr_amount
                    result_df.at[selected_index, 'rr_amount_55'] = 0

                # 从可用索引中移除已处理的索引
                available_indices.remove(selected_index)

            # 打印最终结果
            # print("\n最终分配结果:")
            # print(f"目标55KG桶数: {count_of_barrel_55}")
            # print(f"实际55KG桶数: {total_55_barrels}")
            # print(f"处理的行数: {len(selected_indices)}")
            
            # 验证每行的重量平衡
            for idx in selected_indices:
                original_weight = result_df.loc[idx, 'rr_amount'] * 180
                allocated_weight = (result_df.loc[idx, 'rr_amount_180'] * 180 + 
                                result_df.loc[idx, 'rr_amount_55'] * 55)
                print(f"行 {idx}: 原始重量={original_weight}, 分配后重量={allocated_weight}")
            
            return result_df

    # 从餐厅获取收油记录
    def get_restaurant_oil_records(
            self,res_info: list[dict],vehicle_info: list[dict],
            cp_id: str,days_to_trans: int,month_year: str) :
        """
        获取餐厅的收油记录
        
        Args:
            res_info: 餐厅信息列表
            vehicle_info: 车辆信息列表
            cp_id: CP ID
            
        Returns:
            餐厅的收油记录列表,餐厅信息dataframe,车辆信息dataframe
        """
        try:
        # 调用RestaurantsGroup，通过cp_id获取餐厅列表
            restaurants = [Restaurant(info) for info in res_info]  # 将字典列表转换为 Restaurant 实例列表
            restaurants_group = RestaurantsGroup(restaurants=restaurants,group_type="cp")
            cp_restaurants_group = restaurants_group.filter_by_cp(cp_id)
            
            # 调用VehicleGroup，通过cp_id获取车辆列表
            # 确保每个车辆信息都包含 vehicle_belonged_cp
            for info in vehicle_info:
                info["vehicle_belonged_cp"] = cp_id
            
            vehicles = [Vehicle(info, model = VehicleModel) for info in vehicle_info]  # 将字典列表转换为 Vehicle 实例列表
            vehicle_group = VehicleGroup(vehicles=vehicles,group_type="cp")
            cp_vehicle_group = vehicle_group.filter_by_cp(cp_id)

            # 调用收油ReceiveRecordsGroup，通过cp_id获取收油历史记录
            # if his_oil_info is None:
            #     cp_his_oil_df = None
            # else:
            #     his_oil_info = [ReceiveRecord(info) for info in his_oil_info]  # 将字典列表转换为 ReceiveRecord 实例列表
            #     his_oil_info = ReceiveRecordsGroup(records=his_oil_info,group_type="cp")
            #     cp_his_oil_group = his_oil_info.filter_by_cp(cp_id)
            # # cp_his_oil_group关联cp_restaurants_group，取出rest_distance大于600的rr_vehicle
            #     cp_his_oil_group = cp_his_oil_group.filter_by_restaurant(cp_restaurants_group.to_dataframe().query("rest_distance > 600")['rest_id'])
            # # 将cp_his_oil_group转化为dataframe
            #     cp_his_oil_df = cp_his_oil_group.to_dataframe()


            ## 获取收油重量（成品）和180KG桶占比
            oil_weight = self.conf.runtime.oil_weight
            oil_weight_180kg_ratio = self.conf.get("BUSINESS.REST2CP.180KG桶占比")
            change_rate = self.conf.get("BUSINESS.REST2CP.比率")
            weight_of_barrel = self.conf.get("BUSINESS.REST2CP.吨每桶")
            total_barrels = np.ceil((oil_weight/change_rate)/weight_of_barrel) if oil_weight is not None else None # 先用180KG桶数计算总桶数
            count_of_barrel_180 = np.ceil((oil_weight*oil_weight_180kg_ratio/change_rate)/0.18) if oil_weight is not None else None
            count_of_barrel_55 = np.ceil((oil_weight*(1-oil_weight_180kg_ratio)/change_rate)/0.055) if oil_weight is not None else None


            
            # 创建一个空的列表来存储所有记录
            all_records = []

            # 每个餐厅获取收油日期和收油桶数
            for restaurant in cp_restaurants_group.to_dicts():

                # 获取收油日期
                single_restaurant = ReceiveRecord(info=restaurant,conf=self.conf)
                ## 生成收油表必须的字段，分配每个餐厅的桶数
                single_restaurant.generate()
                ## 汇总每行
                all_records.append(single_restaurant.to_dict())

            # 将餐厅转化为dataframe
            cp_restaurants_df = pd.DataFrame(all_records)
            
            ## 筛选车辆类型为运输车、车辆状态为非冻结
            # 筛选车辆类型是否可用，并且是否过冷却期，只筛选过了冷却器的车辆
            # cp_vehicle_df = cp_vehicle_group.filter_available()
            cp_vehicle_df = cp_vehicle_group.filter_by_type(vehicle_type="to_rest")
            cp_vehicle_df = cp_vehicle_df.to_dataframe()

            # 增加一列随机数作为桶数
            cp_restaurants_df['rr_random_barrel_amount'] = np.random.rand(cp_restaurants_df.shape[0])
            
            # 区分排序方式，按首字母排序和自定义排序
            if hasattr(self.conf.runtime, 'sort_by_letter') and self.conf.runtime.sort_by_letter:
                # 按区域首字母排序
                cp_restaurants_df_sorted = cp_restaurants_df.sort_values(
                    by=['rest_district', 'rest_street', 'rr_random_barrel_amount'],
                    key=lambda col: col.astype(str) if col.name in ['rest_district', 'rest_street'] else col
                )
            elif hasattr(self.conf.runtime, 'district_order') and self.conf.runtime.district_order:
                # 按自定义区域顺序排序
                district_order = self.conf.runtime.district_order
                # 创建区域顺序的映射
                order_map = {name: i for i, name in enumerate(district_order)}
                cp_restaurants_df['district_order_idx'] = cp_restaurants_df['rest_district'].map(lambda x: order_map.get(x, len(order_map)))
                cp_restaurants_df_sorted = cp_restaurants_df.sort_values(
                    by=['district_order_idx', 'rest_district', 'rest_street', 'rr_random_barrel_amount']
                ).drop(columns=['district_order_idx'])
            else:
                # 默认排序
                cp_restaurants_df_sorted = cp_restaurants_df.sort_values(by=['rest_district', 'rest_street', 'rr_random_barrel_amount'])

            # 检查总收油数
            total_oil = cp_restaurants_df_sorted['rr_amount'].sum()
            try:
                min_barrel_per_car, max_barrel_per_car = self.conf.BUSINESS.REST2CP.每车收购量范围[0], self.conf.BUSINESS.REST2CP.每车收购量范围[1]
                assert min_barrel_per_car <= max_barrel_per_car, "每车收购量范围配置错误，最小值大于最大值"
            except:
                LOGGER.error("每车收购量范围配置错误，使用默认值35-44")
                min_barrel_per_car, max_barrel_per_car = 35, 44
            
            ## 如果总收油数小于最小要求，则无法生成收油表
            if total_oil < min_barrel_per_car:
                raise ValueError(f"当前收油总桶数为 {total_oil:.1f} 桶，未达到最小要求（{min_barrel_per_car}桶），无法生成收油表")
            
            ## 如果总收油数小于目标收油数，则无法生成收油表
            if total_barrels is not None and str(total_barrels).strip() != "" and total_oil <total_barrels:
                raise ValueError(f"当前收油总桶数为 {total_oil:.1f} 桶，而完成目标收成品油油重量{oil_weight}吨所需的{total_barrels}桶，无法生成收油表")
            
            # 检查可用车辆数量
            # if total_barrels is not None and str(total_barrels).strip() != "":
            #     min_car_number = np.ceil(total_barrels/min_barrel_per_car) # 收油总桶数/每车收购量范围[0]
            #     if cp_vehicle_df.empty or cp_vehicle_df.shape[0] < min_car_number:
            #         raise ValueError(f"当前可用车辆数量为 {cp_vehicle_df.shape[0]} 辆，而完成目标收成品油重量{oil_weight}吨所需的{min_car_number}辆，无法生成收油表")
                


            # 分配车辆号码，确定收油每辆车的收油记录、条数，不是最后的车辆信息，车辆需要最后重新分配，只是记录个车次数
            try:
                result_df = self._oil_assign_vehicle_numbers(cp_restaurants_df_sorted, cp_vehicle_df, total_barrels, min_barrel_per_car,max_barrel_per_car)
                if result_df.empty:
                    raise ValueError("无法完成车辆分配，请确保每个区域的收油量达到要求（35-44桶）")
            except Exception as e:
            # 转换所有异常为带有明确信息的 ValueError
                error_msg = str(e)
                if "list index out of range" in error_msg:
                    raise ValueError("可用车辆数量不足，无法完成分配")
                else:
                    raise ValueError(f"车辆分配失败: {error_msg}")


            # 调用桶分配函数，前面是默认180KG桶获得的结果，这里需要分55和180KG桶
            result_df = self._allocate_barrels(result_df, count_of_barrel_55)

            
            
            

            # 过滤掉以下划线开头的列名，获得最后的收油表
            result_df = result_df[[col for col in result_df.columns if not col.startswith('_')]]

            ## 由于收油表由餐厅信息得到，需要将餐厅信息中的字段转化成收油表的字段名
            result_df.rename(columns={'rest_chinese_name':'rr_restaurant_name',
                                    'rest_chinese_address':'rr_restaurant_address',
                                    'rest_district':'rr_district',
                                    'rest_street':'rr_street',
                                    'rest_belonged_cp':'rr_cp',
                                    'rest_contact_person':'rr_contact_person',
                                    'rest_english_name':'rr_restaurant_english_name',
                                    'rest_id':'rr_restaurant_id'},inplace=True)
            ## 转成model
            result_df_instance = [ReceiveRecord(info,model = ReceiveRecordModel) for info in result_df.to_dict(orient='records')]
            result_df_instance_group = ReceiveRecordsGroup(result_df_instance)
            result_df_final = result_df_instance_group.to_dataframe()   
            print('收油表生成成功')
            # 获得最终的收油表和平衡表，这里分配最终的车辆信息和平衡表
            oil_records_df, restaurant_balance = self.get_restaurant_balance(result_df_final,days_to_trans,month_year,cp_vehicle_group)
            ##修改餐厅和车辆信息
            # 根据收油表更新餐厅信息中的 rest_verified_date 和 rest_allocated_barrel
            for index, row in oil_records_df.iterrows():
                restaurant_id = row['rr_restaurant_id']
                rest_verified_date = row['rr_date']
                rest_allocated_barrel = row['rr_amount']
                cp_restaurants_group.update_restaurant_info(restaurant_id, {'rest_verified_date': rest_verified_date.strftime('%Y-%m-%d'), 'rest_allocated_barrel': rest_allocated_barrel})

            cp_restaurants_df = cp_restaurants_group.to_dataframe()
            
            cp_vehicle_df = cp_vehicle_group.to_dataframe()
            # print('更新后的车辆数据')
            # print(cp_vehicle_df)

            return oil_records_df,restaurant_balance,cp_restaurants_df,cp_vehicle_df
        except ValueError as ve:
        # 业务逻辑错误，向上传递
            raise ve
        except Exception as e:
            # 其他未预期的错误，包装成 ValueError
            raise ValueError(f"生成收油表时发生错误: {str(e)}")
    # 
    def get_restaurant_balance(self,oil_records_df: pd.DataFrame, n: int,current_date: str, cp_vehicle_group:VehicleGroup ):

        """
        根据给定的步骤处理输入的DataFrame。
        
        :param df: 输入的DataFrame，包含'区域', '车牌号', '累计收油数'字段
        :param n: 多少天运完
        :return: 处理后的DataFrame
        """
        # 步骤1：读取dataframe中的'区域', '车牌号', '累计收油数'字段作为新的dataframe的字段，并去重
        restaurant_balance_df = oil_records_df[['rr_cp','rr_district', 'rr_vehicle_license_plate', 'rr_amount_of_day','temp_vehicle_index']].drop_duplicates()
        print('平衡表条数',len(restaurant_balance_df))
        restaurant_balance_df.rename(columns={'rr_district':'balance_district','rr_vehicle_license_plate':'balance_vehicle_license_plate','rr_amount_of_day':'balance_amount_of_day','rr_cp':'balance_cp'},inplace=True)
        # 步骤2：新建一列榜单净重，公式为累计收油数*0.18-RANDBETWEEN(1,5)/100
        restaurant_balance_df['balance_weight_of_order'] = restaurant_balance_df['balance_amount_of_day'].apply(lambda x: round(x * 0.18 - random.randint(1, 5) / 100,2))

        # 步骤3：新建几列固定值的列
        current_year_month = datetime.datetime.strptime(current_date, '%Y-%m').strftime('%Y%m')
        restaurant_balance_df['balance_oil_type'] = '餐厨废油'
        restaurant_balance_df['balance_tranport_type'] = '大卡车'
        restaurant_balance_df['balance_serial_number'] = [f"{current_year_month}{str(i+1).zfill(3)}" for i in range(len(restaurant_balance_df))]
        restaurant_balance_df['balance_order_number'] = 'B' + restaurant_balance_df['balance_serial_number']

        # 步骤4：计算车数car_number_of_day并新增交付日期列
        car_number_of_day = int(np.ceil(len(restaurant_balance_df) // n)) ## 计算每天大概需要多少辆车
        all_dates_in_month = pd.date_range(
        start=datetime.datetime(datetime.datetime.strptime(current_date, '%Y-%m').year, datetime.datetime.strptime(current_date, '%Y-%m').month, 1),
        end=(datetime.datetime(datetime.datetime.strptime(current_date, '%Y-%m').year, datetime.datetime.strptime(current_date, '%Y-%m').month, 1) + pd.offsets.MonthEnd(0))
        )

    # 2. 随机选 n 天并排序
        if n > len(all_dates_in_month):
            raise ValueError(f'输入天数n={n}大于当月天数{len(all_dates_in_month)}')
        dates_in_month = sorted(random.sample(list(all_dates_in_month), n))
        delivery_dates = []
        days = len(dates_in_month)
        total = len(restaurant_balance_df)
        base = car_number_of_day
        
        # 1. 给每天随机分配车辆数，范围是 [base-3, base+3]
        plan = []
        for _ in range(days):
            # 随机选择 -3 到 +3 的调整值
            adjustment = random.randint(-3, 3)
            daily_cars = max(1, base + adjustment)  # 确保每天至少有1辆车
            plan.append(daily_cars)

        # 2. 计算当前总分配数
        current_total = sum(plan)
        diff = total - current_total

        # 3. 调整分配方案，使总数等于目标总数
        while diff != 0:
            if diff > 0:
                # 需要增加车辆，随机选择一天增加1辆（但不能超过base+3）
                available_days = [i for i in range(days) if plan[i] < base + 3]
                if available_days:
                    day_to_add = random.choice(available_days)
                    plan[day_to_add] += 1
                    diff -= 1
                else:
                    break  # 所有天都已达到最大值
            else:  # diff < 0
                # 需要减少车辆，随机选择一天减少1辆（但不能低于max(1, base-3)）
                min_cars = max(1, base - 3)
                available_days = [i for i in range(days) if plan[i] > min_cars]
                if available_days:
                    day_to_reduce = random.choice(available_days)
                    plan[day_to_reduce] -= 1
                    diff += 1
                else:
                    break  # 所有天都已达到最小值

        # 4. 检查所有天数都在 [max(1, base-3), base+3] 范围内
        min_allowed = max(1, base - 3)
        max_allowed = base + 3
        assert all(min_allowed <= x <= max_allowed for x in plan)
        # 4. 生成 delivery_dates
        for day, count in zip(dates_in_month, plan):
            delivery_dates.extend([day.date()] * count)
        # 保证 delivery_dates 长度和 restaurant_balance_df 一致
        delivery_dates = delivery_dates[:len(restaurant_balance_df)]

        restaurant_balance_df['balance_date'] = delivery_dates[:len(restaurant_balance_df)]
        # 用于存储更新后的车辆分配
        updated_vehicle_assignments = []
        # 根据每辆车去重
        restaurant_balance_temp = restaurant_balance_df[['balance_date','balance_cp','balance_district', 'balance_vehicle_license_plate', 'balance_amount_of_day','temp_vehicle_index']].drop_duplicates()
        # 按日期分组，以便统计每天需要的车辆数量
        daily_vehicle_needs = restaurant_balance_temp.groupby('balance_date').size()
        # 逐行分配车辆
        for index, row in restaurant_balance_temp.iterrows():
            date = row['balance_date']
            date_str = date.strftime('%Y-%m-%d')
            
            # 获取当天可用的车辆
            available_vehicles = cp_vehicle_group.filter_available(date_str)
            available_vehicles = available_vehicles.filter_by_type(vehicle_type="to_rest")
            
            # 如果没有可用车辆，记录并继续使用原车辆
            if available_vehicles.count() == 0:
                needed = daily_vehicle_needs[date]
                raise ValueError(f"日期 {date_str} 没有可用车辆，该日期需要 {needed} 辆车进行收油作业")
            
            # 分配一辆可用车辆
            allocated_vehicle = available_vehicles.allocate(date=date_str)
            if allocated_vehicle is None:
                needed = daily_vehicle_needs[date]
                available = available_vehicles.count()
                raise ValueError(f"日期 {date_str} 车辆分配失败，需要 {needed} 辆车，但只有 {available} 辆可用车辆")
            # 更新车辆最后使用时间
            cp_vehicle_group.update_vehicle_info(
                allocated_vehicle.info['vehicle_id'],
                {'vehicle_last_use': date_str}
            )
            # 记录新的分配
            updated_vehicle_assignments.append({
                'temp_vehicle_index': row['temp_vehicle_index'],
                'balance_date': date,
                'balance_district': row['balance_district'],
                'balance_cp': row['balance_cp'],
                'new_vehicle_id': allocated_vehicle.info['vehicle_id'],
                'new_vehicle_license_plate': allocated_vehicle.info['vehicle_license_plate']
            })

        # 创建更新后的车辆分配DataFrame
        updated_assignments_df = pd.DataFrame(updated_vehicle_assignments)

        # 更新平衡表中的车辆信息
        restaurant_balance_df = pd.merge(
            restaurant_balance_df,
            updated_assignments_df,
            on=['temp_vehicle_index','balance_date','balance_cp','balance_district'],
            how='left'
        )
        # 更新车辆信息
        restaurant_balance_df['balance_vehicle_license_plate'] = restaurant_balance_df['new_vehicle_license_plate']
        restaurant_balance_df['balance_vehicle_id'] = restaurant_balance_df['new_vehicle_id']
        restaurant_balance_df = restaurant_balance_df.drop(columns=['new_vehicle_id', 'new_vehicle_license_plate'])
        
        
        ## 回写收油表，将平衡表中的收购时间和流水号回写到收油表,根据temp_vehicle_index关联，只展示分配车辆的收油表和平衡表
        oil_records_df[['rr_date','rr_serial_number','rr_vehicle_license_plate','rr_vehicle_id']] = pd.merge(
            oil_records_df[['rr_cp', 'rr_district', 'rr_vehicle_license_plate', 'rr_amount_of_day', 'temp_vehicle_index']],
            restaurant_balance_df[['balance_date', 'balance_serial_number', 'balance_vehicle_license_plate', 'balance_cp', 'balance_district', 'balance_amount_of_day', 'temp_vehicle_index','balance_vehicle_id']],
            left_on=['rr_cp', 'rr_district', 'rr_amount_of_day', 'temp_vehicle_index'],
            right_on=['balance_cp', 'balance_district', 'balance_amount_of_day', 'temp_vehicle_index'],
            how='inner'
        )[['balance_date','balance_serial_number','balance_vehicle_license_plate','balance_vehicle_id']]
        
        ## 将收油表和平衡表转成对应的model
        oil_records_df_instance = [ReceiveRecord(info,model = ReceiveRecordModel) for info in oil_records_df.to_dict(orient='records')]
        oil_records_df_instance_group = ReceiveRecordsGroup(oil_records_df_instance)
        oil_records_df_final=oil_records_df_instance_group.to_dataframe()

        restaurant_balance_instances = [
        BalanceRecords(info,model= RestaurantBalanceModel) for info in restaurant_balance_df.to_dict(orient='records')
        ]
        restaurant_balance_instances_group  = BalanceRecordsGroup(restaurant_balance_instances)
        restaurant_balance_final = restaurant_balance_instances_group.to_dataframe()


        return oil_records_df_final, restaurant_balance_final

####################################################################################
    """
    总表：生成毛油库存 期末库存、辅助列、转化系数、产出重量、售出数量、加工量
    传入平衡表_5月表和平衡表总表
    售出数量需要修改，规则没确定
    步骤1：从平衡表复制日期、车牌号、榜单净重、榜单编号、收集城市到总表;
    步骤2：新增一列加工量，如果当前日期为相同日期的最后一行，则加工量等于每个日期的榜单净重和，否则等于0 ；
        新增一列毛油库存，公式为当前行的榜单净重+上一行的毛油库存-当前行的加工量；
        新增一列辅助列，值为当前日期如果等于下一行的日期，则为空值，否则为1；
    新增1列转化系数，值为=RANDBETWEEN(900,930)/1；
    新增1列产出重量，值为round(加工量*转化系数/100,2);
    新增1列售出数量，值为0
    """
    def process_dataframe_with_new_columns(self, cp_id: str, balance_df: pd.DataFrame, total_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        处理DataFrame，添加新的列
        
        :param balance_df: 当月平衡表，输入的DataFrame，至少包含'日期', '车牌号', '榜单净重', '榜单编号', '收集城市'字段
        :param total_df: 总表DataFrame，如果为None则创建新的DataFrame
        :return: 处理后的DataFrame
        """
        # 步骤1：新建一个dataframe,从dataframe复制日期、车牌号、榜单净重、榜单编号、收集城市
        new_df = balance_df[['balance_date', 'balance_vehicle_license_plate', 'balance_weight_of_order', 'balance_order_number', 'balance_district']].copy()
        new_df.rename(columns={'balance_date':'total_supplied_date',
                               'balance_vehicle_license_plate':'total_delivery_trucks_vehicle_registration_no',
                               'balance_weight_of_order':'total_supplied_weight_of_order',
                               'balance_order_number':'total_weighbridge_ticket_number',
                               'balance_district':'total_collection_city'}
                               ,inplace=True)
        
        # 创建RestaurantTotalModel对象列表
        total_records = []
        for _, row in new_df.iterrows():
            # 创建基础记录
            record_dict = {
                'total_supplied_date': row['total_supplied_date'],
                'total_delivery_trucks_vehicle_registration_no': row['total_delivery_trucks_vehicle_registration_no'],
                'total_supplied_weight_of_order': row['total_supplied_weight_of_order'],
                'total_weighbridge_ticket_number': row['total_weighbridge_ticket_number'],
                'total_collection_city': row['total_collection_city'],
                'total_processing_quantity': 0.0,
                'total_iol_mt': 0.0,
                'total_conversion_coefficient': round(np.random.randint(900, 931)/10,2),
                'total_output_quantity': 0.0,
                'total_quantities_sold': 0,  # 这个值会在后面由 process_check_to_sum 更新
                'total_ending_inventory': 0.0,  # 这个值会在后面根据 total_quantities_sold 重新计算
                'total_cp': cp_id,
                'total_sale_number_detail': None,
                'total_volume_per_trucks': row['total_supplied_weight_of_order'],
                'total_customer': None,
                'total_sale_number': None,
                'total_delivery_time': None,
                'total_delivery_address': None
            }
            record = RestaurantTotalModel(**record_dict)
            total_records.append(record)
        
        # 将模型对象列表转换回DataFrame
        new_df = pd.DataFrame([record.dict() for record in total_records])
        
        # 步骤2：计算加工量和毛油库存
        for date in new_df['total_supplied_date'].unique():
            mask = new_df['total_supplied_date'] == date
            if mask.sum() > 0:  # 确保有数据
                total_weight = new_df.loc[mask, 'total_supplied_weight_of_order'].sum()
                last_index = new_df[mask].index[-1]
                new_df.at[last_index, 'total_processing_quantity'] = round(total_weight,2)
                
                # 更新毛油库存
                running_total = 0.0
                for idx in new_df[mask].index:
                    current_weight = new_df.at[idx, 'total_supplied_weight_of_order']
                    previous_inventory = running_total if idx != new_df[mask].index[0] else 0
                    processing_amount = new_df.at[idx, 'total_processing_quantity']
                    new_df.at[idx, 'total_iol_mt'] = round(current_weight + previous_inventory - processing_amount,2)
                    running_total = new_df.at[idx, 'total_iol_mt']
                
                # 将除最后一行外的其他行的三个字段设为 NaN
                for idx in new_df[mask].index[:-1]:  # 除了最后一行
                    new_df.at[idx, 'total_processing_quantity'] = None
                    new_df.at[idx, 'total_output_quantity'] = None
                    new_df.at[idx, 'total_conversion_coefficient'] = None
        
        # 计算产出重量
        new_df['total_output_quantity'] = round(new_df['total_processing_quantity'] * new_df['total_conversion_coefficient'] / 100, 2)
        
        # 计算产出重量总和并保存到runtime配置
        total_output_quantity = new_df['total_output_quantity'].sum()
        if not hasattr(self.conf, 'runtime'):
            self.conf.runtime = type('Runtime', (), {})()
        self.conf.runtime.total_output_quantity = total_output_quantity
        
        # 计算辅助列
        new_df['辅助列'] = new_df['total_supplied_date'].ne(new_df['total_supplied_date'].shift(-1)).astype(int)
        new_df['辅助列'] = new_df['辅助列'].replace({1: 1, 0: None})

        # 如果提供了总表，则合并数据
        if total_df is not None:
            # 以new_df的列为标准
            for col in new_df.columns:
                if col not in total_df.columns:
                    # 如果total_df中不存在该列，添加该列并填充空值
                    total_df[col] = None
            
            # 确保两个DataFrame的列顺序一致
            total_df = total_df[new_df.columns]
            
            # 使用concat合并，保持total_df的顺序
            result_df = pd.concat([total_df, new_df], ignore_index=True)
            return result_df
        
        return new_df
    """
    收货确认书:传入收油表、销售车牌信息、收油重量、收货确认天数
    """
    def generate_df_check(self,cp_id: str, days: int, df_balance: pd.DataFrame, df_car: pd.DataFrame,start_date:str,error_range:tuple) -> pd.DataFrame:
        """
        生成检查数据表
        
        :param days: 天数
        :param df_balance: 平衡总表DataFrame
        :param df_car: 销售车牌表DataFrame
        :param start_date: 开始日期
        :param error_range: 误差区间元组 (min, max)，单位为万分之
        :return: 生成的检查数据表DataFrame
        """
        def random_weight():
            """生成随机重量（吨）"""
            min_weight = 3050 / 100  # 最小可能重量
            if min_weight > oil_weight:
                raise ValueError(f"收货确认书的重量随机数的最小值({min_weight}吨)大于收油重量({oil_weight}吨)，请确认")
            return np.random.randint(3050, 3496) / 100
        
        def get_difference_value():
            """根据误差区间生成随机差值"""
            if error_range is None:
                return 0
            min_error, max_error = error_range
            # 将万分之转换为小数
            min_error = min_error / 10000
            max_error = max_error / 10000
            # 生成随机差值
            return round(np.random.uniform(min_error, max_error), 6)
        
        # 将DataFrame的每一行转换为字典，然后创建Vehicle对象
        vehicles = [Vehicle(row.to_dict(), model=VehicleModel) for _, row in df_car.iterrows()]
        vehicle_group = VehicleGroup(vehicles=vehicles)
        
        # 获取可用的销售车辆
        cp_vehicle_group = vehicle_group.filter_available()
        cp_vehicle_group = cp_vehicle_group.filter_by_type(vehicle_type="to_sale")

        # 从runtime配置中获取收油重量
        change_rate = self.conf.get("BUSINESS.REST2CP.比率")
        weight_of_barrel = self.conf.get("BUSINESS.REST2CP.吨每桶") #设置的每桶重量
        # sum_balance_weight = df_balance['balance_amount_of_day'].sum()*weight_of_barrel*change_rate #平衡表的总收油成品重量
        oil_weight = self.conf.runtime.total_output_quantity
        ## 如果选择的是部分餐厅生成，那么用部分餐厅时输入的收油成品数量，如果选择的是全部餐厅生成，那么用平衡表的总收油的成品重量
        # oil_weight = oil_weight if oil_weight not in (None, "") and isinstance(oil_weight, (int, float)) else sum_balance_weight
        
        # 创建BuyerConfirmationModel对象列表
        check_records = []
        
        # 步骤1：确定行数和重量
        total_weight = 0
        weights = []
        while True:
            weight = random_weight()
            potential_total = total_weight + weight
            # 如果加上这个重量会超过目标重量，就停止
            if potential_total > oil_weight:
                break
            weights.append(weight)
            total_weight = potential_total
        rows_count = len(weights)

        # 步骤2：分配日期
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        base_cars_per_day = rows_count // days
        remaining_total_cars = rows_count
        dates = []

        for day in range(days):
            current_date = start_date + timedelta(days=day)
            
            if day == days - 1:  # 最后一天
                # 将剩余所有车次分配到最后一天
                day_cars = remaining_total_cars
            else:
                # 随机生成当天车次 (基础车次 ± 1)
                day_cars = base_cars_per_day + np.random.choice([-1, 0, 1])
                # 确保不会分配过多或过少
                if remaining_total_cars - day_cars < (days - day - 1):  # 确保后面的天数至少每天能分配1辆车
                    day_cars = remaining_total_cars - (days - day - 1)
                elif remaining_total_cars - day_cars > (days - day - 1) * (base_cars_per_day + 1):  # 确保后面的天数不会超出最大可能车次
                    day_cars = remaining_total_cars - (days - day - 1) * (base_cars_per_day + 1)
            
            # 确保当天车次不会小于0
            day_cars = max(1, min(day_cars, remaining_total_cars))
            remaining_total_cars -= day_cars
            
            # 添加当天的日期
            dates.extend([current_date] * day_cars)
        
        # 创建检查记录
        daily_cars = {}  # 用于记录每天需要的车辆数
        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            daily_cars[date_str] = daily_cars.get(date_str, 0) + 1

        ## 如果weights和dates的长度不一致，则取最小的长度
        min_len = min(len(weights), len(dates))
        weights = weights[:min_len]
        dates = dates[:min_len]
        rows_count = min_len
        for i, (current_date, weight) in enumerate(zip(dates, weights)):
            try:
                current_date_str = current_date.strftime('%Y-%m-%d')
                
                # 获取当天可用的车辆
                available_vehicles = cp_vehicle_group.filter_available(current_date_str)
                available_vehicles = available_vehicles.filter_by_type(vehicle_type="to_sale")
                
                # 如果没有可用车辆，抛出异常
                if available_vehicles.count() == 0:
                    needed = daily_cars[current_date_str]  # 使用当天实际需要的车辆数
                    raise ValueError(f"日期 {current_date_str} 没有可用车辆，该日期需要 {needed} 辆车进行收油作业")
                
                # 分配一辆可用车辆
                allocated_vehicle = available_vehicles.allocate(date=current_date_str)
                if allocated_vehicle is None:
                    needed = daily_cars[current_date_str]  # 使用当天实际需要的车辆数
                    available = available_vehicles.count()
                    raise ValueError(f"日期 {current_date_str} 车辆分配失败，需要 {needed} 辆车，但只有 {available} 辆可用车辆")
                
                # 更新车辆最后使用时间，注意是更新原始数据
                vehicle_group.update_vehicle_info(
                    allocated_vehicle.info['vehicle_id'],
                    {'vehicle_last_use': current_date_str}
                )
                
                # 获取车辆信息
                tare_weight = allocated_vehicle.info['vehicle_tare_weight'] + np.random.randint(1, 14) * 10
                net_weight = int(weight * 1000)
                gross_weight = tare_weight + net_weight
                difference = get_difference_value()
                unload_weight = weight - weight*difference
                
                # 创建完整的记录字典
                record_dict = {
                    'check_date': current_date,
                    'check_name': "工业级混合油",
                    'check_truck_plate_no': allocated_vehicle.info['vehicle_license_plate'],
                    'check_weight': weight,
                    'check_quantity': allocated_vehicle.info['vehicle_driver_name'],
                    'check_weighbridge_ticket_number': f"BD{current_date.strftime('%Y%m')}{str(i+1).zfill(3)}",
                    'check_gross_weight': gross_weight,
                    'check_tare_weight': tare_weight,
                    'check_net_weight': net_weight,
                    'check_unload_weight':  round(unload_weight,6),
                    'check_difference': round(difference,6),
                    'check_belong_cp': cp_id,
                    'check_description_of_material': None
                }
                
                record = BuyerConfirmationModel(**record_dict)
                check_records.append(record)
            except IndexError:
                print(f"IndexError at i={i}, dates={len(dates)}, weights={len(weights)}, rows_count={rows_count}")
                raise
        
        # 将模型对象列表转换为DataFrame
        df_check = pd.DataFrame([record.dict() for record in check_records])
        cp_vehicle_df = vehicle_group.to_dataframe()
        print('generate_df_check运行结束')
        return df_check,cp_vehicle_df
    
    """
    复制收货确认书的"数据透视表"的每日重量一列至物料平衡表-总表，对齐日期
    传入收货确认书和平衡表-总表
    """
    def process_check_to_sum(self, df_generate_check: pd.DataFrame, df_generate_sum: pd.DataFrame) -> pd.DataFrame:
        """
        处理两个DataFrame并生成一个新的DataFrame。
        
        :param df_generate_check: 包含提货日期和重量的DataFrame,收货确认书
        :param df_generate_sum: 包含供应日期和售出数量的DataFrame，物料平衡表-总表
        :return: 处理后的DataFrame
        """
        # 步骤1：对df_generate_check表根据提货日期对重量进行求和汇总得到df_sum
        df_sum = df_generate_check.groupby('check_date')['check_weight'].sum().reset_index()
        df_sum.rename(columns={'check_weight': '汇总重量'}, inplace=True)
        
        # 确保日期列的类型一致
        df_sum['check_date'] = pd.to_datetime(df_sum['check_date'])
        df_generate_sum['total_supplied_date'] = pd.to_datetime(df_generate_sum['total_supplied_date'])
        
        # 步骤2：关联df_generate_sum和df_sum，根据df_generate_sum的供应日期和df_sum的提货日期，
        # 将df_generate_sum中相同日期的最后一行的售出数量赋值为df_sum对应日期的汇总值
        df_merged = pd.merge(df_generate_sum, df_sum, left_on='total_supplied_date', right_on='check_date', how='left')
        
        # 对于每个日期，找到最后一行并将售出数量设置为汇总重量
        for date in df_merged['total_supplied_date'].unique():
            mask = df_merged['total_supplied_date'] == date
            if mask.sum() > 0:  # 确保有数据
                last_index = df_merged[mask].index[-1]  # 获取相同日期中的最后一行索引
                value = df_merged.loc[last_index, '汇总重量'] if pd.notna(df_merged.loc[last_index, '汇总重量']) else 0
                df_merged.at[last_index, 'total_quantities_sold'] = round(float(value),2)
        
        # 删除不必要的列
        df_final = df_merged.drop(columns=['check_date', '汇总重量'])
        
        return df_final
    
    """
    复制流水号、交付时间和销售合同号
    输入收油表和平衡表_5月表"""
    def copy_balance_to_oil_dataframes(self,df_generate_oil: pd.DataFrame, df_generate_balance: pd.DataFrame) -> pd.DataFrame:
        """
        将df_generate_balance的信息合并到df_generate_oil中。
        
        :param df_generate_oil: 主表DataFrame，包含车牌号和累计收油数等信息
        :param df_generate_balance: 包含流水号、交付时间、销售合同号等信息的DataFrame
        :return: 合并后的df_generate_oil DataFrame
        """
        # 检查必要的列是否存在
        required_oil_columns = ['rr_vehicle_license_plate', 'rr_amount_of_day', 'rr_date']
        required_balance_columns = ['balance_vehicle_license_plate', 'balance_amount_of_day', 'balance_date']
        
        missing_oil_columns = [col for col in required_oil_columns if col not in df_generate_oil.columns]
        missing_balance_columns = [col for col in required_balance_columns if col not in df_generate_balance.columns]
        
        if missing_oil_columns:
            raise ValueError(f"df_generate_oil 缺少必要的列: {missing_oil_columns}")
        if missing_balance_columns:
            raise ValueError(f"df_generate_balance 缺少必要的列: {missing_balance_columns}")
        
        # 确保日期列的类型一致
        df_generate_oil['rr_date'] = pd.to_datetime(df_generate_oil['rr_date'])
        df_generate_balance['balance_date'] = pd.to_datetime(df_generate_balance['balance_date'])
        
        # 选择需要的列进行合并
        balance_columns = [
            'balance_vehicle_license_plate', 
            'balance_amount_of_day', 
            'balance_serial_number', 
            'balance_date', 
            'balance_sale_number'
        ]
        
        # 打印调试信息
        # print("df_generate_oil columns:", df_generate_oil.columns.tolist())
        # print("df_generate_balance columns:", df_generate_balance.columns.tolist())
        # print("df_generate_oil shape:", df_generate_oil.shape)
        # print("df_generate_balance shape:", df_generate_balance.shape)
        
        # 执行合并
        merged_df = pd.merge(
            df_generate_oil,
            df_generate_balance[balance_columns],
            left_on=['rr_vehicle_license_plate', 'rr_amount_of_day', 'rr_date'],
            right_on=['balance_vehicle_license_plate', 'balance_amount_of_day', 'balance_date'],
            how='left'
        )
        
        # 更新df_generate_oil的相应列
        df_generate_oil['rr_sale_number'] = merged_df['balance_sale_number']
        
        return df_generate_oil

    def process_balance_sum_contract(self, df_generate_sum: pd.DataFrame, df_generate_check: pd.DataFrame,
                       df_generate_balance_last_month: pd.DataFrame, df_generate_balance_current_month: pd.DataFrame,
                       coeff_number: float, current_date: str):
        """
        处理两个DataFrame并生成一个新的DataFrame。
        
        :param df_generate_sum:总表 包含供应日期、产出重量、期末库存等信息的DataFrame
        :param df_generate_check: 收油表 包含重量列的DataFrame
        :param df_generate_balance_last_month: 上月的平衡表DataFrame，可以为空
        :param df_generate_balance_current_month: 当月的平衡表DataFrame
        :param coeff_number: 浮点型数据，用于后续计算
        :param current_date: 字符串格式的当前日期
        :return: 处理后的DataFrame
        """
        # 检查必要参数是否为空
        if df_generate_sum is None or df_generate_sum.empty:
            raise ValueError("df_generate_sum不能为空")
        if df_generate_check is None or df_generate_check.empty:
            raise ValueError("df_generate_check不能为空")
        if df_generate_balance_current_month is None or df_generate_balance_current_month.empty:
            raise ValueError("df_generate_balance_current_month不能为空")
        if coeff_number is None:
            raise ValueError("coeff_number不能为空")
        if current_date is None:
            raise ValueError("current_date不能为空")

        # 步骤1：sum_product=df_generate_check的重量列进的和
        sum_product = df_generate_check['check_weight'].sum()
        
        # 步骤2：获取上一个日期
        current_date = pd.to_datetime(current_date)
        last_month = (current_date - timedelta(days=current_date.day)).replace(day=1)
        
        # 检查是否存在上个月的数据
        last_month_mask = df_generate_sum['total_supplied_date'].dt.to_period('M') == last_month.to_period('M')
        last_month_data = df_generate_sum[last_month_mask]
        last_month_ending_inventory = 0  # 默认值为0
        if not last_month_data.empty:
            last_month_ending_inventory = last_month_data.iloc[-1]['total_ending_inventory']
        
        # 步骤3：当月的产出重量month_quantity = sum_product-last_month_ending_inventory 
        month_quantity = sum_product - last_month_ending_inventory
        
        # 步骤4：取出df_generate_sum表中供应日期的月份等于current_date月份并且产出重量不为空值或者null值的供应日期和产出重量值，并去重，
        # 循环去重后的供应日期和产出重量值，对产出重量值进行累加求和，当加到某一行的产出重量累加值<=month_quantity 并且下一行的产出重量累加值>month_quantity 时停止，
        # 记录当前行的供应日期stop_date和累加值sum_quantity；
        mask_current_month = (df_generate_sum['total_supplied_date'].dt.to_period('M') == current_date.to_period('M')) & (df_generate_sum['total_output_quantity'].notna())
        filtered_df = df_generate_sum[mask_current_month][['total_supplied_date', 'total_output_quantity']].drop_duplicates()
        
        cumulative_sum = 0
        stop_date = None
        sum_quantity = 0
        for index, row in filtered_df.iterrows():
            cumulative_sum += row['total_output_quantity']
            if cumulative_sum > month_quantity:
                stop_date = row['total_supplied_date']
                sum_quantity = cumulative_sum - row['total_output_quantity']
                break
            else:
                stop_date = filtered_df.iloc[-1]['total_supplied_date']
                sum_quantity = cumulative_sum
        
        # 步骤5：求出剩余的原料remaining_materia= （month_quantity  -sum_quantity）/coeff_number,
        remaining_material = (month_quantity - sum_quantity) / coeff_number
        
        # 依次对df_generate_sum中供应日期大于等于stop_date的行的每车吨量累加求和，直到累加和>remaining_materia停止，记录对应的行索引stop_index
        mask_after_stop_date = (df_generate_sum['total_supplied_date'] >= stop_date) #大于等于，因为stop_date上面是已经大于剩余量的日期
        cumulative_weight = 0
        stop_index = None
        
        # 先获取小于stop_date的最大索引
        mask_before_stop_date = (df_generate_sum['total_supplied_date'] < stop_date)
        last_index_before_stop = df_generate_sum[mask_before_stop_date].index.max() if not df_generate_sum[mask_before_stop_date].empty else None
        
        for idx, row in df_generate_sum[mask_after_stop_date].iterrows():
            cumulative_weight += row['total_output_quantity']
            if cumulative_weight > remaining_material:
                stop_index = idx
                break
            else:
                stop_index = df_generate_sum.index[-1]
        
        # 步骤6：填充df_generate_sum表中分配明细列，
        # 填充规则为1：供应日期的月份=current_date减1个月的合同分配明细列为空的分配明细列；
        # 2：供应日期的月份=current_date对应月份的行：
        #    - 所有小于stop_date的行
        #    - 行索引<=stop_index的行
        fill_value = f"BWD-JC{str(current_date.year)[-2:]}{current_date.month:02d}01"
        
        # 规则1：上个月的空值
        mask_last_month = df_generate_sum['total_supplied_date'].dt.to_period('M') == last_month.to_period('M')
        df_generate_sum.loc[mask_last_month & df_generate_sum['total_sale_number_detail'].isna(), 'total_sale_number_detail'] = fill_value
        
        # 规则2：当月的行
        mask_current_month = df_generate_sum['total_supplied_date'].dt.to_period('M') == current_date.to_period('M')
        # 填充所有小于stop_date的行
        if last_index_before_stop is not None:
            mask_before_stop = df_generate_sum.index <= last_index_before_stop
            df_generate_sum.loc[mask_current_month & mask_before_stop & df_generate_sum['total_sale_number_detail'].isna(), 'total_sale_number_detail'] = fill_value
        
        # 填充大于等于stop_date且索引<=stop_index的行
        mask_until_stop_index = df_generate_sum.index <= stop_index
        df_generate_sum.loc[mask_current_month & mask_until_stop_index & df_generate_sum['total_sale_number_detail'].isna(), 'total_sale_number_detail'] = fill_value

        # 步骤7：如果df_generate_balance_last_month不为空，则填充其合同分配明细列
        if df_generate_balance_last_month is not None and not df_generate_balance_last_month.empty:
            df_generate_balance_last_month.loc[df_generate_balance_last_month['total_sale_number_detail'].isna(), 'total_sale_number_detail'] = fill_value
        
        # 步骤8：填充df_generate_balance_current_month分配明细列，规则为关联df_generate_sum表，根据日期和过磅单编号关联，
        # 填充值为BWD-JC开头，加current_date年份的后2位数字，加current_date月份的第一天
        # 确保日期列的类型一致
        df_generate_balance_current_month['balance_date'] = pd.to_datetime(df_generate_balance_current_month['balance_date'])
        df_generate_sum['total_supplied_date'] = pd.to_datetime(df_generate_sum['total_supplied_date'])
        
        # 保存原始列名
        original_columns = df_generate_balance_current_month.columns.tolist()
        
        # 合并数据，只选择需要的列
        merged_df = df_generate_balance_current_month.merge(
            df_generate_sum[['total_supplied_date', 'total_weighbridge_ticket_number', 'total_sale_number_detail']], 
            left_on=['balance_date', 'balance_order_number'], 
            right_on=['total_supplied_date', 'total_weighbridge_ticket_number'], 
            how='left'
        )
        
        # 只保留原始列，并更新balance_sale_number
        df_generate_balance_current_month = merged_df[original_columns].copy()
        df_generate_balance_current_month['balance_sale_number'] = merged_df['total_sale_number_detail']

        return df_generate_sum, df_generate_balance_last_month, df_generate_balance_current_month

if __name__ == "__main__":
    from app.config.config import CONF
    from app.models.restaurant_model import RestaurantModel
    from app.models.vehicle_model import VehicleModel
    from app.models.receive_record import ReceiveRecordModel
    service = GetReceiveRecordService(model=ReceiveRecordModel,conf=CONF)
    restaurant_list = [
        {
        "rest_id": f"rest_{i}",
        "rest_belonged_cp": "cp1",
        "rest_chinese_name": f"餐厅{i}",
        "rest_english_name": f"Restaurant {i}",
        "rest_province": "省份A",
        "rest_city": "城市A",
        "rest_chinese_address": f"地址{i}",
        "rest_english_address": f"Address {i}",
        "rest_district": "区域A",
        "rest_street": "街道A",
        "rest_contact_person": "联系人A",
        "rest_contact_phone": "12345678901",
        "rest_location": "39.9042,116.4074",
        "rest_distance": 10 + i,  # 示例距离
        "rest_type": "类型A",
        "rest_verified_date": "2023-01-01",
        "rest_allocated_barrel": 100 + i,  # 示例分配桶数
        "rest_other_info": {}
    }
    for i in range(1000)
]
    vehicle_list = [
        {
        "vehicle_id": f"vehicle_{i}",
        "vehicle_belonged_cp": "cp1",
        "vehicle_license_plate": f"车牌{i}",
        "vehicle_driver_name": f"司机{i}",
        "vehicle_type": "to_rest",
        "vehicle_rough_weight": 2000 + i * 100,  # 示例毛重
        "vehicle_tare_weight": 1500 + i * 100,   # 示例皮重
        "vehicle_net_weight": 500 + i * 100,     # 示例净重
        "vehicle_historys": [],
        "vehicle_status": "available",
        "vehicle_last_use": "2023-01-01",
        "vehicle_other_info": {}
    }
    for i in range(10)
]
    
    cp_id = "cp1"
    his_oil_info = None
    oil,restaurant_balance,cp_restaurants_df,cp_vehicle_df = service.get_restaurant_oil_records(restaurant_list, vehicle_list, cp_id,10,'2025-01')
    cp_restaurants_df.to_excel("cp_restaurants_df1.xlsx",index=False)
    cp_vehicle_df.to_excel("cp_vehicle_df1.xlsx",index=False)
    oil.to_excel('oil.xlsx',index=False)
    restaurant_balance.to_excel('balance.xlsx',index=False)
