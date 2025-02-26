from app.services.map_api_service import RestaurantInfo
from app.utils.logger import setup_logger
from geopy.geocoders import Nominatim
import xlwt

def flow5_get_restaurantinfo(n: int, token: str, keywords: str, address: str, maptype: int,filename: str):
    c = RestaurantInfo(n, token, keywords, address, maptype,filename)
    restaurantList=c.get_info_write_file()
    return restaurantList

def flow5_write_to_excel( datalist, filename):
        # 一个Workbook对象，这就相当于创建了一个Excel文件
        book = xlwt.Workbook( style_compression=0)
        sheet = book.add_sheet('餐厅', cell_overwrite_ok=True)

        sheet.write(0, 0, '店名')
        sheet.write(0, 1, '地址')
        sheet.write(0, 2, '电话')

        for i in range(len(datalist)):
            sheet.write(i + 1, 0, datalist[i]['name'])
            sheet.write(i + 1, 1, datalist[i]['address'])
            sheet.write(i + 1, 2, datalist[i]['tel'])

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