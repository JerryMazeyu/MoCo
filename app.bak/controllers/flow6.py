from app.services.rule_service import RuleService
import pandas as pd
from datetime import datetime
from app.config.logging_config import LogConfig
from pydantic import BaseModel, Field
logger = LogConfig.setup_logger('flow6')
"""输入参数：
    restaurant_df: 包含餐厅信息的DataFrame
    df_vehicles: 包含收油表车辆信息的DataFrame
    total_barrels: 收油总桶数限制
    collect_days: 收油天数
    oil_weight: 收油重量
    check_days: 收货确认天数
    check_vehicle_df: 包含销售车牌信息的DataFrame
    current_date: 当前日期字符串，格式为'YYYY-MM-DD'

"""
class flow6_input_params(BaseModel):
    class Config:
        arbitrary_types_allowed = True  # 允许任意类型
    
    restaurant_df: pd.DataFrame = Field(..., description="包含餐厅信息的DataFrame")
    df_vehicles: pd.DataFrame = Field(..., description="包含收油表车辆信息的DataFrame")
    total_barrels: int = Field(..., description="收油总桶数限制")
    collect_days: int = Field(..., description="收油天数")
    oil_weight: float = Field(..., description="收油重量")
    check_days: int = Field(..., description="收货确认天数")
    check_vehicle_df: pd.DataFrame = Field(..., description="包含销售车牌信息的DataFrame")
    current_date: str = Field(..., description="当前日期字符串，格式为'YYYY-MM-DD'")

