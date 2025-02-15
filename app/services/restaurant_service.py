import pandas as pd
from typing import List
from app.models.restaurant_model import Restaurant
from app.config import get_config
from typing import Optional, Union
from app.utils.logger import setup_logger


CONF = get_config()
RESTCONF_NAME_MAP = CONF.BUSINESS.RESTAURANT.餐厅对应关系

class RestaurantService:

    def __init__(self):
        self.restaurants = []
        self.restaurants_df = None
        self.logger = setup_logger("moco.log")
    
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
    
    
    def extract_street_base_batch(self) -> pd.DataFrame:
        """批量生成街道候选列表"""
        tmp = []
        for restaurant in self.restaurants:
            try:
                candidate_street = self.extract_street_base(restaurant.city, restaurant.district, restaurant.chinese_address)
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


    def extract_street_base(self, city: str, district: str, address: str) -> Optional[str]:
        """
        根据城市、区域和地址从配置中匹配对应的街道。
        
        :param city: 城市名称（如：惠州市）
        :param district: 区域名称（如：博罗县）
        :param address: 完整地址字符串（如：惠州市博罗县石湾镇兴业大道东侧壹嘉广场1楼）
        :return: 匹配到的街道名称，如果没有匹配到则返回 None
        """
        # 获取城市和区域对应的街道列表
        streets = self._get_streets_from_config(city, district)

        if not streets:
            return None  # 如果没有配置对应的街道列表，返回 None
        # 从地址中提取街道名
        return self._extract_street_from_address(streets, address)


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


    def assign_restaurant_type_base(self, name: str, address: str) -> Optional[str]:
        """
        根据餐厅名称或地址分配餐厅类型
        :param name: 餐厅名称
        :param address: 餐厅地址
        :return: 匹配到的餐厅类型关键字
        """
        type_mapping = CONF.get("BUSINESS.RESTAURANT.收油关系映射", {})
        matched_types = []

        for keywords, values in type_mapping.items():
            for keyword in keywords.split("/"):
                if keyword in name or keyword in address:
                    # 解析配置的类型编号并获取最大值
                    possible_values = [int(v) for v in str(values).split(",")]
                    max_value = max(possible_values)
                    matched_types.append((keywords, max_value))

        if not matched_types:
            return None  # 未匹配到任何类型

        # 按最大值降序排序，选择最大值对应的关键字
        matched_types.sort(key=lambda x: x[1], reverse=True)
        return matched_types[0][0]  # 返回最大值对应的关键字组（例如“酒楼/酒家/烤鱼”）


    def extract_restaurant_type_batch(self) -> pd.DataFrame:
        """批量生成餐厅类型"""
        tmp = []
        for restaurant in self.restaurants:
            try:
                restaurant_type = self.assign_restaurant_type_base(restaurant.chinese_name, restaurant.chinese_address)
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
