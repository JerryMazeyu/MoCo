import os
import pandas as pd
from typing import List, Optional
from pydantic import ValidationError
from app.models.vehicle_model import Vehicle


class VehicleService:
    def __init__(self, config_file: str = "config/vehicle.xlsx"):
        self.config_file = config_file
        self.vehicles: List[Vehicle] = []
        self.load_from_local()

    def load_from_local(self) -> None:
        """
        尝试从 self.config_file 加载车辆信息；若文件不存在则保持空列表。
        """
        if not os.path.exists(self.config_file):
            self.vehicles = []
            return

        try:
            df = pd.read_excel(self.config_file)
            self.vehicles = []
            for _, row in df.iterrows():
                try:
                    v = Vehicle(
                        license_plate=row["license_plate"],
                        driver_name=row["driver_name"],
                        district=row["district"],
                        max_barrels=int(row["max_barrels"]),
                        allocated_barrels=int(row["allocated_barrels"]),
                        other_info=row.get("other_info", None)
                    )
                    self.vehicles.append(v)
                except ValidationError as ve:
                    print(f"跳过无效记录：{ve}")
        except Exception as e:
            print(f"加载本地文件失败：{e}")
            self.vehicles = []

    def save_to_local(self) -> None:
        """
        将 self.vehicles 写入到 self.config_file
        """
        data = [v.dict() for v in self.vehicles]
        df = pd.DataFrame(data)
        df.to_excel(self.config_file, index=False)

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

    def import_from_excel(self, file_path: str):
        """
        从给定的Excel文件批量导入车辆，追加到当前列表并保存。
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        df = pd.read_excel(file_path)
        for _, row in df.iterrows():
            try:
                vehicle = Vehicle(
                    license_plate=row["license_plate"],
                    driver_name=row["driver_name"],
                    district=row["district"],
                    max_barrels=int(row["max_barrels"]),
                    allocated_barrels=int(row["allocated_barrels"]),
                    other_info=row.get("other_info", None)
                )
                # 这里可以做去重或其他校验
                self.vehicles.append(vehicle)
            except ValidationError as ve:
                print(f"跳过无效记录: {ve}")

        self.save_to_local()
