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
import logging
import queue
import traceback
from app.utils.oss import oss_get_json_file
import gc
try:
    import psutil
except ImportError:
    pass  # psutil可能不存在，在使用前会检查
# 设置日志
LOGGER = setup_logger("moco.log")

class GetRestaurantService:
    """
    餐厅信息获取服务，用于从各种API中获取餐厅信息
    """
    def __init__(self, conf=CONF, benchmark_path=None, name_similarity_threshold=0.6, 
                 address_similarity_threshold=0.6, distance_threshold=1000):
        """
        初始化餐厅获取服务
        
        :param conf: 配置服务实例
        :param benchmark_path: 基准数据文件路径，可选
        :param name_similarity_threshold: 名称相似度阈值，默认0.6
        :param address_similarity_threshold: 地址相似度阈值，默认0.6
        :param distance_threshold: 距离阈值（米），默认1000
        """
        self.conf = conf  # 配置服务
        self.info = []  # 存储获取到的餐厅信息
        self.n = 30 ## 获取页数
        self.restaurants = []  # 最终处理后的餐厅列表
        self.backends = ['gaode', 'baidu', 'serp', 'tripadvisor']  # 支持的后端
        
        # 相似度和距离阈值
        self.name_similarity_threshold = name_similarity_threshold
        self.address_similarity_threshold = address_similarity_threshold
        self.distance_threshold = distance_threshold
        
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
                    '&extensions=all&show_fields=business'.format(self.gaode_token, self.gaode_keywords, self.gaode_type,
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
                    '}&extensions=all&show_fields=business'.format(
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
                            'rest_district': i.get('adname') if i.get('adname') is not None else '',
                            'rest_type_gaode': i.get('type') if i.get('type') is not None else '',
                            'distance': i.get('distance') if i.get('distance') is not None else '',
                            'rest_city': i.get('cityname') if i.get('cityname') is not None else '',
                            'rest_type': self.gaode_keywords if self.gaode_keywords is not None else '',
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
        
    def _calculate_text_similarity(self, text1, text2):
        """
        计算两段文本的相似度（使用Levenshtein距离）
        返回值范围: 0-1，1表示完全相同
        """
        if not text1 or not text2:
            return 0
        
        from Levenshtein import ratio
        return ratio(text1, text2)

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        使用Haversine公式计算两个经纬度点之间的距离（米）
        """
        import math
        
        # 如果经纬度不存在，返回一个很大的距离
        if None in (lat1, lon1, lat2, lon2):
            return float('inf')
        
        # 将经纬度转换为弧度
        lat1, lon1, lat2, lon2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
        
        # Haversine公式
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371000  # 地球半径（米）
        return c * r

    def _dedup(self, restaurant_list=None) -> None:
        """
        对获取到的餐厅信息进行去重
        优化标准:
        1. 门店名相似度>=60%
        2. 地址相似度>=60%
        3. 位置距离<=1000米
        """
        if restaurant_list is None:
            restaurant_list = self.info
        LOGGER.info(f"开始基于相似度和距离去重, 距离相似度阈值为{self.name_similarity_threshold}, 地址相似度阈值为{self.address_similarity_threshold}, 距离阈值为{self.distance_threshold}")
        deduped_info = []
        duplicate_count = 0
        
        # 首先对列表进行排序，保留评分更高或更新的餐厅信息
        # 可以根据实际需求调整排序标准
        sorted_list = sorted(restaurant_list, 
                             key=lambda x: (x.get('rest_chinese_name', ''), x.get('updated_time', '')), 
                             reverse=True)
        
        for i, item1 in enumerate(sorted_list):
            # 假设当前项不是重复项
            is_duplicate = False
            name1 = item1.get('rest_chinese_name', '')
            address1 = item1.get('rest_chinese_address', '')
            location1 = item1.get('rest_location', '')
            
            # 解析经纬度
            lat1, lon1 = None, None
            if location1 and isinstance(location1, str) and ',' in location1:
                try:
                    lat_str, lon_str = location1.split(',', 1)
                    lat1, lon1 = float(lat_str.strip()), float(lon_str.strip())
                except (ValueError, TypeError):
                    pass
            
            # 与已保留的项比较
            for item2 in deduped_info:
                name2 = item2.get('rest_chinese_name', '')
                address2 = item2.get('rest_chinese_address', '')
                location2 = item2.get('rest_location', '')
                
                # 解析经纬度
                lat2, lon2 = None, None
                if location2 and isinstance(location2, str) and ',' in location2:
                    try:
                        lat_str, lon_str = location2.split(',', 1)
                        lat2, lon2 = float(lat_str.strip()), float(lon_str.strip())
                    except (ValueError, TypeError):
                        pass
                
                # 计算相似度和距离
                name_similarity = self._calculate_text_similarity(name1, name2)
                address_similarity = self._calculate_text_similarity(address1, address2)
                distance = self._calculate_distance(lat1, lon1, lat2, lon2)
                
                
                # 判断是否为重复项
                if (name_similarity >= self.name_similarity_threshold and 
                    address_similarity >= self.address_similarity_threshold and 
                    distance <= self.distance_threshold):
                    LOGGER.info(f"去重信息: 餐厅名:{name1}-{name2}({name_similarity}) 地址:{address1}-{address2}({address_similarity}) 距离:{distance}米")
                    is_duplicate = True
                    duplicate_count += 1
                    break
            
            # 如果不是重复项，加入去重后的列表
            if not is_duplicate:
                deduped_info.append(item1)
        
        # 更新信息列表
        count_before = len(self.info)
        self.info = deduped_info
        count_after = len(self.info)
        
        LOGGER.info(f"去重前餐厅信息: {count_before}条，去重后: {count_after}条，去除了 {count_before - count_after} 条重复信息")
        LOGGER.info(f"其中基于相似度和距离去重: {duplicate_count}条")

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
    

    def gen_info_v2(self, restaurants_group: RestaurantsGroup, num_workers: int = 4, logger_file: str = None) -> RestaurantsGroup:
        """
        并行生成餐厅信息(改进版)，支持日志到文件，保证主线程能够返回
        
        :param restaurants_group: 餐厅组合
        :param num_workers: 并行工作线程数，当为1时不使用多线程
        :param logger_file: 日志文件路径，如果提供则将日志写入该文件
        :return: 处理后的餐厅组合
        """
        # 创建心跳文件路径（用于监控进程是否活跃）
        # heartbeat_file = None
        status_file = None
        
        # 定义直接写入主日志的函数
        def write_log(level, message):
            if not logger_file:
                # 如果没有指定日志文件，记录到控制台或标准日志
                if level == "ERROR":
                    LOGGER.error(message)
                elif level == "WARNING":
                    LOGGER.warning(message)
                else:
                    LOGGER.info(message)
                return
                
            try:
                # 使用跨平台方案实现超时功能
                import threading
                
                # 设置超时标志
                write_timeout = False
                
                # 定义超时处理函数
                def timeout_callback():
                    nonlocal write_timeout
                    write_timeout = True
                
                # 创建定时器，1秒后触发超时
                timer = threading.Timer(1.0, timeout_callback)
                timer.start()
                
                try:
                    # 记录起始时间
                    start_time = time.time()
                    
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_line = f"{timestamp} - {level} - {message}\n"
                    with open(logger_file, 'a', encoding='utf-8') as f:
                        f.write(log_line)
                        f.flush()
                        # 只有ERROR级别的日志才强制fsync，减少磁盘I/O
                        if level == "ERROR" and not write_timeout and (time.time() - start_time) < 0.5:
                            try:
                                os.fsync(f.fileno())  # 确保写入磁盘
                            except:
                                pass
                finally:
                    # 取消定时器
                    timer.cancel()
                    
                # 检查是否超时
                if write_timeout:
                    print(f"WARNING: 写入日志超时: {message[:50]}...")
            except Exception as e:
                # 如果写入日志失败，尝试记录到控制台
                print(f"写入日志文件失败: {e}")
        
        
        # 获取餐厅列表
        restaurants = restaurants_group.members
        total_count = len(restaurants)
        processed_count = 0
        success_count = 0
        failed_count = 0
        
        if not restaurants:
            write_log("WARNING", "餐厅列表为空，无需生成信息")
            return restaurants_group
        
        # 处理单个餐厅的函数
        def process_restaurant(restaurant, idx):
            nonlocal processed_count, success_count, failed_count
            
            # 清理所有可能的临时变量
            local_vars = locals().copy()
            for var_name in local_vars:
                if var_name not in ['restaurant', 'idx', 'processed_count', 'success_count', 'failed_count']:
                    locals()[var_name] = None
            
            # 主动进行垃圾回收，释放内存
            gc.collect()
            
            # 在进入函数时释放不必要的内存
            if 'psutil' in sys.modules:
                try:
                    process = psutil.Process()
                    if hasattr(process, 'memory_maps'):
                        process.memory_maps = None
                except Exception:
                    pass
            
            # 线程级别的日志同步锁
            log_lock = threading.Lock()
            
            # 定义带超时功能的文件写入函数
            def write_file_with_timeout(log_line, is_error=False):
                try:
                    # 使用跨平台方案实现超时功能
                    import threading
                    
                    # 设置超时标志
                    write_timeout = False
                    
                    # 定义超时处理函数
                    def timeout_callback():
                        nonlocal write_timeout
                        write_timeout = True
                    
                    # 创建定时器，1秒后触发超时
                    timer = threading.Timer(1.0, timeout_callback)
                    timer.start()
                    
                    try:
                        # 记录起始时间
                        start_time = time.time()
                        
                        with open(logger_file, 'a', encoding='utf-8') as f:
                            f.write(log_line)
                            f.flush()
                            # 错误日志尝试fsync，但有超时保护
                            if is_error and not write_timeout and (time.time() - start_time) < 0.5:
                                try:
                                    os.fsync(f.fileno())
                                except:
                                    pass
                    finally:
                        # 取消定时器
                        timer.cancel()
                        
                    # 检查是否超时
                    return not write_timeout
                except Exception:
                    return False
            
            start_time = time.time()
            restaurant_name = ""
            
            try:
                # 获取餐厅名称
                restaurant_name = restaurant.inst.rest_chinese_name if hasattr(restaurant, 'inst') and hasattr(restaurant.inst, 'rest_chinese_name') else f"餐厅_{idx}"
                
                # 使用锁保护日志写入和计数器更新
                with log_lock:
                    # 直接写入文件而不是使用logger
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_line = f"{timestamp} - INFO - [{idx+1}/{total_count}] 开始处理餐厅: {restaurant_name}\n"
                    write_file_with_timeout(log_line)
                    
                    # 更新处理计数
                    processed_count += 1
                
                # 生成餐厅信息，增加额外的错误处理
                try:
                    # 定期进行垃圾回收
                    gc_start = time.time()
                    gc.collect()
                    gc_time = time.time() - gc_start
                    
                    # 生成餐厅信息
                    restaurant.generate()
                    
                    # 定期进行垃圾回收
                    gc_start = time.time()
                    gc.collect()
                    gc_time = time.time() - gc_start
                except MemoryError:
                    # 特殊处理内存错误
                    # write_thread_log("ERROR", f"处理餐厅 {restaurant_name} 时内存不足")
                    # 尝试紧急释放内存
                    gc.collect()
                    raise
                
                # 使用锁保护日志写入和计数器更新
                with log_lock:
                    success_count += 1
                    elapsed = time.time() - start_time
                    # 直接写入文件而不是使用logger
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_line = f"{timestamp} - INFO - [{idx+1}/{total_count}] 完成处理餐厅: {restaurant_name}，耗时: {elapsed:.2f}秒\n"
                    write_file_with_timeout(log_line)
                
                # 再次进行垃圾回收，确保内存被释放
                gc.collect()
                
                # 显式释放不再需要的对象
                log_lock = None
                
                return (idx, restaurant, None)
            except Exception as e:
                # 使用锁保护日志写入和计数器更新
                with log_lock:
                    failed_count += 1
                    error_msg = str(e)
                    tb_str = traceback.format_exc()
                    # 直接写入文件而不是使用logger
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    log_line = f"{timestamp} - ERROR - [{idx+1}/{total_count}] 处理餐厅 {restaurant_name if restaurant_name else f'餐厅_{idx}'} 时出错: {error_msg}\n{tb_str}\n"
                    if not write_file_with_timeout(log_line, is_error=True):
                        # 写入超时或失败，尝试输出到控制台
                        print(f"ERROR - 处理餐厅 {restaurant_name if restaurant_name else f'餐厅_{idx}'} 时出错: {error_msg}")
                
                # 主动进行多次垃圾回收
                for _ in range(3):
                    gc.collect()
                
                # 显式释放不再需要的对象
                log_lock = None
                error_msg = None
                tb_str = None
                
                return (idx, restaurant, error_msg)
        
        try:
            # 根据num_workers决定使用单线程还是多线程处理
            if num_workers <= 1:
                # 单线程顺序处理
                write_log("INFO", "使用单线程顺序处理")

                
                processed_restaurants = []
                for idx, restaurant in enumerate(restaurants):
                    if idx == 19:
                        print("")
                    idx, result, error = process_restaurant(restaurant, idx)
                    processed_restaurants.append(result)
                    processed_count += 1
                    
                    # 更新状态
                    if processed_count % 1 == 0 or processed_count == total_count:  # 每处理1个餐厅更新一次
                        progress_pct = (processed_count / 2 / total_count) * 100
                        progress_msg = f"进度: {int(processed_count/2)}/{total_count} ({progress_pct:.1f}%)"
                        write_log("INFO", progress_msg)

            else:
                # 使用线程池而非直接创建线程，更容易管理
                write_log("INFO", f"使用多线程并行处理，线程数: {num_workers}")
                # update_status(message=f"使用多线程并行处理，线程数: {num_workers}")
                
                # 预先分配结果列表
                processed_restaurants = [None] * total_count
                results = [None] * total_count
                
                # 使用线程池执行任务
                with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                    # 提交所有任务
                    futures = []
                    for idx, restaurant in enumerate(restaurants):
                        futures.append((idx, executor.submit(process_restaurant, restaurant, idx)))
                    
                    # 处理完成的任务
                    for idx, future in futures:
                        try:
                            result_idx, result, error = future.result()
                            processed_count += 1
                            results[idx] = (result_idx, result, error)
                            
                            # 更新日志和状态
                            if processed_count % 1 == 0 or processed_count == total_count:  # 每处理1个餐厅更新一次
                                progress_pct = (processed_count / 2 / total_count) * 100
                                progress_msg = f"进度: {int(processed_count/2)}/{total_count} ({progress_pct:.1f}%)"
                                write_log("INFO", progress_msg)

                        except Exception as e:
                            processed_count += 1
                            failed_count += 1
                            error_msg = str(e)
                            tb_str = traceback.format_exc()
                            write_log("ERROR", f"处理餐厅 {idx} 时发生未捕获异常: {error_msg}\n{tb_str}")
                            results[idx] = (idx, restaurants[idx], error_msg)
                
                # 处理所有结果
                for idx, result_tuple in enumerate(results):
                    if result_tuple is not None:
                        _, result, _ = result_tuple
                        processed_restaurants[idx] = result
                    else:
                        # 如果结果为None，使用原始餐厅
                        write_log("WARNING", f"餐厅 {idx} 的处理结果丢失，使用原始餐厅对象")
                        processed_restaurants[idx] = restaurants[idx]
            
            # 确保所有处理过的餐厅都是有效对象
            processed_restaurants = [r for r in processed_restaurants if r is not None]
            
            # 创建新的餐厅组合并返回
            result_group = RestaurantsGroup(processed_restaurants, group_type=restaurants_group.group_type)
            completion_msg = f"餐厅信息生成完成，共处理 {len(processed_restaurants)}/{total_count} 个餐厅，成功: {success_count}，失败: {failed_count}"
            write_log("INFO", completion_msg)

            
            return result_group
        except Exception as e:
            error_msg = str(e)
            tb_str = traceback.format_exc()
            write_log("ERROR", f"生成餐厅信息过程中发生严重错误: {error_msg}\n{tb_str}")

            return restaurants_group
    

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
        
        # 加载关键词和屏蔽词（如果还没有加载过）
        if not hasattr(self, '_keywords_already_loaded'):
            self.load_keywords()
            self.load_blocked_words()
        else:
            LOGGER.info("关键词已预先加载，跳过重新加载")


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
                            restaurant_list_accurate = [restaurant for restaurant in restaurant_list if restaurant['rest_city'] == city]
                            LOGGER.info(f"使用严格模式搜索，关键词: {key_words}, 城市: {city_name}, 周边结果：{len(restaurant_list)} 条， 精确结果：{len(restaurant_list_accurate)} 条")
                            restaurant_list = restaurant_list_accurate
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
        restaurant_list = self.info
        LOGGER.info(f"过滤屏蔽词后剩余 {len(self.info)} 条餐厅信息")
        # 去重
        self._dedup(restaurant_list=restaurant_list)
        
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

