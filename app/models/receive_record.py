from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class ReceiveRecordModel(BaseModel):
    """收油记录模型，表示从餐厅到CP的一条记录"""
    
    rr_id: Any = Field(None, description="收油合同号")
    rr_cp: Any = Field(None, description="记录所属的CP的ID")
    rr_date: Any = Field(None, description="收油日期")
    rr_vehicle: Any = Field(None, description="收油对应的车辆ID")
    rr_restaurant: Any = Field(None, description="收油对应的餐厅ID")
    rr_amount: Any = Field(None, description="单次收油桶数") 
    rr_restaurant_id:Any = Field(None, description="餐厅ID")
    rr_restaurant_name: Any = Field(..., description="餐厅名称")
    rr_restaurant_address: Any = Field(None, description="餐厅地址")
    rr_district: Any = Field(None, description="所属区域")
    rr_street: Any = Field(None, description="所属街道")
    rr_contact_person: Any = Field(None, description="饭店负责人")
    rr_vehicle_license_plate: Any = Field(None, description="车辆车牌号")
    rr_amount_180: Any = Field(None, description="180KG桶数")
    rr_amount_55: Any = Field(None, description="55KG桶数")
    rr_amount_of_day: Any = Field(None, description="当日收油总数")
    rr_serial_number: Any = Field(None, description="流水号")
    temp_vehicle_index: Any = Field(None, description="车辆记录唯一标识")
    

class RestaurantBalanceModel(BaseModel):
    """餐厅平衡表模型"""
    balance_date: Any = Field(None, description="交付日期")
    balance_cp: Any = Field(None, description="记录所属的CP的ID")
    balance_oil_type: Any = Field(None, description="货物类型")
    balance_tranport_type: Any = Field(None, description="运输方式")
    balance_serial_number: Any = Field(None, description="流水号")
    balance_vehicle_license_plate: Any = Field(None, description="车牌号")
    balance_weight_of_order: Any = Field(None, description="榜单净重")
    balance_order_number: Any = Field(None, description="磅单编号")
    balance_district: Any = Field(None, description="收集城市")
    balance_sale_number: Any = Field(None, description="销售合同号")
    balance_amount_of_day: Any = Field(None, description="当日收油总数")
    
    
    
