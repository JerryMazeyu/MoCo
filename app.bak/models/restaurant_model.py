from typing import Optional, List, Union, Any
from pydantic import BaseModel, Field, field_validator
# from app.services.address_service import AddressService
from app.utils.conversion import convert_to_pinyin, convert_miles_to_km
from app.config import get_config
import re


class Restaurant(BaseModel):
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


    @field_validator("location")
    def validate_location(cls, value):
        """
        验证 location 字段的格式是否正确
        """
        pattern = re.compile(r'^-?\d+(\.\d+)?,-?\d+(\.\d+)?$')
        if not pattern.match(value):
            raise ValueError(f"location 必须是 '纬度,经度' 格式（例如 '39.9042,116.4074'）, 现在为{value}")
        
        # 分割经纬度并检查范围
        lat, lon = map(float, value.split(","))
        if not (-90 <= lat <= 90):
            raise ValueError("纬度必须在 -90 到 90 之间")
        if not (-180 <= lon <= 180):
            raise ValueError("经度必须在 -180 到 180 之间")
        
        return value
    

    def fill_defaults(self):
        """根据已有数据填充默认值"""
        if not self.english_name and self.chinese_name:
            self.english_name = convert_to_pinyin(self.chinese_name)
        if not self.distance_mile and self.distance_km:
            self.distance_mile = convert_miles_to_km(self.distance_km)
        if not self.contact_person_en and self.contact_person_zh:
            self.contact_person_en = convert_to_pinyin(self.contact_person_zh)
        
    
    def model_dump_with_mapping(self) -> dict:
        """将模型字段映射到 Excel 中的列名"""
        name_mapping = get_config().BUSINESS.RESTAURANT.餐厅对应关系
        dumped_data = self.model_dump()  # 获取对象的原始字段数据
        mapped_data = {}

        for internal_key, value in dumped_data.items():
            if internal_key == "other_info" and isinstance(value, dict):
                # 展开 other_info 中的所有键值对
                for other_key, other_value in value.items():
                    if other_key not in mapped_data:
                        mapped_data[other_key] = other_value
            else:
                if internal_key in name_mapping._config_dict:
                    # 查找映射关系，若找到则添加到 mapped_data 中
                    excel_key = name_mapping._config_dict.get(internal_key)
                    mapped_data[excel_key] = value
                else:
                    mapped_data[internal_key] = value

        return mapped_data
    


