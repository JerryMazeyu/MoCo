import json
import requests
import time
import xlwt
import re
from serpapi import GoogleSearch
from geopy.geocoders import Nominatim
import pandas as pd

## 高德、百度、serp调用谷歌地图
class RestaurantInfo:
    def __init__(self, n, token, keywords, address, maptype,filename):
        self.n = n  # 获取多少页
        self.key = token
        if maptype ==1 :
            self.type = '餐饮'
        elif maptype == 2:
            self.type = '美食'
        else:
            self.type = ''
        self.address = address
        self.keywords = keywords
        self.maptype = maptype
        self.filename = filename
        loc = re.match("@?[-+]?\d+(\.\d+)?,\d+(\.\d+)?", self.address)
        if loc:
            gps = address.split(",")
            p1 = float(gps[0])
            p2 = float(gps[1])
            if maptype != 3:
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
            else:
                # 谷歌地图传入经纬度格式为@+维度+经度+z
                # 由于外国经纬度没有确切的大小关系，所以规定使用谷歌地图维度在前，经度在后
                self.address = '@'+gps[0] + ',' + gps[1]+','+'14z' #地图缩放精度暂设为14z

    # 通过默认的搜索获取餐厅信息
    def create_gaode_url(self):
        urls = []
        for i in range(1, self.n + 1):  # page是当前页码，高德是从1开始， offset是每页多少条数据，默认20条

            url = 'https://restapi.amap.com/v3/place/text?key={}&&keywords={}' \
                  '&types={}&city={}&citylimit=true&output={}&offset=20&page={}' \
                  '&extensions=base&show_fields=business'.format(self.key, self.keywords, self.type,
                                                                 self.address,
                                                                 'JSON', i)
            urls.append(url)
        return urls

    # 通过坐标的搜索获附近取餐厅信息
    def create_gaode_around_url(self):
        urls = []
        for i in range(1, self.n + 1):  # page是当前页码，高德是从1开始， offset是每页多少条数据，默认20条

            url = 'https://restapi.amap.com/v5/place/around?key={}' \
                  '&radius=50000&keywords={}&types={}&location={}&offset=20&page={' \
                  '}&extensions=base&show_fields=business'.format(
                self.key, self.keywords, self.type, self.address, i)
            urls.append(url)
        return urls

    def create_baidu_url(self): #行政区划检索
        urls = []
        for i in range(0, self.n):  # page是当前页码，百度是从0开始， offset是每页多少条数据，默认20条

            url = 'https://api.map.baidu.com/place/v2/search?ak={}&query={}&tag={}' \
                  '&region={}&output={}&city_limit=true&page_size=20&page_num={}'.format(
                self.key, self.keywords, self.type, self.address, 'json', i)  #tag是没事
            urls.append(url)
        return urls

    def create_baidu_around_url(self):
        urls = []
        for i in range(0, self.n):  # page是当前页码，百度是从0开始， offset是每页多少条数据，默认20条

            url = 'https://api.map.baidu.com/place/v2/search?ak={}&query={}&tag={}' \
                  '&location={}&radius=5000&output={}&page_size=20&page_num={}'.format(
                self.key, self.keywords, self.type, self.address, 'json', i)
            urls.append(url)
        return urls


    # 谷歌地图通过行政区划搜索获取餐厅信息
    def create_google_url(self):
        params_list = []
        for i in range(0,self.n):
            params_list.append({'engine': "google_local",
            "q": self.keywords, 
            'location': self.address,
            "api_key": self.key,
            "start":i*20})  # 谷歌地图分页参数，0-第一页，20-第二页，40-第三页
        return params_list
    
    # 谷歌地图通过经纬度搜索获取餐厅信息
    def create_google_around_url(self):
        params_list = []
        for i in range(0,self.n):
            params_list.append({'engine': "google_maps",
            "q": self.keywords, 
            'll': '@'+self.address+',14z',
            'type': "search",
            "api_key": self.key,
            "start":i*20})  # 谷歌地图分页参数，0-第一页，20-第二页，40-第三页
        return params_list
        
    def get_gaode_restaurant(self, urls):
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
                    print(i)
                    j += 1
                    print(j)
                    dict1 = {'name': i.get('name'), 'address': i.get('address'), 'tel': i.get('tel')}
                    datalist.append(dict1)
            else:
                break
        return datalist

    def get_baidu_restaurant(self, urls):
        j = 0
        datalist = []
        for url in urls:
            print(url)
            res = requests.request('GET', url=url)
            time.sleep(1)
            res = json.loads(res.text)
            l = res.get('results')
            # print(l)
            if l is not None and len(l)>0:
                
                for i in l:
                    print(i)
                    j += 1
                    print(j)
                    dict1 = {'name': i.get('name'), 'address': i.get('address'),
                            'tel': i.get('telephone')}
                    datalist.append(dict1)
            else:
                break
        return datalist

    def get_google_restaurant(self, params_list):
        j = 0
        datalist = []
        for params in params_list:
            print(params)
            try:
                search = GoogleSearch(params)
                res = search.get_dict()
                time.sleep(10)
                l = res["local_results"]
            # print(l)
                if l is not None and len(l)>0:

                    for i in l:
                        print()
                        j += 1
                        print(j)
                        dict1 = {'name': i.get('title'), 'address': i.get('address'),'tel': i.get('phone')
                                #  ,'type':i.get('type'),'types':i.get('types'),'latitude':i.get("gps_coordinates")['latitude'],
                                # 'longitude':i.get("gps_coordinates")['longitude'],
                                # 'rating':i.get('rating'),'reviews':i.get('reviews'),
                                # 'open_state':i.get('open_state'),
                                # "operating_hours":i.get('operating_hours'),
                                # "service_options":i.get('service_options')
                                }
                        datalist.append(dict1)
                else:
                    break  
            except:
                break
        return datalist


    def write_to_excel(self, datalist, filename):
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


    ## google
    def write_to_excel_google(self, datalist, filename):

        book = xlwt.Workbook(encoding='utf-8', style_compression=0)
        sheet = book.add_sheet('餐厅', cell_overwrite_ok=True)
        column_title = ['店名','地址','电话'
                        # ,'餐厅类型','餐厅类型_多类','餐厅纬度','餐厅经度','餐厅评分','餐厅评论数','餐厅营业时间',
                        # '餐厅每天营业时间','提供的服务类型'
                        ]
        for i in range(len(column_title)):
            sheet.write(0,i,column_title[i])
        for i in range(len(datalist)):
            j=0
            for value in datalist[i].values():
                sheet.write(i + 1, 0+j, str(value))
                j = j+1

        book.save(filename)  # r'东莞市.xlsx'
        print('save success')

    def get_info_write_file(self):
        # 如果是输入的坐标，直接匹配周边搜索
        loc = re.match("@?[-+]?\d+(\.\d+)?,\d+(\.\d+)?", self.address)
        if self.maptype == 1:
            if loc:
                urls = self.create_gaode_around_url()
            else:
                urls = self.create_gaode_url()
            types = '高德'
            restaurantList = self.get_gaode_restaurant(urls)
        if self.maptype == 2:
            if loc:
                urls = self.create_baidu_around_url()
            else:
                urls = self.create_baidu_url()
            types = '百度'
            restaurantList = self.get_baidu_restaurant(urls)
        if self.maptype == 3:
            if loc:
                urls = self.create_google_around_url()
            else:
                urls = self.create_google_url()
            types = 'google'
            restaurantList = self.get_google_restaurant(urls)
        print(len(restaurantList))
        ## 写入excel
        # fileName = types + '-' + self.address + '-' + self.keywords + '.xls'
        # if self.maptype == 3:
        #     self.write_to_excel_google(restaurantList, self.filename)
        # else:
        #     self.write_to_excel(restaurantList, self.filename)
        ## 返回datalist
        return restaurantList



