from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QGroupBox, QFileDialog, QMessageBox,
                            QTableWidget, QTableWidgetItem, QStackedWidget, QFrame,
                            QGridLayout, QScrollArea, QTabWidget, QHeaderView)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon
import pandas as pd
from datetime import datetime
import os
from app.controllers.flow6 import Flow6Controller
from app.config.logging_config import LogConfig
logger = LogConfig.setup_logger('tab6')

class StepIndicator(QFrame):
    def __init__(self, steps, parent=None):
        super().__init__(parent)
        self.steps = steps
        self.current_step = 0
        self.completed_steps = set()
        self.error_steps = set()
        
        layout = QHBoxLayout()
        self.step_labels = []
        self.step_icons = []
        
        # 图标路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))  # 向上三级到 MoCo 目录
        resources_dir = os.path.join(project_root, 'MoCo','app', 'resources', 'icons')
        self.icons = {
            'finish': os.path.join(resources_dir, 'finish.png'),
            'dealing': os.path.join(resources_dir, 'dealing.png'),
            'unfinish': os.path.join(resources_dir, 'unfinish.png'),
            'error': os.path.join(resources_dir, 'error.png')
        }
        
        for i, step in enumerate(steps):
            step_frame = QFrame()
            step_layout = QVBoxLayout()
            
            # 图标标签
            icon_label = QLabel()
            icon_label.setFixedSize(24, 24)
            icon_pixmap = QPixmap(self.icons['unfinish'])
            icon_label.setPixmap(icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio))
            
            # 步骤文本标签
            text_label = QLabel(f"Step {i+1}: {step}")
            text_label.setStyleSheet("color: gray; padding: 5px;")
            
            step_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
            step_layout.addWidget(text_label, alignment=Qt.AlignCenter)
            step_frame.setLayout(step_layout)
            
            if i > 0:
                separator = QLabel("→")
                layout.addWidget(separator)
            
            layout.addWidget(step_frame)
            self.step_labels.append(text_label)
            self.step_icons.append(icon_label)
            
        layout.addStretch()
        self.setLayout(layout)
        
    def update_progress(self, current_step, completed_steps, error_steps=None):
        self.current_step = current_step
        self.completed_steps = completed_steps
        self.error_steps = error_steps or set()
        
        for i, (label, icon) in enumerate(zip(self.step_labels, self.step_icons)):
            if i in self.error_steps:
                icon_file = self.icons['error']
                label.setStyleSheet("color: red; padding: 5px;")
            elif i in completed_steps:
                icon_file = self.icons['finish']
                label.setStyleSheet("color: green; padding: 5px;")
            elif i == current_step:
                icon_file = self.icons['dealing']
                label.setStyleSheet("color: black; padding: 5px;")
            else:
                icon_file = self.icons['unfinish']
                label.setStyleSheet("color: gray; opacity: 0.5; padding: 5px;")
            
            icon.setPixmap(QPixmap(icon_file).scaled(24, 24, Qt.KeepAspectRatio))

class StepPage(QWidget):
    def __init__(self, step_number, step_name, parent=None):
        super().__init__(parent)
        self.step_number = step_number
        self.step_name = step_name
        
        main_layout = QVBoxLayout()
        
        # 参数设置区域（顶部）
        self.param_group = QGroupBox("参数设置")
        self.param_layout = QHBoxLayout()  # 改为水平布局
        self.param_layout.setSpacing(10)   # 设置组件间距
        self.param_group.setLayout(self.param_layout)
        main_layout.addWidget(self.param_group)
        
        # 结果显示区域（中间，可滚动）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        
        self.result_table = QTableWidget()
        self.result_table.setVisible(False)
        scroll_layout.addWidget(self.result_table)
        scroll_layout.addStretch()
        
        scroll_content.setLayout(scroll_layout)
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        
        # 底部按钮区域
        bottom_layout = QHBoxLayout()
        self.execute_btn = self.create_standard_button("执行")
        self.show_result_btn = self.create_standard_button("显示结果")
        self.export_btn = self.create_standard_button("导出Excel")
        self.prev_btn = self.create_standard_button("上一步")
        self.next_btn = self.create_standard_button("下一步")
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.execute_btn)
        bottom_layout.addWidget(self.show_result_btn)
        bottom_layout.addWidget(self.export_btn)
        bottom_layout.addWidget(self.prev_btn)
        bottom_layout.addWidget(self.next_btn)
        bottom_layout.addStretch()
        
        main_layout.addLayout(bottom_layout)
        self.setLayout(main_layout)
        
        # 初始状态设置
        self.show_result_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.prev_btn.setEnabled(False)  # 初始状态下禁用，在update_ui_state中根据步骤更新
        
        # 添加执行状态标志
        self.is_executed = False
        
        # 记录当前参数布局的位置
        self.current_row = 0
        self.current_col = 0
        self.max_cols = 3  # 每行最多放置的组件数

    def create_standard_button(self, text, is_file_button=False):
        """创建标准大小的按钮"""
        btn = QPushButton(text)
        if is_file_button:
            btn.setFixedSize(300, 30)  # Excel导入按钮尺寸
        else:
            btn.setFixedSize(120, 30)  # 普通按钮尺寸
        return btn

    def add_param_input(self, label_text, placeholder_text="", tooltip_text=""):
        # 创建容器
        container = QWidget()
        container_layout = QHBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        if tooltip_text:
            help_label = QLabel("?")
            help_label.setToolTip(tooltip_text)
            help_label.setStyleSheet("""
                QLabel {
                    color: #666666;
                    background: #eeeeee;
                    border-radius: 8px;
                    padding: 2px 6px;
                    font-size: 10px;
                }
                QLabel:hover {
                    background: #dddddd;
                }
            """)
            container_layout.addWidget(help_label)
        
        label = QLabel(label_text)
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder_text)
        input_field.setFixedSize(200, 30)  # 设置输入框大小
        
        container_layout.addWidget(label)
        container_layout.addWidget(input_field)
        container_layout.addStretch()
        
        container.setLayout(container_layout)
        
        # 添加到水平布局
        self.param_layout.addWidget(container)
        
        return input_field

    def add_file_button(self, button_text):
        button = self.create_standard_button(button_text, is_file_button=True)
        self.param_layout.addWidget(button)
        return button

