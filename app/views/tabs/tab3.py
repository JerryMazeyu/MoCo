from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QComboBox, QGroupBox, QFileDialog, 
                             QMessageBox, QDialog, QTabWidget,QLineEdit, QButtonGroup, QRadioButton, QTreeWidget, QTreeWidgetItem, QInputDialog, QTextEdit)
from PyQt5.QtGui import QPixmap, QColor
from app.utils.logger import get_logger
from app.services.instances.restaurant import Restaurant, RestaurantsGroup
from app.services.instances.receive_record import BalanceTotal, BalanceTotalGroup,BuyerConfirmation,BuyerConfirmationGroup
from app.services.instances.vehicle import Vehicle, VehicleGroup
from app.services.functions.get_receive_record_service import GetReceiveRecordService
from app.services.instances.cp import CP
from app.config.config import CONF
from app.models.receive_record import ReceiveRecordModel,RestaurantTotalModel,BuyerConfirmationModel
from app.models.restaurant_model import RestaurantModel
import oss2
from app.views.tabs.tab2 import CPSelectDialog
from app.views.components.xlsxviewer import XlsxViewerWidget  # 导入 XlsxViewerWidget
from app.utils import rp, oss_get_excel_file,oss_put_excel_file,oss_rename_excel_file
import pandas as pd
from PyQt5.QtCore import Qt
import datetime
import xlsxwriter
import calendar

# 获取全局日志对象
LOGGER = get_logger()

class TransportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("运输信息")
        self.setMinimumWidth(500)  # 适当加宽
        
        layout = QVBoxLayout()
        
        label_width = 150
        input_width = 200  # 建议再加宽
        
        # 年月
        month_layout = QHBoxLayout()
        month_layout.setAlignment(Qt.AlignLeft)
        month_label = QLabel("选择年月:")
        month_label.setFixedWidth(label_width)
        month_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        month_layout.addWidget(month_label)
        self.month_year_combo = QComboBox(self)
        self.month_year_combo.addItems(self.generate_month_year_options())
        self.month_year_combo.setFixedWidth(input_width)
        month_layout.addWidget(self.month_year_combo)
        month_layout.addStretch()
        layout.addLayout(month_layout)
        
        # 运输天数
        days_layout = QHBoxLayout()
        days_layout.setAlignment(Qt.AlignLeft)
        days_label = QLabel("运输天数:")
        days_label.setFixedWidth(label_width)
        days_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        days_layout.addWidget(days_label)
        self.days_input = QLineEdit(self)
        self.days_input.setPlaceholderText("请输入收油天数（1-31）")
        self.days_input.setFixedWidth(input_width)
        days_layout.addWidget(self.days_input)
        days_layout.addStretch()
        layout.addLayout(days_layout)
        
        # 是否全部收油
        collect_layout = QHBoxLayout()
        collect_layout.setAlignment(Qt.AlignLeft)
        collect_label = QLabel("是否全部收油:")
        collect_label.setFixedWidth(label_width)
        collect_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        collect_layout.addWidget(collect_label)
        self.collect_all_radio = QRadioButton("全部收油", self)
        self.collect_partial_radio = QRadioButton("部分收油", self)
        self.collect_all_radio.setChecked(True)
        collect_layout.addWidget(self.collect_all_radio)
        collect_layout.addWidget(self.collect_partial_radio)
        collect_layout.addStretch()
        layout.addLayout(collect_layout)
        
        # 收油重量（整行）
        self.weight_widget = QWidget()
        weight_row_layout = QHBoxLayout(self.weight_widget)
        weight_label = QLabel("收油重量（成品）:")
        weight_label.setFixedWidth(label_width)
        weight_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        weight_row_layout.addWidget(weight_label)
        self.weight_input = QLineEdit()
        self.weight_input.setPlaceholderText("请输入收油重量")
        self.weight_input.setFixedWidth(input_width)
        weight_row_layout.addWidget(self.weight_input)
        weight_row_layout.addWidget(QLabel("吨"))
        weight_row_layout.addStretch()
        self.weight_widget.setVisible(False)
        layout.addWidget(self.weight_widget)
        
        # 180KG桶占比
        bucket_layout = QHBoxLayout()
        bucket_layout.setAlignment(Qt.AlignLeft)
        bucket_label = QLabel("180KG桶占比:")
        bucket_label.setFixedWidth(label_width)
        bucket_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        bucket_layout.addWidget(bucket_label)
        self.bucket_ratio_input = QLineEdit(self)
        self.bucket_ratio_input.setText("1")
        self.bucket_ratio_input.setPlaceholderText("请输入180KG桶占比（0-1）")
        self.bucket_ratio_input.setEnabled(False)
        self.bucket_ratio_input.setFixedWidth(input_width)
        bucket_layout.addWidget(self.bucket_ratio_input)
        bucket_layout.addStretch()
        layout.addLayout(bucket_layout)

        # 区域排序选项
        sort_layout = QHBoxLayout()
        sort_layout.setAlignment(Qt.AlignLeft)
        sort_label = QLabel("按区域首字母排序:")
        sort_label.setFixedWidth(label_width)
        sort_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sort_layout.addWidget(sort_label)
        self.sort_combo = QComboBox(self)
        self.sort_combo.addItems(["是", "否"])
        self.sort_combo.setFixedWidth(input_width)
        self.sort_combo.currentIndexChanged.connect(self.on_sort_option_changed)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # 自定义区域顺序选择框（初始隐藏）
        self.custom_order_widget = QWidget()
        custom_order_layout = QVBoxLayout(self.custom_order_widget)
        
        
        # 已选择的区域显示框
        self.selected_districts_label = QLabel("自定义区域排序：")
        self.selected_districts_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.selected_districts_text = QTextEdit("")
        self.selected_districts_text.setReadOnly(True)
        self.selected_districts_text.setFixedHeight(60)  # 可根据需要调整高度
        self.selected_districts_text.setStyleSheet("background-color: #f0f0f0; padding: 5px; border-radius: 3px;")
        custom_order_layout.addWidget(self.selected_districts_label)
        custom_order_layout.addWidget(self.selected_districts_text)
        
        # 区域选择下拉框
        district_layout = QHBoxLayout()
        self.district_combo = QComboBox(self)
        self.district_combo.setFixedWidth(input_width)
        self.district_combo.currentIndexChanged.connect(self.on_district_selected)
        district_layout.addWidget(self.district_combo)
        
        # 添加按钮
        add_button = QPushButton("添加")
        add_button.clicked.connect(self.add_selected_district)
        district_layout.addWidget(add_button)
        
        # 重置按钮
        reset_button = QPushButton("重置选择")
        reset_button.clicked.connect(self.reset_district_selection)
        district_layout.addWidget(reset_button)
        
        custom_order_layout.addLayout(district_layout)
        
        self.custom_order_widget.setVisible(False)
        layout.addWidget(self.custom_order_widget)
        
        # 按钮
        button_layout = QHBoxLayout()
        self.confirm_button = QPushButton("确认", self)
        self.confirm_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("取消", self)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # 连接信号
        self.weight_input.textChanged.connect(self.validate_weight_input)
        self.collect_all_radio.toggled.connect(self.toggle_weight_input)
        self.collect_partial_radio.toggled.connect(self.toggle_weight_input)
        self.month_year_combo.currentIndexChanged.connect(self.update_days_input)
        
        # 初始化区域选择列表
        self.selected_districts = []
        
        # 设置默认选择当前月份并更新天数
        current_date = datetime.datetime.now()
        default_month_year = f"{current_date.year}-{current_date.month:02d}"
        index = self.month_year_combo.findText(default_month_year)
        if index >= 0:
            self.month_year_combo.setCurrentIndex(index)
            self.update_days_input()  # 手动调用一次更新天数

    def on_sort_option_changed(self, index):
        """当排序选项改变时显示或隐藏自定义顺序输入框"""
        show_custom = index == 1  # 当选择"否"时显示
        self.custom_order_widget.setVisible(show_custom)
        if show_custom:
            # 获取父窗口的餐厅数据
            parent = self.parent()
            if hasattr(parent, 'restaurant_viewer'):
                restaurant_df = parent.restaurant_viewer.get_data()
                if restaurant_df is not None and not restaurant_df.empty:
                    # 获取所有区域并去重
                    all_districts = sorted(restaurant_df['rest_district'].unique())
                    self.setup_district_combo(all_districts)

    def setup_district_combo(self, districts):
        """设置区域选择下拉框"""
        self.district_combo.clear()
        self.district_combo.addItems(districts)
        # 初始化区域选择列表
        self.selected_districts = []

    def on_district_selected(self, index):
        """处理区域选择事件"""
        pass  # 不需要在这里处理，由添加按钮触发

    def add_selected_district(self):
        """添加选中的区域到列表"""
        current_district = self.district_combo.currentText()
        if current_district and current_district not in self.selected_districts:
            self.selected_districts.append(current_district)
            self.update_selected_districts_display()

    def update_selected_districts_display(self):
        """更新已选择区域的显示"""
        if self.selected_districts:
            self.selected_districts_text.setPlainText(", ".join(self.selected_districts))
        else:
            self.selected_districts_text.setPlainText("")

    def reset_district_selection(self):
        """重置区域选择"""
        self.selected_districts.clear()
        self.update_selected_districts_display()

    def toggle_weight_input(self, checked):
        """根据单选按钮状态切换收油重量输入框的显示状态"""
        if self.sender() == self.collect_all_radio and checked:
            self.weight_widget.setVisible(False)
            self.weight_input.setText("")  # 清空输入
        elif self.sender() == self.collect_partial_radio and checked:
            self.weight_widget.setVisible(True)

    def validate_weight_input(self, text):
        """验证收油重量输入是否为有效数值"""
        if text:
            try:
                float(text)
                self.weight_input.setStyleSheet("")
            except ValueError:
                self.weight_input.setStyleSheet("background-color: #FFE4E1;")  # 浅红色背景表示错误
        else:
            self.weight_input.setStyleSheet("")

    def generate_month_year_options(self):
        """生成年月选项"""
        options = []
        for year in range(2020, 2031):  # 2020到2030年
            for month in range(1, 13):
                options.append(f"{year}-{month:02d}")
        return options

    def get_input_data(self):
        """获取输入的数据"""
        weight = self.weight_input.text() if self.collect_partial_radio.isChecked() else ""
        sort_by_letter = self.sort_combo.currentText() == "是"
        custom_order = ",".join(self.selected_districts) if not sort_by_letter and self.selected_districts else None
        return self.days_input.text(), self.month_year_combo.currentText(), self.bucket_ratio_input.text(), weight, sort_by_letter, custom_order

    def update_days_input(self):
        """根据选择的年月更新运输天数的默认值"""
        selected_date = self.month_year_combo.currentText()
        year, month = map(int, selected_date.split('-'))
        # 获取该月的最后一天
        last_day = calendar.monthrange(year, month)[1]
        self.days_input.setPlaceholderText(f"请输入收油天数（1-{last_day}）")
        self.days_input.setText(str(last_day))  # 设置默认值为该月的天数

