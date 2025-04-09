"""
服务功能子模块，用于提供各类服务函数
"""

from app.services.functions.get_restaurant_service import GetRestaurantService
from app.services.functions.get_receive_record_service import GetReceiveRecordService

__all__ = [
    'GetRestaurantService',
    'GetReceiveRecordService'
] 