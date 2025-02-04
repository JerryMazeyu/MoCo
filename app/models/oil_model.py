from typing import List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class OilEntry(BaseModel):
    chinese_name: str = Field(..., description="餐厅名称（中文）")
    english_name: Optional[str] = Field(None, description="餐厅名称（英文）")
    chinese_address: str = Field(..., description="餐厅地址（中文）")
    english_address: Optional[str] = Field(None, description="餐厅地址（英文）")
    barrel_count: int = Field(..., description="桶数")
    district: str = Field(..., description="区域")
    restaurant_manager: str = Field(..., description="饭店负责人")
    contact_phone: str = Field(..., description="联系电话")
    distance: float = Field(..., description="距离（公里）")
    street: Optional[Any] = Field(None, description="街道")


class CollectionRecord(BaseModel):
    serial_no: int = Field(..., description="序号")
    collection_time: datetime = Field(..., description="收购时间")
    transaction_id: str = Field(..., description="流水号")
    license_plate: str = Field(..., description="车牌号")
    sales_contract_no: str = Field(..., description="销售合同号")
    oil_entries: List[OilEntry] = Field(..., description="与该序号关联的收油记录")


class OilCollectionSheet(BaseModel):
    title: str = Field(..., description="收油表标题")
    records: List[CollectionRecord] = Field(..., description="包含的所有序号记录")


# 示例数据
oil_entry_1 = OilEntry(
    chinese_name="海底捞",
    english_name="Haidilao",
    chinese_address="北京市海淀区知春路",
    english_address="Beijing Zhichun Road",
    barrel_count=10,
    district="海淀区",
    restaurant_manager="张三",
    contact_phone="1234567890",
    distance=15.3
)

oil_entry_2 = OilEntry(
    chinese_name="肯德基",
    english_name="KFC",
    chinese_address="北京市朝阳区光华路",
    english_address="Beijing Guanghua Road",
    barrel_count=8,
    district="朝阳区",
    restaurant_manager="李四",
    contact_phone="0987654321",
    distance=12.5
)

collection_record = CollectionRecord(
    serial_no=1,
    collection_time=datetime.now(),
    transaction_id="TRX20250129",
    license_plate="京A12345",
    sales_contract_no="SC20250129",
    oil_entries=[oil_entry_1, oil_entry_2]
)

oil_collection_sheet = OilCollectionSheet(
    title="2025年1月收油表",
    records=[collection_record]
)

print(oil_collection_sheet.json(indent=2, ensure_ascii=False))
