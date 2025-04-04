"""
收油记录服务模块
"""
import datetime
from typing import Dict, List, Optional, Any, Union

from app.services.instances.receive_record import ReceiveRecord, ReceiveRecordsGroup, ReceiveRecordsBalance
from app.utils.logger import logger


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
        super().__init__(model, conf)
        self.records_balance = ReceiveRecordsBalance(model=model, conf=conf)
    
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
                logger.warning(f"开始日期 {start_date} 晚于结束日期 {end_date}")
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
            logger.error(f"日期格式错误: {e}")
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
            
            logger.info(f"成功添加收油记录 {record.info['record_id']} 到 {record_date}")
            return record
        except Exception as e:
            logger.error(f"添加收油记录失败: {e}")
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