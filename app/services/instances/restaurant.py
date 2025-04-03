import requests
from typing import Dict, Any, List, Optional, Union
from app.services.instances.base import BaseInstance, BaseGroup
from app.models import RestaurantModel
from app.utils.hash import hash_text
from app.utils.logger import setup_logger
from app.utils.file_io import rp

# 设置日志
LOGGER = setup_logger("moco.log")

class Restaurant(BaseInstance):
    """
    餐厅实体类，处理餐厅模型的业务逻辑
    """
    def __init__(self, info: Dict[str, Any], model=RestaurantModel, conf=None):
        """
        初始化餐厅实体
        
        :param info: 餐厅信息字典
        :param model: 餐厅模型类，可选
        :param conf: 配置服务，可选
        """
        super().__init__(model)
        self.conf = conf
        
        # 确保必须的字段存在
        assert info.get('rest_chinese_name') is not None, "必须提供餐厅中文名称"
        
        if model:
            # 创建模型实例
            self.inst = model(**info)
        else:
            # 如果没有提供模型类，直接存储info
            self.inst = type('DynamicModel', (), info)
        
        self.status = 'pending'  # 初始状态为待处理
    
    def _generate_id_by_name(self) -> bool:
        """
        根据餐厅名称生成唯一ID
        
        :return: 是否生成成功
        """
        try:
            if not hasattr(self.inst, 'rest_id') or not self.inst.rest_id:
                # 使用餐厅中文名生成哈希ID
                name = self.inst.rest_chinese_name
                self.inst.rest_id = hash_text(name)[:16]  # 取哈希的前16位作为ID
                LOGGER.info(f"已为餐厅 '{name}' 生成ID: {self.inst.rest_id}")
            return True
        except Exception as e:
            LOGGER.error(f"生成餐厅ID失败: {e}")
            return False
    
    def _generate_english_name(self) -> bool:
        """
        生成餐厅英文名
        
        :return: 是否生成成功
        """
        try:
            # 检查是否已有英文名
            if not hasattr(self.inst, 'rest_english_name') or not self.inst.rest_english_name:
                # 这里应该调用翻译API或其他方法获取英文翻译
                # 由于我们没有实际的翻译API，这里只是简单示例
                chinese_name = self.inst.rest_chinese_name
                
                # 如果配置中有翻译API的keys，可以调用它们
                if self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'kimi_keys'):
                    # TODO: 实现调用大模型进行翻译的逻辑
                    # 暂时使用简单的转换（实际项目中应替换为真实翻译）
                    self.inst.rest_english_name = f"{chinese_name} Restaurant"
                else:
                    # 简单地添加"Restaurant"后缀作为示例
                    self.inst.rest_english_name = f"{chinese_name} Restaurant"
                
                LOGGER.info(f"已为餐厅 '{chinese_name}' 生成英文名: {self.inst.rest_english_name}")
            return True
        except Exception as e:
            LOGGER.error(f"生成餐厅英文名失败: {e}")
            return False
    
    def _generate_english_address(self) -> bool:
        """
        生成餐厅英文地址
        
        :return: 是否生成成功
        """
        try:
            # 检查是否已有英文地址
            if (not hasattr(self.inst, 'rest_english_address') or not self.inst.rest_english_address) and hasattr(self.inst, 'rest_chinese_address'):
                # 与英文名类似，这里应该调用翻译API
                chinese_address = self.inst.rest_chinese_address
                
                # 如果配置中有翻译API的keys，可以调用它们
                if self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'kimi_keys'):
                    # TODO: 实现调用大模型进行翻译的逻辑
                    # 暂时使用简单的转换（实际项目中应替换为真实翻译）
                    self.inst.rest_english_address = f"{chinese_address} (translated)"
                else:
                    # 简单地添加标记作为示例
                    self.inst.rest_english_address = f"{chinese_address} (translated)"
                
                LOGGER.info(f"已为餐厅生成英文地址: {self.inst.rest_english_address}")
            return True
        except Exception as e:
            LOGGER.error(f"生成餐厅英文地址失败: {e}")
            return False
    
    def _extract_district_and_street(self) -> bool:
        """
        从地址中提取区域和街道信息
        
        :return: 是否提取成功
        """
        try:
            # 检查是否已有区域和街道信息
            if (not hasattr(self.inst, 'rest_district') or not self.inst.rest_district or 
                not hasattr(self.inst, 'rest_street') or not self.inst.rest_street) and hasattr(self.inst, 'rest_chinese_address'):
                
                chinese_address = self.inst.rest_chinese_address
                
                # 实际项目中应该使用地址解析算法或API
                # 这里使用简单的示例逻辑
                if self.conf and hasattr(self.conf, 'STREETMAPS') and hasattr(self.inst, 'rest_city'):
                    city = self.inst.rest_city
                    streetmaps = getattr(self.conf.STREETMAPS, city.lower(), {})
                    
                    # 遍历区域和街道，查找匹配项
                    for district, streets in streetmaps.items():
                        if district in chinese_address:
                            self.inst.rest_district = district
                            
                            # 查找街道
                            for street in streets:
                                if street in chinese_address:
                                    self.inst.rest_street = street
                                    break
                            break
                
                # 如果未找到，使用默认值或保持为空
                if not hasattr(self.inst, 'rest_district') or not self.inst.rest_district:
                    self.inst.rest_district = "未知区域"
                
                if not hasattr(self.inst, 'rest_street') or not self.inst.rest_street:
                    self.inst.rest_street = "未知街道"
                
                LOGGER.info(f"已为餐厅提取区域和街道: {self.inst.rest_district}, {self.inst.rest_street}")
            return True
        except Exception as e:
            LOGGER.error(f"提取区域和街道失败: {e}")
            return False
    
    def _generate_contact_info(self) -> bool:
        """
        生成联系人信息
        
        :return: 是否生成成功
        """
        try:
            # 检查是否已有联系人信息
            if not hasattr(self.inst, 'rest_contact_person') or not self.inst.rest_contact_person:
                # 在实际项目中，这应该通过查询API获取
                # 这里使用示例值
                self.inst.rest_contact_person = f"{self.inst.rest_chinese_name}负责人"
                LOGGER.info(f"已为餐厅生成联系人: {self.inst.rest_contact_person}")
            
            if not hasattr(self.inst, 'rest_contact_phone') or not self.inst.rest_contact_phone:
                # 生成示例电话号码
                self.inst.rest_contact_phone = f"1388888{hash(self.inst.rest_chinese_name) % 10000:04d}"
                LOGGER.info(f"已为餐厅生成联系电话: {self.inst.rest_contact_phone}")
            
            return True
        except Exception as e:
            LOGGER.error(f"生成联系人信息失败: {e}")
            return False
    
    def _calculate_distance(self) -> bool:
        """
        计算餐厅与所属CP的距离
        
        :return: 是否计算成功
        """
        try:
            # 检查是否已有距离信息和必要的条件
            if (not hasattr(self.inst, 'rest_distance') or not self.inst.rest_distance) and hasattr(self.inst, 'rest_location') and hasattr(self.inst, 'rest_belonged_cp'):
                # 获取餐厅位置
                restaurant_location = self.inst.rest_location
                
                # 在实际项目中，应该查询CP的位置然后计算距离
                # 这里使用一个模拟值
                cp_id = self.inst.rest_belonged_cp
                
                # 使用哈希值来生成一个稳定但随机的距离
                distance_hash = hash(f"{restaurant_location}_{cp_id}")
                distance_km = 1 + abs(distance_hash % 20)  # 1-20公里范围内
                
                self.inst.rest_distance = distance_km
                LOGGER.info(f"已计算餐厅到CP的距离: {distance_km}公里")
            
            return True
        except Exception as e:
            LOGGER.error(f"计算餐厅距离失败: {e}")
            return False
    
    def generate(self) -> bool:
        """
        生成餐厅的所有缺失字段
        
        :return: 是否全部生成成功
        """
        success = True
        
        # 生成ID
        success &= self._generate_id_by_name()
        
        # 生成英文名和地址
        success &= self._generate_english_name()
        success &= self._generate_english_address()
        
        # 提取区域和街道
        success &= self._extract_district_and_street()
        
        # 生成联系信息
        success &= self._generate_contact_info()
        
        # 计算距离
        success &= self._calculate_distance()
        
        # 如果全部成功，更新状态为就绪
        if success:
            self.status = 'ready'
            LOGGER.info(f"餐厅 '{self.inst.rest_chinese_name}' 的所有字段已生成完成")
        
        return success
    
    def __str__(self) -> str:
        """
        返回餐厅的字符串表示
        
        :return: 字符串表示
        """
        if hasattr(self.inst, 'rest_chinese_name') and hasattr(self.inst, 'rest_id'):
            return f"Restaurant(id={self.inst.rest_id}, name={self.inst.rest_chinese_name}, status={self.status})"
        return f"Restaurant(未完成初始化, status={self.status})"