class Tab6(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.flow6_controller = Flow6Controller()
        self.current_step = 0
        self.completed_steps = set()
        
        self.steps = [
            "生成收油表",
            "生成平衡表",
            "生成总表",
            "生成收货确认书",
            "处理确认数据",
            "复制平衡表数据",
            "处理合同编号",
            "最终数据复制"
        ]
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # 步骤指示器
        self.step_indicator = StepIndicator(self.steps)
        layout.addWidget(self.step_indicator)
        
        # 步骤页面堆栈
        self.stacked_widget = QStackedWidget()
        self.create_step_pages()
        layout.addWidget(self.stacked_widget)
        
        self.setLayout(layout)
        self.update_ui_state()

    def create_step_pages(self):
        self.step_pages = []
        for i, step_name in enumerate(self.steps):
            page = StepPage(i + 1, step_name)
            self.setup_step_page(page, i)
            self.step_pages.append(page)
            self.stacked_widget.addWidget(page)
            
    def setup_step_page(self, page: StepPage, step_number: int):
        if step_number == 0:  # 第一步：生成收油表
            page.add_file_input = page.add_file_button("导入餐厅信息Excel")
            page.add_file_input.clicked.connect(lambda: self.import_excel("餐厅信息", page))
            
            page.vehicle_input = page.add_file_button("导入收油表车辆信息Excel")
            page.vehicle_input.clicked.connect(lambda: self.import_excel("车辆信息", page))
            
            page.barrels_input = page.add_param_input("收油总桶数:", "请输入数字")
            
            # 添加弹性空间
            page.param_layout.addStretch()
            
        elif step_number == 1:  # 第二步：生成平衡表
            page.days_input = page.add_param_input("收油天数:", "请输入天数")
            page.date_input = page.add_param_input("本月日期:", "YYYY-MM-DD")
            page.date_input.setText(datetime.now().strftime('%Y-%m-%d'))
            
        elif step_number == 2:  # 第三步：生成总表
            page.total_input = page.add_file_button("导入收油总表Excel")
            page.total_input.clicked.connect(lambda: self.import_excel("收油总表", page))
            
        elif step_number == 3:  # 第四步：生成收货确认书
            page.weight_input = page.add_param_input("收油重量:", "请输入数字(吨)")
            page.check_days_input = page.add_param_input("确认表运输天数:", "请输入天数")
            page.sales_vehicle_input = page.add_file_button("导入销售车牌Excel")
            page.sales_vehicle_input.clicked.connect(lambda: self.import_excel("销售车牌", page))
            
        elif step_number == 6:  # 第七步：处理合同编号
            page.coeff_input = page.add_param_input("生产转化系数:", "请输入系数(0-1)")
        
        # 步骤 4、5、7 没有参数输入
        
        # 连接按钮信号
        page.execute_btn.clicked.connect(lambda: self.execute_step(step_number))
        page.show_result_btn.clicked.connect(lambda: self.show_step_result(step_number))
        page.export_btn.clicked.connect(lambda: self.export_step_result(step_number))
        page.prev_btn.clicked.connect(self.go_to_previous_step)
        page.next_btn.clicked.connect(self.go_to_next_step)

    def execute_step(self, step_number):
        try:
            # 根据步骤号执行相应的控制器方法
            if step_number == 0:  # 第一步：生成收油表
                params = self.get_step_params(0)
                result = self.flow6_controller.step1_generate_oil_collection(
                    restaurant_df=params['restaurant_df'],
                    vehicle_df=params['vehicle_df'],
                    total_barrels=params['total_barrels']
                )
                self.step_pages[0].result = result
                self.step_pages[0].is_executed = True

            elif step_number == 1:  # 第二步：生成平衡表
                params = self.get_step_params(1)
                result = self.flow6_controller.step2_generate_balance(
                    assigned_vehicles=self.flow6_controller.results['assigned_vehicles'],
                    collect_days=params['collect_days'],
                    current_date=params['current_date']
                )
                self.step_pages[1].result = result
                self.step_pages[1].is_executed = True

            elif step_number == 2:  # 第三步：生成总表
                params = self.get_step_params(2)
                result = self.flow6_controller.step3_generate_total_sheet(
                    total_df=params['total_df'],
                    balance_df=self.flow6_controller.results['balance_df']
                )
                self.step_pages[2].result = result
                self.step_pages[2].is_executed = True

            elif step_number == 3:  # 第四步：生成收货确认书
                params = self.get_step_params(3)
                result = self.flow6_controller.step4_generate_receipt_confirmation(
                    oil_weight=params['oil_weight'],
                    check_days=params['check_days'],
                    df_oil=self.flow6_controller.results['assigned_vehicles'],
                    check_vehicle_df=params['check_vehicle_df'],
                    current_date=self.step_pages[1].date_input.text()  # 使用第二步的日期
                )
                self.step_pages[3].result = result
                self.step_pages[3].is_executed = True

            elif step_number == 4:  # 第五步：处理确认数据到汇总表
                result = self.flow6_controller.step5_process_check_to_sum(
                    receipt_confirmation=self.flow6_controller.results['receipt_confirmation'],
                    total_sheet=self.flow6_controller.results['total_sheet']
                )
                self.step_pages[4].result = result
                self.step_pages[4].is_executed = True

            elif step_number == 5:  # 第六步：将平衡表数据复制到收油表
                result = self.flow6_controller.step6_copy_balance_to_oil(
                    balance_df=self.flow6_controller.results['balance_df'],
                    assigned_vehicles=self.flow6_controller.results['assigned_vehicles']
                )
                self.step_pages[5].result = result
                self.step_pages[5].is_executed = True

            elif step_number == 6:  # 第七步：处理平衡表合同编号
                params = self.get_step_params(6)
                result = self.flow6_controller.step7_process_balance_sum_contract(
                    updated_total_sheet=self.flow6_controller.results['updated_total_sheet'],
                    receipt_confirmation=self.flow6_controller.results['receipt_confirmation'],
                    last_month_balance=pd.DataFrame(),  # 这里需要添加上月平衡表的获取方式
                    balance_df=self.flow6_controller.results['balance_df'],
                    coeff_number=params['coeff_number'],
                    current_date=self.step_pages[1].date_input.text()  # 使用第二步的日期
                )
                self.step_pages[6].result = result
                self.step_pages[6].is_executed = True

            elif step_number == 7:  # 第八步：最终将平衡表数据复制到收油表
                result = self.flow6_controller.step8_copy_balance_to_oil_dataframes(
                    updated_oil_collection=self.flow6_controller.results['updated_oil_collection'],
                    balance_df=self.flow6_controller.results['final_current_month']
                )
                self.step_pages[7].result = result
                self.step_pages[7].is_executed = True

            # 更新UI状态
            self.completed_steps.add(step_number)
            self.update_ui_state()
            
            # 启用相关按钮
            page = self.step_pages[step_number]
            page.show_result_btn.setEnabled(True)
            page.export_btn.setEnabled(True)
            page.next_btn.setEnabled(True)
            
            QMessageBox.information(self, "成功", f"步骤 {step_number + 1} 执行完成")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行步骤 {step_number + 1} 时出错: {str(e)}")

    def show_step_result(self, step_number):
        page = self.step_pages[step_number]
        if hasattr(page, 'result'):
            if step_number == 0:  # 第一步有两个DataFrame需要显示
                # 清除现有的表格
                page.result_table.clear()
                
                # 创建标签页来显示多个DataFrame
                tab_widget = QTabWidget()
                
                # 创建并添加第一个表格（排序后的餐厅信息）
                restaurants_table = QTableWidget()
                self.display_dataframe(restaurants_table, page.result['sorted_restaurants'])
                tab_widget.addTab(restaurants_table, "餐厅排序结果")
                
                # 创建并添加第二个表格（分配车辆后的结果）
                vehicles_table = QTableWidget()
                self.display_dataframe(vehicles_table, page.result['assigned_vehicles'])
                tab_widget.addTab(vehicles_table, "车辆分配结果")
                
                # 将原来的result_table替换为tab_widget
                layout = page.findChild(QScrollArea).widget().layout()
                layout.replaceWidget(page.result_table, tab_widget)
                page.result_table.setVisible(False)
                tab_widget.setVisible(True)
                
            else:  # 其他步骤只有一个DataFrame
                self.display_dataframe(page.result_table, page.result)
                page.result_table.setVisible(True)

    def display_dataframe(self, table: QTableWidget, df: pd.DataFrame):
        """显示DataFrame到表格中"""
        if df is None or df.empty:
            return
        
        table.clear()
        table.setRowCount(df.shape[0])
        table.setColumnCount(df.shape[1])
        table.setHorizontalHeaderLabels(df.columns)
        
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iloc[i, j]))
                table.setItem(i, j, item)
        
        table.resizeColumnsToContents()

    def export_step_result(self, step_number):
        page = self.step_pages[step_number]
        if hasattr(page, 'result'):
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存Excel文件", "", "Excel Files (*.xlsx)"
            )
            if file_path:
                try:
                    page.result.to_excel(file_path, index=False)
                    QMessageBox.information(self, "成功", "文件已保存")
                except Exception as e:
                    QMessageBox.critical(self, "错误", f"保存文件时出错: {str(e)}")

    def go_to_previous_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stacked_widget.setCurrentIndex(self.current_step)
            self.update_ui_state()

    def go_to_next_step(self):
        if self.current_step < len(self.steps) - 1 and self.step_pages[self.current_step].is_executed:
            self.current_step += 1
            self.stacked_widget.setCurrentIndex(self.current_step)
            self.update_ui_state()

    def update_ui_state(self):
        self.step_indicator.update_progress(self.current_step, self.completed_steps)
        
        # 更新所有页面的按钮状态
        for i, page in enumerate(self.step_pages):
            # 执行按钮只在当前步骤启用
            page.execute_btn.setEnabled(i == self.current_step)
            
            # 显示结果和导出按钮只在已执行的步骤启用
            page.show_result_btn.setEnabled(page.is_executed)
            page.export_btn.setEnabled(page.is_executed)
            
            # 上一步按钮：除了第一步外都可以点击
            page.prev_btn.setEnabled(i > 0)
            
            # 下一步按钮：只有当前步骤执行完成后才能点击，且不能是最后一步
            page.next_btn.setEnabled(page.is_executed and i < len(self.steps) - 1)
            
            # 如果不是当前页面，禁用所有按钮
            if i != self.current_step:
                page.execute_btn.setEnabled(False)
                page.show_result_btn.setEnabled(False)
                page.export_btn.setEnabled(False)
                page.next_btn.setEnabled(False)
                page.prev_btn.setEnabled(False)

    def import_excel(self, file_type: str, page: StepPage):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择{file_type}文件",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            try:
                df = pd.read_excel(file_path)
                # 保存导入的数据到页面实例
                setattr(page, f"{file_type.lower()}_data", df)
                QMessageBox.information(self, "成功", f"{file_type}导入成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入{file_type}失败: {str(e)}")

    def get_step_params(self, step_number: int) -> dict:
        """获取每个步骤的参数"""
        page = self.step_pages[step_number]
        params = {}
        
        if step_number == 0:
            params = {
                'restaurant_df': getattr(page, '餐厅信息_data', None),
                'vehicle_df': getattr(page, '车辆信息_data', None),
                'total_barrels': int(page.barrels_input.text()) if page.barrels_input.text() else None
            }
        elif step_number == 1:
            params = {
                'collect_days': int(page.days_input.text()) if page.days_input.text() else None,
                'current_date': page.date_input.text()
            }
        elif step_number == 2:
            params = {
                'total_df': getattr(page, '收油总表_data', None)
            }
        elif step_number == 3:
            params = {
                'oil_weight': float(page.weight_input.text()) if page.weight_input.text() else None,
                'check_days': int(page.check_days_input.text()) if page.check_days_input.text() else None,
                'check_vehicle_df': getattr(page, '销售车牌_data', None)
            }
        elif step_number == 6:
            params = {
                'coeff_number': float(page.coeff_input.text()) if page.coeff_input.text() else None
            }
        
        return params
