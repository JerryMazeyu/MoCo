from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QComboBox, QGroupBox, QFileDialog, 
                             QMessageBox, QDialog, QTabWidget,QLineEdit, QButtonGroup, QRadioButton)
from PyQt5.QtGui import QPixmap
from app.utils.logger import get_logger
from app.services.instances.restaurant import Restaurant, RestaurantsGroup
from app.services.instances.vehicle import Vehicle, VehicleGroup
from app.services.functions.get_receive_record_service import GetReceiveRecordService
from app.services.instances.cp import CP
from app.config.config import CONF
from app.models.receive_record import ReceiveRecordModel
import oss2
from app.views.tabs.tab2 import CPSelectDialog
from app.views.components.xlsxviewer import XlsxViewerWidget  # 导入 XlsxViewerWidget
from app.utils import rp, oss_get_excel_file,oss_put_excel_file,oss_rename_excel_file
import pandas as pd
from PyQt5.QtCore import Qt

# 获取全局日志对象
LOGGER = get_logger()

class TransportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("运输信息")
        
        # 布局
        layout = QVBoxLayout()
        
        # 天数输入框
        self.days_input = QLineEdit(self)
        self.days_input.setPlaceholderText("请输入收油天数（1-31）")
        layout.addWidget(QLabel("运输天数:"))
        layout.addWidget(self.days_input)
        
        # 年月下拉框
        self.month_year_combo = QComboBox(self)
        self.month_year_combo.addItems(self.generate_month_year_options())
        layout.addWidget(QLabel("选择年月:"))
        layout.addWidget(self.month_year_combo)

        # 180KG桶占比
        self.bucket_ratio_input = QLineEdit(self)
        self.bucket_ratio_input.setText("1")  # 设置默认值为1
        self.bucket_ratio_input.setPlaceholderText("请输入180KG桶占比（0-1）")
        self.bucket_ratio_input.setEnabled(False)  # 暂时禁用输入
        layout.addWidget(QLabel("180KG桶占比:"))
        layout.addWidget(self.bucket_ratio_input)
        
        # 确认和取消按钮
        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("确认", self)
        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消", self)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def generate_month_year_options(self):
        """生成年月选项"""
        options = []
        for year in range(2020, 2031):  # 2020到2030年
            for month in range(1, 13):
                options.append(f"{year}-{month:02d}")
        return options

    def get_input_data(self):
        """获取输入的数据"""
        return self.days_input.text(), self.month_year_combo.currentText(), self.bucket_ratio_input.text()

class SalesDaysDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("销售运输天数")
        self.balance_total = None
        
        # 布局
        layout = QVBoxLayout()
        
        # 天数输入框
        self.days_input = QLineEdit(self)
        self.days_input.setPlaceholderText("请输入销售运输天数（1-31）")
        layout.addWidget(QLabel("销售运输天数:"))
        layout.addWidget(self.days_input)
        
        # 上传平衡表总表选项
        layout.addWidget(QLabel("是否上传已有平衡表总表:"))
        
        # 创建单选按钮组
        self.upload_group = QButtonGroup(self)
        self.upload_yes = QRadioButton("是", self)
        self.upload_no = QRadioButton("否", self)
        self.upload_no.setChecked(True)  # 默认选择"否"
        
        # 将单选按钮添加到组中
        self.upload_group.addButton(self.upload_yes)
        self.upload_group.addButton(self.upload_no)
        
        # 创建水平布局放置单选按钮
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.upload_yes)
        radio_layout.addWidget(self.upload_no)
        layout.addLayout(radio_layout)
        
        # 文件上传按钮（初始隐藏）
        self.file_button = QPushButton("选择平衡表总表文件", self)
        self.file_button.clicked.connect(self.select_file)
        self.file_button.setVisible(False)
        layout.addWidget(self.file_button)

        # 从OSS读取选项
        self.oss_group = QButtonGroup(self)
        self.oss_yes = QRadioButton("是", self)
        self.oss_no = QRadioButton("否", self)
        self.oss_yes.setChecked(True)  # 默认选择"是"
        
        self.oss_label = QLabel("是否读取OSS平衡表总表:", self)
        layout.addWidget(self.oss_label)
        
        oss_radio_layout = QHBoxLayout()
        oss_radio_layout.addWidget(self.oss_yes)
        oss_radio_layout.addWidget(self.oss_no)
        layout.addLayout(oss_radio_layout)
        
        # 连接单选按钮信号
        self.upload_yes.toggled.connect(self.toggle_file_button)
        self.upload_no.toggled.connect(self.toggle_oss_options)
        
        # 确认和取消按钮
        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("确认", self)
        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消", self)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def toggle_file_button(self, checked):
        """切换文件上传按钮的可见性"""
        self.file_button.setVisible(checked)
        # 当选择上传文件时，隐藏OSS选项
        self.oss_label.setVisible(not checked)
        self.oss_yes.setVisible(not checked)
        self.oss_no.setVisible(not checked)

    def toggle_oss_options(self, checked):
        """切换OSS选项的可见性"""
        self.oss_label.setVisible(checked)
        self.oss_yes.setVisible(checked)
        self.oss_no.setVisible(checked)

    def select_file(self):
        """选择并读取Excel文件"""
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择平衡表总表文件",
            "",
            "Excel Files (*.xlsx);;All Files (*)",
            options=options
        )
        
        if file_name:
            try:
                self.balance_total = pd.read_excel(file_name)
                self.file_button.setText(f"已选择: {file_name.split('/')[-1]}")
            except Exception as e:
                QMessageBox.critical(self, "读取失败", f"读取文件失败: {str(e)}")
                self.balance_total = None
                self.file_button.setText("选择平衡表总表文件")

    def get_input_data(self):
        """获取输入的数据"""
        days_input = self.days_input.text()
        
        # 如果选择上传文件
        if self.upload_yes.isChecked():
            return days_input, self.balance_total
        
        # 如果选择从OSS读取
        if self.upload_no.isChecked() and self.oss_yes.isChecked():
            try:
                # 获取父窗口的total_file路径
                parent = self.parent()
                if hasattr(parent, 'total_file'):
                    self.balance_total = oss_get_excel_file(parent.total_file)
                    if self.balance_total is None:
                        QMessageBox.warning(self, "文件不存在", f"未在OSS中找到文件: {parent.total_file}")
            except Exception as e:
                QMessageBox.critical(self, "读取失败", f"从OSS读取总表失败: {str(e)}")
                self.balance_total = None
        
        return days_input, self.balance_total

