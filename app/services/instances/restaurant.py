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
import random
import mingzi
from datetime import datetime
import math

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
    api_url = f"https://restapi.amap.com/v3/config/district?keywords={city}&subdistrict=3&key={key}"
    response = requests.get(api_url, timeout=5)
    if response.status_code != 200:
        LOGGER.error(f"高德地图API请求失败: {response.status_code}")
        return None
    result = response.json()
    if result.get('status') != '1' or 'districts' not in result:
        LOGGER.error(f"高德地图API返回结果无效: {result}")
        return None
    return result['districts'][0]


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
            # city = convert_to_pinyin(self.inst.rest_city.split("市")[0])  # 城市变成中文了
            city = self.inst.rest_city.split("市")[0]
            address = self.inst.rest_chinese_address
            # 检查是否已有区域和街道信息
            if not hasattr(self.inst, 'rest_district') or not self.inst.rest_district:
                
                candidate_districts = list(self.conf.STREETMAPS._config_dict[city].keys())
                flag = False
                for district in candidate_districts:
                    if district in self.inst.rest_chinese_address:
                        self.inst.rest_district = district
                        LOGGER.info(f"已为餐厅提取区域: {district}")
                        flag = True
                        break
                
                if not flag:
                    LOGGER.warning(f"{str(self.inst)}未找到区域, 尝试使用高德地图API获取区域信息")
                    assert self.inst.rest_location is not None, f"{str(self.inst)}未找到经纬度，无法判断其所属区域"
                    geoinfo = None
                    if hasattr(self.conf, 'runtime') and hasattr(self.conf.runtime, 'geoinfo') and city in self.conf.runtime.geoinfo['name']:
                        LOGGER.info(f"从self.conf.runtime.geoinfo中获取{city}的地理信息")
                        geoinfo = self.conf.runtime.geoinfo[city]
                    else:
                        # 调用高德地图API获取地理信息
                        LOGGER.info(f"调用高德地图API获取{city}的地理信息")
                        geoinfo = robust_query(query_gaode, self.conf.KEYS.gaode_keys, city=city)
                        setattr(self.conf.runtime, 'geoinfo', geoinfo)
                        LOGGER.info(f"已将{city}的地理信息保存到self.conf.runtime.geoinfo中")
                    try:
                        
                        # 分解餐厅位置经纬度
                        rest_lng, rest_lat = self.inst.rest_location.split(',')
                        rest_lng = float(rest_lng)
                        rest_lat = float(rest_lat)
                        min_distance = float('inf')
                        for cand_district in geoinfo['districts']:
                            cand_district_lng, cand_district_lat = cand_district['center'].split(',')
                            cand_district_lng = float(cand_district_lng)
                            cand_district_lat = float(cand_district_lat)
                            distance = ((rest_lng - cand_district_lng) ** 2 + (rest_lat - cand_district_lat) ** 2) ** 0.5
                            if distance < min_distance:
                                min_distance = distance
                                self.inst.rest_district = cand_district['name']
                        LOGGER.info(f"已通过经纬度计算为餐厅找到最近区域: {self.inst.rest_district}")

                    except Exception as e:
                        LOGGER.error(f"解析地理信息出错: {str(e)}")
                        self.conf.runtime.geoinfo[city] = None
                        LOGGER.error(f"地理信息格式无效: {geoinfo}")

            # ==================街道信息=================
            if not hasattr(self.inst, 'rest_street') or not self.inst.rest_street:
                if not hasattr(self.inst, 'rest_district') or not self.inst.rest_district:
                    canditate_streets = ",".join(list(self.conf.STREETMAPS._config_dict[city].values())).split(",")
                else:
                    district = self.inst.rest_district
                    canditate_streets = self.conf.STREETMAPS._config_dict[city][district].split(",")

                flag = False
                for street in canditate_streets:
                    if street in address:
                        self.inst.rest_street = street
                        LOGGER.info(f"已从餐厅地址中为餐厅提取街道: {street}")
                        flag = True
                        break
                
                if not flag:
                    LOGGER.warning(f"{str(self.inst.rest_chinese_name)}未找到街道, 尝试使用API寻找街道信息")
                    assert self.inst.rest_location is not None, f"{str(self.inst)}未找到经纬度，无法判断其所属街道"
                    
                    # 首先判断是否self.conf.runtime中包含geoinfo，如果没有则通过下面的url进行申请，并将返回的内容放到self.conf.runtime.geoinfo中
                    geoinfo = None
                    if hasattr(self.conf, 'runtime') and hasattr(self.conf.runtime, 'geoinfo') and city in self.conf.runtime.geoinfo['name']:
                        LOGGER.info(f"从配置中获取{city}的地理信息")
                        geoinfo = self.conf.runtime.geoinfo
                    else:
                        # 调用高德地图API获取地理信息
                        LOGGER.info(f"调用高德地图API获取{city}的地理信息")
                        
                        # 使用robust_query进行健壮性调用
                        geoinfo = robust_query(query_gaode, self.conf.KEYS.gaode_keys, city)
                        setattr(self.conf.runtime, 'geoinfo', geoinfo)
                        LOGGER.info(f"已将{city}的地理信息保存到self.conf.runtime.geoinfo中")
                    
                    # 如果成功获取地理信息，解析查找最近的街道
                    if geoinfo:
                        try:
                            # 解析其中的geoinfo中的district中的内容
                            if 'districts' in geoinfo and len(geoinfo['districts']) > 0:
                                if hasattr(self.inst, 'rest_district') and self.inst.rest_district:
                                    LOGGER.info(f"已知区域: {self.inst.rest_district}")
                                    street_info = None
                                    for candidate_district in geoinfo['districts']:
                                        if candidate_district['name'] == self.inst.rest_district:
                                            street_info = candidate_district['districts']
                                            break
                                else:
                                    LOGGER.error(f"区域信息为空，将所有街道信息合并")
                                    street_info = []
                                    for candidate_district in geoinfo['districts']:
                                        street_info.extend(candidate_district['districts'])
                            
                                # 分解餐厅位置经纬度
                                rest_lng, rest_lat = self.inst.rest_location.split(',')
                                rest_lng = float(rest_lng)
                                rest_lat = float(rest_lat)

                                min_distance = float('inf')
                                nearest_street = None

                                for street_obj in street_info:
                                    street_lng, street_lat = street_obj['center'].split(',')
                                    street_lng = float(street_lng)
                                    street_lat = float(street_lat)
                                    distance = ((rest_lng - street_lng) ** 2 + (rest_lat - street_lat) ** 2) ** 0.5
                                    if distance < min_distance:
                                        min_distance = distance
                                        nearest_street = street_obj.get('name')
                                
                                self.inst.rest_street = nearest_street
                                LOGGER.info(f"已通过经纬度计算为餐厅找到最近街道: {nearest_street}")

                            else:
                                LOGGER.error(f"地理信息格式无效: {geoinfo}")
                                    
                                
                        except Exception as e:
                            LOGGER.error(f"解析地理信息出错: {str(e)}")
                    else:
                        LOGGER.error("未能获取有效的地理信息，无法确定街道")
                        # 使用默认值
                        if not hasattr(self.inst, 'rest_district') or not self.inst.rest_district:
                            self.inst.rest_district = "未知区域"
                        if not hasattr(self.inst, 'rest_street') or not self.inst.rest_street:
                            self.inst.rest_street = "未知街道"

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
                candidate_types = "/".join(list(self.conf.BUSINESS.RESTAURANT.收油关系映射._config_dict.keys())).split("/")
                for candidate_type in candidate_types:
                    if candidate_type in self.inst.rest_chinese_name:
                        self.inst.rest_type = candidate_type
                        LOGGER.info(f"已直接通过餐厅名为餐厅 '{self.inst.rest_chinese_name}' 推断类型: {self.inst.rest_type}")
                        return True
                    else:
                        LOGGER.warning(f"未找到餐厅类型，尝试使用KIMI API分析")
                        if self.conf and hasattr(self.conf, 'KEYS') and hasattr(self.conf.KEYS, 'kimi_keys'):
                            # 准备餐厅信息
                            rest_info = {
                                'name': self.inst.rest_chinese_name,
                                'address': getattr(self.inst, 'rest_chinese_address', ''),
                                'rest_type': "\n".join(list(self.conf.BUSINESS.RESTAURANT.收油关系映射._config_dict.keys()))
                            }
                            # 调用KIMI API分析餐厅类型
                            def analyze_func(key):
                                return kimi_restaurant_type_analysis(rest_info, key)
                            # 使用robust_query进行健壮性调用
                            rest_type_ans = robust_query(analyze_func, self.conf.KEYS.kimi_keys)
                            rest_type = None
                            for candidate_type in candidate_types:
                                if candidate_type in rest_type_ans:
                                    rest_type = candidate_type
                                    break
                            if rest_type:
                                self.inst.rest_type = rest_type
                                LOGGER.info(f"已通过LLM为餐厅 '{self.inst.rest_chinese_name}' 分析类型: {rest_type}")
                                return True
                            else:
                                # 分析失败，使用默认值
                                self.inst.rest_type = "小食/小吃/美食/饮食/私房菜"
                                LOGGER.warning(f"KIMI API调用失败，使用默认餐厅类型: {self.inst.rest_type}")
                                return True

                        else:
                            # 没有配置KIMI API，使用默认值
                            self.inst.rest_type = "小食/小吃/美食/饮食/私房菜"
                            LOGGER.info(f"未配置KIMI API，使用默认餐厅类型: {self.inst.rest_type}")
                            return True
            else:
                LOGGER.info(f"餐厅 '{self.inst.rest_chinese_name}' 已存在类型: {self.inst.rest_type}")
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
                name = mingzi.mingzi()[0]
                self.inst.rest_contact_person = name
                LOGGER.info(f"已为餐厅生成随机联系人: {self.inst.rest_contact_person}")
            
            if not hasattr(self.inst, 'rest_contact_phone') or not self.inst.rest_contact_phone:
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
                
                ## 获取conf中CP_LOCATION中的cp_id为cp_id的location
                cp_location = None
                for cp_location_item in self.conf.BUSINESS.CP_LOCATION:
                    if cp_location_item['cp_id'] == cp_id:
                        cp_location = cp_location_item['location']
                        break
                
                if not cp_location:
                    LOGGER.warning("警告: 工厂坐标未设置，跳过距离计算")
                    # 给所有餐厅设置一个默认距离
                    self.inst.rest_distance = 0
                else:
                            if not restaurant_location:
                                LOGGER.warning(f"警告: 餐厅{self.inst.rest_chinese_name}没有坐标信息，跳过距离计算")
                                self.inst.rest_distance = 0 
                            else:
                                res_lon, res_lat = map(float, restaurant_location.split(','))  # 假设坐标格式为 "经度,纬度"
                                cp_lon, cp_lat = map(float, cp_location.split(','))  # 假设坐标格式为 "经度,纬度"
                                factory_lat_lon = (cp_lat, cp_lon)
                                distance = self._haversine((res_lat, res_lon), factory_lat_lon)  # 计算距离(维度,经度),(维度,经度)
                                self.inst.rest_distance = distance  
                                LOGGER.info(f"已计算餐厅到CP的距离: {distance}公里")
                # # 使用哈希值来生成一个稳定但随机的距离
                # distance_hash = hash(f"{restaurant_location}_{cp_location}")
                # distance_km = 1 + abs(distance_hash % 20)  # 1-20公里范围内
                
                # self.inst.rest_distance = distance_km
                # LOGGER.info(f"已计算餐厅到CP的距离: {distance_km}公里")
            
            return True
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
        self.inst.rest_verified_date = datetime.now().strftime("%Y-%m-%d")
        LOGGER.info(f"已生成确认日期: {self.inst.rest_verified_date}")
        return True
    
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

        # 生成确认日期
        success &= self._generate_verified_date()
        
        # 如果全部成功，更新状态为就绪
        if success:
            self.status = 'ready'
            self.check()
            LOGGER.info(f"餐厅 '{self.inst.rest_chinese_name}' 的所有字段已生成完成")
        return success
    

    def check(self):
        """
        检查餐厅全部字段都完整
        """
        all_keys = [x for x in self.inst.__dict__.keys() if x.startswith('rest_')]
        for key in all_keys:
            if self.inst.__getattribute__(key) is None and key != 'rest_allocated_barrel' and key != 'rest_verified_date':
                LOGGER.error(f"餐厅 '{self.inst.rest_chinese_name}' 缺少字段: {key}")
                return False
            else:
                LOGGER.info(f"餐厅 '{self.inst.rest_chinese_name}' 字段: {key} 已生成")
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

