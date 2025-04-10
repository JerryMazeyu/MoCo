# ================================ 餐厅收集 ================================

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QComboBox, QGroupBox, QGridLayout,
                            QFileDialog, QMessageBox, QLayout, QListWidget, QDialog, QLineEdit)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter
import pandas as pd
from app.views.components.xlsxviewer import XlsxViewerWidget
from app.views.components.singleton import global_context
from app.utils.logger import get_logger
from app.services.instances.restaurant import youdao_translate, kimi_restaurant_type_analysis
from app.services.instances.restaurant import query_gaode
from app.services.instances.cp import CP
from app.config.config import CONF
import oss2
from app.services.functions.get_restaurant_service import GetRestaurantService
from app.services.instances.restaurant import RestaurantModel
# 获取全局日志对象
LOGGER = get_logger()


# 自定义流式布局类，用于自适应地排列API测试项
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)
        
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        
        self.setSpacing(spacing)
        
        self.itemList = []
    
    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item):
        self.itemList.append(item)
    
    def count(self):
        return len(self.itemList)
    
    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]
        return None
    
    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)
        return None
    
    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height
    
    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QSize()
        
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
            
        margin = self.contentsMargins().left() + self.contentsMargins().right()
        margin += self.contentsMargins().top() + self.contentsMargins().bottom()
        
        size += QSize(margin, margin)
        return size
    
    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        
        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + wid.style().layoutSpacing(
                wid.sizePolicy().controlType(), 
                wid.sizePolicy().controlType(), 
                Qt.Horizontal
            )
            spaceY = self.spacing() + wid.style().layoutSpacing(
                wid.sizePolicy().controlType(), 
                wid.sizePolicy().controlType(), 
                Qt.Vertical
            )
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
            
        return y + lineHeight - rect.y()


