from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class CP(BaseModel):
    """小工厂CP模型，表示收油的中转站"""
    
    cp_id: Any = Field(description="CP的ID（自动随机生成，但也可以指定）")
    cp_name: Any = Field(description="CP的名称（必须有）")
    
    cp_province: Any = Field(description="CP所属的省份")
    cp_city: Any = Field(description="CP所属的城市")
    cp_location: Any = Field(description="CP的经纬度，格式为 '纬度,经度'")
    
    cp_barrels_per_day: Any = Field(description="每天收油量")
    cp_capacity: Any = Field(description="总容量")
    
    cp_recieve_raw: Any = Field(default_factory=list, description="CP自动收油的记录列表，存放所有收油记录（未必被确认）")
    cp_sales_record: Any = Field(default_factory=list, description="CP发货的记录ID列表")
    cp_recieve_record: Any = Field(default_factory=list, description="CP收油确认的记录ID列表")
    
    cp_stock: Any = Field(default=0, description="CP的库存")
    
    cp_vehicle_to_rest: Any = Field(default_factory=list, description="CP所属的面向餐厅收油的车辆ID列表")
    cp_vehicle_to_sale: Any = Field(default_factory=list, description="CP所属的面向销售的车辆ID列表") 