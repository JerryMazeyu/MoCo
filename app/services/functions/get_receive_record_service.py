"""
收油记录服务模块
"""
import datetime
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
from app.models.receive_record import ReceiveRecordModel,RestaurantBalanceModel
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
    def _oil_assign_vehicle_numbers(self,df_restaurants: pd.DataFrame, df_vehicles: pd.DataFrame, total_barrels: int, min_barrel_per_car: int=35) -> pd.DataFrame:
        """
        根据收油数分配车辆号码，并将结果与原DataFrame合并
        
        :param df_restaurants: 包含'镇/街道', '区域', '餐厅类型', '收油数'的DataFrame
        :param df_vehicles: 包含'车牌号'的DataFrame
        :param total_barrels: 总桶数限制
        :param vehicles_over_distance: 最近3天运输超过600KM的车辆
        :return: 处理后的DataFrame
        """
         # 首先检查总收油数是否达到最小要求
        total_oil = df_restaurants['rr_amount'].sum()
        if total_oil < min_barrel_per_car:
            raise ValueError(f"当前收油总桶数为 {total_oil} 桶，未达到最小要求（35桶），无法生成收油表")
        # 初始化变量
        ## 乱序排列车牌号
        vehicle_sorted_df = df_vehicles.sample(frac=1, replace=False)
        result_rows = []
        
        total_accumulated = 0  # 所有车辆的累计收油数
        should_break = False  # 控制外层循环的标志
        

        # 按区域分组
        grouped = df_restaurants.groupby('rest_district')
        
        current_vehicle_index = 0
        for area, group in grouped:
            accumulated_sum = 0
            temp_group = []
            
            for index, row in group.iterrows():
                temp_group.append(row)
                accumulated_sum += row['rr_amount']
                
                # 如果累计值达到在35-44之间，则分配车牌号并重置累计值
                if accumulated_sum >= min_barrel_per_car:
                    # 检查添加这组数据是否会超过总桶数限制
                    print(f"当前累计桶数: {total_accumulated}, 目标桶数: {total_barrels}")
                    if total_accumulated > total_barrels:
                        should_break = True  # 设置跳出标志
                        break
                        
                    # 分配车牌号
                    total_accumulated += accumulated_sum

                    for temp_row in temp_group:
                        temp_row = temp_row.copy()  # 防止修改原DataFrame
                        if current_vehicle_index < len(vehicle_sorted_df):
                            # 正确获取vehicle_id和license_plate
                            current_vehicle = vehicle_sorted_df.iloc[current_vehicle_index]
                            vehicle_id = current_vehicle['vehicle_id']
                            license_plate = current_vehicle['vehicle_license_plate']
                           
                            temp_row['rr_vehicle_license_plate'] = license_plate
                            temp_row['rr_vehicle'] = vehicle_id
                            temp_row['rr_amount_of_day'] = accumulated_sum
                            temp_row['temp_vehicle_index'] =  current_vehicle_index ## 增加一个唯一标识后面分配时间
                            result_rows.append(temp_row)
                            

                            
                        else: 
                            print(f"Warning: No more vehicles available. Current accumulated: {total_accumulated}, Target: {total_barrels}")
                            should_break = True
                            break
                    print(f"分配车辆: {vehicle_id} 车牌: {license_plate} 收油数: {accumulated_sum}")
                    current_vehicle_index += 1    
                    accumulated_sum = 0
                    temp_group = []
            
            # 如果外层循环需要跳出，则不处理剩余数据
            if should_break:
                break
        # 创建结果DataFrame前检查是否有数据
        if not result_rows:
            raise ValueError("没有符合分配条件的数据，请确保每个区域的收油量达到要求（35-44桶）")
        # 创建结果DataFrame
        result_df = pd.DataFrame(result_rows)
        
        # 打印统计信息
        print(f"总分配桶数: {total_accumulated}")
        print(f"总桶数限制: {total_barrels}")
        print(f"已分配车辆数: {len(set(result_df['rr_vehicle_license_plate']))}")
        print(f"已处理餐厅数: {len(result_rows)}")
        print(f"总餐厅数: {len(df_restaurants)}")
        
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
        print("\n最终分配结果:")
        print(f"目标55KG桶数: {count_of_barrel_55}")
        print(f"实际55KG桶数: {total_55_barrels}")
        print(f"处理的行数: {len(selected_indices)}")
        
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
                if "vehicle_belonged_cp" not in info:
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
            oil_weight = self.conf.get("BUSINESS.REST2CP.收油重量（成品）")
            oil_weight_180kg_ratio = self.conf.get("BUSINESS.REST2CP.180KG桶占比")
            change_rate = self.conf.get("BUSINESS.REST2CP.比率")
            total_barrels = np.ceil((oil_weight/change_rate)/0.18) # 先用180KG桶数计算总桶数
            count_of_barrel_180 = np.ceil((oil_weight*oil_weight_180kg_ratio/change_rate)/0.18)
            count_of_barrel_55 = np.ceil((oil_weight*(1-oil_weight_180kg_ratio)/change_rate)/0.055)


            
            # 创建一个空的列表来存储所有记录
            all_records = []

            # 每个餐厅获取收油日期和收油桶数
            for restaurant in cp_restaurants_group.to_dicts():

                # 获取收油日期
                single_restaurant = ReceiveRecord(info=restaurant,conf=self.conf)
                ## 生成收油表必须的字段
                single_restaurant.generate()
                ## 汇总每行
                all_records.append(single_restaurant.to_dict())

            # 将餐厅转化为dataframe
            cp_restaurants_df = pd.DataFrame(all_records)
            
            ## 筛选车辆类型为运输车、车辆状态为非冻结
            # 筛选车辆类型是否可用，并且是否过冷却期，只筛选过了冷却器的车辆
            cp_vehicle_df = cp_vehicle_group.filter_available()
            cp_vehicle_df = cp_vehicle_df.filter_by_type(vehicle_type="to_rest")
            cp_vehicle_df = cp_vehicle_df.to_dataframe()

            # 增加一列随机数作为桶数
            cp_restaurants_df['rr_random_barrel_amount'] = np.random.rand(cp_restaurants_df.shape[0])
            
            # 根据区域，镇/街道、桶数进行排序
            cp_restaurants_df_sorted = cp_restaurants_df.sort_values(by=['rest_district', 'rest_street', 'rr_random_barrel_amount'])

            # 检查总收油数
            total_oil = cp_restaurants_df_sorted['rr_amount'].sum()
            try:
                min_barrel_per_car, max_barrel_per_car = self.conf.BUSINESS.REST2CP.每车收购量范围[0], self.conf.BUSINESS.REST2CP.每车收购量范围[1]
                assert min_barrel_per_car <= max_barrel_per_car, "每车收购量范围配置错误，最小值大于最大值"
                random_barrel_per_car = random.randint(min_barrel_per_car, max_barrel_per_car)
            except:
                LOGGER.error("每车收购量范围配置错误，使用默认值35-44")
                min_barrel_per_car, max_barrel_per_car = 35, 44
                random_barrel_per_car = random.randint(min_barrel_per_car, max_barrel_per_car)
            if total_oil < random_barrel_per_car:
                raise ValueError(f"当前收油总桶数为 {total_oil:.1f} 桶，未达到最小要求（{random_barrel_per_car}桶），无法生成收油表")

            # 检查可用车辆数量
            if cp_vehicle_df.empty:
                raise ValueError("没有可用的运输车辆，请检查车辆信息")

            # 分配车辆号码
            try:
                result_df = self._oil_assign_vehicle_numbers(cp_restaurants_df_sorted, cp_vehicle_df, total_barrels, random_barrel_per_car)
                if result_df.empty:
                    raise ValueError("无法完成车辆分配，请确保每个区域的收油量达到要求（35-44桶）")
            except Exception as e:
            # 转换所有异常为带有明确信息的 ValueError
                error_msg = str(e)
                if "list index out of range" in error_msg:
                    raise ValueError("可用车辆数量不足，无法完成分配")
                else:
                    raise ValueError(f"车辆分配失败: {error_msg}")


            # 计算目标
            print(f"目标180KG桶数: {count_of_barrel_180}")
            print(f"目标55KG桶数: {count_of_barrel_55}")

            # 调用桶分配函数
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
            # 获得最终的收油表和平衡表
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
        dates_in_month = pd.date_range(
                start=datetime.datetime(datetime.datetime.strptime(current_date, '%Y-%m').year, datetime.datetime.strptime(current_date, '%Y-%m').month, 1),
                end=(datetime.datetime(datetime.datetime.strptime(current_date, '%Y-%m').year, datetime.datetime.strptime(current_date, '%Y-%m').month, 1) + pd.offsets.MonthEnd(0))
            )
        delivery_dates = []
        day_index = 0
        # 如果 n 大于 restaurant_balance_df 的长度，随机跳过 n - len(restaurant_balance_df) 个日期
        if n > len(restaurant_balance_df):
            skip_days = n - len(restaurant_balance_df)
            random_skip_days = random.sample(range(len(dates_in_month)), skip_days)
            dates_in_month = [date for i, date in enumerate(dates_in_month) if i not in random_skip_days]

        while day_index < len(dates_in_month):
            delta = int(car_number_of_day + random.choice([-1, 0, 1]))
            if delta <= 0:
                delta = 1  # 确保至少有一辆车
            for _ in range(min(delta, len(restaurant_balance_df) - len(delivery_dates))):
                delivery_dates.append(dates_in_month[day_index].date())
            day_index += 1
        
        # 如果生成的交付日期少于新数据框的行数，则用最后一天填充剩余部分
        if len(delivery_dates) < len(restaurant_balance_df):
            last_date = delivery_dates[-1] if delivery_dates else dates_in_month[-1].date()
            delivery_dates.extend([last_date] * (len(restaurant_balance_df) - len(delivery_dates)))
        
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
        
        
        ## 回写收油表，将平衡表中的收购时间和流水号回写到收油表
        oil_records_df[['rr_date','rr_serial_number','rr_vehicle_license_plate','rr_vehicle_id']] = pd.merge(
            oil_records_df[['rr_cp', 'rr_district', 'rr_vehicle_license_plate', 'rr_amount_of_day', 'temp_vehicle_index']],
            restaurant_balance_df[['balance_date', 'balance_serial_number', 'balance_vehicle_license_plate', 'balance_cp', 'balance_district', 'balance_amount_of_day', 'temp_vehicle_index','balance_vehicle_id']],
            left_on=['rr_cp', 'rr_district', 'rr_amount_of_day', 'temp_vehicle_index'],
            right_on=['balance_cp', 'balance_district', 'balance_amount_of_day', 'temp_vehicle_index'],
            how='left'
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