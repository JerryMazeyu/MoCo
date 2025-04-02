from pydantic import BaseModel, Field
from typing import Dict, Optional, Any
from datetime import datetime


class Restaurant(BaseModel):
    """餐厅模型，表示产生废油的餐厅信息"""
    
    rest_id: Any = Field(description="餐厅id（根据中文名hash后生成，唯一）")
    rest_belonged_cp: Any = Field(description="所属CP（必须有）")
    
    rest_chinese_name: Any = Field(description="餐厅中文名（必须有）")
    rest_english_name: Any = Field(None, description="餐厅英文名")
    rest_province: Any = Field(description="所在省份（必须有）")
    rest_city: Any = Field(description="所在区域/城市（必须有）")
    rest_chinese_address: Any = Field(description="餐厅中文地址（必须有）")
    rest_english_address: Any = Field(None, description="餐厅英文地址")
    rest_district: Any = Field(None, description="所属区域")
    rest_street: Any = Field(None, description="所属街道")
    
    rest_contact_person: Any = Field(None, description="法人信息")
    rest_contact_phone: Any = Field(None, description="法人电话")
    
    rest_location: Any = Field(description="餐厅的经纬度，格式为 '纬度,经度'（例如 '39.9042,116.4074'）")
    rest_distance: Any = Field(description="与所属CP的距离（单位为km）")
    
    rest_type: Any = Field(None, description="餐厅类型")
    rest_verified_date: Any = Field(None, description="上次校验的时间")
    rest_allocated_barrel: Any = Field(None, description="分配的桶数")
    
    rest_other_info: Any = Field(default_factory=dict, description="其他信息") 