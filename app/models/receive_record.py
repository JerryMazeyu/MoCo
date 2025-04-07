from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class ReceiveRecordModel(BaseModel):
    """收油记录模型，表示从餐厅到CP的一条记录"""
    
    rr_id: Any = Field(None, description="收油合同号")
    rr_cp: Any = Field(None, description="记录所属的CP的ID")
    rr_date: Any = Field(None, description="收油日期")
    rr_vehicle: Any = Field(None, description="收油对应的车辆ID")
    rr_restaurant: Any = Field(..., description="收油对应的餐厅ID")
    rr_amount: Any = Field(None, description="单次收油桶数") 
    rr_restaurant_name: Any = Field(None, description="餐厅名称")
    rr_restaurant_address: Any = Field(None, description="餐厅地址")
    rr_district: Any = Field(None, description="所属区域")
    rr_street: Any = Field(None, description="所属街道")
    rr_vehicle_license_plate: Any = Field(None, description="车辆车牌号")
    rr_amount_of_barrel_180kg: Any = Field(None, description="180KG桶数")
    rr_amount_of_barrel_55kg: Any = Field(None, description="55KG桶数")
    rr_amount_of_day: Any = Field(None, description="当日收油总数")
    
    
