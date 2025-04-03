from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Any


class SaleRecordModel(BaseModel):
    """发货记录模型，表示CP到TP或者客户的发货记录"""
    
    sr_contract_id: Any = Field(None, description="销售合同号")
    sr_quantities: Any = Field(None, description="售出数量")
    sr_date: Any = Field(None, description="出货时间")
    sr_to: Any = Field(None, description="接收方ID（TP或者客户Cus）")
    sr_to_type: Any = Field(None, description="接收方类型：贸易场(TP)或客户(Cus)") 