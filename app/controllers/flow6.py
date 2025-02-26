from app.services.rule_service import RuleService
import pandas as pd
from datetime import datetime

def flow6_deal_relation_data(restaurant_df: pd.DataFrame,total_df: pd.DataFrame, vehicle_df: pd.DataFrame,last_month_balance: pd.DataFrame,
                            days: int, coeff_number: float, current_date: str):
    """
    执行完整的flow6_deal_relation_data流程，用于油品收集和平衡表生成
    
    参数:
        restaurant_df: 包含餐厅信息的DataFrame
        total_df: 总表
        vehicle_df: 包含车辆信息的DataFrame
        last_month_balance：上个月的平衡表
        days: 完成操作的天数
        coeff_number: 计算用的转换系数
        current_date: 当前日期字符串，格式为'YYYY-MM-DD'
    """
    rule_service = RuleService()
    
    # 步骤1: 生成收油表
    sorted_restaurants = rule_service.oil_restaurant_sort(restaurant_df)
    assigned_vehicles = rule_service.oil_assign_vehicle_numbers(sorted_restaurants, vehicle_df)
    
    
    # 步骤2: 生成平衡表
    balance_df = rule_service.process_balance_dataframe(assigned_vehicles, days)
    
    # 步骤3: 生成总表（包含库存计算）
    total_sheet = rule_service.process_dataframe_with_new_columns(total_df,balance_df)
    
    # 步骤4: 生成收货确认书
    receipt_confirmation = rule_service.generate_df_check(balance_df, vehicle_df)
    
    # 步骤5: 处理确认数据到汇总表
    updated_total_sheet = rule_service.process_check_to_sum(receipt_confirmation, total_sheet)
    
    # 步骤6: 将平衡表数据复制到收油表
    updated_oil_collection = rule_service.copy_balance_to_oil(balance_df, assigned_vehicles)
    
    # 步骤7: 处理平衡表合同编号
    # 假设我们已有上月和本月的平衡表
    
    
    final_total_sheet, final_last_month, final_current_month = rule_service.process_balance_sum_contract(
        updated_total_sheet,
        receipt_confirmation,
        last_month_balance,
        balance_df,
        coeff_number,
        current_date
    )
    
    # 步骤8: 最终将平衡表数据复制到收油表
    final_oil_collection = rule_service.copy_balance_to_oil_dataframes(updated_oil_collection, balance_df)
    
    return {
        '收油表': final_oil_collection,
        '平衡表': balance_df,
        '总表': final_total_sheet,
        '收货确认书': receipt_confirmation,
        '上月平衡表': final_last_month,
        '本月平衡表': final_current_month
    }

    
