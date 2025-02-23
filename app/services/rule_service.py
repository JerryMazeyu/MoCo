import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Alignment
from openpyxl.utils.cell import get_column_letter
from typing import List, Optional
from pydantic import ValidationError
from app.config import get_config
from app.utils import rp
import numpy as np
from datetime import datetime, timedelta
import random

class RuleService:
    def __init__(self):
        self.conf = get_config()
        self.oil_mapping = self.conf.get("BUSINESS.RESTAURANT.收油关系映射", default={})

    """
    生成收油表步骤，字段名还需要修改
    """

    ## 读取配置文件收油关系映射
    def oil_determine_collection_amount(self,restaurant_type: str, oil_mapping: dict) -> int:
        for key, value in oil_mapping.items():
            if ',' in str(value):
                allocate_value =  [int(item.strip()) for item in str(value).split(',')]
            else:
                allocate_value = [int(value)]
            if any(type_keyword in restaurant_type for type_keyword in key.split('/')):
                return np.random.choice(allocate_value)
        return np.random.choice([1, 2])  # 默认值

    def oil_restaurant_sort(self,df: pd.DataFrame) -> pd.DataFrame:

        # 确保需要的列存在
        required_columns = ['Chinese name', 'English name', 'Chinese Address', 'English Address',
                            'Coordinates', 'Contact person(EN)', 'Telephone number', 'Distance (km)',
                            '镇/街道', '区域', '餐厅类型']
        
        if not all(column in df.columns for column in required_columns):
            raise ValueError("DataFrame缺少必要的列")

        # 增加一列随机数作为桶数
        df['桶数'] = np.random.rand(size=df.shape[0])
        
        # 根据区域，镇/街道、桶数进行排序
        df_sorted = df.sort_values(by=['区域', '镇/街道', '桶数'])

        
        # 应用函数到DataFrame以生成收油数列
        df_sorted['收油数'] = df_sorted['餐厅类型'].apply(lambda x :self.oil_determine_collection_amount(x,self.oil_mapping))
        
        return df_sorted
    
    def oil_assign_vehicle_numbers(df_restaurants: pd.DataFrame, df_vehicles: pd.DataFrame) -> pd.DataFrame:
        """
        根据收油数分配车辆号码，并将结果与原DataFrame合并
        
        :param df_restaurants: 包含'镇/街道', '区域', '餐厅类型', '收油数'的DataFrame
        :param df_vehicles: 包含'车牌号'的DataFrame
        :return: 处理后的DataFrame
        """
        # 初始化一些变量
        vehicle_numbers = df_vehicles['车牌号'].sample(frac=1, replace=False).tolist() #乱序车牌号
        result_rows = []
        current_vehicle_index = 0
        
        # 按区域分组
        grouped = df_restaurants.groupby('区域')
        
        for area, group in grouped:
            accumulated_sum = 0
            temp_group = []
            
            for index, row in group.iterrows():
                temp_group.append(row)
                accumulated_sum += row['收油数']
                
                # 如果累计值在35-44之间，则分配车牌号并重置累计值
                if 35 <= accumulated_sum <= 44:
                    for temp_row in temp_group:
                        temp_row = temp_row.copy()  # 防止修改原DataFrame
                        temp_row['车牌号'] = vehicle_numbers[current_vehicle_index]
                        temp_row['累计收油数'] = accumulated_sum
                        result_rows.append(temp_row)
                    current_vehicle_index = (current_vehicle_index + 1) % len(vehicle_numbers)
                    accumulated_sum = 0
                    temp_group = []
            
            # 清理未达标的数据
            if accumulated_sum < 35 and temp_group:
                continue  # 跳过最后未达标的记录
            
            # 如果有剩余但大于等于35，则分配最后一个车牌号
            if accumulated_sum >= 35:
                for temp_row in temp_group:
                    temp_row = temp_row.copy()  # 防止修改原DataFrame
                    temp_row['车牌号'] = vehicle_numbers[current_vehicle_index]
                    temp_row['累计收油数'] = accumulated_sum
                    result_rows.append(temp_row)
                current_vehicle_index = (current_vehicle_index + 1) % len(vehicle_numbers)
        
        # 返回新的DataFrame
        result_df = pd.DataFrame(result_rows)
        
        # 将结果与原DataFrame进行左连接，确保所有原始数据都在结果中
        merged_df = pd.merge(df_restaurants, result_df[['镇/街道', '区域', '车牌号', '累计收油数']], 
                            on=['镇/街道', '区域'], how='left')
        
        return merged_df

    def oil_write_to_excel_with_merge_cells(self,df: pd.DataFrame, output_path: str):
        """
        将DataFrame写入Excel文件，并合并分配的车牌号和对应的累加收油数单元格
        
        :param df: 要写入Excel的DataFrame
        :param output_path: 输出Excel文件路径
        """
        wb = Workbook()
        ws = wb.active
        
        # 写入数据
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        # 合并单元格
        start_row = 2  # 假设第一行是标题
        while start_row <= ws.max_row:
            end_row = start_row
            while end_row < ws.max_row and ws[f'E{end_row}'].value == ws[f'E{end_row + 1}'].value:
                end_row += 1
            if end_row > start_row:
                ws.merge_cells(start_row=start_row, start_column=6, end_row=end_row, end_column=6)  # 车牌号列
                ws.merge_cells(start_row=start_row, start_column=7, end_row=end_row, end_column=7)  # 累计收油数列
                ws[f'F{start_row}'].alignment = Alignment(horizontal='center', vertical='center')
                ws[f'G{start_row}'].alignment = Alignment(horizontal='center', vertical='center')
            start_row = end_row + 1
        
        wb.save(output_path)


    """
    生成平衡表-五月表步骤
    """

    def process_dataframe(self,df: pd.DataFrame, n: int) -> pd.DataFrame:
        """
        根据给定的步骤处理输入的DataFrame。
        
        :param df: 输入的DataFrame，包含'区域', '车牌号', '累计收油数'字段
        :param n: 多少天运完
        :return: 处理后的DataFrame
        """
        # 步骤1：读取dataframe中的'区域', '车牌号', '累计收油数'字段作为新的dataframe的字段，并去重
        new_df = df[['区域', '车牌号', '累计收油数']].drop_duplicates()

        # 步骤2：新建一列榜单净重，公式为累计收油数*0.18-RANDBETWEEN(1,5)/100
        new_df['榜单净重'] = new_df['累计收油数'].apply(lambda x: x * 0.18 - random.randint(1, 5) / 100)

        # 步骤3：新建几列固定值的列
        current_year_month = datetime.now().strftime('%Y%m')
        new_df['货物类型'] = '餐厨废油'
        new_df['运输方式'] = '大卡车'
        new_df['流水号'] = [f"{current_year_month}{str(i+1).zfill(3)}" for i in range(len(new_df))]
        new_df['榜单编号'] = 'B' + new_df['流水号']

        # 步骤4：计算车数car_number_of_day并新增交付日期列
        car_number_of_day = len(df) // n
        dates_in_month = pd.date_range(start=datetime(datetime.now().year, datetime.now().month, 1), 
                                    end=(datetime(datetime.now().year, datetime.now().month, 1) + pd.offsets.MonthEnd(0)))
        delivery_dates = []
        day_index = 0
        
        while day_index < len(dates_in_month):
            delta = car_number_of_day + random.choice([-1, 0, 1])
            if delta <= 0:
                delta = 1  # 确保至少有一辆车
            for _ in range(min(delta, len(new_df) - len(delivery_dates))):
                delivery_dates.append(dates_in_month[day_index].date())
            day_index += 1
        
        # 如果生成的交付日期少于新数据框的行数，则用最后一天填充剩余部分
        if len(delivery_dates) < len(new_df):
            last_date = delivery_dates[-1] if delivery_dates else dates_in_month[-1].date()
            delivery_dates.extend([last_date] * (len(new_df) - len(delivery_dates)))
        
        new_df['交付日期'] = delivery_dates[:len(new_df)]
        
        return new_df
    
    """
    总表：生成毛油库存 期末库存、辅助列、转化系数、产出重量、售出数量、加工量
    售出数量需要修改，规则没确定
    步骤1：复制日期、车牌号、榜单净重、榜单编号、收集城市;
    步骤2：新增一列加工量，如果当前日期为相同日期的最后一行，则加工量等于每个日期的榜单净重和，否则等于0 ；
        新增一列毛油库存，公式为当前行的榜单净重+上一行的毛油库存-当前行的加工量；
        新增一列辅助列，值为当前日期如果等于下一行的日期，则为空值，否则为1；
    新增1列转化系数，值为=RANDBETWEEN(900,930)/1；
    新增1列产出重量，值为round(加工量*转化系数/100,2);
    新增1列售出数量，值为0
    """
