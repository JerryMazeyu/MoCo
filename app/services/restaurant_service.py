import pandas as pd
from typing import List
from app.models.restaurant_model import Restaurant
from app.config import get_config
from typing import Optional, Union
from app.utils.logger import setup_logger
import requests
import json
import re


CONF = get_config()
RESTCONF_NAME_MAP = CONF.BUSINESS.RESTAURANT.餐厅对应关系

class RestaurantService:

    def __init__(self):
        self.restaurants = []
        self.restaurants_df = None
        self.logger = setup_logger("moco.log")
    
    def call_kimi_api(self, query, api_key=None):
        """
        调用KiMi API进行搜索
        
        :param query: 搜索查询
        :param api_key: API密钥，如果为None则从配置文件中获取
        :return: API响应
        """
        if not api_key:
            # 从配置中获取API密钥
            kimi_keys = CONF.get("SYSTEM.kimi_keys", default=[])
            if not kimi_keys or len(kimi_keys) == 0:
                self.logger.error("未找到KiMi API密钥")
                return None
            api_key = kimi_keys[0]  # 使用第一个密钥
        
        self.logger.info(f"调用KiMi API进行搜索: {query}")
        
        # KiMi API的URL和请求头
        url = "https://kimi.moonshot.cn/api/chat"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 构建请求体
        payload = {
            "model": "moonshot-v1-128k",
            "messages": [
                {
                    "role": "user",
                    "content": f"请帮我联网搜索：{query}，返回简洁的结果。"
                }
            ],
            "temperature": 0.7,
            "tools": [
                {
                    "type": "web_search"
                }
            ]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # 如果响应状态码不是200，则抛出异常
            
            response_data = response.json()
            self.logger.info(f"KiMi API响应: {response_data}")
            
            # 提取回答内容
            if "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0]["message"]["content"]
                return content
            else:
                self.logger.warning("KiMi API响应格式不正确")
                return None
                
        except Exception as e:
            self.logger.error(f"调用KiMi API时出错: {str(e)}")
            return None
    
    def load(self, file: Union[str, pd.DataFrame]) -> List[Restaurant]:
        """加载餐厅数据"""
        if isinstance(file, str):
            self.restaurants_df = self.load_df(file)
            self.restaurants = self.load_from_df(self.restaurants_df)
        elif isinstance(file, pd.DataFrame):
            self.restaurants_df = file
            self.restaurants = self.load_from_df(file)

    
    @staticmethod
    def load_df(file_path: str) -> pd.DataFrame:
        """从 Excel 文件中加载餐厅数据并返回 DataFrame"""
        return pd.read_excel(file_path)

    @staticmethod
    def load_from_df(df: pd.DataFrame) -> List[Restaurant]:
        """从 DataFrame 中加载餐厅数据并返回餐厅对象列表"""
        restaurants = []
        
        for _, row in df.iterrows():
            other_info = {}

            restaurant_data = {
                "chinese_name": row.get(RESTCONF_NAME_MAP.chinese_name, ""),
                "english_name": row.get(RESTCONF_NAME_MAP.english_name, None),
                "chinese_address": row.get(RESTCONF_NAME_MAP.chinese_address, ""),
                "english_address": row.get(RESTCONF_NAME_MAP.english_address, None),
                "restaurant_type": row.get("restaurant_type", None),

                "location": row.get(RESTCONF_NAME_MAP.location, ""),

                "district": row.get(RESTCONF_NAME_MAP.district, ""),
                "city": row.get(RESTCONF_NAME_MAP.city, ""),
                "province": row.get(RESTCONF_NAME_MAP.province, ""),
                "street": row.get("street", None),

                "contact_person_zh": row.get(RESTCONF_NAME_MAP.contact_person_zh, ""),
                "contact_person_en": row.get(RESTCONF_NAME_MAP.contact_person_en, None),
                "contact_phone": str(row.get(RESTCONF_NAME_MAP.contact_phone, "")),
                
                "distance_km": row.get(RESTCONF_NAME_MAP.distance_km, ""),
                "distance_mile": row.get(RESTCONF_NAME_MAP.distance_mile, None),
            }
            
            # 收集其他未映射字段
            for col_name in row.index:
                if col_name not in list(RESTCONF_NAME_MAP._config_dict.values()):
                    other_info[col_name] = row[col_name]
            
            # 初始化餐厅对象并填充默认值
            restaurant = Restaurant(**restaurant_data, other_info=other_info)
            restaurant.fill_defaults()
            restaurants.append(restaurant)
        return restaurants
    
    @staticmethod
    def load_from_excel(file_path: str) -> List[Restaurant]:
        """从 Excel 文件中批量加载餐厅数据并返回餐厅对象列表"""
        df = pd.read_excel(file_path)
        restaurants = []
        
        for _, row in df.iterrows():
            other_info = {}

            restaurant_data = {
                "chinese_name": row.get(RESTCONF_NAME_MAP.chinese_name, ""),
                "english_name": row.get(RESTCONF_NAME_MAP.english_name, None),
                "chinese_address": row.get(RESTCONF_NAME_MAP.chinese_address, ""),
                "english_address": row.get(RESTCONF_NAME_MAP.english_address, None),

                "location": row.get(RESTCONF_NAME_MAP.location, ""),

                "district": row.get(RESTCONF_NAME_MAP.district, ""),
                "city": row.get(RESTCONF_NAME_MAP.city, ""),
                "province": row.get(RESTCONF_NAME_MAP.province, ""),

                "contact_person_zh": row.get(RESTCONF_NAME_MAP.contact_person_zh, ""),
                "contact_person_en": row.get(RESTCONF_NAME_MAP.contact_person_en, None),
                "contact_phone": str(row.get(RESTCONF_NAME_MAP.contact_phone, "")),
                
                "distance_km": row.get(RESTCONF_NAME_MAP.distance_km, ""),
                "distance_mile": row.get(RESTCONF_NAME_MAP.distance_mile, None),
            }
            
            # 收集其他未映射字段
            for col_name in row.index:
                if col_name not in list(RESTCONF_NAME_MAP._config_dict.values()) and col_name != "restaurant_type" and col_name != "street":
                    other_info[col_name] = row[col_name]
            
            # 初始化餐厅对象并填充默认值
            restaurant = Restaurant(**restaurant_data, other_info=other_info)
            restaurant.fill_defaults()  # 自动填充默认值
            restaurants.append(restaurant)
        
        return restaurants


    @staticmethod
    def save_to_excel(restaurants: List[Restaurant], file_path: str):
        """将餐厅数据保存到 Excel 文件"""
        data = [restaurant.model_dump_with_mapping() for restaurant in restaurants]
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False)
    
    
    def extract_street_base_batch(self, use_llm=False) -> pd.DataFrame:
        """
        批量生成街道候选列表
        
        :param use_llm: 是否使用LLM辅助查询
        :return: 更新后的DataFrame和餐厅列表
        """
        tmp = []
        for restaurant in self.restaurants:
            try:
                candidate_street = self.extract_street_base(
                    restaurant.city, 
                    restaurant.district, 
                    restaurant.chinese_address, 
                    use_llm=use_llm,
                    restaurant_name=restaurant.chinese_name
                )
                setattr(restaurant, "street", candidate_street)
                tmp.append(restaurant)
            except Exception as e:
                self.logger.error(f"生成街道候选列表时出错: {str(e)}")
        self.restaurants = tmp
        data = [restaurant.model_dump_with_mapping() for restaurant in self.restaurants]
        self.restaurants_df = pd.DataFrame(data)
        # self.restaurants = self.load_from_df(self.restaurants_df)
        self.logger.info(f"*街道候选列表生成成功。")
        return self.restaurants_df, self.restaurants


    def extract_street_base(self, city: str, district: str, address: str, use_llm=False, restaurant_name=None) -> Optional[str]:
        """
        根据城市、区域和地址从配置中匹配对应的街道。
        
        :param city: 城市名称（如：惠州市）
        :param district: 区域名称（如：博罗县）
        :param address: 完整地址字符串（如：惠州市博罗县石湾镇兴业大道东侧壹嘉广场1楼）
        :param use_llm: 是否使用LLM辅助查询
        :param restaurant_name: 餐厅名称，用于LLM查询时提供更多上下文
        :return: 匹配到的街道名称，如果没有匹配到则返回 None
        """
        # 获取城市和区域对应的街道列表
        streets = self._get_streets_from_config(city, district)

        if not streets:
            return None  # 如果没有配置对应的街道列表，返回 None
            
        # 从地址中提取街道名
        street = self._extract_street_from_address(streets, address)
        
        # 如果常规匹配没有结果且启用了LLM，则使用KiMi API进行查询
        if street is None and use_llm and streets:
            self.logger.info(f"使用LLM查询街道: {city} {district} {restaurant_name} {address}")
            query = f"在{city}{district}中，'{address}'这个地址属于哪个街道？可能的街道有：{', '.join(streets)}"
            
            if restaurant_name:
                query += f"，餐厅名称为'{restaurant_name}'"
                
            kimi_response = self.call_kimi_api(query)
            
            if kimi_response:
                # 在KiMi响应中查找所有可能的街道
                found_streets = []
                for street_name in streets:
                    if street_name in kimi_response:
                        found_streets.append(street_name)
                
                if found_streets:
                    # 如果找到多个街道，选择第一个
                    street = found_streets[0]
                    self.logger.info(f"通过LLM找到街道: {street}")
                else:
                    self.logger.info(f"LLM未能匹配到任何街道")
        
        return street


    def _get_streets_from_config(self, city: str, district: str) -> Optional[list]:
        """
        从配置文件中获取指定城市和区域的街道列表。
        
        :param city: 城市名称
        :param district: 区域名称
        :return: 对应的街道列表或 None
        """
        try:
            return CONF._config["BUSINESS"]["RESTAURANT"]["街道图"][city][district]
        except KeyError:
            # 如果城市或区域不存在于配置中，返回 None
            return None


    def _extract_street_from_address(self, streets: list, address: str) -> Optional[str]:
        """
        从地址中匹配街道名。
        
        :param streets: 街道名称列表
        :param address: 完整地址字符串
        :return: 匹配到的街道名或 None
        """
        for street in streets:
            if street in address:
                return street
        return None


    def assign_restaurant_type_base(self, name: str, address: str, use_llm=False) -> Optional[str]:
        """
        根据餐厅名称和地址匹配对应的餐厅类型。
        
        :param name: 餐厅名称
        :param address: 餐厅地址
        :param use_llm: 是否使用LLM辅助查询
        :return: 匹配到的餐厅类型，如果没有匹配到则返回 None
        """
        # 获取所有可能的餐厅类型映射
        name_mapping = RESTCONF_NAME_MAP

        # 在名称中查找关键字
        restaurant_type = None
        for keyword, res_type in name_mapping.items():
            if keyword in name:
                restaurant_type = res_type
                break

        # 如果在名称中没有找到，则在地址中查找
        if not restaurant_type:
            for keyword, res_type in name_mapping.items():
                if keyword in address:
                    restaurant_type = res_type
                    break
                    
        # 如果常规匹配没有结果且启用了LLM，则使用KiMi API进行查询
        if restaurant_type is None and use_llm:
            self.logger.info(f"使用LLM查询餐厅类型: {name} {address}")
            
            # 准备关键字列表用于查询
            keywords = list(name_mapping.keys())
            query = f"餐厅'{name}'位于'{address}'，它可能是以下哪种类型的餐厅？{', '.join(keywords)}"
            
            kimi_response = self.call_kimi_api(query)
            
            if kimi_response:
                # 在KiMi响应中查找所有可能的关键字
                found_keywords = []
                for keyword in keywords:
                    if keyword in kimi_response:
                        found_keywords.append(keyword)
                
                if found_keywords:
                    # 如果找到多个关键字，选择第一个
                    matched_keyword = found_keywords[0]
                    restaurant_type = name_mapping[matched_keyword]
                    self.logger.info(f"通过LLM找到餐厅类型: {matched_keyword} -> {restaurant_type}")
                else:
                    self.logger.info(f"LLM未能匹配到任何餐厅类型")

        return restaurant_type

    def extract_restaurant_type_batch(self, use_llm=False) -> pd.DataFrame:
        """
        批量生成餐厅类型
        
        :param use_llm: 是否使用LLM辅助查询
        :return: 更新后的DataFrame和餐厅列表
        """
        tmp = []
        for restaurant in self.restaurants:
            try:
                restaurant_type = self.assign_restaurant_type_base(
                    restaurant.chinese_name, 
                    restaurant.chinese_address,
                    use_llm=use_llm
                )
                setattr(restaurant, "restaurant_type", restaurant_type)
                tmp.append(restaurant)
            except Exception as e:
                self.logger.error(f"生成餐厅类型时出错: {str(e)}")
        self.restaurants = tmp
        data = [restaurant.model_dump_with_mapping() for restaurant in self.restaurants]
        self.restaurants_df = pd.DataFrame(data)
        self.restaurants = self.load_from_df(self.restaurants_df)
        self.logger.info(f"*餐厅类型生成成功。")
        return self.restaurants_df, self.restaurants


if __name__ == "__main__":
    rests = RestaurantService.load_from_excel(r"F:\WorkSpace\Project2025\MoCo\app\assets\餐厅信息.xlsx")
    RestaurantService.save_to_excel(rests, r"F:\WorkSpace\Project2025\MoCo\app\assets\餐厅信息2.xlsx")
