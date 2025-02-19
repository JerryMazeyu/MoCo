import sys,os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel, QMessageBox, QComboBox, QTableView,QDialog
from PyQt5.QtCore import Qt,QCoreApplication
import pandas as pd
from PyQt5.QtGui import QStandardItemModel, QStandardItem,QIntValidator  
from app.controllers import flow5_get_restaurantinfo,flow5_location_change,flow5_write_to_excel
from app.config import get_config
from app.utils import rp, setup_logger
import xlrd



class Tab5(QWidget):
    def __init__(self):
        super().__init__()
        self.conf = get_config()
        # 设置窗口标题
        self.setWindowTitle('餐厅获取')
        
        # 初始化变量
        self.city_input_value = "" # 城市名
        self.keywords_input_value = "" # 餐厅关键词
        self.city_lat_lon = "" # 经纬度
        self.api_type = "高德地图"  # 默认API类型
        self.page_number = 1

        # 主布局
        main_layout = QVBoxLayout()
        
        # 第一行：城市输入框、确定和重置按钮
        first_row_layout = QHBoxLayout()
        self.city_input = QLineEdit(self)
        self.city_input.setPlaceholderText("城市")
        self.city_input.setFixedWidth(200)  # 固定输入框大小
        self.confirm_button = QPushButton("确定", self)
        self.reset_button = QPushButton("重置", self)
        self.generate_excel_button = QPushButton("生成餐厅excel", self)
        self.view_results_button = QPushButton("查看餐厅获取结果", self)
        first_row_layout.addWidget(self.city_input)
        first_row_layout.addWidget(self.confirm_button)
        first_row_layout.addWidget(self.reset_button)
        first_row_layout.addWidget(self.generate_excel_button)
        first_row_layout.addWidget(self.view_results_button)

        main_layout.addLayout(first_row_layout)
        # 连接信号与槽
        self.confirm_button.clicked.connect(self.on_confirm)
        self.reset_button.clicked.connect(self.on_reset)
        # 连接信号与槽
        self.generate_excel_button.clicked.connect(self.on_generate_excel)
        self.view_results_button.clicked.connect(self.on_view_results)

       # 添加表格视图用于显示Excel数据
        self.table_view = QTableView(self)
        main_layout.addWidget(self.table_view)
        
        # 设置主布局到窗口
        self.setLayout(main_layout)  


    def on_confirm(self):
        self.city_input_value = self.city_input.text()
        QMessageBox.information(self, "确认", f"您输入的城市是: {self.city_input_value}")
    
    def on_reset(self):
        self.city_input.clear()
        self.city_input_value = ""
        self.keywords_input_value = ""
        self.type_input_value = ""
        QMessageBox.information(self, "重置", "输入已被重置")
    
    ## 获取配置中的api_key
    def get_selected_api_key(self):
        api_map = {
            "高德地图": "gaode_key",
            "百度地图": "baidu_key",
            "serp_谷歌地图": "serp_key",
            "TripAdvior爬取": "tripadvisor_key"
        }
        # 根据当前选择的API类型获取对应的键名
        key_name = api_map.get(self.api_type, "")
        
        if key_name:
            try:
                # 使用属性访问的方式获取配置值
                return getattr(self.conf.SYSTEM, key_name)
            except AttributeError:
                return ""
        return ""
    ## 获取关键字
    def get_keywords(self):
        oil_mapping = self.conf.get("OTHER.Tab5.关键字", default={})
        keyword_lists = oil_mapping
        keywords = []
        lists = keyword_lists.split('/')
        keywords.extend(lists)
        keywords_list = list(set(keywords))
        return keywords_list
    ## 生成excel提示框
    def show_centered_message(self, title, text):
        """显示居中的消息框"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        # 计算居中位置
        geom = self.frameGeometry()
        center = geom.center()
        msg_box.move(int(center.x() - msg_box.sizeHint().width() / 2),
                     int(center.y() - msg_box.sizeHint().height() / 2))
        msg_box.show()
        return msg_box
    
    def remove_duplicates(self,input_list):
        seen = set()
        new_list = []
        for d in input_list:
            # 将字典项转换为元组，以便能够放入集合中进行比较
            item_tuple = tuple(sorted(d.items()))
            if item_tuple not in seen:
                seen.add(item_tuple)
                new_list.append(d)
        return new_list
    ## 生成excel
    def on_generate_excel(self):
        if not self.city_input_value:
            QMessageBox.warning(self, "警告", "请先输入城市并点击确定")
            return
        else:
            # 显示正在生成Excel的信息
            progress_msg = self.show_centered_message("信息", "Excel文件正在生成中，请稍候...")
            QCoreApplication.processEvents()  # 强制刷新事件循环以立即显示消息框


            ## 地名转化为经纬度，如果转不了就用地面
            try:
                try:
                    self.city_lat_lon  = flow5_location_change(self.city_input_value)
                except:
                    self.city_lat_lon = self.city_input_value

                self.restaurantList=[]
                # 动态生成保存路径
                sanitized_city = "".join([c if c.isalnum() or c.isspace() else "_" for c in self.city_input_value])
                self.default_save_path = os.path.join(os.getcwd(), f"{sanitized_city}__restaurant_data.xlsx")
                #获取关键字
                keywords_list= self.get_keywords()
                for api_type in ["百度地图"
                                # ,"高德地图" 
                                #  ,"serp_谷歌地图"
                                ]:
                    self.api_type = api_type
                    # 获取 api_key
                    self.api_key = self.get_selected_api_key()
                    api_number_map = {
                        "高德地图": 1,
                        "百度地图": 2,
                        "serp_谷歌地图": 3,
                        "TripAdvior爬取": 4
                    }
                    # 获取api对应的number
                    api_number = api_number_map.get(self.api_type, 0)

                    #循环关键字
                    for key_words in keywords_list:
                        
                        self.keywords_input_value = key_words
                        print(self.keywords_input_value, api_type,self.default_save_path,sep='\n')
                        restaurantList_api = flow5_get_restaurantinfo(self.page_number,self.api_key, self.keywords_input_value,self.city_lat_lon , api_number,self.default_save_path)
                        self.restaurantList.extend(restaurantList_api)

                print(self.restaurantList)            
                self.restaurantList = self.remove_duplicates(self.restaurantList)
                flow5_write_to_excel(self.restaurantList,self.default_save_path)
                # 关闭正在生成的消息框
                progress_msg.close()

                    # 显示成功消息
                success_msg = self.show_centered_message("成功", f"Excel文件已保存至: {self.default_save_path}")
                success_msg.exec_()

            except Exception as e:
                # 关闭正在生成的消息框
                progress_msg.close()

                # 显示错误信息
                error_msg = self.show_centered_message("错误", f"Excel文件生成失败: {str(e)}")
                error_msg.exec_()
            
    # 展示excel
    def on_view_results(self):
        if hasattr(self, 'default_save_path') and os.path.exists(self.default_save_path):
            df = pd.read_excel(self.default_save_path)
            model = self.pandas_to_model(df)
            self.table_view.setModel(model)
        else:
            QMessageBox.warning(self, "警告", "找不到生成的Excel文件")
    

    def pandas_to_model(self, df):
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(df.columns)
        for row in df.itertuples(index=False):
            data_row = []
            for col in row:
                item = QStandardItem(str(col))
                data_row.append(item)
            model.appendRow(data_row)
        return model
    

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    restaurant_fetcher = Tab5()
    restaurant_fetcher.show()
    
    # 进入应用程序的主循环
    sys.exit(app.exec_())