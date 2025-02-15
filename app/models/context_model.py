from restaurant_model import Restaurant
from vehicle_model import Vehicle
from oil_model import OilEntry, CollectionRecord, OilCollectionSheet
from pydantic import BaseModel, Field
from app.config import ConfigService
from typing import List, Dict, Any, Optional, Union
import pandas as pd

class Context(BaseModel):
    """
    上下文模型。
    """
    base_info: Dict[str, Any] = Field(..., description="基础信息")
    conf: ConfigService = Field(..., description="配置服务")
    restaurants: Optional[Union[List[Restaurant]|pd.DataFrame]] = Field(..., description="可用餐厅列表")
    vehicles: Optional[List[Vehicle]] = Field(..., description="可用车辆列表")
    assignments: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="分配结果")

    oil_entries: Optional[List[OilEntry]] = Field(None, description="油桶信息")
    collection_records: Optional[List[CollectionRecord]] = Field(None, description="收油记录")
    oil_collection_sheets: Optional[List[OilCollectionSheet]] = Field(None, description="收油表")