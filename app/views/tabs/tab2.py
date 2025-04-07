from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QComboBox, QGroupBox, QGridLayout,
                            QFileDialog, QMessageBox, QLayout)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter
import pandas as pd
from app.views.components.xlsxviewer import XlsxViewerWidget


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
            "爱企查API": False,
            "其他API": False
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
        
        # 获取全局logger
        from app.utils.logger import get_logger
        logger = get_logger()
        logger.info(f"正在测试 {api_name} 连通性...")
        
        # 模拟成功/失败结果 (实际应调用真实API测试)
        # 这里简单地将所有API测试设为成功
        success = True
        
        # 更新状态
        self.api_status[api_name] = success
        
        # 更新状态指示灯
        status_light = getattr(self, f"{api_name.replace(' ', '_')}_light", None)
        if status_light:
            self.update_status_light(status_light, success)
        
        # 输出结果
        result = "成功" if success else "失败"
        logger.info(f"{api_name} 测试{result}")
        
        return success


class Tab2(QWidget):
    """餐厅获取Tab，实现餐厅信息获取功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 先保存parent引用，但不直接使用主窗口的方法
        self.main_window_ref = parent
        self.cp_cities = []  # 当前CP的城市列表
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
        
        # 城市选择
        city_label = QLabel("餐厅城市:")
        self.city_combo = QComboBox()
        self.city_combo.setEnabled(False)
        
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
        self.import_button = QPushButton("导入已有餐厅")
        self.import_button.clicked.connect(self.import_restaurants)
        
        control_layout.addWidget(city_label)
        control_layout.addWidget(self.city_combo)
        control_layout.addSpacing(20)
        control_layout.addWidget(self.get_restaurant_button)
        control_layout.addWidget(self.import_button)
        control_layout.addStretch()
        
        self.layout.addWidget(control_frame)
        
        # 使用全局日志记录器记录信息，不需要重定向标准输出
        # 获取全局logger
        from app.utils.logger import get_logger
        self.logger = get_logger()
        
        # 加载示例数据
        self.load_sample_data()
    
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
        self.logger.info("餐厅获取模块已初始化")
        self.logger.info("请选择CP并选择城市，然后点击'餐厅获取'按钮")
    
    def select_cp(self):
        """选择/切换CP"""
        # 模拟CP选择
        # 实际应从配置或主窗口获取CP列表
        cp_list = ["CP001", "CP002", "CP003", "CP004"]
        
        # 简化为直接选择第一个CP
        selected_cp = cp_list[0]
        
        # 更新CP按钮文本
        self.cp_button.setText(f"已选择CP为：{selected_cp}")
        
        # 通知主窗口更新CP
        if self.main_window_ref:
            self.main_window_ref.set_current_cp(selected_cp)
        
        # 更新城市下拉框
        self.update_cities(selected_cp)
    
    def update_cities(self, cp_id):
        """根据CP ID更新城市列表"""
        try:
            # 尝试从应用全局上下文获取CP信息
            import app
            cp_cities_map = {}
            
            if 'config' in app.global_context and app.global_context['config']:
                config = app.global_context['config']
                if 'BUSINESS' in config and 'CP' in config['BUSINESS']:
                    cp_data = config['BUSINESS']['CP']
                    for cp_key in cp_data:
                        if cp_key != 'cp_id' and isinstance(cp_data[cp_key], dict) and 'cities' in cp_data[cp_key]:
                            cp_cities_map[cp_key] = cp_data[cp_key]['cities']
            
            # 如果从全局上下文未获取到，使用默认值
            if not cp_cities_map:
                # 模拟城市列表
                cp_cities_map = {
                    "CP001": ["北京", "上海", "广州", "深圳"],
                    "CP002": ["成都", "重庆", "武汉", "长沙"],
                    "CP003": ["杭州", "南京", "苏州", "宁波"],
                    "CP004": ["西安", "郑州", "济南", "青岛"]
                }
            
            # 更新城市列表
            self.cp_cities = cp_cities_map.get(cp_id, [])
            
            # 更新下拉框
            self.city_combo.clear()
            self.city_combo.addItems(self.cp_cities)
            
            # 启用相关控件
            self.city_combo.setEnabled(True)
            self.get_restaurant_button.setEnabled(True)
        except Exception as e:
            self.logger.error(f"更新城市列表时出错: {str(e)}")
            self.cp_cities = []
            self.city_combo.clear()
            self.city_combo.setEnabled(False)
            self.get_restaurant_button.setEnabled(False)
    
    def get_restaurants(self):
        """获取餐厅信息"""
        try:
            # 获取当前选择的城市
            if self.city_combo.currentIndex() < 0:
                QMessageBox.warning(self, "请选择城市", "请先选择餐厅城市")
                return
            
            city = self.city_combo.currentText()
            
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
            
            # 模拟获取餐厅信息
            self.logger.info(f"正在获取 {city} 的餐厅信息...")
            
            # 模拟数据获取延迟
            import time
            time.sleep(1)
            
            # 创建模拟数据
            data = {
                "餐厅名称": [f"{city}好味餐厅", f"{city}美食城", f"{city}老字号饭店", f"{city}快餐小吃"],
                "地址": [f"{city}市xx区xx路xx号", f"{city}市xx区xx路xx号", f"{city}市xx区xx路xx号", f"{city}市xx区xx路xx号"],
                "电话": ["123-45678900", "123-45678901", "123-45678902", "123-45678903"],
                "营业时间": ["09:00-22:00", "10:00-21:00", "08:30-23:00", "07:00-22:30"],
                "评分": [4.5, 4.2, 4.8, 4.0]
            }
            
            df = pd.DataFrame(data)
            
            # 更新Excel查看器
            self.xlsx_viewer.load_data(data=df)
            
            # 打印完成消息
            self.logger.info(f"{city} 餐厅信息获取完成，共 {len(df)} 条记录")
        except Exception as e:
            self.logger.error(f"获取餐厅信息时出错: {str(e)}")
            QMessageBox.critical(self, "获取失败", f"获取餐厅信息时出错: {str(e)}")
    
    def check_apis(self):
        """检查所有API连通性"""
        all_ok = True
        for api_name, status in self.api_test_widget.api_status.items():
            if not status:
                self.logger.warning(f"{api_name} 未通过测试")
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
                self.logger.info(f"餐厅数据已从 {file_path} 导入")
            except Exception as e:
                QMessageBox.critical(self, "导入错误", f"导入数据时出错：{str(e)}")
        except Exception as e:
            self.logger.error(f"导入餐厅数据时出错: {str(e)}")
            QMessageBox.critical(self, "导入失败", f"导入餐厅数据时出错: {str(e)}")
    
    def update_cp(self, cp_id):
        """更新CP选择按钮的文本并更新城市列表"""
        try:
            if cp_id:
                self.cp_button.setText(f"已选择CP为：{cp_id}")
                self.update_cities(cp_id)
            else:
                self.cp_button.setText("未选择CP")
                self.city_combo.clear()
                self.city_combo.setEnabled(False)
                self.get_restaurant_button.setEnabled(False)
        except Exception as e:
            self.logger.error(f"更新CP时出错: {str(e)}")
            self.cp_button.setText("未选择CP")
            self.city_combo.clear()
            self.city_combo.setEnabled(False)
            self.get_restaurant_button.setEnabled(False) 