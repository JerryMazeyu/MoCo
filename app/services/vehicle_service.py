import os
import pandas as pd
from typing import List, Optional
from pydantic import ValidationError
from app.config import get_config
from app.models.vehicle_model import Vehicle
from app.utils import rp


class VehicleService:
    def __init__(self, file_path: Optional[str] = None) -> None:
        self.vehicles_file = rp(file_path)
        try:
            self.load_from_excel()
        except:
            self.vehicles: List[Vehicle] = []
        self.config = get_config()

    def load_from_excel(self, file_path=None) -> None:
        """
        尝试从 self.vehicles_file 加载车辆信息；若文件不存在则保持空列表。
        """
        if file_path:
            self.vehicles_file = rp(file_path)
        try:
            df = pd.read_excel(self.vehicles_file)
            self.vehicles = []
            for idx, row in df.iterrows():
                # 准备提取需要的字段，若缺失则给默认值
                license_plate = row.get("车牌号", None)
                driver_name = row.get("司机", None)
                vtype = row.get("车辆类型", None)
                district = row.get("所属区域", None)
                max_barrels = row.get("最大收油桶数", 0)
                other_info = row.get("其他信息", None)
                if max_barrels != max_barrels:  # NaN 检查
                    max_barrels = 0
                try:
                    # 转换为 int，若有异常也会被捕获
                    max_barrels = int(max_barrels) if max_barrels else 0
                except ValueError:
                    print(f"[警告] 行 {idx} （车牌号：{license_plate}） 的最大收油桶数不是合法整数，已跳过")
                    continue
                
                # 若必需字段缺失（如 license_plate, driver_name），可以做更严格的校验
                if not license_plate or not driver_name:
                    print(f"[警告] 行 {idx} 缺少必填字段 license_plate/driver_name，已跳过")
                    continue
                
                try:
                    v = Vehicle(
                        license_plate=license_plate,
                        driver_name=driver_name,
                        vtype=vtype,
                        district=district,
                        max_barrels=max_barrels,
                        allocated_barrels=0,
                        other_info=other_info
                    )
                    self.vehicles.append(v)
                except ValidationError as ve:
                    print(f"跳过无效记录：{ve}")

        except Exception as e:
            print(f"加载本地文件失败：{e}")
            self.vehicles = []

    def save_to_excel(self, save_path: Optional[str] = None) -> None:  # 这里修改成带保存路径参数的版本
        """
        将 self.vehicles 写入到 Excel 文件。
        若后续想处理其他格式（如 CSV），可修改实现。
        :param save_path: 若指定，则保存到该路径，否则保存到 self.vehicles_file
        """
        # 确定实际写入的文件路径
        target_file = save_path if save_path else self.vehicles_file

        if not self.vehicles:
            return

        # 只提取需要保存的字段，不包含 allocated_barrels
        data = [
            {
                "车牌号": v.license_plate,
                "司机": v.driver_name,
                "车辆类型": v.district,
                "所属区域": v.district,
                "最大收油桶数": v.max_barrels,
                "其他信息": v.other_info if v.other_info else ""
            }
            for v in self.vehicles
        ]

        df = pd.DataFrame(data)

        try:
            df.to_excel(target_file, index=False)
        except Exception as e:
            print(f"[错误] 写入Excel失败: {e}")

    def get_vehicles(self) -> List[Vehicle]:
        return self.vehicles

    def add_vehicle(self, vehicle: Vehicle) -> None:
        # 简单检查重复车牌
        if any(v.license_plate == vehicle.license_plate for v in self.vehicles):
            raise ValueError("车牌号已存在，请勿重复添加。")
        self.vehicles.append(vehicle)

    def remove_vehicle(self, license_plate: str) -> None:
        self.vehicles = [v for v in self.vehicles if v.license_plate != license_plate]

    def update_vehicle(self, old_license_plate: str, new_vehicle: Vehicle) -> None:
        for i, v in enumerate(self.vehicles):
            if v.license_plate == old_license_plate:
                self.vehicles[i] = new_vehicle
                return
        raise ValueError(f"未找到要更新的车牌号: {old_license_plate}")