class SalesDaysDialog(QDialog):
    def __init__(self, parent=None, min_balance_date=None):
        super().__init__(parent)
        self.setWindowTitle("销售运输天数")
        self.balance_total = None
        self.min_balance_date = min_balance_date
        
        # 布局
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft)  # 主布局左对齐
        
        # 开始运输日期：年、月、日下拉框
        date_layout = QHBoxLayout()
        date_layout.setAlignment(Qt.AlignLeft)
        date_label = QLabel("开始运输日期:")
        date_label.setFixedWidth(120)
        date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        date_layout.addWidget(date_label)

        self.year_combo = QComboBox(self)
        self.year_combo.addItems([str(y) for y in range(2020, 2031)])
        self.year_combo.setFixedWidth(70)
        date_layout.addWidget(self.year_combo)

        self.month_combo = QComboBox(self)
        self.month_combo.addItems([f"{m:02d}" for m in range(1, 13)])
        self.month_combo.setFixedWidth(50)
        date_layout.addWidget(self.month_combo)

        self.day_combo = QComboBox(self)
        self.day_combo.addItems([f"{d:02d}" for d in range(1, 32)])
        self.day_combo.setFixedWidth(50)
        date_layout.addWidget(self.day_combo)

        date_layout.addStretch()
        layout.addLayout(date_layout)

        # 红字提示单独一行，左对齐
        self.date_warn_label = QLabel("")
        self.date_warn_label.setStyleSheet("color: red;")
        self.date_warn_label.setVisible(False)
        warn_layout = QHBoxLayout()
        warn_layout.setAlignment(Qt.AlignLeft)
        warn_layout.addSpacing(120)  # 与上面label对齐
        warn_layout.addWidget(self.date_warn_label, alignment=Qt.AlignLeft)
        warn_layout.addStretch()
        layout.addLayout(warn_layout)
        
        # 天数输入框
        days_layout = QHBoxLayout()
        days_layout.setAlignment(Qt.AlignLeft)
        days_label = QLabel("销售运输天数:")
        days_label.setFixedWidth(120)
        days_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        days_layout.addWidget(days_label)
        self.days_input = QLineEdit(self)
        self.days_input.setPlaceholderText("请输入销售运输天数（1-31）")
        self.days_input.setFixedWidth(150)
        self.days_input.textChanged.connect(self.validate_days)  # 添加验证
        days_layout.addWidget(self.days_input)
        days_layout.addStretch()
        layout.addLayout(days_layout)

        # 天数警告提示
        self.days_warn_label = QLabel("")
        self.days_warn_label.setStyleSheet("color: red;")
        self.days_warn_label.setVisible(False)
        days_warn_layout = QHBoxLayout()
        days_warn_layout.setAlignment(Qt.AlignLeft)
        days_warn_layout.addSpacing(120)  # 与上面label对齐
        days_warn_layout.addWidget(self.days_warn_label, alignment=Qt.AlignLeft)
        days_warn_layout.addStretch()
        layout.addLayout(days_warn_layout)

        # 是否忽略库存
        ignore_layout = QHBoxLayout()
        ignore_layout.setAlignment(Qt.AlignLeft)
        ignore_label = QLabel("是否忽略库存:")
        ignore_label.setFixedWidth(120)
        ignore_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        ignore_layout.addWidget(ignore_label)
        self.ignore_stock_combo = QComboBox(self)
        self.ignore_stock_combo.addItems(["否", "是"])
        self.ignore_stock_combo.setCurrentIndex(0)
        self.ignore_stock_combo.setFixedWidth(70)
        ignore_layout.addWidget(self.ignore_stock_combo)
        ignore_layout.addStretch()
        layout.addLayout(ignore_layout)
        
        # 上传平衡表总表选项
        upload_label = QLabel("是否上传已有平衡表总表:")
        upload_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(upload_label, alignment=Qt.AlignLeft)
        
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
        radio_layout.setAlignment(Qt.AlignLeft)
        radio_layout.addWidget(self.upload_yes)
        radio_layout.addWidget(self.upload_no)
        layout.addLayout(radio_layout)
        
        # 文件上传按钮（初始隐藏）
        self.file_button = QPushButton("选择平衡表总表文件", self)
        self.file_button.clicked.connect(self.select_file)
        self.file_button.setVisible(False)
        layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        # 从OSS读取选项
        self.oss_group = QButtonGroup(self)
        self.oss_yes = QRadioButton("是", self)
        self.oss_no = QRadioButton("否", self)
        self.oss_yes.setChecked(True)  # 默认选择"是"
        
        self.oss_label = QLabel("是否读取OSS平衡表总表:", self)
        self.oss_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.oss_label, alignment=Qt.AlignLeft)
        
        oss_radio_layout = QHBoxLayout()
        oss_radio_layout.setAlignment(Qt.AlignLeft)
        oss_radio_layout.addWidget(self.oss_yes)
        oss_radio_layout.addWidget(self.oss_no)
        layout.addLayout(oss_radio_layout)
        
        # 连接单选按钮信号
        self.upload_yes.toggled.connect(self.toggle_file_button)
        self.upload_no.toggled.connect(self.toggle_oss_options)

        # 连接日期下拉框信号（只做日下拉框更新）
        self.year_combo.currentIndexChanged.connect(self.update_day_combo)
        self.month_combo.currentIndexChanged.connect(self.update_day_combo)
        
        # 确认和取消按钮
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignLeft)
        self.confirm_button = QPushButton("确认", self)
        self.confirm_button.clicked.connect(self.on_confirm_clicked)
        self.cancel_button = QPushButton("取消", self)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def update_day_combo(self):
        """根据年/月动态更新日下拉框"""
        year = int(self.year_combo.currentText())
        month = int(self.month_combo.currentText())
        import calendar
        max_day = calendar.monthrange(year, month)[1]
        current_day = self.day_combo.currentText()
        self.day_combo.clear()
        self.day_combo.addItems([f"{d:02d}" for d in range(1, max_day + 1)])
        if current_day and current_day.isdigit() and int(current_day) <= max_day:
            self.day_combo.setCurrentText(current_day)
        else:
            self.day_combo.setCurrentIndex(0)

    def validate_days(self):
        """验证销售运输天数"""
        try:
            # 获取当前选择的年月日
            year = int(self.year_combo.currentText())
            month = int(self.month_combo.currentText())
            day = int(self.day_combo.currentText())
            
            # 获取输入的天数
            days_text = self.days_input.text()
            if not days_text:
                self.days_warn_label.setVisible(False)
                self.confirm_button.setEnabled(True)
                return
                
            days = int(days_text)
            if days <= 0:
                self.days_warn_label.setText("销售运输天数必须大于0")
                self.days_warn_label.setVisible(True)
                self.confirm_button.setEnabled(False)
                return
            
            # 计算当月最后一天
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            
            # 计算运输结束日期
            end_day = day + days - 1
            
            # 如果结束日期超过当月最后一天
            if end_day > last_day:
                max_allowed_days = last_day - day + 1
                self.days_warn_label.setText(f"运输天数过多，从{day}号开始最多可选{max_allowed_days}天")
                self.days_warn_label.setVisible(True)
                self.confirm_button.setEnabled(False)
            else:
                self.days_warn_label.setVisible(False)
                self.confirm_button.setEnabled(True)
                
        except ValueError:
            self.days_warn_label.setText("请输入有效的数字")
            self.days_warn_label.setVisible(True)
            self.confirm_button.setEnabled(False)

    def on_confirm_clicked(self):
        """点击确认时校验日期和天数"""
        year = self.year_combo.currentText()
        month = self.month_combo.currentText()
        day = self.day_combo.currentText()
        days = self.days_input.text()
        
        # 先判断都不为空且为数字
        if not (year and month and day and year.isdigit() and month.isdigit() and day.isdigit()):
            self.date_warn_label.setText("请选择完整的运输日期")
            self.date_warn_label.setVisible(True)
            return
            
        if not days or not days.isdigit():
            self.days_warn_label.setText("请输入有效的销售运输天数")
            self.days_warn_label.setVisible(True)
            return

        if self.min_balance_date:
            year = int(year)
            month = int(month)
            day = int(day)
            import datetime
            try:
                selected_date = datetime.date(year, month, day)
            except Exception:
                self.date_warn_label.setText("请选择有效的运输日期")
                self.date_warn_label.setVisible(True)
                return
            if selected_date < self.min_balance_date:
                self.date_warn_label.setText(f"运输日期需要在 {self.min_balance_date.strftime('%Y-%m-%d')} 之后")
                self.date_warn_label.setVisible(True)
                return
                
        # 再次验证天数（以防万一）
        self.validate_days()
        if self.days_warn_label.isVisible():
            return
            
        # 所有校验通过，关闭弹窗
        self.date_warn_label.setVisible(False)
        self.days_warn_label.setVisible(False)
        self.accept()

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
        year = self.year_combo.currentText()
        month = self.month_combo.currentText()
        day = self.day_combo.currentText()
        start_date = f"{year}-{month}-{day}"
        ignore_stock = self.ignore_stock_combo.currentText()
        # 如果选择上传文件
        if self.upload_yes.isChecked():
            return days_input, self.balance_total, start_date, ignore_stock
        # 如果选择从OSS读取
        if self.upload_no.isChecked() and self.oss_yes.isChecked():
            try:
                parent = self.parent()
                if hasattr(parent, 'total_file'):
                    self.balance_total = oss_get_excel_file(parent.total_file)
                    if self.balance_total is None:
                        QMessageBox.warning(self, "文件不存在", f"未在OSS中找到文件: {parent.total_file}")
            except Exception as e:
                QMessageBox.critical(self, "读取失败", f"从OSS读取总表失败: {str(e)}")
                self.balance_total = None
        return days_input, self.balance_total, start_date, ignore_stock

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
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                font-size: 15px;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ec971f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #f0f0f0;
            }
        """)
        
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
        # 新增下载模板按钮
        self.download_template_button = QPushButton("下载模板数据")
        self.download_template_button.setMinimumWidth(140)
        self.download_template_button.setStyleSheet("""
            QPushButton {
                background-color: #2176ae;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #18507a;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #f0f0f0;
            }
        """)
        self.download_template_button.clicked.connect(self.download_template)
        bottom_layout.addWidget(self.download_template_button)
        # 其余按钮
        self.save_all_button = QPushButton("保存到OSS")
        self.save_all_button.clicked.connect(self.save_all_data)
        self.save_all_button.setMinimumWidth(200)
        self.save_all_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #f0f0f0;
            }
        """)
        bottom_layout.addStretch()  # 添加弹性空间，使按钮靠右
        bottom_layout.addWidget(self.save_all_button)
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
                    # self.restaurant_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.restaurant_file,show_open=False,show_save=False)
                    # self.vehicle_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.vehicle_file,show_open=False,show_save=False)
                    # self.report_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.receive_record_file,show_open=False,show_save=False)
                    # self.balance_view = XlsxViewerWidget(use_oss=True, oss_path=self.balance_record_file,show_open=False,show_save=False)
                    # self.total_view = XlsxViewerWidget(use_oss=True, oss_path=self.total_file,show_open=False,show_save=False)
                    # self.check_view = XlsxViewerWidget(use_oss=True, oss_path=self.check_file,show_open=False,show_save=False)
                    self.restaurant_viewer = XlsxViewerWidget(
                        use_oss=True, 
                        oss_path=self.restaurant_file,
                        show_open=False, 
                        show_save=False, 

                        display_columns=[
                            'rest_chinese_name', 'rest_english_name', 'rest_city',
                            'rest_chinese_address', 'rest_district','rest_street','rest_contact_person',
                            'rest_contact_phone','rest_location','rest_distance','rest_type'
                        ]
                    )
                    self.vehicle_viewer = XlsxViewerWidget(
                        use_oss=True, 
                        oss_path=self.vehicle_file,
                        show_open=False, 
                        show_save=False, 
                        display_columns=[
                            'vehicle_license_plate', 'vehicle_driver_name', 'vehicle_type',
                            'vehicle_rough_weight', 'vehicle_tare_weight','vehicle_status',
                            'vehicle_last_use','vehicle_cooldown_days'
                        ]
                    )
                    self.report_viewer = XlsxViewerWidget(
                        use_oss=True, 
                        oss_path=self.receive_record_file,
                        show_open=False, 
                        show_save=False, 
                        display_columns=[
                            'rr_date', 'rr_restaurant_name', 'rr_restaurant_address','rr_contact_person',
                            'rr_amount','rr_serial_number', 'rr_vehicle_license_plate', 'rr_district','rr_street',
                            'rr_sale_number','rr_amount_of_day','temp_vehicle_index'
                        ]
                    )
                    self.balance_view = XlsxViewerWidget(
                        use_oss=True, 
                        oss_path=self.balance_record_file,
                        show_open=False, 
                        show_save=False, 
                        display_columns=[
                            'balance_date', 'balance_oil_type', 'balance_tranport_type',
                            'balance_serial_number', 'balance_vehicle_license_plate', 'balance_weight_of_order',
                            'balance_order_number', 'balance_district', 'balance_sale_number',
                            'balance_amount_of_day'
                        ]
                    )
                    self.total_view = XlsxViewerWidget(
                        use_oss=True, 
                        oss_path=self.total_file,
                        show_open=False, 
                        show_save=False, 
                        display_columns=[
                            'total_sale_number_detail', 'total_supplied_date','total_delivery_trucks_vehicle_registration_no',
                            'total_volume_per_trucks', 'total_weighbridge_ticket_number', 'total_collection_city',
                            'total_iol_mt', 'total_processing_quantity', 'total_output_quantity',
                            'total_conversion_coefficient', 'total_customer', 'total_sale_number',
                            'total_quantities_sold','total_ending_inventory','total_delivery_time','total_delivery_address','total_supplied_weight_of_order'
                        ]
                    )
                    self.check_view = XlsxViewerWidget(
                        use_oss=True, 
                        oss_path=self.check_file,
                        show_open=False, 
                        show_save=False, 
                        display_columns=[
                            'check_date', 'check_name', 'check_description_of_material', 'check_truck_plate_no',
                            'check_weight', 'check_quantity', 'check_weighbridge_ticket_number',
                            'check_gross_weight', 'check_tare_weight', 'check_net_weight',
                            'check_unload_weight','check_difference'
                        ]
                    )
                    
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
        if self.step_status_dict[2] == 'finish':
            for step in [3, 4]:
                self.step_status_dict[step] = 'unfinish'
            for viewer in [self.report_viewer, self.balance_view, self.total_view, self.check_view]:
                if viewer:
                    try:
                        viewer.clear_data()
                    except AttributeError:
                        import pandas as pd
                        viewer.load_data(data=pd.DataFrame())
            # 重置后续按钮状态和颜色
            for btn in [self.generate_report_button, self.generate_total_button]:
                btn.setEnabled(False)
                btn.setStyleSheet(self.button_style_tpl.format(bg='#BDBDBD', border_color='#E0E0E0'))
            self.update_step_status(2, 'unfinish')
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
            
            # 获取列名映射关系
            reverse_mapping = {v: k for k, v in self.vehicle_viewer.column_mapping.items() if k.startswith('vehicle_')}
            
            # 检查并转换中文列名到英文字段名
            columns_to_rename = {}
            for col in vehicle_data.columns:
                if col in reverse_mapping:
                    columns_to_rename[col] = reverse_mapping[col]
            
            # 如果有需要重命名的列，进行重命名
            if columns_to_rename:
                vehicle_data = vehicle_data.rename(columns=columns_to_rename)
            
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
        if self.step_status_dict[3] == 'finish':
            QMessageBox.warning(self, "操作错误", "您需要重新载入车辆信息")
            return
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
            days_input, month_year, bucket_ratio, weight, sort_by_letter, custom_order = dialog.get_input_data()
            year, month = month_year.split('-')
            CONF.runtime.dates_to_trans = f'{year}-{month}-{days_input}'
            
            # 验证天数输入
            if not days_input.isdigit() or not (1 <= int(days_input) <= 31):
                QMessageBox.warning(self, "输入错误", "运输天数必须为1到31之间的数字。")
                self.update_step_status(3, 'error')
                return
            
            # 处理输入数据
            days_to_trans = int(days_input)
            
            # 获取所有区域并去重
            all_districts = sorted(restaurant_df['rest_district'].unique())
            
            # 如果选择自定义顺序，验证输入的区域是否有效
            if not sort_by_letter and custom_order:
                custom_districts = [d.strip() for d in custom_order.split(',')]
                invalid_districts = [d for d in custom_districts if d not in all_districts]
                if invalid_districts:
                    QMessageBox.warning(self, "输入错误", f"以下区域不存在：{', '.join(invalid_districts)}")
                    self.update_step_status(3, 'error')
                    return
                # 使用自定义顺序
                district_order = custom_districts
            else:
                # 使用字母顺序
                district_order = sorted(all_districts)
            
            # 将区域顺序传递给服务层
            CONF.runtime.district_order = district_order
            CONF.runtime.sort_by_letter = sort_by_letter
            
            try:
                service = GetReceiveRecordService(model=ReceiveRecordModel, conf=CONF)
                # 设置收油重量到runtime配置中
                if not hasattr(CONF, 'runtime'):
                    setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                
                # 根据是否选择部分收油来设置收油重量
                if weight:  # 如果选择了部分收油且有输入重量
                    try:
                        weight_float = float(weight)
                        if weight_float <= 0:
                            QMessageBox.warning(self, "输入错误", "收油重量必须大于0。")
                            self.update_step_status(3, 'error')
                            return
                        CONF.runtime.oil_weight = weight_float
                        self.logger.info(f"运输天数: {days_to_trans}, 选择的年月: {month_year}, 收油重量: {weight_float}吨")
                    except ValueError:
                        QMessageBox.warning(self, "输入错误", "收油重量必须是有效的数字。")
                        self.update_step_status(3, 'error')
                        return
                else:  # 如果选择了全部收油
                    CONF.runtime.oil_weight = None
                    self.logger.info(f"运输天数: {days_to_trans}, 选择的年月: {month_year}, 全部收油")

                oil_records_df, restaurant_balance, cp_restaurants_df, cp_vehicle_df = service.get_restaurant_oil_records(
                    self.restaurants, 
                    self.vehicles, 
                    self.current_cp['cp_id'],
                    days_to_trans, 
                    month_year
                )
                # 更新所有相关页面的数据
                    # 1. 更新收油表
                self.report_viewer.load_data(data=oil_records_df)
                
                # 2. 更新平衡表
                self.balance_view.load_data(data=restaurant_balance)
                
                # 3. 更新餐厅信息
                self.restaurant_viewer.load_data(data=cp_restaurants_df)
                
                # 4. 更新车辆信息
                self.vehicle_viewer.load_data(data=cp_vehicle_df)
                
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
        # 如果已完成且不是unfinish，清空后续步骤状态和数据，并重置按钮状态和颜色
        if self.step_status_dict[1] == 'finish':
            for step in [2, 3, 4]:
                self.step_status_dict[step] = 'unfinish'
            self.vehicles = []
            # 清空后续viewer数据
            for viewer in [self.vehicle_viewer, self.report_viewer, self.balance_view, self.total_view, self.check_view]:
                if viewer:
                    try:
                        viewer.clear_data()
                    except AttributeError:
                        viewer.load_data(data=pd.DataFrame())
            # 重置后续按钮状态和颜色
            for btn in [self.load_vehicles_button, self.generate_report_button, self.generate_total_button]:
                btn.setEnabled(False)
                btn.setStyleSheet(self.button_style_tpl.format(bg='#BDBDBD', border_color='#E0E0E0'))
            self.update_step_status(1, 'unfinish')
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
                
                # 获取列名映射关系
                reverse_mapping = {v: k for k, v in self.restaurant_viewer.column_mapping.items() if k.startswith('rest_')}
                
                # 检查并转换中文列名到英文字段名
                columns_to_rename = {}
                for col in restaurant_data.columns:
                    if col in reverse_mapping:
                        columns_to_rename[col] = reverse_mapping[col]
                
                # 如果有需要重命名的列，进行重命名
                if columns_to_rename:
                    restaurant_data = restaurant_data.rename(columns=columns_to_rename)
                
                restaurant_data['rest_belonged_cp'] = self.current_cp['cp_id']
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
                    if self.total_view.save_file():
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
        if self.step_status_dict[4] == 'finish':
            QMessageBox.warning(self, "操作错误", "您需要重新载入车辆信息")
            return
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

            # 获取min_balance_date
            min_balance_date = pd.to_datetime(balance_df['balance_date']).min().date() + datetime.timedelta(days=1)

            # 弹出销售运输天数输入对话框
            dialog = SalesDaysDialog(self, min_balance_date=min_balance_date)
            if dialog.exec_() == QDialog.Accepted:
                days_input, balance_total, start_date, ignore_stock = dialog.get_input_data()
                # 验证天数输入
                if not days_input.isdigit() or not (1 <= int(days_input)):
                    QMessageBox.warning(self, "输入错误", "销售运输天数必须大于1的数字。")
                    self.update_step_status(4, 'error')
                    return
                # 校验天数与开始日期不超过当月最后一天
                try:
                    start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                    days = int(days_input)
                    # 计算本月最后一天
                    next_month = start_dt.replace(day=28) + datetime.timedelta(days=4)
                    last_day = next_month - datetime.timedelta(days=next_month.day)
                    end_dt = start_dt + datetime.timedelta(days=days-1)
                    if end_dt > last_day:
                        QMessageBox.warning(self, "输入错误", f"开始日期+天数已超过{start_dt.strftime('%Y-%m')}月的最后一天({last_day.strftime('%Y-%m-%d')})，请重新选择。")
                        self.update_step_status(4, 'error')
                        return
                    
                except Exception as e:
                    QMessageBox.warning(self, "输入错误", f"日期校验失败: {e}")
                    self.update_step_status(4, 'error')
                    return
                
                # 调用服务生成总表和收货确认书
                service = GetReceiveRecordService(model=ReceiveRecordModel, conf=CONF)

                # 如果上传了总表数据，先进行验证和转换
                if balance_total is not None:
                    try:
                        # 获取列名映射关系
                        reverse_mapping = {v: k for k, v in self.total_view.column_mapping.items() if k.startswith('total_')}
                        
                        # 检查并转换中文列名到英文字段名
                        columns_to_rename = {}
                        for col in balance_total.columns:
                            if col in reverse_mapping:
                                columns_to_rename[col] = reverse_mapping[col]
                        
                        # 如果有需要重命名的列，进行重命名
                        if columns_to_rename:
                            balance_total = balance_total.rename(columns=columns_to_rename)

                        ## 默认上传的餐厅为所选择的餐厅
                        balance_total['total_cp'] = self.current_cp['cp_id']

                        # 转换为RestaurantTotal对象列表
                        total_records = [BalanceTotal(info) for info in balance_total.to_dict('records')]
                        
                        # 使用RestaurantTotalGroup进行过滤
                        total_group = BalanceTotalGroup(instances=total_records)
                        filtered_total = total_group.filter_by_cp(self.current_cp['cp_id']).to_dataframe()
                        
                        # 更新balance_total为过滤后的数据
                        balance_total = filtered_total
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "missing" in error_msg.lower():
                            # 提取缺失字段信息
                            missing_field = error_msg.split("missing")[-1].strip()
                            QMessageBox.critical(self, "数据验证失败", f"载入的总表缺少必要字段: {missing_field}\n请确认数据完整性。")
                        else:
                            QMessageBox.critical(self, "数据验证失败", f"验证总表数据时出错: {error_msg}")
                        self.update_step_status(4, 'error')
                        return

                # 1. 先生成总表的基础结构
                total_df = service.process_dataframe_with_new_columns(self.current_cp['cp_id'], balance_df, balance_total)

                # 2. 生成收货确认书
                check_df,cp_vehicle_df = service.generate_df_check(self.current_cp['cp_id'],int(days_input), balance_df, vehicle_df,start_date)

                # 3. 更新总表的售出数量
                total_df = service.process_check_to_sum(check_df, total_df)

                # 4. 重新计算期末库存
                # 从balance_df获取月份信息
                current_date = balance_df['balance_date'].min().strftime('%Y-%m')
                year, month = current_date.split('-')
                start_date = pd.to_datetime(f'{year}-{month}-01')
                
                # 获取上个月的期末库存
                previous_month_end = total_df[total_df['total_supplied_date'] < start_date]
                previous_end_stock = 0.0
                if not previous_month_end.empty:
                    previous_end_stock = previous_month_end.iloc[-1]['total_ending_inventory']
                
                # 只计算从指定月份开始的库存
                for index, row in total_df.iterrows():
                    if row['total_supplied_date'] >= start_date:
                        current_output = row['total_output_quantity'] if pd.notna(row['total_output_quantity']) else 0
                        current_sale = row['total_quantities_sold'] if pd.notna(row['total_quantities_sold']) else 0
                        current_inventory = round(current_output + previous_end_stock - current_sale, 2)
                        if ignore_stock == '否' and current_inventory < 0:
                            QMessageBox.critical(self, "库存不足", "当前库存无法满足销售，请确认")
                            self.update_step_status(4, 'error')
                            return
                        total_df.at[index, 'total_ending_inventory'] = current_inventory
                        previous_end_stock = current_inventory

                # 5. 处理合同分配
                coeff_number = CONF.BUSINESS.REST2CP.比率
                
                # 调用合同分配处理函数
                total_df, balance_last_month, balance_current_month = service.process_balance_sum_contract(
                    total_df, check_df, None, balance_df, coeff_number, current_date
                )
                oil_records_df = service.copy_balance_to_oil_dataframes(oil_records_df, balance_current_month)

                # 在展示之前，通过实体类规范数据字段
                try:
                    # 处理总表数据
                    total_records = [BalanceTotal(info, model=RestaurantTotalModel) for info in total_df.to_dict('records')]
                    total_group = BalanceTotalGroup(instances=total_records)
                    total_df = total_group.to_dataframe()

                    # 处理收货确认书数据
                    check_records = [BuyerConfirmation(info, model=BuyerConfirmationModel) for info in check_df.to_dict('records')]
                    check_group = BuyerConfirmationGroup(instances=check_records)
                    check_df = check_group.to_dataframe()
                except Exception as e:
                    QMessageBox.critical(self, "数据验证失败", f"数据验证转换失败: {str(e)}")
                    self.update_step_status(4, 'error')
                    return

                # 更新总表和收货确认书、收油表、平衡表视图
                self.total_view.load_data(data=total_df)
                self.check_view.load_data(data=check_df)
                self.report_viewer.load_data(data=oil_records_df,
                    merge_key='temp_vehicle_index',
                    merge_columns=['rr_date', 'rr_serial_number', 'rr_vehicle_license_plate','rr_amount_of_day'])
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

    def download_template(self):
        from PyQt5.QtWidgets import QDialogButtonBox, QDialog, QVBoxLayout, QLabel, QComboBox, QFileDialog, QMessageBox
        from PyQt5.QtCore import Qt
        # 自定义对话框
        class TemplateDialog(QDialog):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.setWindowTitle("选择模板类型")
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
                layout = QVBoxLayout(self)
                label = QLabel("请选择要下载的模板：")
                layout.addWidget(label)
                self.combo = QComboBox(self)
                self.combo.addItems(["餐厅信息模板", "平衡总表模板"])
                layout.addWidget(self.combo)
                btn_box = QDialogButtonBox(self)
                self.ok_btn = btn_box.addButton("确定", QDialogButtonBox.AcceptRole)
                self.cancel_btn = btn_box.addButton("取消", QDialogButtonBox.RejectRole)
                btn_box.accepted.connect(self.accept)
                btn_box.rejected.connect(self.reject)
                layout.addWidget(btn_box)
            def get_selected(self):
                return self.combo.currentText()
        # 弹出自定义对话框
        dialog = TemplateDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        item = dialog.get_selected()
        # 另存为对话框
        file_dialog = QFileDialog(self)
        file_dialog.setWindowTitle("另存为")
        file_dialog.setNameFilter("Excel Files (*.xlsx)")
        file_dialog.resize(700, 400)
        if file_dialog.exec_() == QFileDialog.Accepted:
            file_path = file_dialog.selectedFiles()[0]
        else:
            return
        if not file_path.endswith('.xlsx'):
            file_path += '.xlsx'
        import os
        if os.path.exists(file_path):
            reply = QMessageBox.question(self, "文件已存在", f"文件 {file_path} 已存在，是否替换？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        if item == "餐厅信息模板":
            self.save_restaurant_template(file_path)
        elif item == "平衡总表模板":
            self.save_total_template(file_path)
        QMessageBox.information(self, "保存成功", f"模板已成功保存到：\n{file_path}")

    def save_restaurant_template(self, file_path):
        fields = list(RestaurantModel.schema()['properties'].keys())
        descs = [RestaurantModel.schema()['properties'][f].get('description', '') for f in fields]
        must_fields = ["rest_belonged_cp", "rest_chinese_name", "rest_city", "rest_chinese_address", "rest_district", "rest_type"]
        merge_tip = "标红字段为必填字段，上传文件时删除第二行和第三行"
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet()
        # 标红必填字段
        for col, field in enumerate(fields):
            if field in must_fields:
                worksheet.write(0, col, field, workbook.add_format({'font_color': 'red', 'bold': True}))
                worksheet.write(1, col, descs[col], workbook.add_format({'font_color': 'red', 'bold': True}))
            else:
                worksheet.write(0, col, field)
                worksheet.write(1, col, descs[col])
        # 合并蓝色提示
        worksheet.merge_range(2, 0, 2, len(fields)-1, merge_tip, workbook.add_format({'align': 'center', 'font_color': 'blue', 'bold': True}))
        workbook.close()

    def save_total_template(self, file_path):
        fields = list(RestaurantTotalModel.schema()['properties'].keys())
        descs = [RestaurantTotalModel.schema()['properties'][f].get('description', '') for f in fields]
        must_fields = ["total_cp", "total_supplied_date", "total_delivery_trucks_vehicle_registration_no", "total_volume_per_trucks", "total_weighbridge_ticket_number", "total_collection_city", "total_ending_inventory", "total_quantities_sold"]
        merge_tip = "标红字段为必填字段，上传文件时删除第二行和第三行"
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet()
        # 标红必填字段
        for col, field in enumerate(fields):
            if field in must_fields:
                worksheet.write(0, col, field, workbook.add_format({'font_color': 'red', 'bold': True}))
                worksheet.write(1, col, descs[col], workbook.add_format({'font_color': 'red', 'bold': True}))
            else:
                worksheet.write(0, col, field)
                worksheet.write(1, col, descs[col])
        # 合并蓝色提示
        worksheet.merge_range(2, 0, 2, len(fields)-1, merge_tip, workbook.add_format({'align': 'center', 'font_color': 'blue', 'bold': True}))
        workbook.close()
