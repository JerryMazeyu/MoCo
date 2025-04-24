import requests
from typing import Dict, Any, List, Optional, Union
from app.services.instances.base import BaseInstance, BaseGroup
from app.models import RestaurantModel
from app.utils.hash import hash_text
from app.utils.logger import setup_logger
from app.utils.file_io import rp
from app.utils.query import robust_query
from app.utils.conversion import convert_to_pinyin, translate_text
import hashlib
import time
import uuid
import json
from openai import OpenAI
from app.config.config import CONF
import random
import mingzi
from datetime import datetime
import math
from app.utils.oss import oss_get_json_file
import pandas as pd

# 设置日志
LOGGER = setup_logger("moco.log")

# ===========有道Utils==========

def calculateSign(appKey, appSecret, q, salt, curtime):
    strSrc = appKey + getInput(q) + salt + curtime + appSecret
    return encrypt(strSrc)

def encrypt(strSrc):
    hash_algorithm = hashlib.sha256()
    hash_algorithm.update(strSrc.encode('utf-8'))
    return hash_algorithm.hexdigest()

def getInput(input):
    if input is None:
        return input
    inputLen = len(input)
    return input if inputLen <= 20 else input[0:10] + str(inputLen) + input[inputLen - 10:inputLen]

def addAuthParams(appKey, appSecret, params):
    q = params.get('q')
    if q is None:
        q = params.get('img')
    q = "".join(q)
    salt = str(uuid.uuid1())
    curtime = str(int(time.time()))
    sign = calculateSign(appKey, appSecret, q, salt, curtime)
    params['appKey'] = appKey
    params['salt'] = salt
    params['curtime'] = curtime
    params['signType'] = 'v3'
    params['sign'] = sign

def youdao_translate(text: str, from_lang: str = 'zh', to_lang: str = 'en', conf: str = None) -> Optional[str]:
    """
    调用有道翻译API
    
    :param text: 要翻译的文本
    :param from_lang: 源语言
    :param to_lang: 目标语言
    :param conf: API密钥，格式为'app_key:app_secret'
    :return: 翻译结果或None
    """
    if not text or not conf:
        return None
    
    # 解析app_key和app_secret
    try:
        app_key, app_secret = conf.split(':')
    except ValueError:
        LOGGER.error(f"无效的有道翻译API密钥格式，应为'app_key:app_secret'")
        return None
    
    try:
        
        data = {'q': text, 'from': from_lang, 'to': to_lang}
        addAuthParams(app_key, app_secret, data)

        header = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post('https://openapi.youdao.com/api', data=data, headers=header, timeout=5)
        
        if response.status_code != 200:
            LOGGER.error(f"有道翻译API请求失败: {response.status_code}")
            return None
            
        result = response.json()
        if 'translation' not in result or not result['translation']:
            LOGGER.error(f"有道翻译返回结果无效: {result}")
            return None
            
        return result['translation'][0]
        
    except Exception as e:
        LOGGER.error(f"有道翻译API调用异常: {str(e)}")
        return None

# ===========高德Utils==========

def query_gaode(key, city):
    if not city:
        LOGGER.error("城市名称为空")
        return None
        
    api_url = f"https://restapi.amap.com/v3/config/district?keywords={city}&subdistrict=3&key={key}"
    try:
        response = requests.get(api_url, timeout=5)
        if response.status_code != 200:
            LOGGER.error(f"高德地图API请求失败: {response.status_code}")
            return None
            
        result = response.json()
        if result.get('status') != '1':
            LOGGER.error(f"高德地图API返回状态错误: {result.get('info', '未知错误')}")
            return None
            
        if 'districts' not in result or not result['districts']:
            LOGGER.error(f"未找到城市 '{city}' 的信息")
            return None
            
        return result['districts'][0]
    except Exception as e:
        LOGGER.error(f"查询城市 '{city}' 时发生错误: {str(e)}")
        return None


# ===========KIMI Utils==========

def search_impl(arguments: Dict[str, Any]) -> Any:
    """
    在使用 Moonshot AI 提供的 search 工具的场合，只需要原封不动返回 arguments 即可，
    不需要额外的处理逻辑。
 
    但如果你想使用其他模型，并保留联网搜索的功能，那你只需要修改这里的实现（例如调用搜索
    和获取网页内容等），函数签名不变，依然是 work 的。
 
    这最大程度保证了兼容性，允许你在不同的模型间切换，并且不需要对代码有破坏性的修改。
    """
    return arguments