class Flow6Controller:
    def __init__(self):
        self.rule_service = RuleService()
        self.logger = logger
        # 存储每个步骤的结果
        self.results = {
            'sorted_restaurants': pd.DataFrame(),    # 排序后的餐厅信息DataFrame
            'assigned_vehicles': pd.DataFrame(),     # 分配车辆后的DataFrame
            'balance_df': pd.DataFrame(),           # 平衡表DataFrame
            'total_sheet': pd.DataFrame(),          # 总表DataFrame
            'receipt_confirmation': pd.DataFrame(),  # 收货确认书DataFrame
            'updated_total_sheet': pd.DataFrame(),   # 更新后的总表DataFrame
            'updated_oil_collection': pd.DataFrame(), # 更新后的收油表DataFrame
            'final_results': {                      # 最终结果字典，包含多个DataFrame
                '收油表': pd.DataFrame(),
                '平衡表': pd.DataFrame(),
                '总表': pd.DataFrame(),
                '收货确认书': pd.DataFrame(),
                '上月平衡表': pd.DataFrame(),
                '本月平衡表': pd.DataFrame()
            }
        }
    """
    执行完整的flow6_deal_relation_data流程，用于油品收集和平衡表生成
    
    参数:
        restaurant_df: 包含餐厅信息的DataFrame
        total_df: 总表
        vehicle_df: 包含收油表车辆信息的DataFrame
        last_month_balance：上个月的平衡表
        days: 完成收油的天数
        coeff_number: 计算用的转换系数
        current_date: 当前日期字符串，格式为'YYYY-MM-DD'
        total_barrels: 总桶数限制
        check_days: 收货确认天数
        check_vehicle_df: 包含销售车牌信息的DataFrame
    """
    def step1_generate_oil_collection(self, restaurant_df: pd.DataFrame, vehicle_df: pd.DataFrame,total_barrels: int) -> dict:
        """第一步：生成收油表"""
        try:
            self.logger.info("开始执行步骤1：生成收油表")
            sorted_restaurants = self.rule_service.oil_restaurant_sort(restaurant_df)
            assigned_vehicles = self.rule_service.oil_assign_vehicle_numbers(sorted_restaurants, vehicle_df,total_barrels)
            
            self.results['sorted_restaurants'] = sorted_restaurants
            self.results['assigned_vehicles'] = assigned_vehicles
            
            self.logger.info("步骤1执行完成")
            return {
                'sorted_restaurants': sorted_restaurants,
                'assigned_vehicles': assigned_vehicles
            }
        except Exception as e:
            self.logger.error(f"步骤1执行失败: {str(e)}")
            raise
    def step2_generate_balance(self, assigned_vehicles: pd.DataFrame, collect_days: int,current_date: str) -> pd.DataFrame:
        """第二步：生成平衡表"""
        try:
            self.logger.info("开始执行步骤2：生成平衡表")
            balance_df = self.rule_service.process_balance_dataframe(assigned_vehicles, collect_days,current_date)
            
            self.results['balance_df'] = balance_df
            
            self.logger.info("步骤2执行完成")
            return balance_df
        except Exception as e:
            self.logger.error(f"步骤2执行失败: {str(e)}")
            raise

    def step3_generate_total_sheet(self, total_df: pd.DataFrame, balance_df: pd.DataFrame) -> pd.DataFrame:
        """第三步：生成总表"""
        try:
            self.logger.info("开始执行步骤3：生成总表")
            total_sheet = self.rule_service.process_dataframe_with_new_columns(total_df, balance_df)
            
            self.results['total_sheet'] = total_sheet
            
            self.logger.info("步骤3执行完成")
            return total_sheet
        except Exception as e:
            self.logger.error(f"步骤3执行失败: {str(e)}")
            raise
        
    def step4_generate_receipt_confirmation(self, oil_weight: float, check_days: int, df_oil: pd.DataFrame, check_vehicle_df: pd.DataFrame,current_date:str) -> pd.DataFrame:
        """第四步：生成收货确认书"""
        try:
            self.logger.info("开始执行步骤4：生成收货确认书")
            receipt_confirmation = self.rule_service.generate_df_check(oil_weight, check_days, df_oil, check_vehicle_df,current_date)
            
            self.results['receipt_confirmation'] = receipt_confirmation
            
            self.logger.info("步骤4执行完成")
            return receipt_confirmation
        except Exception as e:
            self.logger.error(f"步骤4执行失败: {str(e)}")
            raise
    
    def step5_process_check_to_sum(self, receipt_confirmation: pd.DataFrame, total_sheet: pd.DataFrame) -> pd.DataFrame:
        """第五步：处理确认数据到汇总表"""
        try:
            self.logger.info("开始执行步骤5：处理确认数据到汇总表")
            updated_total_sheet = self.rule_service.process_check_to_sum(receipt_confirmation, total_sheet)
            
            self.results['updated_total_sheet'] = updated_total_sheet
            
            self.logger.info("步骤5执行完成")
            return updated_total_sheet
        except Exception as e:
            self.logger.error(f"步骤5执行失败: {str(e)}")
            raise

    def step6_copy_balance_to_oil(self, balance_df: pd.DataFrame, assigned_vehicles: pd.DataFrame) -> pd.DataFrame:
        """第六步：将平衡表数据复制到收油表"""
        try:
            self.logger.info("开始执行步骤6：将平衡表数据复制到收油表")
            updated_oil_collection = self.rule_service.copy_balance_to_oil(balance_df, assigned_vehicles)
            
            self.results['updated_oil_collection'] = updated_oil_collection
            
            self.logger.info("步骤6执行完成")
            return updated_oil_collection
        except Exception as e:
            self.logger.error(f"步骤6执行失败: {str(e)}")
            raise

    def step7_process_balance_sum_contract(self, updated_total_sheet: pd.DataFrame, receipt_confirmation: pd.DataFrame, last_month_balance: pd.DataFrame, balance_df: pd.DataFrame, coeff_number: float, current_date: str) -> pd.DataFrame:
        """第七步：处理平衡表合同编号"""
        try:
            self.logger.info("开始执行步骤7：处理平衡表合同编号")
            final_total_sheet, final_last_month, final_current_month = self.rule_service.process_balance_sum_contract(
                updated_total_sheet,
                receipt_confirmation,
                last_month_balance,
                balance_df,
                coeff_number,
                current_date
            )
            
            self.results['final_total_sheet'] = final_total_sheet
            self.results['final_last_month'] = final_last_month
            self.results['final_current_month'] = final_current_month
            
            self.logger.info("步骤7执行完成")
            return final_total_sheet, final_last_month, final_current_month
        except Exception as e:
            self.logger.error(f"步骤7执行失败: {str(e)}")
            raise

    def step8_copy_balance_to_oil_dataframes(self, updated_oil_collection: pd.DataFrame, balance_df: pd.DataFrame) -> pd.DataFrame:
        """第八步：最终将平衡表数据复制到收油表"""
        try:
            self.logger.info("开始执行步骤8：最终将平衡表数据复制到收油表")
            final_oil_collection = self.rule_service.copy_balance_to_oil_dataframes(updated_oil_collection, balance_df)
            
            self.results['final_oil_collection'] = final_oil_collection
            
            self.logger.info("步骤8执行完成")
            return final_oil_collection
        except Exception as e:
            self.logger.error(f"步骤8执行失败: {str(e)}")
            raise

    def step9_return_results(self) -> dict:
        """第九步：返回所有结果"""
        try:
            self.logger.info("开始执行步骤9：返回所有结果")
            final_results = {
                '收油表': self.results['final_oil_collection'],
                '平衡表': self.results['balance_df'],
                '总表': self.results['final_total_sheet'],
                '收货确认书': self.results['receipt_confirmation'],
                '上月平衡表': self.results['final_last_month'],
                '本月平衡表': self.results['final_current_month']
            }
            
            self.logger.info("步骤9执行完成")
            return final_results
        except Exception as e:
            self.logger.error(f"步骤9执行失败: {str(e)}")
            raise

    
    # 检查步骤结果,查看和处理每个步骤结果
    def check_step_results(self, step_name: str):
        """检查步骤结果"""
        if step_name in self.results:
            df = self.results[step_name]
            if isinstance(df, pd.DataFrame):
                print(f"\n{step_name} 结果预览:")
                print(f"形状: {df.shape}")
                print(f"列名: {df.columns.tolist()}")
                print("\n前5行数据:")
                print(df.head())
                print("\n数据类型:")
                print(df.dtypes)