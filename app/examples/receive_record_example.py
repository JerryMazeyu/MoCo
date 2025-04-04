"""
收油记录示例脚本
"""
import datetime
import random
from typing import Dict, List

from app.services.instances.restaurant import Restaurant
from app.services.instances.vehicle import Vehicle
from app.services.instances.receive_record import ReceiveRecord, ReceiveRecordsGroup
from app.services.functions.get_receive_record_service import GetReceiveRecordService


def create_sample_data():
    """创建样例数据"""
    # 创建示例餐厅
    restaurants = []
    for i in range(1, 6):
        restaurant_info = {
            "restaurant_id": f"REST-{i:04d}",
            "name": f"测试餐厅 {i}",
            "address": f"测试地址 {i}",
            "cp_id": f"CP-{random.randint(1, 3):02d}",  # 随机分配给3个CP
            "phone": f"1388888{i:04d}"
        }
        restaurants.append(Restaurant(restaurant_info))
    
    # 创建示例车辆
    vehicles = []
    for i in range(1, 4):
        vehicle_info = {
            "plate_number": f"京A-{1000+i}",
            "driver_name": f"司机{i}",
            "driver_phone": f"1399999{i:04d}",
            "capacity": random.uniform(5.0, 15.0),
            "type": "oil_truck"
        }
        vehicles.append(Vehicle(vehicle_info))
    
    return restaurants, vehicles


def main():
    """主函数"""
    print("创建样例数据...")
    restaurants, vehicles = create_sample_data()
    
    # 初始化收油记录服务
    record_service = GetReceiveRecordService()
    
    # 创建今天的几条记录
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    print(f"\n创建今天 ({today}) 的收油记录:")
    
    for i in range(5):
        # 随机选择餐厅和车辆
        restaurant = random.choice(restaurants)
        vehicle = random.choice(vehicles)
        
        # 创建记录信息
        record_info = {
            "restaurant_id": restaurant.info["restaurant_id"],
            "cp_id": restaurant.info["cp_id"],
            "vehicle_id": vehicle.info.get("vehicle_id", ""),
            "driver_name": vehicle.info["driver_name"],
            "amount": round(random.uniform(20.0, 100.0), 2),
            "date": today
        }
        
        # 添加记录并确认
        record = record_service.add_record(record_info)
        if record:
            record.confirm_record()
            print(f"添加记录: 餐厅={restaurant.info['name']}, "
                  f"车辆={vehicle.info['plate_number']}, "
                  f"数量={record.info['amount']}升")
    
    # 获取今天的记录组并打印汇总
    today_group = record_service.get_by_date(today)
    daily_report = today_group.get_daily_report()
    
    print("\n今日收油汇总:")
    print(f"总收油量: {daily_report['total_amount']}升")
    print(f"记录数量: {daily_report['record_count']}条")
    
    print("\n按CP汇总:")
    for cp_id, amount in daily_report['cp_summary'].items():
        print(f"CP {cp_id}: {amount}升")
    
    # 创建昨天的几条记录
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"\n创建昨天 ({yesterday}) 的收油记录:")
    
    for i in range(3):
        restaurant = random.choice(restaurants)
        vehicle = random.choice(vehicles)
        
        record_info = {
            "restaurant_id": restaurant.info["restaurant_id"],
            "cp_id": restaurant.info["cp_id"],
            "vehicle_id": vehicle.info.get("vehicle_id", ""),
            "driver_name": vehicle.info["driver_name"],
            "amount": round(random.uniform(20.0, 100.0), 2),
            "date": yesterday
        }
        
        record = record_service.add_record(record_info)
        if record:
            record.confirm_record()
            print(f"添加记录: 餐厅={restaurant.info['name']}, "
                  f"车辆={vehicle.info['plate_number']}, "
                  f"数量={record.info['amount']}升")
    
    # 获取餐厅的收油记录
    restaurant = restaurants[0]
    print(f"\n获取餐厅 '{restaurant.info['name']}' 的收油记录:")
    restaurant_records = record_service.get_restaurant_records(restaurant.info["restaurant_id"])
    
    if restaurant_records:
        for record in restaurant_records:
            print(f"日期: {record.info['date']}, 数量: {record.info['amount']}升")
    else:
        print("没有找到记录")
    
    # 获取CP的收油记录
    cp_id = "CP-01"
    print(f"\n获取CP '{cp_id}' 的收油记录:")
    cp_records = record_service.get_cp_records(cp_id)
    
    if cp_records:
        total_amount = sum(record.info['amount'] for record in cp_records)
        print(f"记录数量: {len(cp_records)}条")
        print(f"总收油量: {total_amount}升")
    else:
        print("没有找到记录")
    
    # 生成当月报表
    now = datetime.datetime.now()
    print(f"\n{now.year}年{now.month}月收油报表:")
    monthly_report = record_service.get_monthly_report(now.year, now.month)
    
    print(f"总收油量: {monthly_report['total_amount']}升")
    print(f"总记录数: {monthly_report['total_records']}条")
    
    print("\n按CP汇总:")
    for cp_id, amount in monthly_report['cp_summary'].items():
        print(f"CP {cp_id}: {amount}升")


if __name__ == "__main__":
    main() 