from app.models.cp_model import CPModel
from typing import Dict, List, Any, Optional


class CP(CPModel):
    """小工厂CP实例类，继承自CPModel"""
    
    @property
    def status(self) -> str:
        """
        返回CP的状态，根据库存与容量比较
        状态: "未满" 或 "已满"
        """
        if self.cp_capacity is None or self.cp_stock >= self.cp_capacity:
            return "已满"
        else:
            return "未满"
    
    def show(self, detail: bool = False) -> Dict[str, Any]:
        """
        展示CP信息
        
        Args:
            detail: 是否显示详细信息
            
        Returns:
            包含CP信息的字典
        """
        base_info = {
            "CP ID": self.cp_id,
            "CP 名称": self.cp_name,
            "状态": self.status,
            "库存": self.cp_stock,
            "总容量": self.cp_capacity,
            "剩余容量": None if self.cp_capacity is None else (self.cp_capacity - self.cp_stock),
            "每日收油量": self.cp_barrels_per_day
        }
        
        if detail:
            location_info = {
                "省份": self.cp_province,
                "城市": self.cp_city,
                "位置坐标": self.cp_location
            }
            
            records_info = {
                "待确认收油记录数": len(self.cp_recieve_records_raw),
                "确认收油记录数": len(self.cp_recieve_records),
                "销售记录数": len(self.cp_sales_records)
            }
            
            vehicles_info = {
                "收油车辆数": len(self.cp_vehicles_to_restaurant),
                "销售车辆数": len(self.cp_vehicles_to_sales)
            }
            
            return {**base_info, **location_info, **records_info, **vehicles_info}
        
        return base_info
    
    def __str__(self) -> str:
        """字符串表示"""
        info = self.show(detail=False)
        parts = [f"{k}: {v}" for k, v in info.items()]
        return f"CP({', '.join(parts)})"
