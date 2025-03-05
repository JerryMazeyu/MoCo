from app.services.map_api_service import RestaurantInfo
from app.utils.logger import setup_logger
from geopy.geocoders import Nominatim
import xlwt
import random
import time

def flow5_get_restaurantinfo(n: int, token: str, keywords: str, address: str, maptype: int,filename: str):
    c = RestaurantInfo(n, token, keywords, address, maptype,filename)
    restaurantList=c.get_info_write_file()
    return restaurantList

def flow5_write_to_excel(datalist, filename):
        # 一个Workbook对象，这就相当于创建了一个Excel文件
        book = xlwt.Workbook( style_compression=0)
        sheet = book.add_sheet('餐厅', cell_overwrite_ok=True)

        sheet.write(0, 0, '店名')
        sheet.write(0, 1, '地址')
        sheet.write(0, 2, '电话')
        sheet.write(0, 3, '坐标')
        sheet.write(0, 4, '所属区县')
        sheet.write(0, 5, '类型')
        sheet.write(0, 6, '距离')
        sheet.write(0, 7, '城市')


        for i in range(len(datalist)):
            sheet.write(i + 1, 0, datalist[i]['name'])
            sheet.write(i + 1, 1, datalist[i]['address'])
            sheet.write(i + 1, 2, datalist[i]['tel'])
            sheet.write(i + 1, 3, datalist[i]['location'])
            sheet.write(i + 1, 4, datalist[i]['adname'])
            sheet.write(i + 1, 5, datalist[i]['type'])
            sheet.write(i + 1, 6, datalist[i]['distance'])
            sheet.write(i + 1, 7, datalist[i]['cityname'])

        book.save(filename)  # r'东莞市.xlsx'
        print('save success')
## 根据地区获得经纬度
def flow5_location_change(city_name):
    gps = Nominatim(user_agent='myuseragent')
    location = gps.geocode(city_name)
    try:
        lont_lat=(str(location.latitude)+','+str(location.longitude))
    except:
        pass
    return lont_lat

## 测试API连通性的模拟函数
def flow5_test_api_connectivity(api_type, api_key):
    """
    测试指定API的连通性
    
    参数:
        api_type (str): API类型，可以是 "kimi", "gaode", "baidu", "serp", "tripadvisor"
        api_key (str): API密钥
        
    返回:
        bool: 连通测试是否成功
        str: 错误消息（如果有）
    """
    print(f"正在测试{api_type} API连通性，API密钥: {api_key[:5]}***")
    
    # 模拟网络延迟
    time.sleep(1)
    
    # 模拟API连通性测试结果
    # 在实际实现中，这里应该发送实际的API请求来检测连通性
    success_rate = {
        "kimi": 0.9,        # 90%成功率
        "gaode": 0.95,      # 95%成功率
        "baidu": 0.85,      # 85%成功率
        "serp": 0.8,        # 80%成功率
        "tripadvisor": 0.7  # 70%成功率
    }
    
    # 检查API密钥不为空
    if not api_key:
        return False, "API密钥无效或为默认值"
        
    # 随机模拟测试结果
    is_success = random.random() < success_rate.get(api_type, 0.5)
    
    if is_success:
        return True, "API连接成功"
    else:
        error_messages = {
            "kimi": "Kimi API返回401错误，请检查密钥是否有效",
            "gaode": "高德API请求超时，请稍后重试",
            "baidu": "百度API返回权限错误，请检查密钥权限",
            "serp": "SERP API返回配额已用尽错误",
            "tripadvisor": "TripAdvisor API连接被拒绝"
        }
        return False, error_messages.get(api_type, "未知错误")