def process_dataframe_with_new_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    
    :param df: 输入的DataFrame，至少包含'日期', '车牌号', '榜单净重', '榜单编号', '收集城市'字段
    :return: 处理后的DataFrame
    """
    # 步骤1：新建一个dataframe,从dataframe复制日期、车牌号、榜单净重、榜单编号、收集城市
    new_df = df[['日期', '车牌号', '榜单净重', '榜单编号', '收集城市']].copy()
    
    # 初始化新增的列
    new_df['加工量'] = 0.0
    new_df['毛油库存'] = 0.0
    new_df['辅助列'] = None
    new_df['转化系数'] = [np.random.randint(900, 931) for _ in range(len(new_df))]
    new_df['产出重量'] = round(new_df['加工量'] * new_df['转化系数'] / 100, 2)
    new_df['售出数量'] = 0
    new_df['期末库存'] = 0.0
    
    # 步骤2：计算加工量和毛油库存
    for date in new_df['日期'].unique():
        mask = new_df['日期'] == date
        if mask.sum() > 0:  # 确保有数据
            total_weight = new_df.loc[mask, '榜单净重'].sum()
            last_index = new_df[mask].index[-1]
            new_df.at[last_index, '加工量'] = total_weight
            
            # 更新毛油库存
            running_total = 0.0
            for idx in new_df[mask].index:
                current_weight = new_df.at[idx, '榜单净重']
                previous_inventory = running_total if idx != new_df[mask].index[0] else 0
                processing_amount = new_df.at[idx, '加工量']
                new_df.at[idx, '毛油库存'] = current_weight + previous_inventory - processing_amount
                running_total = new_df.at[idx, '毛油库存']
                
    # 计算产出重量
    new_df['产出重量'] = round(new_df['加工量'] * new_df['转化系数'] / 100, 2)
    
    # 计算辅助列
    new_df['辅助列'] = new_df['日期'].ne(new_df['日期'].shift(-1)).astype(int)
    new_df['辅助列'] = new_df['辅助列'].replace({1: 1, 0: None})
    
    # 计算期末库存
    previous_end_stock = 0.0 #第一行的期末库存前一行默认0
    for index, row in new_df.iterrows():
        current_output = row['产出重量']
        current_sale = row['售出数量']
        new_df.at[index, '期末库存'] = current_output + previous_end_stock - current_sale
        previous_end_stock = new_df.at[index, '期末库存']
    
    return new_df