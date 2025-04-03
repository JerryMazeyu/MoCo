from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class CPModel(BaseModel):
    """小工厂CP模型，表示收油的中转站"""
    
    cp_id: Any = Field(None, description="CP的ID（自动随机生成，但也可以指定）")
    cp_name: Any = Field(None, description="CP的名称（必须有）")
    
    cp_province: Any = Field(None, description="CP所属的省份")
    cp_city: Any = Field(None, description="CP所属的城市")
    cp_location: Any = Field(None, description="CP的经纬度，格式为 '纬度,经度'")
    
    cp_barrels_per_day: Any = Field(None, description="每天收油量")
    cp_capacity: Any = Field(None, description="总容量")
    
    cp_recieve_records_raw: Any = Field(default_factory=list, description="CP自动收油的记录列表，存放所有收油记录（未必被确认）")
    cp_sales_records: Any = Field(default_factory=list, description="CP发货的记录ID列表")
    cp_recieve_records: Any = Field(default_factory=list, description="CP收油确认的记录ID列表")
    
    cp_stock: Any = Field(default=0, description="CP的库存")
    
    cp_vehicles_to_restaurant: Any = Field(default_factory=list, description="CP所属的面向餐厅收油的车辆ID列表")
    cp_vehicles_to_sales: Any = Field(default_factory=list, description="CP所属的面向销售的车辆ID列表") 