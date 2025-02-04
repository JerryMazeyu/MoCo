from app.services.vehicle_service import VehicleService
from app.models.vehicle_model import Vehicle

vehicle_service = None

def flow2_init_service(config_file: str = "config/vehicle.xlsx"):
    """
    初始化 / 重置车辆服务 (可在程序启动时或重新加载时调用)
    """
    global vehicle_service
    vehicle_service = VehicleService(config_file)

def flow2_get_vehicles():
    """
    获取当前全部车辆列表
    """
    global vehicle_service
    return vehicle_service.get_vehicles()

def flow2_add_vehicle(vehicle: Vehicle):
    """
    新增一辆车
    """
    global vehicle_service
    vehicle_service.add_vehicle(vehicle)
    vehicle_service.save_to_local()

def flow2_remove_vehicle(license_plate: str):
    """
    删除指定车牌号的车辆
    """
    global vehicle_service
    vehicle_service.remove_vehicle(license_plate)
    vehicle_service.save_to_local()

def flow2_update_vehicle(old_license_plate: str, new_vehicle: Vehicle):
    """
    更新指定车牌号的车辆信息
    """
    global vehicle_service
    vehicle_service.update_vehicle(old_license_plate, new_vehicle)
    vehicle_service.save_to_local()

def flow2_import_from_excel(file_path: str):
    """
    从给定的Excel文件中批量导入车辆
    """
    global vehicle_service
    vehicle_service.import_from_excel(file_path)