if __name__ == '__main__':
    # 地图key
    # c = RestaurantInfo(20, key, '火锅','餐饮', '东莞市',1)
    # c = RestaurantInfo(25, key, '中餐','餐饮', '东莞市',1)
    # c = RestaurantInfo(25, key, '外国餐厅','餐饮', '东莞市',1)
    # 百度大类是美食，高德大类是餐饮
    # key = 'bDIXrHBLFe7s9ojCVtZjxxLlEhrZNbWg'  # 百度地图示例
    # #       页数  地图key 搜到字段  类型（不变） 城市(可以是坐标)  接口类型：2-百度，1-高德
    # # c = RestaurantInfo(25, key, '快餐', '美食', '23.019135,113.74483', 2)
    # c = RestaurantInfo(25, key, '火锅', '美食', '东莞市', 2)
    # c.get_info_write_file()

    # # 高德地图示例
    key = '4bd94b7b4fed38f78e13d1055dd0f7ce'  # 注意坐标，高德和百度经纬度是不一样的
    # c = RestaurantInfo(25, key, '快餐', '餐饮', '113.74483,23.019135', 1)
    c = RestaurantInfo(5, key, '火锅', '餐饮服务', '杭州', 1,'d:/git/Git/program/MOCO/MoCo-main/test.xlsx')
    c.get_info_write_file()

    # 谷歌地图serp示例，每次调用每一页至多返回20条，第三个参数默认为英语，第四个参数无作用
    # google_key = '8fee04febd8ef9f2ef5e3732b9a81519e8e97fea28687e8f7aaf5a43c0a1cd50'
    # c = RestaurantInfo(12, google_key, 'restaurant', '美食', '1.666889,101.400299', 3)
    # c.get_info_write_file()