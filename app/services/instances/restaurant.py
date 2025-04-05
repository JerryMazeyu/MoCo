import requests
from typing import Dict, Any, List, Optional, Union
from app.services.instances.base import BaseInstance, BaseGroup
from app.models import RestaurantModel
from app.utils.hash import hash_text
from app.utils.logger import setup_logger
from app.utils.file_io import rp
from app.utils.query import robust_query
from app.utils.conversion import convert_to_pinyin
import hashlib
import time
import uuid
import json
from openai import OpenAI
from app.config.config import CONF

# 设置日志
LOGGER = setup_logger("moco.log")

def youdao_translate(text: str, from_lang: str = 'zh', to_lang: str = 'en', conf: str = None) -> Optional[str]:
    """
    调用有道翻译API
    
    :param text: 要翻译的文本
    :param from_lang: 源语言
    :param to_lang: 目标语言
    :param app_key: API密钥
    :return: 翻译结果或None
    """
    if not text or not app_key:
        return None
    
    # 解析app_key和app_secret
    try:
        app_key, app_secret = app_key.split(':')
    except ValueError:
        LOGGER.error(f"无效的有道翻译API密钥格式，应为'app_key:app_secret'")
        return None
    
    try:
        # 添加鉴权参数
        salt = str(uuid.uuid1())
        curtime = str(int(time.time()))
        
        # 计算签名
        def get_input(input_text):
            if input_text is None:
                return input_text
            input_len = len(input_text)
            return input_text if input_len <= 20 else input_text[0:10] + str(input_len) + input_text[input_len - 10:input_len]
        
        sign_str = app_key + get_input(text) + salt + curtime + app_secret
        sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
        
        # 构建请求
        data = {
            'q': text, 
            'from': from_lang, 
            'to': to_lang,
            'appKey': app_key,
            'salt': salt,
            'curtime': curtime,
            'signType': 'v3',
            'sign': sign
        }
        
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
        
        # 进行API调用
        completion = client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=messages,
            temperature=0.3,
            tools=tools,
        )
        
        # 处理工具调用
        message = completion.choices[0].message        
        
        return message.content.strip()
        
    except Exception as e:
        LOGGER.error(f"KIMI餐厅类型分析异常: {str(e)}")
        return None

class Restaurant(BaseInstance):
    """
    餐厅实体类，处理餐厅模型的业务逻辑
    """
    def __init__(self, info: Dict[str, Any], model=RestaurantModel, conf=CONF):
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
                        self.inst.rest_english_name = convert_to_pinyin(chinese_name)
                        LOGGER.warning(f"翻译API调用失败，使用默认英文名: {self.inst.rest_english_name}")
                else:
                    # 没有配置翻译API，使用默认值
                    self.inst.rest_english_name = f"{chinese_name} Restaurant"
                    LOGGER.info(f"未配置翻译API，使用默认英文名: {self.inst.rest_english_name}")
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
                # 获取餐厅中文地址
                chinese_address = self.inst.rest_chinese_address
                
                # 如果配置中有翻译API的keys，调用有道翻译
                if self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'youdao_keys'):
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
                        self.inst.rest_english_address = convert_to_pinyin(chinese_address)
                        LOGGER.warning(f"翻译API调用失败，使用默认英文地址: {self.inst.rest_english_address}")
                else:
                    # 没有配置翻译API，使用默认值
                    self.inst.rest_english_address = f"{chinese_address} (needs translation)"
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
        try:
            # 检查是否已有区域和街道信息
            if (not hasattr(self.inst, 'rest_district') or not self.inst.rest_district or 
                not hasattr(self.inst, 'rest_street') or not self.inst.rest_street) and hasattr(self.inst, 'rest_chinese_address'):
                
                city = convert_to_pinyin(self.inst.rest_city.split("市")[0])
                address = self.inst.rest_chinese_address

                candidate_districts = list(CONF.STREETMAPS._config_dict[city].keys())
                flag = False
                for district in candidate_districts:
                    if district in self.inst.rest_chinese_address:
                        self.inst.rest_district = district
                        LOGGER.info(f"已为餐厅提取区域: {district}")
                        flag = True
                        break
                
                if not flag:
                    LOGGER.warning(f"{str(self.inst)}未找到区域")
                
                if not hasattr(self.inst, 'rest_district') or not self.inst.rest_district:
                    canditate_streets = ",".join(list(CONF.STREETMAPS._config_dict[city].values())).split(",")
                else:
                    canditate_streets = CONF.STREETMAPS._config_dict[city][district].split(",")

                flag = False
                for street in canditate_streets:
                    if street in address:
                        self.inst.rest_street = street
                        LOGGER.info(f"已从餐厅地址中为餐厅提取街道: {street}")
                        flag = True
                        break
                
                if not flag:
                    LOGGER.warning(f"{str(self.inst)}未找到街道, 尝试使用API寻找街道信息")
                    # 首先判断是否CONF.runtime中包含
                    url = f"https://restapi.amap.com/v3/config/district?keywords=北京&subdistrict=2&key=<用户的key>"
                    

            return True
        except Exception as e:
            LOGGER.error(f"提取区域和街道失败: {e}")
            return False
    
    def _generate_type(self) -> bool:
        """
        使用KIMI分析餐厅类型
        
        :return: 是否生成成功
        """
        try:
            # 检查是否已有餐厅类型
            if not hasattr(self.inst, 'rest_type') or not self.inst.rest_type:
                candidate_types = "/".join(list(CONF.BUSINESS.RESTAURANT.收油关系映射._config_dict.keys())).split("/")
                if self.inst.rest_chinese_name in candidate_types:
                    self.inst.rest_type = self.inst.rest_chinese_name
                    LOGGER.info(f"已直接通过餐厅名为餐厅 '{self.inst.rest_chinese_name}' 推断类型: {rest_type}")
                elif self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'kimi_keys'):
                    # 准备餐厅信息
                    rest_info = {
                        'name': self.inst.rest_chinese_name,
                        'address': getattr(self.inst, 'rest_chinese_address', ''),
                        'rest_type': "\n".join(list(CONF.BUSINESS.RESTAURANT.收油关系映射._config_dict.keys()))
                    }
                    
                    # 调用KIMI API分析餐厅类型
                    def analyze_func(key):
                        return kimi_restaurant_type_analysis(rest_info, key)
                    
                    # 使用robust_query进行健壮性调用
                    rest_type = robust_query(analyze_func, self.conf.KEYS.kimi_keys)
                    
                    if rest_type:
                        self.inst.rest_type = rest_type
                        LOGGER.info(f"已通过LLM为餐厅 '{self.inst.rest_chinese_name}' 分析类型: {rest_type}")
                    else:
                        # 分析失败，使用默认值
                        self.inst.rest_type = "餐馆/饭店"
                        LOGGER.warning(f"KIMI API调用失败，使用默认餐厅类型: {self.inst.rest_type}")
                else:
                    # 没有配置KIMI API，使用默认值
                    self.inst.rest_type = "餐馆/饭店"
                    LOGGER.info(f"未配置KIMI API，使用默认餐厅类型: {self.inst.rest_type}")
                
            return True
        except Exception as e:
            LOGGER.error(f"分析餐厅类型失败: {e}")
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
        
        # 分析餐厅类型
        success &= self._generate_type()
        
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