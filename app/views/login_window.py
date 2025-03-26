from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                           QPushButton, QMessageBox, QHBoxLayout, QFrame)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QBrush, QColor
from app.controllers.flow_login import validate_user_info
import os

class LoginWindow(QWidget):
    # 定义登录成功的信号，携带用户信息
    loginSuccessful = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("MoCo 数据助手 - 登录")
        self.setGeometry(0, 0, 1000, 600)
        
        # 设置背景图片
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # 向上三级到 MoCo 目录
        resources_dir = os.path.join(project_root, 'MoCo','app', 'resources', 'icons')
        background_path = os.path.join(resources_dir, 'background.jpg')
        
        # 检查背景图片是否存在并能够正确加载
        background = QPixmap(background_path)
        if background.isNull():
            print(f"Error: Could not load background image from {background_path}")
            # 设置备用背景颜色
            self.setStyleSheet("background-color: #f0f0f0;")
        else:
            palette = self.palette()
            palette.setBrush(QPalette.Window, 
                            QBrush(background.scaled(self.size(), 
                                                   Qt.IgnoreAspectRatio, 
                                                   Qt.SmoothTransformation)))
            self.setPalette(palette)
            self.setAutoFillBackground(True)

        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建登录框容器
        login_frame = QFrame()
        login_frame.setFixedSize(400, 300)  # 设置登录框大小
        login_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(45, 45, 45, 0.8);
                border-radius: 10px;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: none;
                border-radius: 5px;
                background-color: white;
            }
            QPushButton#loginButton {
                background-color: #e77c8e;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                min-width: 200px;
            }
            QPushButton#loginButton:hover {
                background-color: #d66c7e;
            }
        """)
        
        # 登录框布局
        login_layout = QVBoxLayout(login_frame)
        login_layout.setSpacing(20)
        login_layout.setContentsMargins(40, 40, 40, 40)
        
        # 用户名输入
        username_label = QLabel("用户名")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        
        # 密码输入
        password_label = QLabel("密码")
        password_container = QWidget()
        password_layout = QHBoxLayout(password_container)
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.setSpacing(0)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        
        # 眼睛图标按钮
        self.eye_button = QPushButton()
        self.eye_button.setFixedSize(30, 30)
        self.eye_button.setStyleSheet("""
            QPushButton {
                border: none;
                margin: 0;
                padding: 0;
                background: transparent;
            }
        """)
        
        # 获取正确的资源文件路径 (app/resource/icons)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # 向上三级到 MoCo 目录
        resources_dir = os.path.join(project_root, 'MoCo','app', 'resources', 'icons')
        
        eye_closed_path = os.path.join(resources_dir, 'eye-closed.png') 
        eye_open_path = os.path.join(resources_dir, 'eye-open.png')
        
        self.eye_closed_icon = QIcon(QPixmap(eye_closed_path))
        self.eye_open_icon = QIcon(QPixmap(eye_open_path))
        self.eye_button.setIcon(self.eye_closed_icon)
        
        password_layout.addWidget(self.password_input)
        password_layout.addWidget(self.eye_button)
        
        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.setObjectName("loginButton")
        
        # 添加所有组件到登录框布局
        login_layout.addWidget(username_label)
        login_layout.addWidget(self.username_input)
        login_layout.addWidget(password_label)
        login_layout.addWidget(password_container)
        login_layout.addStretch(1)
        login_layout.addWidget(self.login_button, alignment=Qt.AlignCenter)
        
        # 将登录框添加到主布局并居中
        main_layout.addStretch(1)
        main_layout.addWidget(login_frame, alignment=Qt.AlignCenter)
        main_layout.addStretch(1)
        
        self.setLayout(main_layout)
        
        # 连接信号
        self.eye_button.clicked.connect(self.toggle_password_visibility)
        self.login_button.clicked.connect(self.attempt_login)
        self.is_password_visible = False

    def resizeEvent(self, event):
        """窗口大小改变时重新设置背景图片"""
        super().resizeEvent(event)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))  # 向上三级到 MoCo 目录
        resources_dir = os.path.join(project_root, 'MoCo','app', 'resources', 'icons')
        background_path = os.path.join(resources_dir, 'background.jpg')
        background = QPixmap(background_path)
        if not background.isNull():
            palette = self.palette()
            palette.setBrush(QPalette.Window, 
                            QBrush(background.scaled(self.size(), 
                                                   Qt.IgnoreAspectRatio, 
                                                   Qt.SmoothTransformation)))
            self.setPalette(palette)

    def toggle_password_visibility(self):
        """切换密码显示/隐藏状态"""
        self.is_password_visible = not self.is_password_visible
        if self.is_password_visible:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.eye_button.setIcon(self.eye_closed_icon)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.eye_button.setIcon(self.eye_open_icon)

    def attempt_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "输入错误", "用户名和密码不能为空")
            return
        
        try:
            # 使用控制器验证用户身份
            is_valid, user_role = validate_user_info(username, password)
            
            if is_valid:
                # 登录成功，发送信号
                self.loginSuccessful.emit({
                    "username": username,
                    "role": user_role,
                    # 可以添加其他需要的用户信息
                })
                self.close()
            else:
                # 登录失败
                QMessageBox.warning(self, "登录失败", "用户名或密码错误")
                
        except Exception as e:
            QMessageBox.critical(self, "连接错误", f"无法连接到服务器: {str(e)}") 