class Tab3(QWidget):
    """收油表生成Tab，实现餐厅和车辆信息的加载与收油表生成"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent
        self.current_cp = None
        self.restaurants = []
        self.vehicles = []
        self.xlsx_viewer = None  # 初始化为 None
        self.step_status_dict = {1: 'unfinish', 2: 'unfinish', 3: 'unfinish', 4: 'unfinish'}
        self.initUI()
    
    def initUI(self):
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        
        # 顶部布局 - 包含CP选择按钮
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # CP选择按钮
        self.cp_button = QPushButton("未选择CP")
        self.cp_button.clicked.connect(self.select_cp)
        self.cp_button.setMinimumWidth(200)
        self.cp_button.setStyleSheet("font-size: 15px; font-weight: bold;")
        
        # 清空按钮
        self.clear_button = QPushButton("清空页面")
        self.clear_button.clicked.connect(self.clear_page)
        self.clear_button.setMinimumWidth(120)
        self.clear_button.setStyleSheet("font-size: 15px; font-weight: bold;")
        
        top_layout.addStretch(1)
        top_layout.addWidget(self.cp_button)
        top_layout.addWidget(self.clear_button)  # 添加清空按钮
        
        self.layout.addLayout(top_layout)
        
        # 创建步骤状态布局和按钮布局的容器
        steps_and_buttons_layout = QHBoxLayout()
        
        # 步骤按钮样式（白色字体，圆角，带边框）
        self.button_style_tpl = """
        QPushButton {{
            background-color: {bg};
            color: white;
            border: 1.5px solid {border_color};
            border-radius: 20px;
            padding: 10px 32px;
            font-weight: bold;
            min-width: 160px;
            font-size: 18px;
        }}
        QPushButton:disabled {{
            background-color: {bg};
            color: white;
            border: 1.5px solid {border_color};
            opacity: 1;
        }}
        """
        # 箭头样式
        arrow_style = """
        QLabel {{
            color: #2196F3;
            font-size: 32px;
            font-weight: bold;
            padding-left: 16px;
            padding-right: 16px;
        }}
        """
        # 创建左侧的垂直布局，用于放置第一步的按钮
        step1_layout = QVBoxLayout()
        self.load_restaurants_button = QPushButton("上传餐厅信息")
        self.load_restaurants_button.clicked.connect(self.upload_restaurant_file)
        self.load_restaurants_button.setEnabled(False)
        self.load_restaurants_button.setMinimumWidth(160)
        self.load_restaurants_button.setSizePolicy(self.load_restaurants_button.sizePolicy().Expanding, self.load_restaurants_button.sizePolicy().Preferred)
        step1_layout.addWidget(self.load_restaurants_button, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addLayout(step1_layout)
        steps_and_buttons_layout.addSpacing(20)
        
        arrow1 = QLabel("→")
        arrow1.setStyleSheet(arrow_style)
        steps_and_buttons_layout.addWidget(arrow1, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addSpacing(20)
        
        # 创建中间的垂直布局，用于放置第二步的按钮
        step2_layout = QVBoxLayout()
        self.load_vehicles_button = QPushButton("载入车辆信息")
        self.load_vehicles_button.clicked.connect(self.load_vehicles)
        self.load_vehicles_button.setEnabled(False)
        self.load_vehicles_button.setMinimumWidth(160)
        self.load_vehicles_button.setSizePolicy(self.load_vehicles_button.sizePolicy().Expanding, self.load_vehicles_button.sizePolicy().Preferred)
        step2_layout.addWidget(self.load_vehicles_button, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addLayout(step2_layout)
        steps_and_buttons_layout.addSpacing(20)
        
        arrow2 = QLabel("→")
        arrow2.setStyleSheet(arrow_style)
        steps_and_buttons_layout.addWidget(arrow2, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addSpacing(20)
        
        # 创建右侧的垂直布局，用于放置第三步的按钮
        step3_layout = QVBoxLayout()
        self.generate_report_button = QPushButton("生成收油表和平衡表")
        self.generate_report_button.clicked.connect(self.generate_report)
        self.generate_report_button.setEnabled(False)
        self.generate_report_button.setMinimumWidth(180)
        self.generate_report_button.setSizePolicy(self.generate_report_button.sizePolicy().Expanding, self.generate_report_button.sizePolicy().Preferred)
        step3_layout.addWidget(self.generate_report_button, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addLayout(step3_layout)
        steps_and_buttons_layout.addSpacing(20)
        
        arrow3 = QLabel("→")
        arrow3.setStyleSheet(arrow_style)
        steps_and_buttons_layout.addWidget(arrow3, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addSpacing(20)
        
        # 创建第四步的垂直布局
        step4_layout = QVBoxLayout()
        self.generate_total_button = QPushButton("生成总表和收货确认书")
        self.generate_total_button.clicked.connect(self.generate_total)
        self.generate_total_button.setEnabled(False)
        self.generate_total_button.setMinimumWidth(180)
        self.generate_total_button.setSizePolicy(self.generate_total_button.sizePolicy().Expanding, self.generate_total_button.sizePolicy().Preferred)
        step4_layout.addWidget(self.generate_total_button, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addLayout(step4_layout)
        
        # 添加弹性空间
        steps_and_buttons_layout.addStretch()
        
        # 将步骤和按钮的布局添加到主布局
        self.layout.addLayout(steps_and_buttons_layout)
        
        # 创建带有页签的数据展示区
        self.tab_widget = QTabWidget()
        
        # 初始化XlsxViewerWidget实例为None
        self.restaurant_viewer = None
        self.vehicle_viewer = None
        self.report_viewer = None
        self.balance_view = None
        self.total_view = None
        self.check_view = None
        
        self.layout.addWidget(self.tab_widget)
            # 在添加 tab_widget 之后，添加保存所有按钮的布局
        bottom_layout = QHBoxLayout()
        self.save_all_button = QPushButton("保存所有信息")
        self.save_all_button.clicked.connect(self.save_all_data)
        self.save_all_button.setMinimumWidth(140)
        self.save_all_button.setStyleSheet("font-size: 15px; font-weight: bold;")
        bottom_layout.addStretch()  # 添加弹性空间，使按钮靠右
        bottom_layout.addWidget(self.save_all_button)
        
        # 将底部布局添加到主布局
        self.layout.addLayout(bottom_layout)
        # 获取全局日志对象
        self.logger = get_logger()
        # 初始化按钮状态颜色（全部灰色且不可点击）
        for btn in [self.load_restaurants_button, self.load_vehicles_button, self.generate_report_button, self.generate_total_button]:
            btn.setEnabled(False)
            btn.setStyleSheet(self.button_style_tpl.format(bg='#BDBDBD', border_color='#E0E0E0'))
    
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
                    
                    # 获取配置中的CP ID列表 - 直接使用CONF.BUSINESS.CP，因为它就是一个ID列表
                    conf_cp_ids = []
                    if hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                        conf_cp_ids = CONF.BUSINESS.CP.cp_id  # 直接使用列表
                    
                    LOGGER.info(f"配置中的CP ID列表: {conf_cp_ids}")
                    
                    if cp_data['cp_id'] in conf_cp_ids:
                        LOGGER.info(f"选择的CP {cp_data['cp_name']} (ID: {cp_data['cp_id']}) 在配置中存在")
                    else:
                        LOGGER.warning(f"选择的CP {cp_data['cp_name']} (ID: {cp_data['cp_id']}) 不在配置中")
                        reply = QMessageBox.question(
                            self, 'CP不在配置中', 
                            f'选择的CP "{cp_data["cp_name"]}" 不在配置列表中。是否继续使用？',
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                        )
                        if reply == QMessageBox.No:
                            return
                
                    # 保存选择的CP到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                    
                    CONF.runtime.CP = cp_data
                    self.current_cp = cp_data
                    
                    # 在创建新的 viewer 之前，先清除所有现有的标签页
                    self.tab_widget.clear()
                    
                    # 生成文件路径
                    self.restaurant_file = f"CPs/{cp_data['cp_id']}/restaurant/restaurants.xlsx"
                    self.vehicle_file = f"CPs/{cp_data['cp_id']}/vehicle/vehicles.xlsx"
                    self.receive_record_file = f"CPs/{cp_data['cp_id']}/receive_record/receive_records.xlsx"
                    self.balance_record_file = f"CPs/{cp_data['cp_id']}/balance_record/balance_record.xlsx"
                    self.total_file = f"CPs/{cp_data['cp_id']}/total/total.xlsx"
                    self.check_file = f"CPs/{cp_data['cp_id']}/check/check.xlsx"
                    
                    # 在选择CP后创建XlsxViewerWidget实例
                    self.restaurant_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.restaurant_file,show_open=False,show_save=False)
                    self.vehicle_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.vehicle_file,show_open=False,show_save=False)
                    self.report_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.receive_record_file,show_open=False,show_save=False)
                    self.balance_view = XlsxViewerWidget(use_oss=True, oss_path=self.balance_record_file,show_open=False,show_save=False)
                    self.total_view = XlsxViewerWidget(use_oss=True, oss_path=self.total_file,show_open=False,show_save=False)
                    self.check_view = XlsxViewerWidget(use_oss=True, oss_path=self.check_file,show_open=False,show_save=False)
                    
                    # 将XlsxViewerWidget实例添加到tab_widget
                    self.tab_widget.addTab(self.restaurant_viewer, "餐厅信息")
                    self.tab_widget.addTab(self.vehicle_viewer, "车辆信息")
                    self.tab_widget.addTab(self.report_viewer, "收油表")
                    self.tab_widget.addTab(self.balance_view, "平衡表")
                    self.tab_widget.addTab(self.total_view, "总表")
                    self.tab_widget.addTab(self.check_view, "收货确认书")
                    
                    # 更新CP按钮文本
                    self.cp_button.setText(f"已选择CP为：{cp_data['cp_name']}")
                    
                    # 通知主窗口更新CP
                    if self.main_window_ref:
                        self.main_window_ref.set_current_cp(cp_data['cp_id'])
                    
                    # 启用第一步按钮，禁用后续按钮
                    self.load_restaurants_button.setEnabled(True)
                    self.load_vehicles_button.setEnabled(False)
                    self.generate_report_button.setEnabled(False)
                    # 只调用一次，第一步为蓝色，其余为灰色
                    self.update_step_status(1, 'unfinish')
                
        except Exception as e:
            LOGGER.error(f"选择CP时出错: {str(e)}")
            LOGGER.error(f"CONF.BUSINESS.CP的内容: {getattr(CONF.BUSINESS, 'CP', None)}")
            QMessageBox.critical(self, "选择CP失败", f"选择CP时出错: {str(e)}")
    
    def update_step_status(self, step, status):
        self.step_status_dict[step] = status
        button_map = {
            1: self.load_restaurants_button,
            2: self.load_vehicles_button,
            3: self.generate_report_button,
            4: self.generate_total_button,
        }
        color_map = {
            'finish':   ('#4CAF50', '#4CAF50'),   # 绿色
            'error':    ('#F44336', '#F44336'),   # 红色
            'dealing':  ('#FFB300', '#FFB300'),   # 黄色
            'unfinish': ('#BDBDBD', '#E0E0E0'),   # 灰色
            'blue':     ('#2196F3', '#2196F3'),   # 蓝色
        }
        # 找到下一个未完成的步骤
        next_step = None
        for i in range(1, 5):
            if self.step_status_dict[i] != 'finish':
                next_step = i
                break
        for i in range(1, 5):
            btn = button_map[i]
            st = self.step_status_dict[i]
            if st == 'finish':
                btn.setEnabled(True)
                btn.setStyleSheet(self.button_style_tpl.format(bg=color_map['finish'][0], border_color=color_map['finish'][1]))
            elif i == step:
                if status == 'dealing':
                    btn.setEnabled(False)
                    btn.setStyleSheet(self.button_style_tpl.format(bg=color_map['dealing'][0], border_color=color_map['dealing'][1]))
                elif status == 'error':
                    btn.setEnabled(True)
                    btn.setStyleSheet(self.button_style_tpl.format(bg=color_map['error'][0], border_color=color_map['error'][1]))
                else:
                    btn.setEnabled(True)
                    btn.setStyleSheet(self.button_style_tpl.format(bg=color_map['blue'][0], border_color=color_map['blue'][1]))
            elif i == next_step:
                btn.setEnabled(True)
                btn.setStyleSheet(self.button_style_tpl.format(bg=color_map['blue'][0], border_color=color_map['blue'][1]))
            else:
                btn.setEnabled(False)
                btn.setStyleSheet(self.button_style_tpl.format(bg=color_map['unfinish'][0], border_color=color_map['unfinish'][1]))

    ## 从oss载入餐厅
    def load_restaurants(self):
        """载入餐厅信息"""
        self.update_step_status(1, 'dealing')
        try:
            if not hasattr(self, 'restaurant_file'):
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 从OSS读取数据
            try:
                restaurant_data = oss_get_excel_file(self.restaurant_file)
                if restaurant_data is None:
                    QMessageBox.warning(self, "文件不存在", f"未找到文件: {self.restaurant_file}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "读取失败", f"从OSS读取餐厅信息失败: {str(e)}")
                return
            
            # 转换为Restaurant对象列表
            self.restaurants = [Restaurant(info) for info in restaurant_data.to_dict('records')]
            
            # 使用RestaurantsGroup进行过滤
            restaurants_group = RestaurantsGroup(self.restaurants)
            self.restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dicts()
            filter_restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dataframe()
            # 将数据加载到餐厅信息页签
            self.restaurant_viewer.load_data(data=filter_restaurants)
            
            # 切换到餐厅信息页签
            self.tab_widget.setCurrentIndex(0)
            
            self.logger.info(f"成功载入餐厅信息，共 {len(self.restaurants)} 条记录")
            self.update_step_status(1, 'finish')
        except Exception as e:
            self.logger.error(f"载入餐厅信息时出错: {str(e)}")
            QMessageBox.critical(self, "载入失败", f"载入餐厅信息时出错: {str(e)}")
            self.update_step_status(1, 'error')
    
    def load_vehicles(self):
        """载入车辆信息"""
        self.update_step_status(2, 'dealing')
        try:
            if not hasattr(self, 'vehicle_file'):
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 从OSS读取数据
            try:
                vehicle_data = oss_get_excel_file(self.vehicle_file)
                if vehicle_data is None:
                    QMessageBox.warning(self, "文件不存在", f"未找到文件: {self.vehicle_file}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "读取失败", f"从OSS读取车辆信息失败: {str(e)}")
                return
            
            # 转换为Vehicle对象列表
            self.vehicles = [Vehicle(info) for info in vehicle_data.to_dict('records')]
            
            # 使用VehicleGroup进行过滤
            vehicles_group = VehicleGroup(self.vehicles)
            self.vehicles = vehicles_group.filter_by_cp(self.current_cp['cp_id']).to_dicts()
            filter_vehicles = vehicles_group.filter_by_cp(self.current_cp['cp_id']).to_dataframe()
            # 将数据加载到车辆信息页签
            self.vehicle_viewer.load_data(data=filter_vehicles)
            
            # 切换到车辆信息页签
            self.tab_widget.setCurrentIndex(1)
            
            self.logger.info(f"成功载入车辆信息，共 {len(self.vehicles)} 条记录")
            self.update_step_status(2, 'finish')
        except Exception as e:
            self.logger.error(f"载入车辆信息时出错: {str(e)}")
            QMessageBox.critical(self, "载入失败", f"载入车辆信息时出错: {str(e)}")
            self.update_step_status(2, 'error')
    
    def generate_report(self):
        """生成收油表"""
        self.update_step_status(3, 'dealing')
         # 首先从 XlsxViewerWidget 获取最新的数据
        if not self.restaurant_viewer or not self.vehicle_viewer:
            QMessageBox.warning(self, "数据不完整", "请先载入餐厅信息和车辆信息。")
            self.update_step_status(3, 'error')
            return
         # 获取最新的餐厅数据
        restaurant_df = self.restaurant_viewer.get_data()
        if restaurant_df is None or restaurant_df.empty:
            QMessageBox.warning(self, "数据不完整", "餐厅信息为空，请先载入餐厅数据。")
            self.update_step_status(3, 'error')
            return
         # 获取最新的车辆数据
        vehicle_df = self.vehicle_viewer.get_data()
        if vehicle_df is None or vehicle_df.empty:
            QMessageBox.warning(self, "数据不完整", "车辆信息为空，请先载入车辆数据。")
            self.update_step_status(3, 'error')
            return
        
        self.restaurants = restaurant_df.to_dict('records')
        self.vehicles = vehicle_df.to_dict('records')
        # 弹出运输信息对话框
        dialog = TransportDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            days_input, month_year, bucket_ratio = dialog.get_input_data()
            year, month = month_year.split('-')
            CONF.runtime.dates_to_trans = f'{year}-{month}-{days_input}'
            # 验证天数输入
            if not days_input.isdigit() or not (1 <= int(days_input) <= 31):
                QMessageBox.warning(self, "输入错误", "运输天数必须为1到31之间的数字。")
                self.update_step_status(3, 'error')
                return
            
            # 处理输入数据
            days_to_trans = int(days_input)
            self.logger.info(f"运输天数: {days_to_trans}, 选择的年月: {month_year}")
            
            try:
                service = GetReceiveRecordService(model=ReceiveRecordModel, conf=CONF)
                oil_records_df, restaurant_balance, cp_restaurants_df, cp_vehicle_df = service.get_restaurant_oil_records(self.restaurants, self.vehicles, self.current_cp['cp_id'],days_to_trans, month_year)
                # 更新所有相关页面的数据
                    # 1. 更新收油表
                self.report_viewer.load_data(data=oil_records_df)
                
                # 2. 更新平衡表
                self.balance_view.load_data(data=restaurant_balance)
                
                # 3. 更新餐厅信息
                self.restaurant_viewer.load_data(data=cp_restaurants_df)
                
                # 4. 更新车辆信息
                self.vehicle_viewer.load_data(data=cp_vehicle_df)
                # 验证更新
                # self.logger.info("更新后的数据:")
                # self.logger.info(f"显示的数据:\n{self.vehicle_viewer.get_data()}")
                
                # 切换到收油表页签
                self.tab_widget.setCurrentIndex(2)
                
                self.logger.info("收油表、平衡表生成成功")
                self.update_step_status(3, 'finish')
            except Exception as e:
                self.logger.error(f"生成收油表、平衡表时出错: {str(e)}")
                QMessageBox.critical(self, "生成失败", f"生成收油表时出错: {str(e)}")
                self.update_step_status(3, 'error')
        else:
            self.update_step_status(3, 'unfinish')
    
    def upload_restaurant_file(self):
        """上传餐厅信息文件"""
        if not hasattr(self, 'vehicle_file'):
            QMessageBox.warning(self, "未选择CP", "请先选择CP")
            return
        
        self.update_step_status(1, 'dealing')
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "选择餐厅信息文件", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_name:
            try:
            # 直接使用pandas读取本地Excel文件
                restaurant_data = pd.read_excel(file_name)
                if restaurant_data.empty:
                    QMessageBox.warning(self, "文件为空", "所选文件没有数据")
                    self.update_step_status(1, 'error')
                    return
                
                # 转换为Restaurant对象列表
                self.restaurants = [Restaurant(info) for info in restaurant_data.to_dict('records')]
                
                # 使用RestaurantsGroup进行过滤
                restaurants_group = RestaurantsGroup(self.restaurants)
                self.restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dicts()
                filter_restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dataframe()
                
                # 将数据加载到餐厅信息页签
                self.restaurant_viewer.load_data(data=filter_restaurants)
                
                # 切换到餐厅信息页签
                self.tab_widget.setCurrentIndex(0)
                

                
                self.logger.info(f"成功载入餐厅信息，共 {len(self.restaurants)} 条记录")
                self.update_step_status(1, 'finish')
            except Exception as e:
                self.logger.error(f"上传餐厅信息时出错: {str(e)}")
                QMessageBox.critical(self, "上传失败", f"上传餐厅信息时出错: {str(e)}")
                self.update_step_status(1, 'error')

    def clear_page(self):
        """清空页面，重置所有状态"""
        self.current_cp = None
        self.restaurants = []
        self.vehicles = []
        self.cp_button.setText("未选择CP")
        self.load_restaurants_button.setEnabled(False)
        self.load_vehicles_button.setEnabled(False)
        self.generate_report_button.setEnabled(False)
        self.generate_total_button.setEnabled(False)
        self.tab_widget.clear()  # 清空所有页签内容

        # 重置所有步骤状态
        self.step_status_dict = {1: 'unfinish', 2: 'unfinish', 3: 'unfinish', 4: 'unfinish'}
        for btn in [self.load_restaurants_button, self.load_vehicles_button, self.generate_report_button, self.generate_total_button]:
            btn.setEnabled(False)
            btn.setStyleSheet(self.button_style_tpl.format(bg='#BDBDBD', border_color='#E0E0E0'))

    """保存所有信息（车辆信息、收油表、平衡表）"""
    def save_all_data(self):
        try:
            success_count = 0
            error_messages = []
            
            # 保存车辆信息
            if self.vehicle_viewer :
                try:
                    if self.vehicle_viewer.save_file():
                        success_count += 1
                except Exception as e:
                    error_messages.append(f"保存车辆信息失败: {str(e)}")
            
            # 保存收油表
            if self.report_viewer :
                try:
                    if self.report_viewer.save_file():
                        success_count += 1
                except Exception as e:
                    error_messages.append(f"保存收油表失败: {str(e)}")
            
            # 保存平衡表
            if self.balance_view :
                try:
                    if self.balance_view.save_file():
                        success_count += 1
                except Exception as e:
                    error_messages.append(f"保存平衡表失败: {str(e)}")
            # 保存总表
            if self.total_view:
                try:
                    if self.balance_view.save_file():
                        success_count +=1
                except Exception as e:
                    error_messages.append(f"保存总表失败: {str(e)}")
            # 保存收货确认书
            if self.check_view:
                try:
                    if self.check_view.save_file():
                        success_count +=1
                except Exception as e:
                    error_messages.append(f"保存总表失败: {str(e)}")
            # 显示保存结果
            if error_messages:
                # 如果有错误，显示错误信息
                error_text = "\n".join(error_messages)
                if success_count > 0:
                    QMessageBox.warning(
                        self,
                        "部分保存成功",
                        f"成功保存 {success_count} 个文件。\n\n以下保存失败：\n{error_text}"
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "保存失败",
                        f"所有保存操作失败：\n{error_text}"
                    )
            elif success_count > 0:
                # 如果全部成功，显示成功信息
                QMessageBox.information(
                    self,
                    "保存成功",
                    f"已成功保存所有修改的文件（{success_count} 个）。"
                )
            else:
                # 如果没有需要保存的内容
                QMessageBox.information(
                    self,
                    "无需保存",
                    "没有需要保存的修改内容。"
                )
                
        except Exception as e:
            self.logger.error(f"保存所有信息时出错: {str(e)}")
            QMessageBox.critical(
                self,
                "保存错误",
                f"保存过程中发生错误：{str(e)}"
            )

    def generate_total(self):
        """生成总表和收货确认书"""
        self.update_step_status(4, 'dealing')
        try:
            # 获取车辆信息
            vehicle_df = self.vehicle_viewer.get_data()
            if vehicle_df is None or vehicle_df.empty:
                QMessageBox.warning(self, "数据不完整", "车辆信息为空，请先载入车辆数据。")
                self.update_step_status(4, 'error')
                return

            # 获取收油表数据
            oil_records_df = self.report_viewer.get_data()
            if oil_records_df is None or oil_records_df.empty:
                QMessageBox.warning(self, "数据不完整", "收油表为空，请先生成收油表。")
                self.update_step_status(4, 'error')
                return

            # 获取平衡表数据
            balance_df = self.balance_view.get_data()
            if balance_df is None or balance_df.empty:
                QMessageBox.warning(self, "数据不完整", "平衡表为空，请先生成平衡表。")
                self.update_step_status(4, 'error')
                return

            # 弹出销售运输天数输入对话框
            dialog = SalesDaysDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                days_input, balance_total = dialog.get_input_data()
                
                # 验证天数输入
                if not days_input.isdigit() or not (1 <= int(days_input) <= 31):
                    QMessageBox.warning(self, "输入错误", "销售运输天数必须为1到31之间的数字。")
                    self.update_step_status(4, 'error')
                    return
                
                # 调用服务生成总表和收货确认书
                service = GetReceiveRecordService(model=ReceiveRecordModel, conf=CONF)

                # 1. 先生成总表的基础结构
                total_df = service.process_dataframe_with_new_columns(balance_df, balance_total)

                # 2. 生成收货确认书
                check_df,cp_vehicle_df = service.generate_df_check(int(days_input), balance_df, vehicle_df)

                # 3. 更新总表的售出数量
                total_df = service.process_check_to_sum(check_df, total_df)

                # 4. 重新计算期末库存
                previous_end_stock = 0.0  # 第一行的期末库存前一行默认0
                for index, row in total_df.iterrows():
                    current_output = row['total_output_quantity'] if pd.notna(row['total_output_quantity']) else 0
                    current_sale = row['total_quantities_sold'] if pd.notna(row['total_quantities_sold']) else 0
                    current_inventory = round(current_output + previous_end_stock - current_sale, 2)
                    if current_inventory < 0:
                        raise ValueError(f"{row['total_supplied_date']}库存不足: 当前产出量({current_output}) + 上期库存({previous_end_stock}) < 售出数量({current_sale})")
                    total_df.at[index, 'total_ending_inventory'] = current_inventory
                    previous_end_stock = current_inventory

                # 5. 处理合同分配
                coeff_number = CONF.BUSINESS.REST2CP.比率
                current_date = balance_df['balance_date'].min().strftime('%Y-%m')
                
                # 调用合同分配处理函数
                total_df, balance_last_month, balance_current_month = service.process_balance_sum_contract(
                    total_df, check_df, None, balance_df, coeff_number, current_date
                )
                oil_records_df = service.copy_balance_to_oil_dataframes(oil_records_df, balance_current_month)

                # 更新总表和收货确认书、收油表、平衡表视图
                self.total_view.load_data(data=total_df)
                self.check_view.load_data(data=check_df)
                self.report_viewer.load_data(data=oil_records_df)
                self.balance_view.load_data(data=balance_current_month)
                ## 更新车辆信息
                self.vehicle_viewer.load_data(data=cp_vehicle_df)

                # 切换到总表页签
                self.tab_widget.setCurrentIndex(4)

                self.logger.info("总表和收货确认书生成成功")
                self.update_step_status(4, 'finish')
            else:
                self.update_step_status(4, 'unfinish')
        except Exception as e:
            self.logger.error(f"生成总表和收货确认书时出错: {str(e)}")
            QMessageBox.critical(self, "生成失败", f"生成总表和收货确认书时出错: {str(e)}")
            self.update_step_status(4, 'error')