def kimi_restaurant_type_analysis(rest_info: Dict[str, str], api_key: str = None) -> Optional[str]:
    """
    使用KIMI分析餐厅类型
    
    :param rest_info: 包含餐厅名称和地址的字典 {'name': '餐厅名', 'address': '地址', 'rest_type': '餐厅类型'}
    :param api_key: KIMI API密钥
    :return: 分析结果或None
    """
    if not rest_info or not api_key or 'name' not in rest_info:
        return None
        
    try:
        # 准备餐厅类型列表
        rest_types = rest_info.get('rest_type', '')
        
        # 构建提示词
        prompt = """
        请你搜索餐厅"{name}"，其地址是"{address}"，我想确认其属于以下哪一种餐厅类型：
        {types}
        请你查找餐厅的信息，并综合自己的分析，如果没有相关网络的答案，则需要分析名字的信息来推理相关的结果可能是什么，分析后给我最简短的回答，请直接告诉我答案。
        """.format(
            name=rest_info.get('name', ''),
            address=rest_info.get('address', ''),
            types=rest_types
        )
        
        # 初始化客户端
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1",
        )
        
        # 定义搜索工具
        tools = [
            {
                "type": "builtin_function",
                "function": {
                    "name": "$web_search",
                }
            }
        ]
        
        # 构建会话信息
        messages = [
            {"role": "system", "content": "你是一个专业的餐厅类型分析专家，请根据用户提供的餐厅名称和地址，分析其属于哪一种餐厅类型。"},
            {"role": "user", "content": prompt}
        ]
        
        
        finish_reason = None
        while finish_reason is None or finish_reason == "tool_calls":
            # 进行API调用
            completion = client.chat.completions.create(
                model="moonshot-v1-8k",
                messages=messages,
                temperature=0.3,
                tools=tools,
                tool_choice="required",
            )
            choice = completion.choices[0]
            finish_reason = choice.finish_reason
            if finish_reason == "tool_calls":  # <-- 判断当前返回内容是否包含 tool_calls
                messages.append(choice.message)  # <-- 我们将 Kimi 大模型返回给我们的 assistant 消息也添加到上下文中，以便于下次请求时 Kimi 大模型能理解我们的诉求
                for tool_call in choice.message.tool_calls:  # <-- tool_calls 可能是多个，因此我们使用循环逐个执行
                    tool_call_name = tool_call.function.name
                    tool_call_arguments = json.loads(tool_call.function.arguments)  # <-- arguments 是序列化后的 JSON Object，我们需要使用 json.loads 反序列化一下
                    if tool_call_name == "$web_search":
                        tool_result = search_impl(tool_call_arguments)
                    else:
                        tool_result = f"Error: unable to find tool by name '{tool_call_name}'"
    
                    # 使用函数执行结果构造一个 role=tool 的 message，以此来向模型展示工具调用的结果；
                    # 注意，我们需要在 message 中提供 tool_call_id 和 name 字段，以便 Kimi 大模型
                    # 能正确匹配到对应的 tool_call。
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call_name,
                        "content": json.dumps(tool_result),  # <-- 我们约定使用字符串格式向 Kimi 大模型提交工具调用结果，因此在这里使用 json.dumps 将执行结果序列化成字符串
                    })
    
        return choice.message.content
        
        
    except Exception as e:
        LOGGER.error(f"KIMI餐厅类型分析异常: {str(e)}")
        return None
    

# ===========  解析地理信息 ==========

