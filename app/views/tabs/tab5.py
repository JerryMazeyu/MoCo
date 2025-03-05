import sys,os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, 
    QLabel, QMessageBox, QComboBox, QTableView, QDialog, QGroupBox, QScrollArea,
    QGridLayout, QListWidget, QListWidgetItem, QFrame, QSizePolicy, QCheckBox,
    QSplitter
)
from PyQt5.QtCore import Qt, QCoreApplication
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIntValidator, QDoubleValidator, QColor, QPalette
import pandas as pd
from app.controllers import flow5_get_restaurantinfo, flow5_location_change, flow5_write_to_excel, flow5_test_api_connectivity
from app.config import get_config
from app.utils import rp, setup_logger
import xlrd
import math



class ApiStatusIndicator(QLabel):
    """API连通性状态指示器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)  # 尺寸稍微加大一点
        # 确保无文本显示
        self.setText("")
        self.setStatus(None)  # 初始状态为未知
        
    def setStatus(self, is_connected):
        """设置连接状态
        
        参数:
            is_connected: None表示未测试，True表示连接成功，False表示连接失败
        """
        base_style = """
            border-radius: 11px;
            margin: 2px;
        """
        
        if is_connected is None:
            # 灰色 - 未测试
            self.setStyleSheet(base_style + """
                background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, 
                                                 stop:0 #A0A0A0, stop:1 #808080);
                border: 1.5px solid #666666;
            """)
            self.setToolTip("未测试连通性")
        elif is_connected:
            # 绿色 - 连接成功
            self.setStyleSheet(base_style + """
                background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, 
                                                 stop:0 #00D000, stop:1 #00A000);
                border: 1.5px solid #008800;
            """)
            self.setToolTip("连接成功")
        else:
            # 红色 - 连接失败
            self.setStyleSheet(base_style + """
                background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.8, fx:0.5, fy:0.5, 
                                                 stop:0 #FF3030, stop:1 #D00000);
                border: 1.5px solid #AA0000;
            """)
            self.setToolTip("连接失败")


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
        
        # API状态指示器字典
        self.api_indicators = {}
        # 选中的API列表
        self.selected_apis = []

        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建可调整大小的分割器
        top_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter = QSplitter(Qt.Horizontal)
        main_splitter = QSplitter(Qt.Vertical)
        
        # 第一行：城市输入框、工厂坐标部分
        # 城市输入部分
        city_group = QGroupBox("城市")
        city_layout = QVBoxLayout()
        self.city_input = QLineEdit(self)
        self.city_input.setPlaceholderText("输入城市名称")
        city_layout.addWidget(self.city_input)
        city_group.setLayout(city_layout)
        
        # 设置城市输入框的大小策略
        city_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        city_group.setMaximumHeight(100)
        
        # 工厂坐标部分
        factory_group = QGroupBox("工厂坐标")
        factory_layout = QVBoxLayout()
        
        # 经纬度输入框
        coord_layout = QHBoxLayout()
        self.latitude_input = QLineEdit()
        self.latitude_input.setPlaceholderText("纬度")
        self.latitude_input.setValidator(QDoubleValidator())
        self.longitude_input = QLineEdit()
        self.longitude_input.setPlaceholderText("经度")
        self.longitude_input.setValidator(QDoubleValidator())
        coord_layout.addWidget(QLabel("纬度:"))
        coord_layout.addWidget(self.latitude_input)
        coord_layout.addWidget(QLabel("经度:"))
        coord_layout.addWidget(self.longitude_input)
        factory_layout.addLayout(coord_layout)
        
        # 预设工厂坐标按钮区域
        factory_scroll = QScrollArea()
        factory_scroll.setWidgetResizable(True)
        factory_content = QWidget()
        self.factory_buttons_layout = QGridLayout(factory_content)
        
        # 创建工厂按钮
        self.create_factory_buttons()
        
        factory_scroll.setWidget(factory_content)
        factory_layout.addWidget(factory_scroll)
        factory_group.setLayout(factory_layout)
        
        # 设置工厂坐标框的大小策略
        factory_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        factory_group.setMaximumHeight(100)
        
        # 添加到顶部分割器
        top_splitter.addWidget(city_group)
        top_splitter.addWidget(factory_group)
        top_splitter.setSizes([1, 2])  # 设置初始大小比例
        
        # 第二行：关键词和屏蔽词显示
        keywords_group = QGroupBox("查询关键词")
        keywords_layout = QVBoxLayout()
        self.keywords_list = QListWidget()
        self.load_keywords()
        keywords_layout.addWidget(self.keywords_list)
        keywords_group.setLayout(keywords_layout)
        
        # 设置关键词列表的大小策略
        keywords_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        blocked_group = QGroupBox("屏蔽词")
        blocked_layout = QVBoxLayout()
        self.blocked_list = QListWidget()
        self.load_blocked_words()
        blocked_layout.addWidget(self.blocked_list)
        blocked_group.setLayout(blocked_layout)
        
        # 设置屏蔽词列表的大小策略
        blocked_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # 添加到底部分割器
        bottom_splitter.addWidget(keywords_group)
        bottom_splitter.addWidget(blocked_group)
        bottom_splitter.setSizes([1, 1])  # 设置初始大小比例
        
        # 添加到主分割器
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(bottom_splitter)
        main_splitter.setSizes([1, 3])  # 设置初始大小比例
        
        # 添加主分割器到布局
        main_layout.addWidget(main_splitter)
        
        # 添加API选择区域
        api_group = QGroupBox("选择API后端")
        api_layout = QGridLayout()
        
        # API类型及其显示名称映射
        api_types = {
            "kimi": "Kimi AI",
            "gaode": "高德地图",
            "baidu": "百度地图",
            "serp": "SERP",
            "tripadvisor": "TripAdvisor"
        }
        
        row = 0
        col = 0
        max_cols = 3
        
        # 为每个API类型创建复选框和测试按钮
        for api_code, api_name in api_types.items():
            # 复选框
            checkbox = QCheckBox(api_name)
            if api_code == "gaode":  # 默认选择高德地图
                checkbox.setChecked(True)
                self.selected_apis.append(api_code)
            checkbox.stateChanged.connect(lambda state, code=api_code: self.on_api_selected(state, code))
            
            # 测试按钮
            test_button = QPushButton("测试连通性")
            test_button.clicked.connect(lambda checked, code=api_code: self.test_api_connectivity(code))
            
            # 状态指示器
            indicator = ApiStatusIndicator()
            self.api_indicators[api_code] = indicator
            
            # 添加到网格布局
            api_layout.addWidget(checkbox, row, col*3)
            api_layout.addWidget(test_button, row, col*3+1)
            api_layout.addWidget(indicator, row, col*3+2)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)
        
        # 按钮布局
        buttons_layout = QHBoxLayout()
        self.reset_button = QPushButton("重置", self)
        self.generate_excel_button = QPushButton("生成餐厅excel", self)
        self.view_results_button = QPushButton("查看餐厅获取结果", self)
        
        # 添加三个新按钮
        self.verify_button = QPushButton("餐厅智能验证", self)
        self.translate_button = QPushButton("餐厅地址翻译", self)
        self.distance_button = QPushButton("餐厅距离获取", self)
        
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.generate_excel_button)
        buttons_layout.addWidget(self.view_results_button)
        buttons_layout.addWidget(self.verify_button)
        buttons_layout.addWidget(self.translate_button)
        buttons_layout.addWidget(self.distance_button)
        main_layout.addLayout(buttons_layout)
        
        # 连接信号与槽
        self.reset_button.clicked.connect(self.on_reset)
        self.generate_excel_button.clicked.connect(self.on_generate_excel)
        self.view_results_button.clicked.connect(self.on_view_results)
        self.verify_button.clicked.connect(self.on_verify_restaurants)
        self.translate_button.clicked.connect(self.on_translate_addresses)
        self.distance_button.clicked.connect(self.on_calculate_distances)

        # 添加表格视图用于显示Excel数据
        self.table_view = QTableView(self)
        main_layout.addWidget(self.table_view)
        
        # 设置主布局到窗口
        self.setLayout(main_layout)
    
    def on_api_selected(self, state, api_code):
        """处理API选择状态变化"""
        if state == Qt.Checked:
            if api_code not in self.selected_apis:
                self.selected_apis.append(api_code)
        else:
            if api_code in self.selected_apis:
                self.selected_apis.remove(api_code)
    
    def test_api_connectivity(self, api_code):
        """测试指定API的连通性"""
        # 获取API密钥
        api_key = self.get_api_key(api_code)
        
        if not api_key:
            QMessageBox.warning(self, "警告", f"未找到{api_code}的API密钥，请在配置中设置。")
            self.api_indicators[api_code].setStatus(False)
            return
        
        # 显示测试中消息
        QMessageBox.information(self, "测试中", f"正在测试{api_code}的连通性，请稍候...")
        
        try:
            # 调用测试函数
            
            is_connected, message = flow5_test_api_connectivity(api_code, api_key)
            
            # 更新状态指示器
            self.api_indicators[api_code].setStatus(is_connected)
            
            # 显示测试结果
            if is_connected:
                QMessageBox.information(self, "测试成功", f"{api_code} API连接成功！")
            else:                                                                                                                                                                                                                                                                                                                                                                                                                                                              
                QMessageBox.warning(self, "测试失败", f"{api_code} API连接失败：{message}")
        except Exception as e:
            self.api_indicators[api_code].setStatus(False)
            QMessageBox.critical(self, "错误", f"测试过程中发生错误：{str(e)}")
    
    def get_api_key(self, api_code):
        """获取指定API的密钥"""
        api_key_mapping = {
            "kimi": "kimi_keys",
            "gaode": "gaode_keys",
            "baidu": "baidu_keys",
            "serp": "serp_keys",
            "tripadvisor": "tripadvisor_keys"
        }
        api_code = api_code
        key_name = api_key_mapping.get(api_code)
        if not key_name:
            return ""
        
        # 从配置中获取API密钥列表
        key_list = self.conf.get(f"SYSTEM.{key_name}", default=[])
        if key_list and isinstance(key_list, list) and len(key_list) > 0:
            return key_list[0]  # 返回第一个密钥
        return ""
    
    def create_factory_buttons(self):
        """创建工厂坐标按钮"""
        # 清除现有按钮
        while self.factory_buttons_layout.count():
            item = self.factory_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取工厂坐标列表
        factory_coords = self.conf.get("BUSINESS.FACYORY.工厂坐标", default=[])
        if not factory_coords:
            # 如果没有坐标数据，显示提示
            label = QLabel("没有预设工厂坐标")
            self.factory_buttons_layout.addWidget(label, 0, 0)
            return
            
        # 创建工厂按钮
        row, col = 0, 0
        max_cols = 2  # 每行最多显示的按钮数
        
        for factory_item in factory_coords:
            for factory_name, coords in factory_item.items():
                btn = QPushButton(factory_name)
                btn.setToolTip(f"坐标: {coords}")
                # 使用lambda创建函数闭包，传递坐标
                btn.clicked.connect(lambda checked, c=coords: self.set_factory_coords(c))
                self.factory_buttons_layout.addWidget(btn, row, col)
                
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
    
    def set_factory_coords(self, coords):
        """设置工厂坐标到输入框"""
        try:
            lat, lon = coords.split(',')
            self.latitude_input.setText(lat.strip())
            self.longitude_input.setText(lon.strip())
            QMessageBox.information(self, "成功", f"已设置坐标: {lat}, {lon}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法设置坐标: {e}")
    
    def load_keywords(self):
        """从配置加载关键词列表"""
        self.keywords_list.clear()
        keywords = self.conf.get("OTHER.Tab5.关键词", default=[])
        for keyword in keywords:
            self.keywords_list.addItem(keyword)
    
    def load_blocked_words(self):
        """从配置加载屏蔽词列表"""
        self.blocked_list.clear()
        blocked_words = self.conf.get("OTHER.Tab5.屏蔽词", default=[])
        for word in blocked_words:
            self.blocked_list.addItem(word)
    
    def prepare_search(self):
        """准备搜索参数，返回是否可以继续"""
        self.city_input_value = self.city_input.text().strip()
        if not self.city_input_value:
            QMessageBox.warning(self, "警告", "请输入城市名称")
            return False
        
        # 获取工厂经纬度
        lat = self.latitude_input.text().strip()
        lon = self.longitude_input.text().strip()
        self.factory_lat_lon = f"{lat},{lon}"
        
        # 检查是否选择了API
        if not self.selected_apis:
            QMessageBox.warning(self, "警告", "请至少选择一个API后端")
            return False
        
        # 获取关键词列表
        keywords = self.get_keywords()
        if not keywords:
            QMessageBox.warning(self, "警告", "没有找到关键词，请在配置中设置")
            return False
        
        # 构建确认信息
        api_names = [self.get_api_display_name(api) for api in self.selected_apis]
        coord_info = f"坐标: {self.city_lat_lon}" if self.city_lat_lon else "将自动获取城市坐标"
        message = (
            f"确认以下信息:\n\n"
            f"城市: {self.city_input_value}\n"
            f"{coord_info}\n"
            f"使用API: {', '.join(api_names)}\n"
            f"关键词数量: {len(keywords)}个\n\n"
            "是否继续?"
        )
        
        reply = QMessageBox.question(
            self, "确认", message, 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        return reply == QMessageBox.Yes
    
    def get_api_display_name(self, api_code):
        """获取API的显示名称"""
        api_names = {
            "kimi": "Kimi AI",
            "gaode": "高德地图",
            "baidu": "百度地图",
            "serp": "SERP 谷歌地图",
            "tripadvisor": "TripAdvisor"
        }
        return api_names.get(api_code, api_code)
    
    def on_reset(self):
        """重置所有输入字段"""
        self.city_input.clear()
        self.latitude_input.clear()
        self.longitude_input.clear()
        self.city_input_value = ""
        self.keywords_input_value = ""
        self.city_lat_lon = ""
        QMessageBox.information(self, "重置", "所有输入已被重置")
    
    def get_selected_api_key(self, api_code):
        """获取指定API的密钥"""
        return self.get_api_key(api_code)
    
    ## 获取关键字
    def get_keywords(self):
        keywords = []
        for i in range(self.keywords_list.count()):
            keywords.append(self.keywords_list.item(i).text())
        return keywords
    ## 获取屏蔽字
    def get_blocked_words(self):
        blocked_words = []
        for i in range(self.blocked_list.count()):
            blocked_words.append(self.blocked_list.item(i).text())
        return blocked_words
    
    ## 计算两个经纬度之间的距离（单位：公里）
    def haversine(self,coord1, coord2):
        """计算两个经纬度之间的距离（单位：公里）"""
        R = 6371  # 地球半径，单位为公里
        lat1, lon1 = coord1
        lat2, lon2 = map(float, coord2.split(','))

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c  # 返回距离，单位为公里
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
    
    def remove_duplicates(self,restaurant_list):
        seen = set()
        unique_list = []
        for restaurant in restaurant_list:
            # 假设我们根据 'name' 和 'address' 来去重
            identifier = (restaurant['name'], restaurant['address'])
            if identifier not in seen:
                seen.add(identifier)
                unique_list.append(restaurant)
        return unique_list
    
    ## 生成excel
    def on_generate_excel(self):
        # 先进行确认
        if not self.prepare_search():
            return
            
        # 显示正在生成Excel的信息
        progress_msg = self.show_centered_message("信息", "Excel文件正在生成中，请稍候...")
        QCoreApplication.processEvents()  # 强制刷新事件循环以立即显示消息框

        ## 地名转化为经纬度，如果转不了就用地面
        try:
            # 如果已经输入的经纬度，则使用输入的坐标,如果输入的是城市,则转化为经纬度
            try:
                self.city_lat_lon = flow5_location_change(self.city_input_value)
            except:
                self.city_lat_lon = self.city_input_value
            print(self.city_lat_lon)
            self.restaurantList=[]
            # 动态生成保存路径
            sanitized_city = "".join([c if c.isalnum() or c.isspace() else "_" for c in self.city_input_value])
            self.default_save_path = os.path.join(os.getcwd(), f"{sanitized_city}__restaurant_data.xlsx")
            
            # 获取关键字
            keywords_list = self.get_keywords()
            
            # API类型映射
            api_code_to_number = {
                "gaode": 1,
                "baidu": 2,
                "serp": 3,
                "tripadvisor": 4,
                "kimi": 5
            }
            
            # 遍历选中的API
            for api_code in self.selected_apis:
                # 获取API密钥
                api_key = self.get_api_key(api_code)
                # 获取API编号
                api_number = api_code_to_number.get(api_code, 0)
                
                if not api_key or api_number == 0:
                    print(f"跳过 {api_code}: 无效的API密钥或未知的API类型")
                    continue
                
                # 遍历关键词
                for key_words in keywords_list:
                    self.keywords_input_value = key_words
                    print(f"搜索关键词: {self.keywords_input_value}, API类型: {api_code}, 坐标: {self.city_lat_lon}")
                    
                    try:
                        restaurantList_api = flow5_get_restaurantinfo(
                            self.page_number, api_key, self.keywords_input_value,
                            self.city_lat_lon, api_number, self.default_save_path
                        )
                        self.restaurantList.extend(restaurantList_api)
                    except Exception as e:
                        print(f"API {api_code} 搜索失败: {str(e)}")
            
            try:
                # 去重
                self.restaurantList = self.remove_duplicates(self.restaurantList)
                ## 去除屏蔽词
                blocked_words = self.get_blocked_words()
                self.restaurantList = [restaurant for restaurant in self.restaurantList if not any(word in restaurant['name'] for word in blocked_words)]

                # 计算每个餐厅与工厂的距离并添加到字典中
                for restaurant in self.restaurantList:
                    # 提取餐厅的坐标
                    res_lon, res_lat = map(float, restaurant['location'].split(','))  # 假设坐标格式为 "经度,纬度"
                    distance = self.haversine((res_lat, res_lon), self.factory_lat_lon)  # 计算距离
                    restaurant['distance_to_factory'] = distance  # 添加新的键
                flow5_write_to_excel(self.restaurantList, self.default_save_path)
                # 关闭进度消息框
                progress_msg.accept()
                # 显示保存成功信息
                QMessageBox.information(self, "成功", f"Excel文件已保存到：\n{self.default_save_path}")
            except Exception as e:
                # 如果出错，也关闭进度消息框并显示错误信息
                progress_msg.accept()
                QMessageBox.critical(self, "错误", f"Excel生成失败: {str(e)}")
        except Exception as e:
            # 处理任何异常
            if progress_msg:
                progress_msg.accept()
            QMessageBox.critical(self, "错误", f"Excel生成过程中出错: {str(e)}")
    
    def on_view_results(self):
        """查看生成的Excel文件内容"""
        try:
            if hasattr(self, 'default_save_path') and os.path.exists(self.default_save_path):
                df = pd.read_excel(self.default_save_path)
                model = self.pandas_to_model(df)
                self.table_view.setModel(model)
                self.table_view.resizeColumnsToContents()
            else:
                QMessageBox.warning(self, "警告", "请先生成Excel文件")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法读取Excel文件: {str(e)}")
    
    def pandas_to_model(self, df):
        """将 pandas DataFrame 转换为 QStandardItemModel"""
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(df.columns)
        
        for row_idx, row in df.iterrows():
            items = [QStandardItem(str(cell)) for cell in row]
            model.appendRow(items)
            
        return model
        
    def on_verify_restaurants(self):
        """餐厅智能验证功能"""
        print("开始进行餐厅智能验证...")
        try:
            if not hasattr(self, 'default_save_path') or not os.path.exists(self.default_save_path):
                QMessageBox.warning(self, "警告", "请先生成Excel文件")
                return
                
            # 这里添加智能验证逻辑，暂时用通知代替
            QMessageBox.information(self, "功能提示", "餐厅智能验证功能即将实现")
            pass
        except Exception as e:
            QMessageBox.critical(self, "错误", f"餐厅智能验证过程中出错: {str(e)}")
    
    def on_translate_addresses(self):
        """餐厅地址翻译功能"""
        print("开始进行餐厅地址翻译...")
        try:
            if not hasattr(self, 'default_save_path') or not os.path.exists(self.default_save_path):
                QMessageBox.warning(self, "警告", "请先生成Excel文件")
                return
                
            # 这里添加地址翻译逻辑，暂时用通知代替
            QMessageBox.information(self, "功能提示", "餐厅地址翻译功能即将实现")
            pass
        except Exception as e:
            QMessageBox.critical(self, "错误", f"餐厅地址翻译过程中出错: {str(e)}")
    
    def on_calculate_distances(self):
        """餐厅距离获取功能"""
        print("开始进行餐厅距离获取...")
        try:
            if not hasattr(self, 'default_save_path') or not os.path.exists(self.default_save_path):
                QMessageBox.warning(self, "警告", "请先生成Excel文件")
                return
                
            # 检查是否有工厂坐标
            lat = self.latitude_input.text().strip()
            lon = self.longitude_input.text().strip()
            if not lat or not lon:
                QMessageBox.warning(self, "警告", "请先输入工厂坐标")
                return
                
            # 这里添加距离计算逻辑，暂时用通知代替
            QMessageBox.information(self, "功能提示", "餐厅距离获取功能即将实现")
            pass
        except Exception as e:
            QMessageBox.critical(self, "错误", f"餐厅距离获取过程中出错: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 创建并显示主窗口
    restaurant_fetcher = Tab5()
    restaurant_fetcher.show()
    
    # 进入应用程序的主循环
    sys.exit(app.exec_())