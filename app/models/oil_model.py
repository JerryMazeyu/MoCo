from typing import Optional, List, Union, Any
from pydantic import BaseModel, Field, field_validator

class Oil(BaseModel):
    chinese_name: str = Field(..., description="餐厅的中文名字")
    english_name: Optional[str] = Field(None, description="餐厅的英文名字")
    chinese_address: str = Field(..., description="餐厅的中文地址")
    english_address: Optional[str] = Field(None, description="餐厅的英文地址")
    restaurant_type: Any = Field(None, description="餐厅类型编号")
    
    location: str = Field(..., description="餐厅的经纬度，格式为 '纬度,经度'（例如 '39.9042,116.4074'）")
    
    district: str = Field(..., description="所在区域")
    city: str = Field(..., description="所在城市")
    province: str = Field(None, description="所在省份")
    street: Any = Field(None, description="餐厅的镇/街道名称")
    
    contact_person_zh: str = Field(..., description="联系人中文名字")
    contact_person_en: Optional[str] = Field(..., description="联系人英文名字")
    contact_phone: str = Field(..., description="联系人电话")

    distance_km: float = Field(..., description="餐厅距离基准点的距离（单位：公里）")
    distance_mile: Optional[float] = Field(None, description="餐厅距离基准点的距离（单位：英里）")
    
    other_info: Optional[dict] = Field(default_factory=dict, description="存储其他的扩展信息")