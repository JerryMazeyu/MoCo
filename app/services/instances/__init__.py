"""
实体实例子模块，用于处理模型的业务逻辑
"""

from app.services.instances.base import BaseInstance, BaseGroup
from app.services.instances.restaurant import Restaurant, RestaurantsGroup

__all__ = [
    'BaseInstance', 
    'BaseGroup',
    'Restaurant',
    'RestaurantsGroup'
] 