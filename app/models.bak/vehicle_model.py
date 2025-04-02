from typing import List, Optional, Any
from pydantic import BaseModel, Field

class Vehicle(BaseModel):
    """
    车辆模型。
    """
    license_plate: str = Field(..., description="车牌号")
    driver_name: str = Field(..., description="司机姓名")
    vtype: str = Field(..., description="车辆类型")
    district: str = Field(..., description="所属区域")
    max_barrels: int = Field(..., description="最大收集油桶数")
    allocated_barrels: int = Field(0, description="已分配油桶数")
    other_info: Optional[Any] = Field(None, description="其他信息")