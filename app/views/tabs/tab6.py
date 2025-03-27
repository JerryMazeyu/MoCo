from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QGroupBox, QFileDialog, QMessageBox,
                            QTableWidget, QTableWidgetItem, QStackedWidget)
from PyQt5.QtCore import Qt
import pandas as pd
from datetime import datetime
import os
from app.controllers.flow6 import Flow6Controller

class Tab6(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.restaurant_df = None
        self.total_df = None
        self.vehicle_df = None
        self.last_month_balance = None
        self.current_step = 0  # 当前执行步骤
        self.flow6_controller = None  # Flow6Controller实例
        
        self.init_ui()

    def init_ui(self):
        # 主布局
        main_layout = QVBoxLayout()
        
        # 创建堆叠窗口部件用于切换不同步骤的界面
        self.stacked_widget = QStackedWidget()
        
        # 创建第一页（数据导入和参数设置页面）
        first_page = QWidget()
        first_page_layout = QVBoxLayout()
        
        # 添加原有的导入和参数设置组件
        first_page_layout.addWidget(self.create_import_group())
        first_page_layout.addWidget(self.create_param_group())
        
        # 开始执行按钮
        self.start_btn = QPushButton("开始执行")
        self.start_btn.clicked.connect(self.start_execution)
        first_page_layout.addWidget(self.start_btn)
        
        first_page.setLayout(first_page_layout)
        
        # 创建结果展示页面
        self.result_page = QWidget()
        result_layout = QVBoxLayout()
        
        # 结果表格
        self.result_table = QTableWidget()
        result_layout.addWidget(self.result_table)
        
        # 按钮组
        button_layout = QHBoxLayout()
        self.export_btn = QPushButton("导出Excel")
        self.next_btn = QPushButton("下一步")
        self.modify_btn = QPushButton("修改数据")
        
        self.export_btn.clicked.connect(self.export_current_result)
        self.next_btn.clicked.connect(self.execute_next_step)
        self.modify_btn.clicked.connect(self.modify_current_result)
        
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.modify_btn)
        button_layout.addWidget(self.next_btn)
        
        result_layout.addLayout(button_layout)
        self.result_page.setLayout(result_layout)
        
        # 添加页面到堆叠窗口
        self.stacked_widget.addWidget(first_page)
        self.stacked_widget.addWidget(self.result_page)
        
        main_layout.addWidget(self.stacked_widget)
        self.setLayout(main_layout)

    def create_import_group(self):
        # 文件导入区域
        import_group = QGroupBox("数据导入")
        import_layout = QVBoxLayout()
        
        # 导入按钮
        self.restaurant_btn = QPushButton("导入餐厅Excel")
        self.total_btn = QPushButton("导入平衡表总表Excel")
        self.vehicle_btn = QPushButton("导入车辆信息Excel")
        self.last_month_btn = QPushButton("导入上个月平衡表Excel")
        
        # 连接按钮信号
        self.restaurant_btn.clicked.connect(lambda: self.import_excel("餐厅Excel"))
        self.total_btn.clicked.connect(lambda: self.import_excel("平衡表总表Excel"))
        self.vehicle_btn.clicked.connect(lambda: self.import_excel("车辆信息Excel"))
        self.last_month_btn.clicked.connect(lambda: self.import_excel("上个月平衡表Excel"))
        
        # 添加按钮到导入布局
        import_layout.addWidget(self.restaurant_btn)
        import_layout.addWidget(self.total_btn)
        import_layout.addWidget(self.vehicle_btn)
        import_layout.addWidget(self.last_month_btn)
        import_group.setLayout(import_layout)
        
        return import_group

    def create_param_group(self):
        """创建参数设置组"""
        param_group = QGroupBox("参数设置")
        param_layout = QVBoxLayout()
        
        # 操作天数输入
        days_layout = QHBoxLayout()
        days_label = QLabel("操作天数:")
        self.days_entry = QLineEdit()
        self.days_entry.setPlaceholderText("例如：30（表示在30天内完成所有收油任务）")
        days_help = QLabel("?")
        days_help.setToolTip("设置在多少天内完成所有餐厅的收油操作\n"
                            "例如：如果有90个餐厅需要收油，设置30天\n"
                            "系统会将收油任务平均分配在这30天内完成")
        days_layout.addWidget(days_label)
        days_layout.addWidget(self.days_entry)
        days_layout.addWidget(days_help)
        
        # 转换系数输入
        coeff_layout = QHBoxLayout()
        coeff_label = QLabel("转换系数:")
        self.coeff_entry = QLineEdit()
        self.coeff_entry.setPlaceholderText("例如：0.85（用于计算剩余原料量）")
        coeff_help = QLabel("?")
        coeff_help.setToolTip("用于计算剩余原料量的转换系数\n"
                             "计算公式：剩余原料 = (月度数量 - 累计数量) / 转换系数")
        coeff_layout.addWidget(coeff_label)
        coeff_layout.addWidget(self.coeff_entry)
        coeff_layout.addWidget(coeff_help)
        
        # 添加参数输入到参数布局
        param_layout.addLayout(days_layout)
        param_layout.addLayout(coeff_layout)
        
        # 添加当前日期输入
        date_layout = QHBoxLayout()
        date_label = QLabel("当前日期:")
        self.date_entry = QLineEdit()
        self.date_entry.setText(datetime.now().strftime('%Y-%m-%d'))
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_entry)
        param_layout.addLayout(date_layout)
        
        param_group.setLayout(param_layout)
        return param_group

    ## 导入必要的excel文件
    def import_excel(self, button_text):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择{button_text}文件",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            try:
                df = pd.read_excel(file_path)
                if button_text == "餐厅Excel":
                    self.restaurant_df = df
                elif button_text == "平衡表总表Excel":
                    self.total_df = df
                elif button_text == "车辆信息Excel":
                    self.vehicle_df = df
                elif button_text == "上个月平衡表Excel":
                    self.last_month_balance = df
                QMessageBox.information(self, "成功", f"{button_text}导入成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入{button_text}失败: {str(e)}")

    def start_execution(self):
        """开始执行流程"""
        if self.validate_inputs():
            try:
                # 初始化Flow6Controller
                self.flow6_controller = Flow6Controller()
                self.current_step = 0
                # 执行第一步
                self.execute_next_step()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"执行过程出错: {str(e)}")

    def execute_next_step(self):
        """执行下一步"""
        try:
            if self.current_step == 0:
                # 执行步骤1：生成收油表
                result = self.flow6_controller.step1_generate_oil_collection(
                    self.restaurant_df, 
                    self.vehicle_df
                )
                self.show_result(result['assigned_vehicles'], "收油表生成结果")
                
            elif self.current_step == 1:
                # 执行步骤2：生成平衡表
                result = self.flow6_controller.step2_generate_balance(
                    self.flow6_controller.results['assigned_vehicles'],
                    int(self.days_entry.text())
                )
                self.show_result(result, "平衡表生成结果")
                
            # ... 其他步骤 ...
            
            self.current_step += 1
            self.stacked_widget.setCurrentIndex(1)  # 显示结果页面
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行步骤{self.current_step + 1}时出错: {str(e)}")

    def show_result(self, df: pd.DataFrame, title: str):
        """显示结果到表格"""
        self.result_table.clear()
        self.result_table.setRowCount(df.shape[0])
        self.result_table.setColumnCount(df.shape[1])
        self.result_table.setHorizontalHeaderLabels(df.columns)

        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                item = QTableWidgetItem(str(df.iloc[i, j]))
                self.result_table.setItem(i, j, item)

        self.result_table.resizeColumnsToContents()
        QMessageBox.information(self, "完成", f"{title}已生成")

    def export_current_result(self):
        """导出当前结果到Excel"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存Excel文件",
                "",
                "Excel Files (*.xlsx)"
            )
            if file_path:
                # 获取当前表格数据并转换为DataFrame
                rows = self.result_table.rowCount()
                cols = self.result_table.columnCount()
                headers = [self.result_table.horizontalHeaderItem(i).text() for i in range(cols)]
                
                data = []
                for row in range(rows):
                    row_data = []
                    for col in range(cols):
                        item = self.result_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    data.append(row_data)
                
                df = pd.DataFrame(data, columns=headers)
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "成功", "文件已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出文件时出错: {str(e)}")

    def modify_current_result(self):
        """修改当前结果"""
        # 启用表格编辑
        self.result_table.setEditTriggers(QTableWidget.DoubleClicked)
        QMessageBox.information(self, "提示", "双击单元格可以修改数据\n修改完成后点击下一步继续")

    def validate_inputs(self):
        """验证输入数据"""
        if any(df is None for df in [self.restaurant_df, self.total_df, self.vehicle_df, self.last_month_balance]):
            QMessageBox.critical(self, "错误", "请确保所有Excel文件都已导入")
            return False
        
        try:
            days = int(self.days_entry.text())
            if days <= 0:
                QMessageBox.critical(self, "错误", "操作天数必须大于0")
                return False
                
            coeff_number = float(self.coeff_entry.text())
            if coeff_number <= 0 or coeff_number > 1:
                QMessageBox.critical(self, "错误", "转换系数必须在0-1之间")
                return False
                
            datetime.strptime(self.date_entry.text(), '%Y-%m-%d')
            return True
            
        except ValueError as e:
            QMessageBox.critical(self, "错误", f"请确保输入的参数格式正确:\n{str(e)}")
            return False
