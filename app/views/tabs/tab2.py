# ================================ 餐厅收集 ================================
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QComboBox, QGroupBox, QGridLayout,
                            QFileDialog, QMessageBox, QLayout, QListWidget, QDialog, QLineEdit, 
                            QApplication, QCheckBox, QSpinBox, QRadioButton, QToolButton)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QThread, pyqtSignal, QEvent
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
        # 确保在主线程执行UI更新
        if QApplication.instance().thread() != QThread.currentThread():
            # 如果在非主线程中调用，推迟到主线程执行
            QApplication.instance().postEvent(self, QEvent(QEvent.Type.User))
            return
            
        if status is None:
            color = QColor(150, 150, 150)  # 灰色，表示未测试
        elif status:
            color = QColor(0, 200, 0)  # 绿色，表示成功
        else:
            color = QColor(255, 0, 0)  # 红色，表示失败
        
        # 创建一个填充的圆形图标
        pixmap = QPixmap(QSize(16, 16))
        pixmap.fill(Qt.transparent)
        
        try:
            # 使用 QPainter 直接绘制
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            
            label.setPixmap(pixmap)
        except Exception as e:
            LOGGER.error(f"绘制状态指示灯失败: {str(e)}")
            # 创建一个备用的纯色pixmap以防绘制失败
            fallback = QPixmap(QSize(16, 16))
            fallback.fill(color)
            label.setPixmap(fallback)
    
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
    finished = pyqtSignal(pd.DataFrame, str)  # 完成信号，携带查询结果和文件路径
    error = pyqtSignal(str)  # 错误信号，携带错误信息
    progress = pyqtSignal(str)  # 进度信号，用于实时更新进度
    
    def __init__(self, city, cp_id, use_llm=True):
        super().__init__()
        self.city = city
        self.cp_id = cp_id
        self.use_llm = use_llm
        self.running = True
        
        # 创建临时目录
        import tempfile
        self.temp_dir = tempfile.gettempdir()
    
    def stop(self):
        """停止线程执行"""
        self.running = False
    
    def run(self):
        try:
            LOGGER.info(f"线程开始: 正在获取 {self.city} 的餐厅信息...")
            self.progress.emit(f"开始获取 {self.city} 的餐厅信息...")
            
            # 创建服务实例
            restaurant_service = GetRestaurantService()
            
            # 检查线程是否仍在运行
            if not self.running:
                LOGGER.info("线程被用户中断")
                return
                
            # 获取基础餐厅信息
            self.progress.emit(f"正在从API获取餐厅基础信息...")
            try:
                restaurant_service.run(cities=self.city, cp_id=self.cp_id, model_class=RestaurantModel, 
                                      file_path=None, use_api=True, if_gen_info=False, use_llm=self.use_llm)
            except Exception as e:
                LOGGER.error(f"获取餐厅基础信息时出错: {str(e)}")
                self.error.emit(f"获取餐厅基础信息时出错: {str(e)}")
                return
            
            # 检查是否有餐厅信息
            if not restaurant_service.restaurants:
                LOGGER.warning(f"未找到 {self.city} 的餐厅信息")
                self.error.emit(f"未找到 {self.city} 的餐厅信息")
                return
                
            restaurants_count = len(restaurant_service.restaurants)
            self.progress.emit(f"已找到 {restaurants_count} 家餐厅，正在生成详细信息...")
            
            # 为大量餐厅进行分批处理
            if restaurants_count > 500:
                LOGGER.warning(f"餐厅数量过多 ({restaurants_count})，可能需要较长处理时间")
                self.progress.emit(f"餐厅数量较多 ({restaurants_count})，正在分批处理...")
            
            # 检查线程是否仍在运行
            if not self.running:
                LOGGER.info("线程被用户中断")
                return
                
            # 获取餐厅组
            restaurant_group = restaurant_service.get_restaurants_group()
            
            # 单独执行生成信息步骤，带错误处理
            try:
                # 减少工作线程数，防止资源占用过多
                num_workers = 6  # 固定使用6个工作线程，避免资源争用
                self.progress.emit(f"使用 {num_workers} 个工作线程生成餐厅详细信息...")
                
                # 将use_llm参数传递给gen_info方法
                restaurant_group = restaurant_service.gen_info(restaurant_group, num_workers=num_workers)
            except Exception as e:
                LOGGER.error(f"生成餐厅详细信息时出错: {str(e)}")
                self.progress.emit(f"生成餐厅详细信息时出错，但会继续处理已获取的数据")
                # 继续使用原始餐厅组
            
            # 最后一次检查线程是否仍在运行
            if not self.running:
                LOGGER.info("线程被用户中断")
                return
                
            # 转换为DataFrame并发送结果
            try:
                self.progress.emit(f"正在将餐厅信息转换为表格数据...")
                restaurant_data = restaurant_group.to_dataframe()
                
                # 保存完整数据到临时文件
                import os
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(self.temp_dir, f"restaurants_{self.city}_{timestamp}.xlsx")
                
                self.progress.emit(f"正在保存完整数据到临时文件: {file_path}")
                restaurant_data.to_excel(file_path, index=False)
                LOGGER.info(f"已将完整数据({len(restaurant_data)}条记录)保存到: {file_path}")
                
                # 清理内存中的大对象，确保发送前已经释放资源
                restaurant_group = None
                restaurant_service = None
                
                # 强制垃圾回收
                import gc
                gc.collect()
                
                LOGGER.info(f"{self.city} 餐厅信息获取完成，共 {len(restaurant_data)} 条记录")
                self.progress.emit(f"餐厅信息获取完成，共 {len(restaurant_data)} 条记录")
                self.finished.emit(restaurant_data, file_path)
            except Exception as e:
                LOGGER.error(f"转换餐厅数据为DataFrame时出错: {str(e)}")
                self.error.emit(f"处理餐厅数据时出错: {str(e)}")
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
        self.conf = CONF
        
        # 用于跟踪临时文件
        self.temp_files = []
        
        self.conf.runtime.SEARCH_RADIUS = 50
        self.conf.runtime.STRICT_MODE = False
        # 高级配置默认值
        self.search_radius = 50  # 默认搜索半径
        self.strict_mode = False  # 默认非严格模式
        
        self.initUI()
    
    def __del__(self):
        """析构函数，清理资源"""
        self.cleanup_temp_files()
        
    def cleanup_temp_files(self):
        """清理临时文件"""
        
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    LOGGER.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                LOGGER.error(f"删除临时文件时出错: {str(e)}")
                
        # 清空列表
        self.temp_files = []
    
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
        self.xlsx_viewer = XlsxViewerWidget(show_open=False, show_save=False, show_save_as=True, show_refresh=False)
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
        
        # 根据CP位置搜索按钮
        self.search_by_cp_button = QPushButton("根据CP位置搜索")
        self.search_by_cp_button.clicked.connect(self.search_by_cp_location)
        self.search_by_cp_button.setEnabled(False)
        self.search_by_cp_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #46b8da;
            }
        """)
        
        # 详细配置按钮
        self.advanced_config_button = QToolButton()
        self.advanced_config_button.setText("详细配置 ⬇️")
        self.advanced_config_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.advanced_config_button.setStyleSheet("""
            QToolButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #f8f9fa;
            }
            QToolButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.advanced_config_button.setCheckable(True)
        self.advanced_config_button.clicked.connect(self.toggle_advanced_config)
        
        # 添加使用大模型的复选框
        self.use_llm_checkbox = QCheckBox("使用大模型生成餐厅类型")
        self.use_llm_checkbox.setChecked(True)  # 默认选中
        self.use_llm_checkbox.setEnabled(False)  # 默认禁用，需要先选择CP
        
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
        control_layout.addWidget(self.search_by_cp_button)  # 添加根据CP位置搜索按钮
        control_layout.addSpacing(10)
        control_layout.addWidget(self.advanced_config_button)  # 添加详细配置按钮
        control_layout.addSpacing(10)
        control_layout.addWidget(self.use_llm_checkbox)  # 添加复选框
        control_layout.addSpacing(10)
        control_layout.addWidget(self.get_restaurant_button)
        # control_layout.addWidget(self.import_button)
        control_layout.addStretch()
        
        self.layout.addWidget(control_frame)
        
        # 创建高级配置面板（默认隐藏）
        self.create_advanced_config_panel()
        
        # 使用全局日志记录器记录信息，不需要重定向标准输出
        # 获取全局logger
        from app.utils.logger import get_logger
        self.logger = get_logger()
        
        # 加载示例数据
        # self.load_sample_data()
    
    def create_advanced_config_panel(self):
        """创建高级配置面板"""
        self.advanced_config_frame = QFrame()
        self.advanced_config_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                margin-top: 5px;
            }
        """)
        
        # 使用水平布局替代网格布局
        advanced_layout = QHBoxLayout(self.advanced_config_frame)
        advanced_layout.setContentsMargins(10, 10, 10, 10)
        advanced_layout.setSpacing(15)
        
        # 搜索半径配置
        radius_label = QLabel("搜索半径(KM):")
        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(1, 999)
        self.radius_spinbox.setValue(self.search_radius)
        self.radius_spinbox.setSuffix(" KM")
        # 设置为只能容纳4位数字的宽度
        self.radius_spinbox.setFixedWidth(80)
        self.radius_spinbox.valueChanged.connect(self.update_search_radius)
        
        # 严格模式选项
        strict_mode_label = QLabel("是否严格模式:")
        self.strict_mode_yes = QRadioButton("是")
        self.strict_mode_no = QRadioButton("否")
        self.strict_mode_no.setChecked(True)  # 默认为否
        
        # 将单选按钮连接到更新函数
        self.strict_mode_yes.toggled.connect(self.update_strict_mode)
        
        # 创建一个水平布局来容纳单选按钮
        strict_radio_layout = QHBoxLayout()
        strict_radio_layout.setSpacing(5)
        strict_radio_layout.setContentsMargins(0, 0, 0, 0)
        strict_radio_layout.addWidget(self.strict_mode_yes)
        strict_radio_layout.addWidget(self.strict_mode_no)
        strict_radio_layout.addStretch()
        
        # 添加到水平布局中
        advanced_layout.addWidget(radius_label)
        advanced_layout.addWidget(self.radius_spinbox)
        advanced_layout.addSpacing(20)
        advanced_layout.addWidget(strict_mode_label)
        advanced_layout.addLayout(strict_radio_layout)
        advanced_layout.addStretch(1)
        
        # 隐藏高级配置面板
        self.advanced_config_frame.setVisible(False)
        
        # 添加到主布局
        self.layout.addWidget(self.advanced_config_frame)
    
    def toggle_advanced_config(self):
        """切换高级配置面板显示状态"""
        is_visible = self.advanced_config_frame.isVisible()
        self.advanced_config_frame.setVisible(not is_visible)
        
        # 更新按钮文本
        if is_visible:
            self.advanced_config_button.setText("详细配置 ⬇️")
        else:
            self.advanced_config_button.setText("详细配置 ⬆️")
    
    def update_search_radius(self, value):
        """更新搜索半径配置"""
        self.conf.runtime.SEARCH_RADIUS = value
        self.search_radius = value
        LOGGER.info(f"搜索半径已更新为: {value} KM")
    
    def update_strict_mode(self, checked):
        """更新严格模式设置"""
        if checked:
            self.conf.runtime.STRICT_MODE = True
            self.strict_mode = True
            LOGGER.info("严格模式已启用")
        else:
            self.conf.runtime.STRICT_MODE = False
            self.strict_mode = False
            LOGGER.info("严格模式已禁用")
    
    def search_by_cp_location(self):
        """根据CP位置进行搜索"""
        try:
            if not self.current_cp:
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 获取CP位置信息
            cp_city, cp_location = self.get_cp_location()
            self.conf.runtime.CP_LOCATION = cp_location
            self.conf.runtime.CP_CITY = cp_city
            if not cp_location:
                QMessageBox.warning(self, "位置信息缺失", "当前CP没有可用的位置信息")
                return
            
            # 使用CP位置信息进行搜索，传递搜索半径和严格模式参数
            LOGGER.info(f"使用CP位置进行搜索: {cp_location}, 半径: {self.search_radius}KM, 严格模式: {'是' if self.strict_mode else '否'}")
            
            # 将城市信息设置到城市输入框
            self.city_input.setText(cp_location)
            
            # 直接调用餐厅获取函数
            self.get_restaurants(city=cp_city)
            
        except Exception as e:
            LOGGER.error(f"根据CP位置搜索时出错: {str(e)}")
            QMessageBox.critical(self, "搜索失败", f"根据CP位置搜索时出错: {str(e)}")
    
    def get_cp_location(self):
        """获取当前CP的位置信息"""
        try:
            current_cp_city = self.conf.runtime.CP.get('cp_city', None)
            current_cp_location = self.conf.runtime.CP.get('cp_location', None)
            LOGGER.info(f"当前CP城市: {current_cp_city}, 当前CP位置: {current_cp_location}")
            return current_cp_city, current_cp_location
        except Exception as e:
            LOGGER.error(f"获取CP位置信息时出错: {str(e)}")
            return None
    
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
                    
                    # 启用城市输入框、复选框和获取餐厅按钮
                    self.city_input.setEnabled(True)  # 启用城市输入框
                    self.use_llm_checkbox.setEnabled(True)  # 启用复选框
                    self.get_restaurant_button.setEnabled(True)  # 启用获取餐厅按钮
                    self.search_by_cp_button.setEnabled(True)  # 启用根据CP位置搜索按钮
                    
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
    
    def get_restaurants(self, city=None):
        """获取餐厅信息"""
        try:
            # 检查是否已经有一个正在运行的线程
            if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
                # 线程正在运行，则停止它
                self.worker.stop()
                self.get_restaurant_button.setText("餐厅获取")
                if hasattr(self, 'progress_label'):
                    self.progress_label.setText("操作已取消")
                LOGGER.info("用户取消了餐厅获取操作")
                return
                
            if city:
                city = city
            else:
                # 获取当前输入的城市
                city = self.city_input.text().strip()  # 获取输入框中的城市名称
            if not city:
                QMessageBox.warning(self, "请输入城市", "请先输入餐厅城市")
                return
            
            # 获取是否使用大模型
            use_llm = self.use_llm_checkbox.isChecked()
            LOGGER.info(f"用户选择{'使用' if use_llm else '不使用'}大模型生成餐厅类型")
            
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
            self.get_restaurant_button.setText("取消获取")
            
            # 添加进度提示
            if not hasattr(self, 'progress_label'):
                self.progress_label = QLabel("正在准备...")
                self.progress_label.setStyleSheet("color: #666; margin-top: 5px;")
                self.layout.addWidget(self.progress_label)
            else:
                self.progress_label.setText("正在准备...")
                self.progress_label.setVisible(True)
            
            # 创建工作线程，传递使用大模型的选项和高级配置
            self.worker = RestaurantWorker(
                city=city, 
                cp_id=self.current_cp['cp_id'], 
                use_llm=use_llm
            )
            
            # 将搜索半径和严格模式设置到工作线程中（如果Worker类支持这些参数）
            self.worker.search_radius = self.search_radius
            self.worker.strict_mode = self.strict_mode
            
            # 连接信号
            self.worker.finished.connect(self.on_restaurant_search_finished)
            self.worker.error.connect(self.on_restaurant_search_error)
            self.worker.progress.connect(self.update_progress)
            
            # 启动线程
            LOGGER.info(f"启动餐厅获取线程，搜索城市: {city}，{'使用' if use_llm else '不使用'}大模型，搜索半径: {self.search_radius}KM，严格模式: {'是' if self.strict_mode else '否'}")
            self.worker.start()
            
        except Exception as e:
            LOGGER.error(f"启动餐厅获取线程时出错: {str(e)}")
            QMessageBox.critical(self, "获取失败", f"启动餐厅获取线程时出错: {str(e)}")
            self.get_restaurant_button.setText("餐厅获取")
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
    
    def update_progress(self, message):
        """更新进度信息"""
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(message)
    
    def on_restaurant_search_finished(self, restaurant_data, file_path):
        """餐厅搜索完成的回调函数"""
        try:
            # 记录临时文件，用于程序退出时清理
            self.temp_files.append(file_path)
            
            # 检查数据量大小
            row_count = len(restaurant_data)
            LOGGER.info(f"收到餐厅数据，共 {row_count} 条记录")
            
            # 限制显示的数据量，无论多大只显示前100行
            max_display_rows = 100
            if row_count > max_display_rows:
                LOGGER.warning(f"数据量过大 ({row_count} 行)，将只显示前 {max_display_rows} 行")
                restaurant_data_display = restaurant_data.head(max_display_rows).copy()
                warning_msg = f"数据量过大，仅显示前 {max_display_rows} 条记录（共 {row_count} 条）"
            else:
                restaurant_data_display = restaurant_data
                warning_msg = None
            
            # 确保在主线程中更新UI
            QApplication.processEvents()
            
            # 更新Excel查看器 - 只显示有限的数据
            self.xlsx_viewer.load_data(data=restaurant_data_display)
            
            # 显示成功消息，包含文件路径信息
            success_msg = f"餐厅信息获取完成，共 {row_count} 条记录"
            if warning_msg:
                success_msg += "\n" + warning_msg
            success_msg += f"\n\n完整数据已保存到文件：\n{file_path}"
            
            # 创建一个带有"打开文件"按钮的消息框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("获取成功")
            msg_box.setText(success_msg)
            msg_box.setIcon(QMessageBox.Information)
            
            # 添加打开文件按钮
            open_button = msg_box.addButton("打开完整数据", QMessageBox.ActionRole)
            close_button = msg_box.addButton("关闭", QMessageBox.RejectRole)
            
            # 显示消息框并处理响应
            msg_box.exec_()
            
            # 如果点击了打开文件按钮
            if msg_box.clickedButton() == open_button:
                self.open_file_external(file_path)
            
            # 恢复按钮状态
            self.get_restaurant_button.setText("餐厅获取")
            
            # 隐藏进度标签
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 清理线程
            if hasattr(self, 'worker'):
                self.worker.disconnect()  # 断开所有信号连接
                self.worker = None
            
        except Exception as e:
            LOGGER.error(f"处理餐厅搜索结果时出错: {str(e)}")
            QMessageBox.critical(self, "处理失败", f"处理餐厅搜索结果时出错: {str(e)}")
            self.get_restaurant_button.setText("餐厅获取")
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 清理线程
            if hasattr(self, 'worker'):
                self.worker.disconnect()
                self.worker = None
    
    def open_file_external(self, file_path):
        """使用系统默认应用打开文件"""
        try:
            import os
            import platform
            import subprocess
            
            LOGGER.info(f"尝试打开文件: {file_path}")
            
            if os.path.exists(file_path):
                system = platform.system()
                
                if system == 'Windows':
                    os.startfile(file_path)
                elif system == 'Darwin':  # macOS
                    subprocess.call(['open', file_path])
                else:  # Linux
                    subprocess.call(['xdg-open', file_path])
                    
                LOGGER.info(f"已使用系统默认应用打开文件: {file_path}")
            else:
                LOGGER.error(f"文件不存在: {file_path}")
                QMessageBox.warning(self, "文件错误", f"文件不存在: {file_path}")
        except Exception as e:
            LOGGER.error(f"打开文件时出错: {str(e)}")
            QMessageBox.critical(self, "打开失败", f"无法打开文件: {str(e)}")
    
    def on_restaurant_search_error(self, error_msg):
        """餐厅搜索出错的回调函数"""
        QMessageBox.critical(self, "获取失败", f"获取餐厅信息时出错: {error_msg}")
        self.get_restaurant_button.setText("餐厅获取")
        if hasattr(self, 'progress_label'):
            self.progress_label.setVisible(False)
            
        # 清理线程
        if hasattr(self, 'worker'):
            self.worker.disconnect()  # 断开所有信号连接
            self.worker = None
    
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