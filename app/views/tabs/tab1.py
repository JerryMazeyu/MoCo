import os
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QMessageBox,
    QProgressBar, QLabel, QFrame,
    QSizePolicy, QDialog, QLineEdit
)
from components.xlsxviewer import XlsxViewer
from app.controllers import flow1_load_df, flow1_generate_candidate_street, flow1_generate_restaurant_type
from app.config import get_config
from app.utils import rp, setup_logger
from components.singleton import global_context

class Tab1(QWidget):
    def __init__(self, parent=None):
        super(Tab1, self).__init__(parent)
        self.conf = get_config()
        try:
            self.last_dir = self.conf.OTHER.tab1.last_dir
        except:
            self.last_dir = rp("")
        self.logger = setup_logger("moco.log")
        self.msg = "请导入餐厅数据"
        
        # 创建主布局
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)  # 设置主布局的边距

        # 创建顶部布局，用于进度条和标签
        self.top_layout = QHBoxLayout()
        # self.progress_bar = QProgressBar()
        self.progress_label = QLabel(self.msg)
        # self.progress_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.top_layout.addWidget(self.progress_label)
        # self.top_layout.addWidget(self.progress_bar)
        
        # 创建左侧按钮布局
        self.left_layout = QVBoxLayout()
        self.left_layout.setSpacing(10)

        self.import_button = QPushButton("导入餐厅数据")
        self.extract_street_button = QPushButton("获取街道信息")
        self.extract_restaurant_type_button = QPushButton("获取餐厅类型")
        # self.edit_button = QPushButton("配置信息")
        # self.next_button = QPushButton("下一步")

        # 强制按钮不要垂直拉伸
        for btn in (self.import_button, self.extract_street_button, self.extract_restaurant_type_button):
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setFixedWidth(120)
        
        # 设置按钮固定宽度
        button_width = 120
        self.import_button.setFixedWidth(button_width)
        self.extract_street_button.setFixedWidth(button_width)
        self.extract_restaurant_type_button.setFixedWidth(button_width)
        # self.edit_button.setFixedWidth(button_width)
        # self.next_button.setFixedWidth(button_width)
        
        self.left_layout.addWidget(self.import_button)
        self.left_layout.addWidget(self.extract_street_button)
        self.left_layout.addWidget(self.extract_restaurant_type_button)
        # self.left_layout.addWidget(self.edit_button)
        # self.left_layout.addWidget(self.next_button)

        self.left_layout.addStretch(1)  # 在底部添加弹性空间
        
        # 创建右侧布局，初始显示占位符
        self.right_layout = QVBoxLayout()
        # 占位符组件，用于表格显示之前的占位
        self.table_placeholder = QFrame()
        self.table_placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.table_placeholder.setFrameShape(QFrame.Box)  # 设置边框样式为矩形
        self.table_placeholder.setStyleSheet("""
            background-color: #f0f0f0;  /* 灰色背景 */
            border: 0px solid #d3d3d3;  /* 浅灰色边框 */
        """)
        self.right_layout.addWidget(self.table_placeholder)

        # 初始化 XlsxViewer
        self.xlsx_viewer = XlsxViewer()
        self.xlsx_viewer.setVisible(False)  # 初始隐藏
        
        # 添加顶部布局、分割线和主水平布局到主布局
        self.main_h_layout = QHBoxLayout()
        self.main_h_layout.addLayout(self.left_layout, 1)
        self.main_h_layout.addLayout(self.right_layout, 4)
        
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)  # 设置为水平线
        divider.setStyleSheet("background-color: #e0e0e0; height:0.5px")  # 可选：设置线的颜色

        # 添加至主布局
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addSpacing(5)
        self.main_layout.addWidget(divider)
        self.main_layout.addSpacing(5)
        self.main_layout.addLayout(self.main_h_layout)
        
        # 设置主布局
        self.setLayout(self.main_layout)

        # ========== 按钮信号绑定 ==========
        self.import_button.clicked.connect(self.load_data)
        self.extract_street_button.clicked.connect(self.extract_street)
        self.extract_restaurant_type_button.clicked.connect(self.extract_restaurant_type)

    def update_message(self, message: str):
        self.msg = message
        self.progress_label.setText(self.msg)

    def load_data(self):
        """弹出文件选择框并加载 Excel 数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 Excel 文件",
            self.last_dir,
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if file_path:
            # 更新 last_dir 并保存到配置
            self.logger.info(f"数据路径为：{file_path}")
            self.update_message(f"加载数据路径为：{file_path}")
            
            self.last_dir = os.path.dirname(file_path)
            self.save_last_directory(self.last_dir)
            try:
                df, restaurants = flow1_load_df(file_path)
                self.xlsx_viewer.load_data(df)
                global_context.data["restaurants"] = restaurants

                # 将 XlsxViewer 添加到右侧布局
                self.right_layout.removeWidget(self.table_placeholder)
                self.right_layout.addWidget(self.xlsx_viewer)
                self.xlsx_viewer.get_file_path(file_path)
                self.xlsx_viewer.setVisible(True)
                self.xlsx_viewer.show()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"加载 Excel 文件时出错：\n{str(e)}")
                return
    
    def extract_street(self):
        """提取街道信息"""
        try:
            self.update_message("正在提取街道信息...")
            df_with_street, restaurants_with_street = flow1_generate_candidate_street(self.xlsx_viewer.file_path)
            global_context.data["restaurants"] = restaurants_with_street
            self.xlsx_viewer.refresh_data(df=df_with_street)
            self.update_message("街道信息提取成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"提取街道信息时出错：\n{str(e)}")
            return
    
    def extract_restaurant_type(self):
        """提取餐厅类型"""
        try:
            self.update_message("正在提取餐厅类型...")
            df_with_type, restaurant_with_rest_type = flow1_generate_restaurant_type(self.xlsx_viewer.file_path)
            global_context.data["restaurants"] = restaurant_with_rest_type
            self.xlsx_viewer.refresh_data(df=df_with_type)
            self.update_message("餐厅类型提取成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"提取餐厅类型时出错：\n{str(e)}")
            return
    
    def save_last_directory(self, path):
        """保存 last_dir 到配置文件"""
        self.conf.OTHER.Tab1.last_dir = path
        self.conf.save()


        
