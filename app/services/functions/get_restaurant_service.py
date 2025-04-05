import os
import json
import requests
import pandas as pd
from typing import Dict, Any, List, Optional, Union
import threading
import time
from app.services.instances.restaurant import Restaurant, RestaurantsGroup
from app.utils.logger import setup_logger
from app.utils.file_io import rp
from app.config.config import CONF

# 设置日志
LOGGER = setup_logger("moco.log")

class GetRestaurantsService:
    """
    餐厅信息获取服务，用于从各种API中获取餐厅信息
    """
    def __init__(self, conf=CONF, benchmark_path=None):
        """
        初始化餐厅获取服务
        
        :param conf: 配置服务实例
        :param benchmark_path: 基准数据文件路径，可选
        """
        self.conf = conf  # 配置服务
        self.info = []  # 存储获取到的餐厅信息
        self.restaurants = []  # 最终处理后的餐厅列表
        self.backends = ['gaode', 'baidu', 'serp', 'tripadvisor']  # 支持的后端
        
        # 如果提供了基准数据，则加载
        self.benchmark = []
        if benchmark_path:
            self._load_benchmark_from_path(benchmark_path)
    
    def _load_benchmark_from_path(self, path):
        """
        从文件加载基准数据
        
        :param path: 文件路径
        """
        try:
            file_ext = os.path.splitext(path)[1].lower()
            if file_ext == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    self.benchmark = json.load(f)
                LOGGER.info(f"已从JSON文件加载基准数据: {path}, 共 {len(self.benchmark)} 条")
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(path)
                self.benchmark = df.to_dict('records')
                LOGGER.info(f"已从Excel文件加载基准数据: {path}, 共 {len(self.benchmark)} 条")
            elif file_ext == '.csv':
                df = pd.read_csv(path)
                self.benchmark = df.to_dict('records')
                LOGGER.info(f"已从CSV文件加载基准数据: {path}, 共 {len(self.benchmark)} 条")
            else:
                LOGGER.error(f"不支持的文件类型: {file_ext}")
        except Exception as e:
            LOGGER.error(f"加载基准数据失败: {e}")
    
    def _load_from_file(self, path):
        """
        从文件加载餐厅信息
        
        :param path: 文件路径
        """
        try:
            file_ext = os.path.splitext(path)[1].lower()
            data = []
            
            if file_ext == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif file_ext in ['.xlsx', '.xls']:
                df = pd.read_excel(path)
                data = df.to_dict('records')
            elif file_ext == '.csv':
                df = pd.read_csv(path)
                data = df.to_dict('records')
            else:
                LOGGER.error(f"不支持的文件类型: {file_ext}")
                return
            
            # 添加来源标记
            for item in data:
                item['source'] = 'file'
            
            self.info.extend(data)
            LOGGER.info(f"已从文件加载餐厅信息: {path}, 共 {len(data)} 条")
        except Exception as e:
            LOGGER.error(f"从文件加载餐厅信息失败: {e}")
    
    def _gaode_search(self) -> List[Dict]:
        """
        从高德地图API获取餐厅信息
        
        :param keywords: 搜索关键词，默认为配置中的关键词
        :param city: 城市名称
        :param radius: 搜索半径（米）
        :return: 是否获取成功
        """
        # CONF.runtime
        # search rests
        # 异常处理
        pass
        # try:
        #     # 检查是否有API密钥
        #     if not self.conf or not hasattr(self.conf, 'KEYS') or not hasattr(self.conf.KEYS, 'gaode_keys') or not self.conf.KEYS.gaode_keys:
        #         LOGGER.error("未配置高德地图API密钥")
        #         return False
            
        #     # 获取API密钥
        #     api_key = self.conf.KEYS.gaode_keys[0]
            
        #     # 获取搜索关键词
        #     if not keywords:
        #         if hasattr(self.conf, 'OTHER') and hasattr(self.conf.OTHER, 'Tab5') and hasattr(self.conf.OTHER.Tab5, '关键词'):
        #             keywords = self.conf.OTHER.Tab5.关键词
        #         else:
        #             keywords = ['餐厅', '餐馆', '饭店', '小吃', '美食']
            
        #     # 如果是字符串，转换为列表
        #     if isinstance(keywords, str):
        #         keywords = [keywords]
            
        #     # 存储结果
        #     results = []
            
        #     # 遍历关键词进行搜索
        #     for keyword in keywords:
        #         # 构建API请求URL
        #         url = f"https://restapi.amap.com/v3/place/text?key={api_key}&keywords={keyword}&types=餐饮&city={city}&extensions=all"
                
        #         # 发送请求
        #         response = requests.get(url)
        #         data = response.json()
                
        #         # 检查请求是否成功
        #         if data.get('status') == '1' and 'pois' in data:
        #             for poi in data['pois']:
        #                 # 转换为餐厅信息格式
        #                 restaurant_info = {
        #                     'rest_chinese_name': poi.get('name', ''),
        #                     'rest_city': city or poi.get('cityname', ''),
        #                     'rest_province': poi.get('pname', ''),
        #                     'rest_chinese_address': poi.get('address', ''),
        #                     'rest_location': poi.get('location', ''),  # 格式为 "经度,纬度"
        #                     'rest_type': poi.get('type', ''),
        #                     'source': 'gaode'
        #                 }
                        
        #                 # 如果有电话信息，添加
        #                 if 'tel' in poi:
        #                     restaurant_info['rest_contact_phone'] = poi['tel']
                        
        #                 results.append(restaurant_info)
                    
        #             LOGGER.info(f"高德地图API搜索 '{keyword}' 返回 {len(data['pois'])} 条结果")
        #         else:
        #             LOGGER.warning(f"高德地图API搜索 '{keyword}' 失败: {data.get('info', '')}")
                
        #         # 避免请求过快被限制
        #         time.sleep(0.5)
            
        #     # 将结果添加到信息列表中
        #     self.info.extend(results)
        #     LOGGER.info(f"高德地图API共获取 {len(results)} 条餐厅信息")
        #     return True
        # except Exception as e:
        #     LOGGER.error(f"从高德地图API获取餐厅信息失败: {e}")
        #     return False
    
    def _baidu_search(self, keywords=None, city=None, radius=None) -> List[Dict]:
        """
        从百度地图API获取餐厅信息
        
        :param keywords: 搜索关键词，默认为配置中的关键词
        :param city: 城市名称
        :param radius: 搜索半径（米）
        :return: 是否获取成功
        """
        LOGGER.info("Serp API搜索功能尚未实现")
        return False
    
    def _serp_search(self, keywords=None, city=None) -> List[Dict]:
        """
        从Serp API获取餐厅信息
        
        :param keywords: 搜索关键词，默认为配置中的关键词
        :param city: 城市名称
        :return: 是否获取成功
        """
        # 这里是示例实现，真实情况下需要根据实际API调整
        LOGGER.info("Serp API搜索功能尚未实现")
        return False
    
    def _tripadvisor_search(self, keywords=None, city=None) -> List[Dict]:
        """
        从TripAdvisor API获取餐厅信息
        
        :param keywords: 搜索关键词，默认为配置中的关键词
        :param city: 城市名称
        :return: 是否获取成功
        """
        # 这里是示例实现，真实情况下需要根据实际API调整
        LOGGER.info("TripAdvisor API搜索功能尚未实现")
        return False
    
    def _dedup(self) -> None:
        """
        对获取到的餐厅信息进行去重
        """
        # 创建一个唯一标识符集合
        unique_identifiers = set()
        deduped_info = []
        
        for item in self.info:
            # 创建唯一标识符（使用餐厅名称和地址组合）
            name = item.get('rest_chinese_name', '')
            address = item.get('rest_chinese_address', '')
            identifier = f"{name}|{address}"
            
            # 如果标识符不在集合中，添加到去重结果
            if identifier not in unique_identifiers:
                unique_identifiers.add(identifier)
                deduped_info.append(item)
        
        # 更新信息列表
        count_before = len(self.info)
        self.info = deduped_info
        count_after = len(self.info)
        
        LOGGER.info(f"去重前餐厅信息: {count_before}条，去重后: {count_after}条，去除了 {count_before - count_after} 条重复信息")
    
    def _info_to_restaurant(self, model_class=None, cp_id=None) -> None:
        """
        将餐厅信息转换为餐厅实体
        
        :param model_class: 餐厅模型类，可选
        :param cp_id: 餐厅所属CP ID，可选
        """
        self.restaurants = []
        
        for data in self.info:
            # 如果提供了CP ID，添加到数据中
            if cp_id:
                data['rest_belonged_cp'] = cp_id
            
            # 创建餐厅实体
            restaurant = Restaurant(data, model=model_class, conf=self.conf)
            
            # 生成缺失字段
            restaurant.generate()
            
            # 添加到餐厅列表
            self.restaurants.append(restaurant)
        
        LOGGER.info(f"已将 {len(self.info)} 条餐厅信息转换为餐厅实体")
    
    def get_restaurants_group(self, group_type='all') -> RestaurantsGroup:
        """
        获取餐厅组合
        
        :param group_type: 组合类型
        :return: 餐厅组合
        """
        return RestaurantsGroup(self.restaurants, group_type=group_type)
    
    def run(self, cities=None, keywords=None, cp_id=None, model_class=None, file_path=None, use_api=True) -> RestaurantsGroup:
        """
        执行获取餐厅信息的完整流程
        
        :param cities: 城市列表或城市名
        :param keywords: 搜索关键词
        :param cp_id: 餐厅所属CP ID
        :param model_class: 餐厅模型类
        :param file_path: 餐厅信息文件路径
        :param use_api: 是否使用API获取餐厅信息
        :return: 餐厅组合
        """
        # 如果提供了文件路径，从文件加载
        if file_path:
            self._load_from_file(file_path)
        
        # 如果使用API获取，并且提供了城市
        if use_api and cities:
            # 如果是字符串，转换为列表
            if isinstance(cities, str):
                cities = [cities]
            
            # 遍历城市进行搜索
            for city in cities:
                LOGGER.info(f"开始搜索城市: {city}")
                
                # 使用高德地图API
                self._gaode_search(keywords=keywords, city=city)
                
                # 使用百度地图API
                self._baidu_search(keywords=keywords, city=city)
                
                # 这里可以添加其他API的搜索
                # self._serp_search(keywords=keywords, city=city)
                # self._tripadvisor_search(keywords=keywords, city=city)
        
        # 去重
        self._dedup()
        
        # 转换为餐厅实体
        self._info_to_restaurant(model_class=model_class, cp_id=cp_id)
        
        # 返回餐厅组合
        return self.get_restaurants_group()
    
    def save_results(self, folder_path=None, filename_prefix='restaurants'):
        """
        保存获取到的餐厅信息
        
        :param folder_path: 保存文件夹路径，默认为assets
        :param filename_prefix: 文件名前缀
        :return: 是否保存成功
        """
        try:
            # 如果没有指定文件夹，使用默认的assets文件夹
            if not folder_path:
                folder_path = rp("", folder="assets")
            
            # 确保文件夹存在
            os.makedirs(folder_path, exist_ok=True)
            
            # 获取当前时间戳
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            # 保存原始信息为JSON
            json_path = os.path.join(folder_path, f"{filename_prefix}_raw_{timestamp}.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.info, f, ensure_ascii=False, indent=2)
            LOGGER.info(f"已将原始餐厅信息保存为JSON: {json_path}")
            
            # 保存餐厅实体为Excel
            if self.restaurants:
                group = self.get_restaurants_group()
                excel_path = os.path.join(folder_path, f"{filename_prefix}_{timestamp}.xlsx")
                group.save_to_excel(excel_path)
                LOGGER.info(f"已将餐厅实体保存为Excel: {excel_path}")
            
            return True
        except Exception as e:
            LOGGER.error(f"保存餐厅信息失败: {e}")
            return False 