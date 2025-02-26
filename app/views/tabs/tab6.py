from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QLineEdit, QGroupBox, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
import pandas as pd
from datetime import datetime
import os
from app.controllers.flow6 import flow6_deal_relation_data

class Tab6(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.restaurant_df = None
        self.total_df = None
        self.vehicle_df = None
        self.last_month_balance = None
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
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
        
        # 参数设置区域
        param_group = QGroupBox("参数设置")
        param_layout = QVBoxLayout()
        
        # 操作天数输入
        days_layout = QHBoxLayout()
        days_label = QLabel("操作天数:")
        self.days_entry = QLineEdit()
        days_layout.addWidget(days_label)
        days_layout.addWidget(self.days_entry)
        
        # 转换系数输入
        coeff_layout = QHBoxLayout()
        coeff_label = QLabel("转换系数:")
        self.coeff_entry = QLineEdit()
        coeff_layout.addWidget(coeff_label)
        coeff_layout.addWidget(self.coeff_entry)
        
        # 当前日期输入
        date_layout = QHBoxLayout()
        date_label = QLabel("当前日期:")
        self.date_entry = QLineEdit()
        self.date_entry.setText(datetime.now().strftime('%Y-%m-%d'))
        date_layout.addWidget(date_label)
        date_layout.addWidget(self.date_entry)
        
        # 添加参数输入到参数布局
        param_layout.addLayout(days_layout)
        param_layout.addLayout(coeff_layout)
        param_layout.addLayout(date_layout)
        param_group.setLayout(param_layout)
        
        # 生成按钮
        self.generate_btn = QPushButton("生成对应表")
        self.generate_btn.clicked.connect(self.generate_tables)
        
        # 添加所有组件到主布局
        layout.addWidget(import_group)
        layout.addWidget(param_group)
        layout.addWidget(self.generate_btn)
        layout.addStretch()
        
        self.setLayout(layout)

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

    def generate_tables(self):
        # 验证所有必要的数据是否已导入
        if any(df is None for df in [self.restaurant_df, self.total_df, self.vehicle_df, self.last_month_balance]):
            QMessageBox.critical(self, "错误", "请确保所有Excel文件都已导入")
            return

        try:
            days = int(self.days_entry.text())
            coeff_number = float(self.coeff_entry.text())
            current_date = self.date_entry.text()

            # 调用控制器函数处理数据
            result = flow6_deal_relation_data(
                self.restaurant_df,
                self.total_df,
                self.vehicle_df,
                self.last_month_balance,
                days,
                coeff_number,
                current_date
            )

            # 创建输出目录
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 保存所有生成的表格
            for name, df in result.items():
                output_path = os.path.join(output_dir, f"{name}_{current_date}.xlsx")
                df.to_excel(output_path, index=False)

            QMessageBox.information(self, "成功", f"所有表格已生成并保存到 {output_dir} 目录")

        except ValueError as e:
            QMessageBox.critical(self, "错误", "请确保输入的参数格式正确")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"生成表格时发生错误: {str(e)}")