class ApiTestWidget(QWidget):
    """API测试组件，用于测试各种API连接"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_status = {
            "高德API": False,
            "有道API": False,
            "KIMI API": False,
            "阿里OSS": False,
            "爱企查API": False
        }
        self.initUI()
    
    def initUI(self):
        # 使用流式布局，自动适应一行显示多少个API测试项
        self.layout = FlowLayout(self, margin=5, spacing=10)
        
        # 为每个API创建一个小的组合控件
        for api_name in self.api_status.keys():
            # 创建一个容器小部件来容纳每个API测试项的控件
            api_widget = QWidget()
            api_layout = QHBoxLayout(api_widget)
            api_layout.setContentsMargins(0, 0, 0, 0)
            api_layout.setSpacing(5)
            
            # 创建标签
            label = QLabel(api_name + ":")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # 创建测试按钮
            test_button = QPushButton("测试")
            test_button.setProperty("api_name", api_name)
            test_button.clicked.connect(self.test_api)
            test_button.setFixedWidth(60)
            
            # 创建状态指示灯
            status_label = QLabel()
            status_label.setFixedSize(16, 16)
            self.update_status_light(status_label, None)
            
            # 保存状态指示灯引用
            setattr(self, f"{api_name.replace(' ', '_')}_light", status_label)
            
            # 添加到此API项的布局
            api_layout.addWidget(label)
            api_layout.addWidget(test_button)
            api_layout.addWidget(status_label)
            
            # 将整个API项添加到流式布局
            self.layout.addWidget(api_widget)
    
    def update_status_light(self, label, status):
        """更新状态指示灯"""
        if status is None:
            color = QColor(150, 150, 150)  # 灰色，表示未测试
        elif status:
            color = QColor(0, 200, 0)  # 绿色，表示成功
        else:
            color = QColor(255, 0, 0)  # 红色，表示失败
        
        # 创建一个填充的圆形图标
        pixmap = QPixmap(QSize(16, 16))
        pixmap.fill(Qt.transparent)
        
        # 使用 QPainter 直接绘制
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        label.setPixmap(pixmap)
    
    def test_api(self):
        """测试API连通性"""
        button = self.sender()
        if not button:
            return
        
        api_name = button.property("api_name")
        if not api_name:
            return
        
        LOGGER.info(f"正在测试 {api_name} 连通性...")
        
        success = False
        try:
            # 根据API类型进行相应的测试
            if api_name == "高德API":
                # 测试高德地图API
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'gaode_keys') and CONF.KEYS.gaode_keys:
                    key = CONF.KEYS.gaode_keys[0]
                    result = query_gaode(key, "北京")
                    success = result is not None and 'name' in result
                    LOGGER.info(f"高德API测试结果: {result}")
                else:
                    LOGGER.error("未找到高德地图API密钥")
            
            elif api_name == "有道API":
                # 测试有道翻译API
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'youdao_keys') and CONF.KEYS.youdao_keys:
                    key = CONF.KEYS.youdao_keys[0]
                    result = youdao_translate("测试文本", 'zh', 'en', key)
                    success = result is not None
                    LOGGER.info(f"有道API测试结果: {result}")
                else:
                    LOGGER.error("未找到有道翻译API密钥")
            
            elif api_name == "KIMI API":
                # 测试KIMI API
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'kimi_keys') and CONF.KEYS.kimi_keys:
                    key = CONF.KEYS.kimi_keys[0]
                    rest_info = {
                        'name': '测试餐厅',
                        'address': '北京市海淀区',
                        'rest_type': '中餐/快餐'
                    }
                    result = kimi_restaurant_type_analysis(rest_info, key)
                    success = result is not None
                    LOGGER.info(f"KIMI API测试结果: {result}")
                else:
                    LOGGER.error("未找到KIMI API密钥")
            
            elif api_name == "阿里OSS":
                # 测试阿里云OSS连接
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'oss'):
                    oss_conf = CONF.KEYS.oss
                    access_key_id = oss_conf.get('access_key_id')
                    access_key_secret = oss_conf.get('access_key_secret')
                    endpoint = oss_conf.get('endpoint')
                    bucket_name = oss_conf.get('bucket_name')
                    region = oss_conf.get('region')
                    
                    if all([access_key_id, access_key_secret, endpoint, bucket_name]):
                        auth = oss2.Auth(access_key_id, access_key_secret)
                        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
                        # 尝试列出前缀为CPs的对象
                        result = list(oss2.ObjectIterator(bucket, prefix='CPs/', max_keys=1))
                        success = True  # 如果没有异常，则认为连接成功
                        LOGGER.info(f"阿里OSS测试结果: 成功")
                    else:
                        LOGGER.error("阿里云OSS配置不完整")
                else:
                    LOGGER.error("未找到阿里云OSS配置")
            
            elif api_name == "爱企查API":
                # 爱企查API测试 - 暂未实现，可以根据实际情况添加
                LOGGER.warning("爱企查API测试功能尚未实现")
                success = False
        
        except Exception as e:
            LOGGER.error(f"{api_name} 测试失败: {e}")
            success = False
        
        # 更新状态
        self.api_status[api_name] = success
        
        # 更新状态指示灯
        status_light = getattr(self, f"{api_name.replace(' ', '_')}_light", None)
        if status_light:
            self.update_status_light(status_light, success)
        
        # 输出结果
        result = "成功" if success else "失败"
        LOGGER.info(f"{api_name} 测试{result}")
        
        return success


# CP选择对话框
class CPSelectDialog(QDialog):
    def __init__(self, cp_list, parent=None):
        super().__init__(parent)
        self.cp_list = cp_list
        self.selected_cp = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("选择CP")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # 创建列表控件显示CP
        self.list_widget = QListWidget()
        for cp in self.cp_list:
            # 使用字典访问方式而不是 get 方法
            cp_name = cp['cp_name'] if isinstance(cp, dict) else cp.cp_name
            cp_id = cp['cp_id'] if isinstance(cp, dict) else cp.cp_id
            self.list_widget.addItem(f"{cp_name} (ID: {cp_id})")
        
        # 添加按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addWidget(QLabel("请选择CP:"))
        layout.addWidget(self.list_widget)
        layout.addLayout(button_layout)
    
    def get_selected_cp(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            index = self.list_widget.row(selected_items[0])
            if 0 <= index < len(self.cp_list):
                return self.cp_list[index]
        return None


# 餐厅获取工作线程类
class RestaurantWorker(QThread):
    # 定义信号
    finished = pyqtSignal(pd.DataFrame)  # 完成信号，携带查询结果
    error = pyqtSignal(str)  # 错误信号，携带错误信息
    
    def __init__(self, city, cp_id):
        super().__init__()
        self.city = city
        self.cp_id = cp_id
    
    def run(self):
        try:
            LOGGER.info(f"线程开始: 正在获取 {self.city} 的餐厅信息...")
            
            restaurant_service = GetRestaurantService()
            restaurant_service.run(cities=self.city, cp_id=self.cp_id, model_class=RestaurantModel, file_path=None, use_api=True)

            restaurant_group = restaurant_service.get_restaurants_group()
            restaurant_data = restaurant_group.to_dataframe()
            
            LOGGER.info(f"{self.city} 餐厅信息获取完成，共 {len(restaurant_data)} 条记录")
            self.finished.emit(restaurant_data)
        except Exception as e:
            LOGGER.error(f"获取餐厅信息时出错: {str(e)}")
            self.error.emit(str(e))


class Tab2(QWidget):
    """餐厅获取Tab，实现餐厅信息获取功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 先保存parent引用，但不直接使用主窗口的方法
        self.main_window_ref = parent
        self.cp_cities = []  # 当前CP的城市列表
        self.current_cp = None  # 当前选择的CP
        self.initUI()
    
    def initUI(self):
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)  # 减小组件间距
        
        # 顶部布局 - 包含CP选择按钮
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("餐厅获取")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        # CP按钮 - 放在最右上角
        self.cp_button = QPushButton("未选择CP")
        self.cp_button.clicked.connect(self.select_cp)
        self.cp_button.setFixedWidth(150)
        self.cp_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        
        top_layout.addWidget(title_label)
        top_layout.addStretch(1)  # 将CP按钮推到右侧
        top_layout.addWidget(self.cp_button)
        
        self.layout.addLayout(top_layout)
        
        # API测试区
        api_group = QGroupBox("API连通性测试")
        api_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        api_layout = QVBoxLayout(api_group)
        api_layout.setContentsMargins(5, 10, 5, 5)
        api_layout.setSpacing(0)
        
        self.api_test_widget = ApiTestWidget()
        api_layout.addWidget(self.api_test_widget)
        
        # 减小API测试区域的高度
        api_group.setMaximumHeight(100)  # 限制最大高度
        self.layout.addWidget(api_group)
        
        # 主体区域 - 使用Splitter分隔日志和餐厅信息
        main_content = QVBoxLayout()
        
        # 餐厅信息区域
        excel_group = QGroupBox("餐厅信息")
        excel_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        excel_layout = QVBoxLayout(excel_group)
        self.xlsx_viewer = XlsxViewerWidget()
        excel_layout.addWidget(self.xlsx_viewer)
        
        # 添加到主内容区域
        main_content.addWidget(excel_group)
        
        
        # 添加主内容区域到主布局
        self.layout.addLayout(main_content, 1)
        
        # 底部控制区
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding-top: 5px;
            }
        """)
        
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 城市输入框
        city_label = QLabel("餐厅城市:")
        self.city_input = QLineEdit()  # 创建输入框
        self.city_input.setPlaceholderText("请输入城市名称")  # 设置占位符
        self.city_input.setEnabled(False)  # 启用输入框
        self.city_input.setMinimumWidth(200)  # 设置最小宽度
        self.city_input.setMaximumWidth(250)  # 设置最大宽度
        
        # 获取餐厅按钮
        self.get_restaurant_button = QPushButton("餐厅获取")
        self.get_restaurant_button.clicked.connect(self.get_restaurants)
        self.get_restaurant_button.setEnabled(False)
        self.get_restaurant_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        
        # 导入按钮
        # self.import_button = QPushButton("导入已有餐厅")
        # self.import_button.clicked.connect(self.import_restaurants)
        
        control_layout.addWidget(city_label)
        control_layout.addWidget(self.city_input)  # 使用输入框
        control_layout.addSpacing(20)
        control_layout.addWidget(self.get_restaurant_button)
        # control_layout.addWidget(self.import_button)
        control_layout.addStretch()
        
        self.layout.addWidget(control_frame)
        
        # 使用全局日志记录器记录信息，不需要重定向标准输出
        # 获取全局logger
        from app.utils.logger import get_logger
        self.logger = get_logger()
        
        # 加载示例数据
        # self.load_sample_data()
    
    def load_sample_data(self):
        """加载示例数据"""
        # 创建示例数据
        data = {
            "餐厅名称": ["好味餐厅", "美食城", "老字号饭店", "快餐小吃"],
            "地址": ["北京市海淀区xx路xx号", "上海市浦东新区xx路xx号", "广州市天河区xx路xx号", "深圳市南山区xx路xx号"],
            "电话": ["010-12345678", "021-23456789", "020-34567890", "0755-45678901"],
            "营业时间": ["09:00-22:00", "10:00-21:00", "08:30-23:00", "07:00-22:30"],
            "评分": [4.5, 4.2, 4.8, 4.0]
        }
        
        df = pd.DataFrame(data)
        self.xlsx_viewer.load_data(data=df)
        
        # 输出一些初始消息到控制台
        LOGGER.info("餐厅获取模块已初始化")
        LOGGER.info("请选择CP并选择城市，然后点击'餐厅获取'按钮")
    
    def select_cp(self):
        """选择/切换CP"""
        try:
            # 获取OSS上的CP列表
            cp_list = CP.list()
            
            if not cp_list:
                QMessageBox.warning(self, "CP列表为空", "未找到任何CP数据，请先添加CP。")
                return
            
            # 获取配置中的CP ID列表 - 直接使用CONF.BUSINESS.CP，因为它就是一个ID列表
            conf_cp_ids = []
            if hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                conf_cp_ids = CONF.BUSINESS.CP.cp_id  # 直接使用列表

            available_cp_list = [cp for cp in cp_list if cp['cp_id'] in conf_cp_ids]
            
            # 显示CP选择对话框
            dialog = CPSelectDialog(available_cp_list, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_cp = dialog.get_selected_cp()
                if selected_cp:
                    # 将列表中的字典转换为对象
                    cp_data = {
                        'cp_id': selected_cp['cp_id'] if isinstance(selected_cp, dict) else selected_cp.cp_id,
                        'cp_name': selected_cp['cp_name'] if isinstance(selected_cp, dict) else selected_cp.cp_name
                    }
                    
                    
                    # 保存选择的CP到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                    
                    CONF.runtime.CP = cp_data
                    self.current_cp = cp_data
                    
                    # 更新CP按钮文本
                    self.cp_button.setText(f"已选择CP为：{cp_data['cp_name']}")
                    
                    # 启用城市输入框和获取餐厅按钮
                    self.city_input.setEnabled(True)  # 启用城市输入框
                    self.get_restaurant_button.setEnabled(True)  # 启用获取餐厅按钮
                    
                    # 通知主窗口更新CP
                    if self.main_window_ref:
                        self.main_window_ref.set_current_cp(cp_data['cp_id'])
        except Exception as e:
            LOGGER.error(f"选择CP时出错: {str(e)}")
            LOGGER.error(f"CONF.BUSINESS.CP的内容: {getattr(CONF.BUSINESS, 'CP', None)}")
            QMessageBox.critical(self, "选择CP失败", f"选择CP时出错: {str(e)}")
    
    def update_cities(self, cp_id):
        """根据CP ID更新城市列表"""
        try:
            # 获取当前选择的CP中的城市信息
            cities = []
            
            # 首先尝试从CONF.runtime.CP获取城市列表
            if hasattr(CONF, 'runtime') and hasattr(CONF.runtime, 'CP'):
                # 使用字典访问方式而不是get方法
                if isinstance(CONF.runtime.CP, dict):
                    cities = CONF.runtime.CP.get('cities', [])
                    
                    # 如果cities为空，尝试从其他字段构建城市列表
                    if not cities and 'cp_city' in CONF.runtime.CP:
                        cities = [CONF.runtime.CP['cp_city']]
            
            # 如果未获取到，则尝试从CONF.BUSINESS.CP获取
            if not cities and hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                cp_data = getattr(CONF.BUSINESS.CP, str(cp_id), None)
                if cp_data:
                    if hasattr(cp_data, 'cities'):
                        cities = cp_data.cities
                    elif hasattr(cp_data, 'cp_city'):
                        cities = [cp_data.cp_city]
            
            # 如果还是未获取到，尝试从配置字典中获取
            if not cities and hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                cp_cities_map = {}
                config_dict = getattr(CONF.BUSINESS.CP, '_config_dict', {})
                
                for cp_key, cp_value in config_dict.items():
                    if cp_key != 'cp_id' and isinstance(cp_value, dict):
                        if 'cities' in cp_value:
                            cp_cities_map[cp_key] = cp_value['cities']
                        elif 'cp_city' in cp_value:
                            cp_cities_map[cp_key] = [cp_value['cp_city']]
                
                # 如果配置中有此CP的城市列表
                cities = cp_cities_map.get(str(cp_id), [])
            
            # 记录调试信息
            LOGGER.info(f"更新城市列表: CP ID = {cp_id}")
            LOGGER.info(f"获取到的城市列表: {cities}")
            
            # 更新城市列表
            self.cp_cities = cities
            
            # 更新下拉框
            self.city_combo.clear()
            if cities:
                self.city_combo.addItems(self.cp_cities)
                # 启用相关控件
                self.city_combo.setEnabled(True)
                self.get_restaurant_button.setEnabled(True)
            else:
                LOGGER.warning(f"CP {cp_id} 没有关联的城市")
                self.city_combo.setEnabled(False)
                self.get_restaurant_button.setEnabled(False)
            
        except Exception as e:
            LOGGER.error(f"更新城市列表时出错: {str(e)}")
            LOGGER.error(f"CONF.runtime.CP的内容: {getattr(CONF.runtime, 'CP', None)}")
            self.cp_cities = []
            self.city_combo.clear()
            self.city_combo.setEnabled(False)
            self.get_restaurant_button.setEnabled(False)
    
    def get_restaurants(self):
        """获取餐厅信息"""
        try:
            # 获取当前输入的城市
            city = self.city_input.text().strip()  # 获取输入框中的城市名称
            if not city:
                QMessageBox.warning(self, "请输入城市", "请先输入餐厅城市")
                return
            
            # 检查API连通性
            api_ok = self.check_apis()
            if not api_ok:
                reply = QMessageBox.question(
                    self, 'API连接问题', 
                    '一个或多个API测试未通过。是否继续？',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # 禁用获取按钮，防止重复点击
            self.get_restaurant_button.setEnabled(False)
            self.get_restaurant_button.setText("正在获取...")
            
            # 创建工作线程
            self.worker = RestaurantWorker(city=city, cp_id=self.current_cp['cp_id'])
            
            # 连接信号
            self.worker.finished.connect(self.on_restaurant_search_finished)
            self.worker.error.connect(self.on_restaurant_search_error)
            
            # 启动线程
            LOGGER.info(f"启动餐厅获取线程，搜索城市: {city}")
            self.worker.start()
            
        except Exception as e:
            LOGGER.error(f"启动餐厅获取线程时出错: {str(e)}")
            QMessageBox.critical(self, "获取失败", f"启动餐厅获取线程时出错: {str(e)}")
            self.get_restaurant_button.setEnabled(True)
            self.get_restaurant_button.setText("餐厅获取")
    
    def on_restaurant_search_finished(self, restaurant_data):
        """餐厅搜索完成的回调函数"""
        try:
            # 更新Excel查看器
            self.xlsx_viewer.load_data(data=restaurant_data)
            
            # 显示成功消息
            QMessageBox.information(self, "获取成功", f"餐厅信息获取完成，共 {len(restaurant_data)} 条记录")
            
            # 恢复按钮状态
            self.get_restaurant_button.setEnabled(True)
            self.get_restaurant_button.setText("餐厅获取")
            
        except Exception as e:
            LOGGER.error(f"处理餐厅搜索结果时出错: {str(e)}")
            QMessageBox.critical(self, "处理失败", f"处理餐厅搜索结果时出错: {str(e)}")
            self.get_restaurant_button.setEnabled(True)
            self.get_restaurant_button.setText("餐厅获取")
    
    def on_restaurant_search_error(self, error_msg):
        """餐厅搜索出错的回调函数"""
        QMessageBox.critical(self, "获取失败", f"获取餐厅信息时出错: {error_msg}")
        self.get_restaurant_button.setEnabled(True)
        self.get_restaurant_button.setText("餐厅获取")
    
    def check_apis(self):
        """检查所有API连通性"""
        all_ok = True
        for api_name, status in self.api_test_widget.api_status.items():
            if not status:
                LOGGER.warning(f"{api_name} 未通过测试")
                all_ok = False
        
        return all_ok
    
    def import_restaurants(self):
        """导入已有餐厅"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入餐厅数据", "", "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv);;所有文件 (*.*)"
            )
            
            if not file_path:
                return
            
            try:
                # 加载选择的文件
                self.xlsx_viewer.load_data(file_path)
                LOGGER.info(f"餐厅数据已从 {file_path} 导入")
            except Exception as e:
                QMessageBox.critical(self, "导入错误", f"导入数据时出错：{str(e)}")
        except Exception as e:
            LOGGER.error(f"导入餐厅数据时出错: {str(e)}")
            QMessageBox.critical(self, "导入失败", f"导入餐厅数据时出错: {str(e)}")
    
    def update_cp(self, cp_id):
        """更新CP选择按钮的文本并更新城市列表"""
        try:
            if cp_id:
                # 尝试从OSS获取CP信息
                cp = CP.get_by_id(cp_id)
                if cp:
                    cp_name = cp.inst.cp_name
                    self.cp_button.setText(f"已选择CP为：{cp_name}")
                    
                    # 保存到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                    
                    # 从CP实例创建字典
                    cp_data = {}
                    for key, value in cp.inst.__dict__.items():
                        if not key.startswith('_'):
                            cp_data[key] = value
                    
                    CONF.runtime.CP = cp_data
                    self.current_cp = cp_data
                    
                    # 更新城市列表
                    self.city_input.clear()
                    self.city_input.setEnabled(True)
                    # self.update_cities(cp_id)
                else:
                    LOGGER.error(f"未找到ID为{cp_id}的CP")
                    self.cp_button.setText("未选择CP")
                    self.city_input.clear()
                    self.city_input.setEnabled(False)
                    self.get_restaurant_button.setEnabled(False)
            else:
                self.cp_button.setText("未选择CP")
                self.city_input.clear()
                self.city_input.setEnabled(False)
                self.get_restaurant_button.setEnabled(False)
        except Exception as e:
            LOGGER.error(f"更新CP时出错: {str(e)}")
            self.cp_button.setText("未选择CP")
            self.city_input.clear()
            self.city_input.setEnabled(False)
            self.get_restaurant_button.setEnabled(False) 