class RestaurantsGroup(BaseGroup):
    """
    餐厅组合类，用于管理多个餐厅实体
    """
    def __init__(self, restaurants: List[Restaurant] = None, group_type: str = None):
        """
        初始化餐厅组合
        
        :param restaurants: 餐厅列表
        :param group_type: 组合类型，如'city'、'cp'等
        """
        super().__init__(restaurants, group_type)
    
    def filter_by_district(self, district: str) -> 'RestaurantsGroup':
        """
        按区域筛选餐厅
        
        :param district: 区域名称
        :return: 筛选后的餐厅组合
        """
        return self.filter(lambda r: hasattr(r.inst, 'rest_district') and r.inst.rest_district == district)
    
    def filter_by_cp(self, cp_id: str) -> 'RestaurantsGroup':
        """
        按所属CP筛选餐厅
        
        :param cp_id: CP ID
        :return: 筛选后的餐厅组合
        """
        return self.filter(lambda r: hasattr(r.inst, 'rest_belonged_cp') and r.inst.rest_belonged_cp == cp_id)
    
    def filter_by_distance(self, max_distance: float) -> 'RestaurantsGroup':
        """
        按距离筛选餐厅
        
        :param max_distance: 最大距离（公里）
        :return: 筛选后的餐厅组合
        """
        return self.filter(lambda r: hasattr(r.inst, 'rest_distance') and r.inst.rest_distance <= max_distance)
    
    def get_by_id(self, rest_id: str) -> Optional[Restaurant]:
        """
        按ID获取餐厅
        
        :param rest_id: 餐厅ID
        :return: 餐厅实体或None
        """
        for restaurant in self.members:
            if hasattr(restaurant.inst, 'rest_id') and restaurant.inst.rest_id == rest_id:
                return restaurant
        return None
    
    def get_by_name(self, name: str, is_chinese: bool = True) -> Optional[Restaurant]:
        """
        按名称获取餐厅
        
        :param name: 餐厅名称
        :param is_chinese: 是否为中文名
        :return: 餐厅实体或None
        """
        attr = 'rest_chinese_name' if is_chinese else 'rest_english_name'
        for restaurant in self.members:
            if hasattr(restaurant.inst, attr) and getattr(restaurant.inst, attr) == name:
                return restaurant
        return None
    
    def __str__(self) -> str:
        """
        返回餐厅组合的字符串表示
        
        :return: 字符串表示
        """
        return f"RestaurantsGroup(数量={self.count()}, 类型={self.group_type})" 