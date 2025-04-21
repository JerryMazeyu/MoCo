import os
import json
import requests
import pandas as pd
from typing import Dict, Any, List, Optional, Union
import threading
import time
import sys 
import concurrent.futures
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from app.services.instances.restaurant import Restaurant, RestaurantsGroup
from app.utils.logger import setup_logger
from app.utils.file_io import rp
from app.config.config import CONF
from app.utils.query import robust_query
import re
import math
from app.utils.oss import oss_get_json_file
# 设置日志
LOGGER = setup_logger("moco.log")

class GetRestaurantService:
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
        self.n = 30 ## 获取页数
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
    
     ## 利用高德地图自动获取地区以及下一级地区经纬度
    
    def _gaode_get_lat_lng(self, token = None, address = None, subdistrict = 1) -> dict: # 默认查下一级
        parama = 'keywords={}&subdistrict={}&key={}'.format(address, subdistrict, token)
        get_area_url = 'https://restapi.amap.com/v3/config/district?'+parama
        res = requests.request('GET', url=get_area_url)
        jsonData = res.json()
        lon_lat_list = {}
        if jsonData['status'] == '1':
            center_district = jsonData['districts'][0]['center']
            area_name = jsonData['districts'][0]['name']
            lon_lat_list[area_name] = center_district
            if subdistrict == 1:
                if jsonData['districts'][0]['districts'] is not None:
                    for i in jsonData['districts'][0]['districts']:
                        area_name = i['name']
                        lon_lat_list[area_name] = i['center']
            elif subdistrict == 2:
                if jsonData['districts'][0]['districts'] is not None:
                    for i in jsonData['districts'][0]['districts']:
                        area_name = i['name']
                        lon_lat_list[area_name] = i['center']
                        if i['districts'] is not None:
                            for j in i['districts']:
                                area_name = j['name']
                                lon_lat_list[area_name] = j['center']
        else:
            print("{}查询失败".format(self.address))
        return lon_lat_list

    def _gaode_search(self, n = None, token = None, keywords = None, address = None, maptype = 1, radius = 50000) -> list[dict]:
        """
        从高德地图API获取餐厅信息
        
        :param n: 页码
        :param token: 高德地图token
        :param keywords: 搜索关键词
        :param address: 搜索地址
        :param maptype: 地图类型
        :param radius: 搜索半径
        :return: 餐厅信息列表
        """
        self.gaode_type = '餐饮'
        self.gaode_keywords = keywords
        self.gaode_address = address
        self.gaode_maptype = maptype
        self.gaode_n = n
        self.gaode_token = token
        self.gaode_radius = radius
        loc = re.match("@?[-+]?\d+(\.\d+)?,\d+(\.\d+)?", self.gaode_address)
        if loc:
            gps = address.split(",")
            p1 = float(gps[0])
            p2 = float(gps[1])
            if p1 > p2:
                # 百度是小的（纬度）在前
                if maptype != 1:
                    self.address = gps[1] + ',' + gps[0]
                else:
                    self.address = gps[0] + ',' + gps[1]
            else:
                # 百度是小的（纬度）在前
                if maptype != 1:
                    self.address = gps[0] + ',' + gps[1]
                else:
                    self.address = gps[1] + ',' + gps[0]
        # 通过默认的搜索获取餐厅信息
        def create_gaode_url():
            urls = []
            for i in range(1, self.n + 1):  # page是当前页码，高德是从1开始， offset是每页多少条数据，默认20条

                url = 'https://restapi.amap.com/v3/place/text?key={}&&keywords={}' \
                    '&types={}&city={}&citylimit=true&output={}&offset=20&page={}' \
                    '&extensions=base&show_fields=business'.format(self.gaode_token, self.gaode_keywords, self.gaode_type,
                                                                    self.gaode_address,
                                                                    'JSON', i)
                urls.append(url)
            return urls

        # 通过坐标的搜索获附近取餐厅信息
        def create_gaode_around_url():
            urls = []
            for i in range(1, self.n + 1):  
                # page是当前页码，高德是从1开始， offset是每页多少条数据，默认20条，默认周边5万米

                url = 'https://restapi.amap.com/v3/place/around?key={}' \
                    '&radius={}&keywords={}&types={}&location={}&offset=20&page={' \
                    '}&extensions=base&show_fields=business'.format(
                    self.gaode_token, self.gaode_radius,self.gaode_keywords, self.gaode_type, self.gaode_address, i)
                urls.append(url)
            return urls
        
        ## 获取高德餐厅信息
        def get_gaode_restaurant(urls):
            j = 0
            datalist = []
            for url in urls:
                # print(url)
                res = requests.request('GET', url=url)
                time.sleep(1)
                res = json.loads(res.text)
                l = res.get('pois')
                if l is not None and len(l)>0:
                    for i in l:
                        j += 1
                        dict1 = {
                            'rest_chinese_name': i.get('name') if i.get('name') is not None else '',
                            'rest_chinese_address': i.get('address') if i.get('address') is not None else '',
                            'rest_contact_phone': i.get('tel') if i.get('tel') is not None else '',
                            'rest_location': i.get('location') if i.get('location') is not None else '',
                            'adname': i.get('adname') if i.get('adname') is not None else '',
                            'rest_type_gaode': i.get('type') if i.get('type') is not None else '',
                            'distance': i.get('distance') if i.get('distance') is not None else '',
                            'rest_city': i.get('cityname') if i.get('cityname') is not None else '',
                        }
                        # 注意：不再在这里设置rest_type字段，而是在run方法中根据use_llm参数决定是否设置
                        datalist.append(dict1)
                    if len(l)<20: ## 当最后一次小于20的话说明最后一页，退出
                        break
                else:
                    break
            return datalist
        
        # 如果是输入的坐标，直接匹配周边搜索
        if loc:
            LOGGER.info(f"使用周边搜索，地址: {self.gaode_address}")
            urls = create_gaode_around_url()
            print("<<<>>>", urls[0])
        else:
            LOGGER.info(f"使用关键词搜索，关键词: {self.gaode_keywords}")
            urls = create_gaode_url()
        restaurantList = get_gaode_restaurant(urls)
        ## 写入excel
        # fileName = types + '-' + self.address + '-' + self.keywords + '.xls'
        # if self.maptype == 3:
        #     self.write_to_excel_google(restaurantList, self.filename)
        # else:
        #     self.write_to_excel(restaurantList, self.filename)
        ## 返回datalist
        return restaurantList          
       

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

    def load_keywords(self):
        """从配置加载关键词列表"""
        self.keywords_list=[]
        keywords = self.conf.get("BUSINESS.RESTAURANT.关键词", default=[])
        for keyword in keywords:
            self.keywords_list.append(keyword)
    
    def load_blocked_words(self):
        """从配置加载屏蔽词列表"""
        self.blocked_list=[]
        blocked_words = self.conf.get("BUSINESS.RESTAURANT.屏蔽词", default=[])
        for word in blocked_words:
            self.blocked_list.append(word)
        
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

    def _haversine(self,coord1, coord2):
        """计算两个经纬度之间的距离（单位：公里）"""
        R = 6371  # 地球半径，单位为公里
        
        # 处理第一个坐标
        try:
            if isinstance(coord1, tuple) and len(coord1) == 2:
                lat1, lon1 = coord1
            elif isinstance(coord1, list) and len(coord1) == 2:
                lat1, lon1 = coord1
            elif isinstance(coord1, str):
                lat1, lon1 = map(float, coord1.split(','))
            else:
                print(f"无效的坐标1格式: {coord1}")
                return 0
        except Exception as e:
            print(f"处理坐标1出错: {e}, 坐标值: {coord1}")
            return 0
        
        # 处理第二个坐标
        try:
            if isinstance(coord2, tuple) and len(coord2) == 2:
                lat2, lon2 = coord2
            elif isinstance(coord2, list) and len(coord2) == 2:
                lat2, lon2 = coord2
            elif isinstance(coord2, str):
                # 确保是字符串且包含逗号
                lat2, lon2 = map(float, coord2.split(','))
            else:
                print(f"无效的坐标2格式: {coord2}")
                return 0
        except Exception as e:
            print(f"处理坐标2出错: {e}, 坐标值: {coord2}")
            return 0

        # 确保所有值都是数值类型
        try:
            lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
            
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)

            a = (math.sin(dlat / 2) ** 2 +
                math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
            c = 2 * math.asin(math.sqrt(a))
            return R * c  # 返回距离，单位为公里
        except Exception as e:
            print(f"计算距离出错: {e}, 坐标值: {lat1},{lon1} 和 {lat2},{lon2}")
            return 0
        
    def _info_to_restaurant(self, model_class=None, cp_id=None) -> None:
        """
        将餐厅信息转换为餐厅实体
        
        :param model_class: 餐厅模型类，可选
        :param cp_id: 餐厅所属CP ID，可选
        """
        self.restaurants = []
        ## 加入工厂的地理位置，方便计算距离
        if cp_id:   
            cp_location_file = f"CPs/{cp_id}/{cp_id}.json"  # 直接使用OSS路径格式
            cp_location_info = oss_get_json_file(cp_location_file)
            cp_location = cp_location_info['cp_location']
            LOGGER.info(f"已获取CP {cp_id} 经纬度: {cp_location}")
        else:
            cp_location = None  
        
        for data in self.info:
            # 如果提供了CP ID，添加到数据中
            if cp_id:
                data['rest_belonged_cp'] = cp_id
            
            # 创建餐厅实体
            restaurant = Restaurant(data, model=model_class, conf=self.conf,cp_location = cp_location)
            
            # 添加到餐厅列表
            self.restaurants.append(restaurant)
        
        LOGGER.info(f"已将 {len(self.info)} 条餐厅信息转换为餐厅实体")
    

    def gen_info(self, restaurants_group: RestaurantsGroup, num_workers: int = 4) -> RestaurantsGroup:
        """
        并行生成餐厅信息
        
        :param restaurants_group: 餐厅组合
        :param num_workers: 并行工作线程数
        :return: 处理后的餐厅组合
        """
        LOGGER.info(f"开始并行生成餐厅信息，使用 {num_workers} 个工作线程")
        
        def process_restaurant(restaurant):
            try:
                restaurant.generate()
                return restaurant
            except Exception as e:
                LOGGER.error(f"生成餐厅 {restaurant.inst.rest_chinese_name if hasattr(restaurant.inst, 'rest_chinese_name') else '未知'} 信息时出错: {e}")
                # 返回原始餐厅对象，不中断处理流程
                return restaurant

        # 获取餐厅列表
        restaurants = restaurants_group.members
        
        if not restaurants:
            LOGGER.warning("餐厅列表为空，无需生成信息")
            return restaurants_group
        

        try:
            # 使用线程池并行处理
            processed_restaurants = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                # 使用list收集future对象，确保所有任务都被处理
                future_to_restaurant = {executor.submit(process_restaurant, restaurant): restaurant for restaurant in restaurants}
                for future in concurrent.futures.as_completed(future_to_restaurant):
                    try:
                        result = future.result()
                        processed_restaurants.append(result)
                    except Exception as e:
                        restaurant = future_to_restaurant[future]
                        LOGGER.error(f"处理餐厅时发生未捕获异常: {e}，餐厅: {restaurant.inst.rest_chinese_name if hasattr(restaurant.inst, 'rest_chinese_name') else '未知'}")
                        # 将原始餐厅对象添加到结果中，确保不丢失数据
                        processed_restaurants.append(restaurant)
            
            # 创建新的餐厅组合并返回
            result_group = RestaurantsGroup(processed_restaurants, group_type=restaurants_group.group_type)
            LOGGER.info(f"餐厅信息生成完成，共处理 {len(processed_restaurants)} 个餐厅")
            
            return result_group
        except Exception as e:
            LOGGER.error(f"生成餐厅信息过程中发生严重错误: {e}")
            # 出现错误时返回原始组合，确保不中断程序执行
            return restaurants_group

    
    def get_restaurants_group(self, group_type='all') -> RestaurantsGroup:
        """
        获取餐厅组合
        
        :param group_type: 组合类型
        :return: 餐厅组合
        """
        return RestaurantsGroup(self.restaurants, group_type=group_type)
    
    def run(self, cities=None, cp_id=None, model_class=None, file_path=None, use_api=True, if_gen_info=True, use_llm=True) -> RestaurantsGroup:

        """
        执行获取餐厅信息的完整流程
        
        :param cities: 城市列表或城市名
        :param cp_id: 餐厅所属CP ID
        :param model_class: 餐厅模型类
        :param file_path: 餐厅信息文件路径
        :param use_api: 是否使用API获取餐厅信息
        :param if_gen_info: 是否生成餐厅信息，如翻译和类型分析等
        :param use_llm: 是否使用大模型生成餐厅类型，默认为True
        :return: 餐厅组合
        """
        # 如果提供了文件路径，从文件加载
        if file_path:
            self._load_from_file(file_path)
        
        # 加载关键词和屏蔽词
        self.load_keywords()
        self.load_blocked_words()


        # 如果使用API获取，并且提供了城市
        if use_api and cities:
            # 如果是字符串，转换为列表
            if isinstance(cities, str):
                cities = [cities]
            
            # 遍历城市进行搜索
            for city in cities:
                LOGGER.info(f"开始搜索城市: {city}")
                def _gaode_get_lat_lont_func(key):
                    return self._gaode_get_lat_lng(token=key, address=city)
                city_list = robust_query(_gaode_get_lat_lont_func, self.conf.KEYS.gaode_keys)
                # 使用高德地图API
                for key_words in self.keywords_list:
                    LOGGER.info(f"开始搜索关键词: {key_words}")
                    for city_name, city_lat_lng in city_list.items():
                        try:
                            strict_mode = self.conf.runtime.STRICT_MODE
                        except:
                            strict_mode = False
                        try:
                            radius = int(self.conf.runtime.SEARCH_RADIUS * 1000)
                        except:
                            radius = 50000

                        def _gaode_search_func(key):
                            return self._gaode_search(n = self.n, token = key, keywords = key_words, address = city_lat_lng, maptype = 1, radius = radius)
                        restaurant_list = robust_query(_gaode_search_func, self.conf.KEYS.gaode_keys)
                        
                        if strict_mode:
                            restaurant_list_accurate = [restaurant for restaurant in restaurant_list if restaurant['adname'] == city_name]
                            LOGGER.info(f"使用严格模式搜索，关键词: {key_words}, 城市: {city_name}, 周边结果：{len(restaurant_list)} 条， 精确结果：{len(restaurant_list_accurate)} 条")

                        # 根据use_llm设置决定是否在这里设置rest_type
                        if not use_llm:
                            for restaurant in restaurant_list:
                                restaurant['rest_type'] = key_words
                        else:
                            # 如果使用大模型，则不设置rest_type，让_generate_type方法处理
                            for restaurant in restaurant_list:
                                if 'rest_type' in restaurant:
                                    del restaurant['rest_type']
                        
                        ## 将获得的餐厅信息添加到info中
                        self.info.extend(restaurant_list)
                        LOGGER.info(f"高德地图API搜索{city_name}结果: {len(restaurant_list)} 条")

        # 屏蔽词
        LOGGER.info(f"开始过滤屏蔽词")
        self.info = [restaurant for restaurant in self.info if not any(word in restaurant['rest_chinese_name'] for word in self.blocked_list)]
        LOGGER.info(f"过滤屏蔽词后剩余 {len(self.info)} 条餐厅信息")
        # 去重
        self._dedup()
        
        # 转换为餐厅实体
        self._info_to_restaurant(model_class=model_class, cp_id=cp_id)
        
        # 获取餐厅组合
        restaurant_group = self.get_restaurants_group()
        
        # 如果需要生成信息，则调用gen_info方法
        if if_gen_info:
            LOGGER.info("开始生成餐厅信息")
            restaurant_group = self.gen_info(restaurant_group)
        else:
            LOGGER.info("跳过生成餐厅信息")
        
        # 返回餐厅组合
        return restaurant_group
    
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
        

if __name__ == "__main__":
    from app.services.instances.restaurant import RestaurantModel
    service = GetRestaurantService()
    service.run(cities="广州", cp_id="de441ba852", model_class=RestaurantModel, file_path=None, use_api=True)
    service.save_results(folder_path=None, filename_prefix='restaurants')

