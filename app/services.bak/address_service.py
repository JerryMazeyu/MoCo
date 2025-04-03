import re
import requests
from typing import Optional
from app.config import CONF

class AddressService:
    def __init__(self, config=CONF):
        self.config = config
        self.apikeys = self.config.SYSTEM.apikeys

    def extract_town_from_address(self, address: str, city: str, district: str) -> Optional[str]:
        """
        从地址中提取镇级地址，如果找不到，则使用高德地图 API 进行查询
        """
        # 获取当前城市和区县的配置镇信息
        configured_towns = self.config.get(f"BUSINESS.RESTAURANT.districts.{city}.{district}", [])

        # 正则模式匹配 “镇” 或 “街道”
        town_pattern = re.compile(r"(.*?(镇|街道))")

        match = town_pattern.search(address)
        if match:
            potential_town = match.group(1)
            # 检查匹配到的镇名是否在配置文件中
            if any(potential_town in town for town in configured_towns):
                return potential_town
            else:
                # 如果镇名未在配置中直接匹配上，也允许返回找到的值
                return potential_town

        # 如果没有匹配到 “镇” 或 “街道”，使用高德地图 API 进行查询
        return self._query_town_from_location(address)

    def _query_town_from_location(self, location: str) -> Optional[str]:
        """
        使用高德地图 API 根据经纬度查询镇/街道信息
        """
        amap_api_key = self.config.get("SYSTEM.amap_api_key", "")
        api_url = f"https://restapi.amap.com/v3/geocode/regeo?location={location}&key={amap_api_key}"

        response = requests.get(api_url)
        if response.status_code == 200:
            data = response.json()
            # 提取返回地址中的 “乡镇” 字段
            town_name = data.get("regeocode", {}).get("addressComponent", {}).get("township")
            return town_name
        return None
