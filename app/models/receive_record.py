from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class ReceiveRecordModel(BaseModel):
    """收油记录模型，表示从餐厅到CP的一条记录"""
    
    rr_id: Any = Field(description="收油合同号")
    rr_cp: Any = Field(description="记录所属的CP的ID")
    rr_date: Any = Field(description="收油日期")
    rr_vehicle: Any = Field(description="收油对应的车辆ID")
    rr_restaurant: Any = Field(description="收油对应的餐厅ID")
    rr_amount: Any = Field(description="单次收油量") 