def parse_geo_data(data: Union[str, Dict], level: str, filter_condition: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    解析地理信息数据，返回指定级别的所有区域名称和中心位置。
    
    参数:
        data: 字典对象或JSON文件路径
        level: 要提取的级别，可以是 'province', 'city', 'district', 'street'
        filter_condition: 筛选条件，格式为{'level': 'city', 'name': '广州市'}或{'level': 'district', 'adcode': '440105'}
    
    返回:
        包含指定级别地理实体的列表，每个实体包含name和center信息
    """
    # 如果输入是文件路径，则先读取文件
    if isinstance(data, str):
        with open(data, 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    # 用于存储所有符合要求的地理实体
    result = []
    
    # 解析筛选条件
    filter_level = None
    filter_criteria = {}
    if filter_condition:
        filter_level = filter_condition.get('level')
        filter_criteria = {k: v for k, v in filter_condition.items() if k != 'level'}
    
    # 递归查找指定级别的地理实体
    def search_level(item: Dict, parent_info: List[Dict] = None, in_filtered_branch: bool = False):
        if parent_info is None:
            parent_info = []
        
        # 获取当前项信息
        current_level = item.get('level', '')
        current_name = item.get('name', '')
        item_info = {'level': current_level, 'name': current_name, 'item': item}
        
        # 检查当前项是否符合筛选条件
        matches_filter = False
        if filter_criteria:
            if filter_level and current_level == filter_level:
                matches_filter = all(item.get(key) == value for key, value in filter_criteria.items() if key in item)
            elif not filter_level:
                matches_filter = all(item.get(key) == value for key, value in filter_criteria.items() if key in item)
        
        # 更新筛选分支状态
        in_filtered_branch = in_filtered_branch or matches_filter
        
        # 如果当前项级别与目标级别匹配，并且在筛选分支内或无筛选条件
        if current_level == level and (not filter_criteria or in_filtered_branch):
            path = ' > '.join([p['name'] for p in parent_info] + [current_name])
            result.append({
                'name': current_name,
                'center': item.get('center', ''),
                'adcode': item.get('adcode', ''),
                'path': path
            })
        
        # 递归处理子区域
        districts = item.get('districts', [])
        for district in districts:
            search_level(district, parent_info + [item_info], in_filtered_branch)
    
    # 开始递归搜索
    search_level(data)
    
    return result

def get_geo_data_by_level(data: Union[str, Dict], level: str, filter_by: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    获取指定级别的地理实体信息，只返回名称和中心位置。
    
    参数:
        data: 字典对象或JSON文件路径
        level: 要提取的级别，可以是 'province', 'city', 'district', 'street'
        filter_by: 筛选条件，如{'name': '广州市'}或{'adcode': '440100'}，
                  也可以指定级别{'level': 'city', 'name': '广州市'}
    
    返回:
        包含指定级别地理实体的列表，每个实体只包含name和center信息
    """
    entities = parse_geo_data(data, level, filter_by)
    return [{'name': entity['name'], 'center': entity['center']} for entity in entities]

# 简化的函数，直接通过名称进行筛选
def get_geo_data_by_name_and_level(data: Union[str, Dict], level: str, name: str, 
                                  parent_level: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    通过名称筛选，获取指定区域下特定级别的地理实体信息。
    
    参数:
        data: 字典对象或JSON文件路径
        level: 要提取的级别，可以是 'province', 'city', 'district', 'street'
        name: 要筛选的区域名称
        parent_level: 父级区域的级别，可选。如果指定，则筛选特定级别下的区域
    
    返回:
        包含指定级别地理实体的列表，每个实体只包含name和center信息
    """
    filter_by = {'name': name}
    if parent_level:
        filter_by['level'] = parent_level
    return get_geo_data_by_level(data, level, filter_by)











class Restaurant(BaseInstance):
    """
    餐厅实体类，处理餐厅模型的业务逻辑
    """
    def __init__(self, info: Dict[str, Any], model=RestaurantModel, conf=CONF,cp_location = None):
        """
        初始化餐厅实体
        
        :param info: 餐厅信息字典
        :param model: 餐厅模型类，可选
        :param conf: 配置服务，可选
        """
        super().__init__(model)
        self.conf = conf
        self.cp_location = cp_location
        
        # 确保必须的字段存在
        if info.get('rest_chinese_name') is None:
            info['rest_chinese_name'] = "未命名餐厅"
            LOGGER.warning(f"创建餐厅时未提供名称，使用默认名称")
        
        if model:
            # 创建模型实例
            self.inst = model(**info)
        else:
            # 如果没有提供模型类，直接存储info
            self.inst = type('DynamicModel', (), info)
        
        self.status = 'pending'  # 初始状态为待处理

        try:
            if not hasattr(self.conf.runtime, 'geoinfo'):
                LOGGER.info(f"初始化地理位置信息...")
                geoinfo = robust_query(query_gaode, self.conf.KEYS.gaode_keys, city=self.inst.rest_city)
                setattr(self.conf.runtime, 'geoinfo', {})
                self.conf.runtime.geoinfo[self.inst.rest_city] = geoinfo
        except Exception as e:
            LOGGER.error(f"初始化地理位置信息失败: {e}")
            self.conf.runtime.geoinfo = None
    
    def _generate_id_by_name(self) -> bool:
        """
        根据餐厅名称生成唯一ID
        
        :return: 是否生成成功
        """
        try:
            if not hasattr(self.inst, 'rest_id') or pd.isna(self.inst.rest_id) or not self.inst.rest_id:
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
            if not hasattr(self.inst, 'rest_english_name') or pd.isna(self.inst.rest_english_name) or not self.inst.rest_english_name:
                # 获取餐厅中文名
                chinese_name = self.inst.rest_chinese_name
                
                # 如果配置中有翻译API的keys，调用有道翻译
                if self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'youdao_keys'):
                    # 调用有道翻译API
                    def translate_func(key):
                        return youdao_translate(chinese_name, 'zh', 'en', key)
                    
                    # 使用robust_query进行健壮性调用
                    english_name = robust_query(translate_func, self.conf.KEYS.youdao_keys)
                    
                    if english_name:
                        self.inst.rest_english_name = english_name
                        LOGGER.info(f"已为餐厅 '{chinese_name}' 使用有道翻译生成英文名: {english_name}")
                    else:
                        # 翻译失败，使用默认值
                        # self.inst.rest_english_name = convert_to_pinyin(chinese_name)
                        candidate_english_name = translate_text(chinese_name)
                        if "MYMEMORY WARNING" in candidate_english_name:
                            candidate_english_name = f"{convert_to_pinyin(chinese_name)}"
                        self.inst.rest_english_name = candidate_english_name
                        LOGGER.warning(f"翻译API调用失败，使用默认英文名: {self.inst.rest_english_name}")
                else:
                    # 没有配置翻译API，使用默认值
                    self.inst.rest_english_name = f"{convert_to_pinyin(chinese_name)} Restaurant"
                    LOGGER.info(f"未配置翻译API，使用默认英文名: {self.inst.rest_english_name}")
            return True
        except Exception as e:
            self.inst.rest_english_name = f"{convert_to_pinyin(self.inst.rest_chinese_name)} Restaurant"
            LOGGER.error(f"{self.inst.rest_chinese_name}生成餐厅英文名失败: {e}, 使用默认英文名: {self.inst.rest_english_name}")
            return True
    
    def _generate_english_address(self) -> bool:
        """
        生成餐厅英文地址
        
        :return: 是否生成成功
        """
        try:
            # 检查是否已有英文地址
            if (not hasattr(self.inst, 'rest_english_address') or pd.isna(self.inst.rest_english_address) or not self.inst.rest_english_address) and hasattr(self.inst, 'rest_chinese_address'):
                # 获取餐厅中文地址
                chinese_address = self.inst.rest_chinese_address
                
                # 如果配置中有翻译API的keys，调用有道翻译
                if self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'youdao_keys') and len(self.conf.KEYS.youdao_keys) > 0:
                    # 调用有道翻译API
                    def translate_func(key):
                        return youdao_translate(chinese_address, 'zh', 'en', key)
                    
                    # 使用robust_query进行健壮性调用
                    english_address = robust_query(translate_func, self.conf.KEYS.youdao_keys)
                    
                    if english_address:
                        self.inst.rest_english_address = english_address
                        LOGGER.info(f"已为餐厅使用有道翻译生成英文地址: {english_address}")
                    else:
                        # 翻译失败，使用默认值
                        # self.inst.rest_english_address = convert_to_pinyin(chinese_address)
                        candidate_english_address = translate_text(chinese_address)
                        if "MYMEMORY WARNING" in candidate_english_address:
                            candidate_english_address = f"{convert_to_pinyin(chinese_address)}"
                        self.inst.rest_english_address = candidate_english_address
                        LOGGER.warning(f"翻译API调用失败，使用默认英文地址: {self.inst.rest_english_address}")
                else:
                    # 没有配置翻译API，使用默认值
                    candidate_english_address = translate_text(chinese_address)
                    if "MYMEMORY WARNING" in candidate_english_address:
                        candidate_english_address = f"{convert_to_pinyin(chinese_address)}"
                    self.inst.rest_english_address = candidate_english_address
                    LOGGER.info(f"未配置翻译API，使用默认英文地址: {self.inst.rest_english_address}")
            return True
        except Exception as e:
            LOGGER.error(f"生成餐厅英文地址失败: {e}")
            return False
    
    def _extract_district_and_street(self) -> bool:
        """
        从地址中提取区域和街道信息
        
        :return: 是否提取成功
        """
        result = True
        # ================== 提取区域 ==================
        try:
            target_district = None
            # city = convert_to_pinyin(self.inst.rest_city.split("市")[0])  # 城市变成中文了
            city = self.inst.rest_city.split("市")[0]
            address = self.inst.rest_chinese_address
            # 检查是否已有区域和街道信息
            if not hasattr(self.inst, 'rest_district') or not self.inst.rest_district or pd.isna(self.inst.rest_district):  # 没有街道信息，生成
                
                geoinfo = None
                if hasattr(self.conf, 'runtime') and hasattr(self.conf.runtime, 'geoinfo') and city in self.conf.runtime.geoinfo.keys():
                    LOGGER.info(f"从self.conf.runtime.geoinfo中获取{city}的地理信息")
                    geoinfo = self.conf.runtime.geoinfo[city]
                else:
                    # 调用高德地图API获取地理信息
                    LOGGER.info(f"调用高德地图API获取{city}的地理信息")
                    geoinfo = robust_query(query_gaode, self.conf.KEYS.gaode_keys, city=city)
                    # 确保geoinfo不为None
                    if geoinfo is None:
                        LOGGER.error(f"无法获取城市 {city} 的地理信息")
                        self.inst.rest_district = city + "区"  # 设置默认区域
                        result = False
                        return result
                    # 确保runtime存在
                    if not hasattr(self.conf, 'runtime'):
                        setattr(self.conf, 'runtime', type('RuntimeConfig', (), {}))
                    # 确保geoinfo存在
                    if not hasattr(self.conf.runtime, 'geoinfo'):
                        setattr(self.conf.runtime, 'geoinfo', {})
                    self.conf.runtime.geoinfo[city] = geoinfo  # 将获取到的地理信息保存到self.conf.runtime.geoinfo中
                    LOGGER.info(f"已将{city}的地理信息保存到self.conf.runtime.geoinfo中")
                
                flag = False
                cand_district = get_geo_data_by_level(geoinfo, 'district')
                for district in cand_district:
                    if district['name'] in address:
                        self.inst.rest_district = district['name']
                        flag = True 
                        LOGGER.info(f"已为餐厅提取区域: {district['name']}")
                        break
                if not flag:  # 没有能从地址中提取的区域，尝试基于地理信息距离获取区域信息
                    LOGGER.warning(f"{str(self.inst)}未找到区域, 尝试基于地理信息距离获取区域信息")
                    if not hasattr(self.inst, 'rest_location') or not self.inst.rest_location:
                        LOGGER.warning(f"{str(self.inst)}未找到经纬度，无法判断其所属区域，使用默认区域")
                        self.inst.rest_district = city + "区"  # 设置默认区域
                    else:
                        try:
                            rest_lng, rest_lat = self.inst.rest_location.split(',')
                            rest_lng = float(rest_lng)
                            rest_lat = float(rest_lat)
                            min_distance = float('inf')
                            
                            for district in cand_district:
                                district_lng, district_lat = district['center'].split(',')
                                district_lng = float(district_lng)
                                district_lat = float(district_lat)
                                distance = ((rest_lng - district_lng) ** 2 + (rest_lat - district_lat) ** 2) ** 0.5
                                if distance < min_distance:
                                    min_distance = distance
                                    target_district = district['name']
                            LOGGER.info(f"已通过经纬度计算为餐厅找到最近区域: {target_district}")
                            self.inst.rest_district = target_district
                            result &= True
                        except Exception as e:
                            LOGGER.error(f"计算餐厅区域距离时出错: {e}")
                            self.inst.rest_district = city + "区"  # 设置默认区域
                            result &= False
        except Exception as e:
            result &= False
            LOGGER.error(f"提取区域失败: {e}")
            # 设置默认区域
            if hasattr(self.inst, 'rest_city'):
                self.inst.rest_district = self.inst.rest_city.split("市")[0] + "区"
            else:
                self.inst.rest_district = "未知区"
        
        # ================== 提取街道 ==================
        try:
            if not hasattr(self.inst, 'rest_street') or pd.isna(self.inst.rest_street) or not self.inst.rest_street:  # 如果没有，则生成
               
                try:
                    geoinfo = self.conf.runtime.geoinfo[city]
                except: # 如果没有geoinfo则生成
                    # 调用高德地图API获取地理信息
                    LOGGER.info(f"调用高德地图API获取{city}的地理信息")
                    geoinfo = robust_query(query_gaode, self.conf.KEYS.gaode_keys, city=city)
                    # 确保geoinfo不为None
                    if geoinfo is None:
                        LOGGER.error(f"无法获取城市 {city} 的地理信息")
                        self.inst.rest_street = "未知街道"  # 设置默认街道
                        result = False
                        return result
                    # 确保runtime存在
                    if not hasattr(self.conf, 'runtime'):
                        setattr(self.conf, 'runtime', type('RuntimeConfig', (), {}))
                    # 确保geoinfo存在
                    if not hasattr(self.conf.runtime, 'geoinfo'):
                        setattr(self.conf.runtime, 'geoinfo', {})
                    self.conf.runtime.geoinfo[city] = geoinfo  # 将获取到的地理信息保存到self.conf.runtime.geoinfo中
                    LOGGER.info(f"已将{city}的地理信息保存到self.conf.runtime.geoinfo中")
                
                if target_district:
                    cand_street = get_geo_data_by_level(geoinfo, 'street', {'name': target_district, 'level': 'district'})
                else:
                    cand_street = get_geo_data_by_level(geoinfo, 'street')

                flag = False
                # 从cand_street中提取街道信息
                for street in cand_street:
                    if street['name'] in address:
                        self.inst.rest_street = street['name']
                        LOGGER.info(f"已为餐厅提取街道: {street['name']}")
                        flag = True
                        break
                if not flag:
                    LOGGER.warning(f"{str(self.inst)}未找到街道, 尝试基于地理信息距离获取街道信息")
                    if not hasattr(self.inst, 'rest_location') or not self.inst.rest_location:
                        LOGGER.warning(f"{str(self.inst)}未找到经纬度，无法判断其所属街道，使用默认街道")
                        self.inst.rest_street = "未知街道"  # 设置默认街道
                    else:
                        try:
                            rest_lng, rest_lat = self.inst.rest_location.split(',')
                            rest_lng = float(rest_lng)
                            rest_lat = float(rest_lat)
                            min_distance = float('inf')
                            target_street = None
                            for street in cand_street:
                                street_lng, street_lat = street['center'].split(',')
                                street_lng = float(street_lng)
                                street_lat = float(street_lat)
                                distance = ((rest_lng - street_lng) ** 2 + (rest_lat - street_lat) ** 2) ** 0.5
                                if distance < min_distance:
                                    min_distance = distance
                                    target_street = street['name']  
                            LOGGER.info(f"已通过经纬度计算为餐厅找到最近街道: {target_street}")
                            self.inst.rest_street = target_street
                            result &= True
                        except Exception as e:
                            LOGGER.error(f"计算餐厅街道距离时出错: {e}")
                            self.inst.rest_street = "未知街道"  # 设置默认街道
                            result &= False
        except Exception as e:
            result &= False
            LOGGER.error(f"提取街道失败: {e}")
            # 设置默认街道
            self.inst.rest_street = "未知街道"
        
        return result
    
    def _generate_type(self) -> bool:
        """
        使用KIMI分析餐厅类型
        
        :return: 是否生成成功
        """
        try:
            # 检查是否已有餐厅类型
            if not hasattr(self.inst, 'rest_type') or pd.isna(self.inst.rest_type) or not self.inst.rest_type:
                # 首先尝试通过餐厅名称中包含的关键词推断类型
                if hasattr(self.conf, 'BUSINESS') and hasattr(self.conf.BUSINESS, 'RESTAURANT') and hasattr(self.conf.BUSINESS.RESTAURANT, '收油关系映射'):
                    candidate_types_merged = list(self.conf.BUSINESS.RESTAURANT.收油关系映射._config_dict.keys())
                    candidate_types = "/".join(list(self.conf.BUSINESS.RESTAURANT.收油关系映射._config_dict.keys())).split("/")
                    
                    # 尝试通过餐厅名称中包含的关键词匹配类型
                    for candidate_type in candidate_types:
                        if candidate_type in self.inst.rest_chinese_name:
                            self.inst.rest_type = candidate_type
                            LOGGER.info(f"已直接通过餐厅名为餐厅 '{self.inst.rest_chinese_name}' 推断类型: {self.inst.rest_type}")
                            return True
                    
                    # 如果通过名称未能推断类型，尝试使用KIMI API
                    LOGGER.info(f"未从餐厅名称推断出类型，尝试使用KIMI API分析")
                    if self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'kimi_keys'):
                        # 准备餐厅信息
                        rest_info = {
                            'name': self.inst.rest_chinese_name,
                            'address': getattr(self.inst, 'rest_chinese_address', ''),
                            'rest_type_gaode': getattr(self.inst, 'rest_type_gaode', ''),
                            'candidate_types': "\n".join(candidate_types)
                        }
                        # 调用KIMI API分析餐厅类型
                        def analyze_func(key):
                            return kimi_restaurant_type_analysis(rest_info, key)
                        
                        # 使用robust_query进行健壮性调用
                        rest_type_ans = robust_query(analyze_func, self.conf.KEYS.kimi_keys)
                        
                        if rest_type_ans:
                            # 从KIMI的回答中找出最匹配的类型
                            matched_type = None
                            for candidate_type in candidate_types:
                                if candidate_type in rest_type_ans:
                                    matched_type = candidate_type
                                    break
                            
                            if matched_type: # TODO
                                for candidate_type_lst in candidate_types_merged:
                                    if matched_type in candidate_type_lst:
                                        self.inst.rest_type = candidate_type_lst
                                        LOGGER.info(f"已通过LLM为餐厅 '{self.inst.rest_chinese_name}' 分析类型: {matched_type}")
                                        return True
                            else:  # 如果没有匹配的类型，使用默认类型
                                self.inst.rest_type = "小食/小吃/美食/饮食/私房菜"
                                LOGGER.warning(f"无法确定餐厅类型，使用默认餐厅类型: {self.inst.rest_type}")
                                return False
                        else:  # 如果KIMI分析失败，使用默认类型
                            self.inst.rest_type = "小食/小吃/美食/饮食/私房菜"
                            LOGGER.warning(f"无法确定餐厅类型，使用默认餐厅类型: {self.inst.rest_type}")
                            return False
                    else:  # 如果没有KIMI Keys 则使用默认类型
                        self.inst.rest_type = "小食/小吃/美食/饮食/私房菜"
                        LOGGER.warning(f"无法确定餐厅类型，使用默认餐厅类型: {self.inst.rest_type}")
                        return False
                else:  # 如果不存在收油关系映射或者配置不全
                    # 配置不完整
                    self.inst.rest_type = "小食/小吃/美食/饮食/私房菜"
                    LOGGER.warning(f"配置不完整，使用默认餐厅类型: {self.inst.rest_type}")
            else:  # 如果已存在类型
                LOGGER.info(f"餐厅 '{self.inst.rest_chinese_name}' 已存在类型: {self.inst.rest_type}")
            return True
        except Exception as e:
            LOGGER.error(f"分析餐厅类型失败: {e}")
            # 出现异常时，设置默认类型
            self.inst.rest_type = "小食/小吃/美食/饮食/私房菜"
            LOGGER.warning(f"异常情况下使用默认餐厅类型: {self.inst.rest_type}")
            return False

    def _generate_contact_info(self) -> bool:
        """
        生成联系人信息
        
        :return: 是否生成成功
        """
        try:  # TODO 需要优化   
            name = mingzi.mingzi()[0]
            self.inst.rest_contact_person = name
            LOGGER.info(f"已为餐厅生成随机联系人: {self.inst.rest_contact_person}")
            
            # if (not hasattr(self.inst, 'rest_contact_phone') or 
            #     (isinstance(self.inst.rest_contact_phone, (str, int, float)) and pd.isna(self.inst.rest_contact_phone)) or
            #     (hasattr(self.inst.rest_contact_phone, 'size') and self.inst.rest_contact_phone.size == 0) or
            #     self.inst.rest_contact_phone == ''):
                
            # 生成随机手机号
            prefix = ["130", "131", "132", "133", "134", "135", "136", "137", "138", "139", 
                        "150", "151", "152", "153", "155", "156", "157", "158", "159", 
                        "176", "177", "178", "180", "181", "182", "183", "184", "185", "186", "187", "188", "189"]
            
            phone_prefix = random.choice(prefix)
            phone_suffix = ''.join(random.choices('0123456789', k=8))
            self.inst.rest_contact_phone = phone_prefix + phone_suffix
            LOGGER.info(f"已为餐厅生成随机联系电话: {self.inst.rest_contact_phone}")
            
            return True
        except Exception as e:
            # 增强错误日志
            import traceback
            LOGGER.error(f"生成联系人信息失败: {e}")
            LOGGER.error(f"错误详细信息: {traceback.format_exc()}")
            
            # 即使出错，也设置默认值防止后续处理出错
            if not hasattr(self.inst, 'rest_contact_person') or pd.isna(self.inst.rest_contact_person):
                self.inst.rest_contact_person = ""
            if not hasattr(self.inst, 'rest_contact_phone') or pd.isna(self.inst.rest_contact_phone):
                self.inst.rest_contact_phone = ""
            
            return False
    
    def _calculate_distance(self,cp_location) -> bool:
        """
        计算餐厅与所属CP的距离
        
        :return: 是否计算成功
        """
        try:
            # 检查是否已有距离信息和必要的条件
            if (not hasattr(self.inst, 'rest_distance') or pd.isna(self.inst.rest_distance) or not self.inst.rest_distance or self.inst.rest_distance == 0) and hasattr(self.inst, 'rest_location') and hasattr(self.inst, 'rest_belonged_cp'):
                # 获取餐厅位置
                restaurant_location = self.inst.rest_location
                
                
                if hasattr(self.conf.runtime, 'CP'):
                    cp_location = self.conf.runtime.CP['cp_location']
                    res_lon, res_lat = map(float, restaurant_location.split(','))  # 假设坐标格式为 "经度,纬度"
                    cp_lon, cp_lat = map(float, cp_location.split(','))  # 假设坐标格式为 "经度,纬度"
                    factory_lat_lon = (cp_lat, cp_lon)
                    distance = self._haversine((res_lat, res_lon), factory_lat_lon)  # 计算距离(维度,经度),(维度,经度)
                    self.inst.rest_distance = distance  
                    LOGGER.info(f"已计算餐厅到CP的距离: {distance}公里")
                    return True
                else:
                    LOGGER.warning("警告: 工厂坐标未设置，跳过距离计算")
                    # 给所有餐厅设置一个默认距离
                    self.inst.rest_distance = 0
                    return False
            
        except Exception as e:
            LOGGER.error(f"计算餐厅距离失败: {e}")
            return False
    
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
        
    def _generate_verified_date(self) -> bool:
        """
        生成确认日期
        
        :return: 是否生成成功
        """
        try:
            self.inst.rest_verified_date = datetime.now().strftime("%Y-%m-%d")
            LOGGER.info(f"已生成确认日期: {self.inst.rest_verified_date}")
            return True
        except Exception as e:
            LOGGER.error(f"生成确认日期失败: {e}")
            return False
    
    def _generate_belonged_cp(self) -> bool:
        """
        生成所属CP
        
        :return: 是否生成成功
        """
        try:
            if not hasattr(self.inst, 'rest_belonged_cp') or pd.isna(self.inst.rest_belonged_cp) or not self.inst.rest_belonged_cp:
                if hasattr(self.conf.runtime, 'CP'):
                    self.inst.rest_belonged_cp = self.conf.runtime.CP['cp_id']
                    LOGGER.info(f"已生成所属CP: {self.inst.rest_belonged_cp}")
                    return True
            else:
                LOGGER.warning("警告: CP信息未设置，跳过所属CP生成")
                return False
        except Exception as e:
            LOGGER.error(f"生成所属CP失败: {e}")
            return False


    def generate(self) -> bool:
        """
        生成餐厅的所有缺失字段
        
        :return: 是否全部生成成功
        """
        success = True
        
        # 生成ID
        success &= self._generate_id_by_name()

        success &= self._generate_belonged_cp()
        
        # 生成英文名和地址
        success &= self._generate_english_name()
        success &= self._generate_english_address()
        
        # 提取区域和街道
        success &= self._extract_district_and_street()
        
        # 分析餐厅类型
        success &= self._generate_type()
        
        # 生成联系信息
        success &= self._generate_contact_info()
        
        # 计算距离
        success &= self._calculate_distance(self.cp_location)

        # 生成确认日期
        success &= self._generate_verified_date()
        
        # 如果全部成功，更新状态为就绪
        if success:
            self.status = 'ready'
            is_complete = self.check()
            if not is_complete:
                LOGGER.error(f"餐厅 '{self.inst.rest_chinese_name}' 缺少字段，请检查")
                return False
            else:
                LOGGER.info(f"餐厅 '{self.inst.rest_chinese_name}' 的所有字段已生成完成")
        return success
    

    def check(self):
        """
        检查餐厅全部字段都完整
        """
        all_keys = [x for x in self.inst.__dict__.keys() if x.startswith('rest_')]
        for key in all_keys:
            try:
                if (pd.isna(self.inst.__getattribute__(key)) or self.inst.__getattribute__(key) is None) and (key != 'rest_allocated_barrel' and key != 'rest_verified_date'):
                    LOGGER.error(f"餐厅 '{self.inst.rest_chinese_name}' 缺少字段: {key}")
                    return False
                if key == 'rest_distance' and self.inst.__getattribute__(key) == 0:
                    LOGGER.error(f"餐厅 '{self.inst.rest_chinese_name}' 距离为0，请检查")
                    return False
            except:
                pass
            # if self.inst.__getattribute__(key) is None and key != 'rest_allocated_barrel' and key != 'rest_verified_date':
            #     LOGGER.error(f"餐厅 '{self.inst.rest_chinese_name}' 缺少字段: {key}")
            #     return False
            # else:
            #     pass
                # LOGGER.info(f"餐厅 '{self.inst.rest_chinese_name}' 字段: {key} 已检验")
        return True

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
    
    def update_restaurant_info(self, restaurant_id: str, update_dict: Dict[str, Any]) -> bool:
        """
        更新指定餐厅的信息
        
        :param restaurant_id: 餐厅ID
        :param update_dict: 包含要更新的字段及其新值的字典
        :return: 更新成功返回True，失败返回False
        """
        for restaurant in self.members:
            if restaurant.inst.rest_id == restaurant_id:
                for key, value in update_dict.items():
                    setattr(restaurant.inst, key, value)  # 更新餐厅实例的属性
                # LOGGER.info(f"成功更新餐厅 {restaurant_id} 的信息: {update_dict}")
                return True
        LOGGER.warning(f"未找到餐厅ID: {restaurant_id}，无法更新信息")
        return False

