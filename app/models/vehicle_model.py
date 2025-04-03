from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime


class VehicleModel(BaseModel):
    """车辆模型，表示用于收油和销售的车辆信息"""
    
    vehicle_id: Any = Field(description="车辆ID（根据车牌号hash后生成）")
    vehicle_belonged_cp: Any = Field(None, description="所属CP（这里注意，除了CP之外可能还会有贸易场TP，此时为空）")
    
    vehicle_license_plate: Any = Field(description="车牌号信息（必须有）")
    vehicle_driver_name: Any = Field(description="司机姓名（必须有）")
    vehicle_type: Any = Field(description="车辆类型（目前有餐厅收集车to_rest、销售运输车to_sale两种）")
    
    vehicle_rough_weight: Any = Field(description="毛重（根据不同的类型有计算公式）")
    vehicle_tare_weight: Any = Field(description="皮重（根据不同的类型有计算公式）")
    vehicle_net_weight: Any = Field(description="净重（毛重-皮重）")
    
    vehicle_historys: Any = Field(default_factory=list, description="每次收油的记录，是一个列表，仅仅维护过去5次")
    vehicle_status: Any = Field(default="available", description="状态（分为可用available和不可用unavailable）")
    vehicle_last_use: Any = Field(None, description="上次使用的日期")
    
    vehicle_other_info: Any = Field(default_factory=dict, description="其他信息") 