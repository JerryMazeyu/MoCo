from restaurant_model import Restaurant
from vehicle_model import Vehicle
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
import pandas as pd

class Context(BaseModel):
    """
    上下文模型。
    """
    restaurants: Optional[Union[List[Restaurant]|pd.DataFrame]] = Field(..., description="可用餐厅列表")
    vehicles: Optional[List[Vehicle]] = Field(..., description="可用车辆列表")
    # assignments: mapping from vehicle license_plate to a list of assigned restaurant details and barrel counts
    assignments: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="分配结果")