import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, 
                           QPushButton, QMessageBox, QHBoxLayout, QFrame, QToolButton)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap, QIcon, QPalette, QBrush, QColor
from app.utils.file_io import rp
# from app.controllers.flow_login import validate_user_info
from PyQt5.QtCore import QSize, Qt
from app.utils.logger import setup_logger
from app.utils.oss import oss_get_json_file
from app.utils.hash import hash_text


class LoginController:
    def __init__(self):
        self.logger = setup_logger()
    
    def validate_user_info(self, username, password):
        """
        验证用户信息
        
        Args:
            username (str): 用户名
            password (str): 用户输入的密码（未哈希）
            
        Returns:
            tuple: (bool, str) - (是否验证成功, 用户类型/角色)
        """
        try:
            # 获取用户信息文件
            user_info = oss_get_json_file('login_info.json')
            if not user_info:
                self.logger.error("无法获取用户信息文件")
                return False, None
            
            # 对输入的密码进行哈希
            hashed_password = hash_text(password)
            
            # 验证用户身份
            for user_key, user_data in user_info.items():
                if user_data["username"] == username and user_data["password"] == hashed_password:
                    self.logger.info(f"用户 {username} 验证成功")
                    return True, user_key
            
            self.logger.info(f"用户 {username} 验证失败")
            return False, None
            
        except Exception as e:
            self.logger.error(f"验证用户信息时发生错误: {e}")
            return False, None

# 提供便捷的函数接口
def validate_user_info(username, password):
    """
    验证用户信息的便捷函数
    
    Args:
        username (str): 用户名
        password (str): 用户输入的密码（未哈希）
        
    Returns:
        tuple: (bool, str) - (是否验证成功, 用户类型/角色)
    """
    controller = LoginController()
    return controller.validate_user_info(username, password) 



class PasswordLineEdit(QLineEdit):
    """自定义密码输入框，集成显示/隐藏密码按钮"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        self.setPlaceholderText("请输入密码")
        self.setMaximumWidth(400)  # 限制最大宽度
        
        # 设置眼睛图标路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        resources_dir = os.path.join(project_root, 'app', 'resources', 'icons')
        
        self.eye_closed_path = os.path.join(resources_dir, 'eye-closed.png') 
        self.eye_open_path = os.path.join(resources_dir, 'eye-open.png')
        
        # 创建显示/隐藏密码按钮
        self.toggle_button = QToolButton(self)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setFixedSize(18, 18) # 调整按钮大小
        self.toggle_button.setStyleSheet("""
            QToolButton {
                border: none;
                background: transparent;
                padding: 0px;
            }
        """)
        
        # 加载图标
        self._load_icons_or_text()
        
        # 连接按钮信号
        self.toggle_button.toggled.connect(self.on_toggled)
        
        # 初始调整按钮位置和内边距
        self.adjust_button_position()
    
    def resizeEvent(self, event):
        """当大小改变时调整按钮位置"""
        super().resizeEvent(event)
        self.adjust_button_position()
    
    def adjust_button_position(self):
        """调整按钮位置，使其在输入框内部右侧"""
        button_size = self.toggle_button.size()
        frame_width = self.style().pixelMetric(self.style().PM_DefaultFrameWidth)
        content_rect = self.rect().adjusted(+frame_width, +frame_width, -frame_width, -frame_width)
        
        # 将按钮放在输入框内部右侧，留一点边距
        self.toggle_button.move(
            content_rect.right() - button_size.width() - 3, # 距离右边框3px
            (content_rect.height() - button_size.height()) // 2
        )
        
        # 设置右侧内边距，防止文本与按钮重叠
        padding = button_size.width() + 8 # 按钮宽度 + 左右边距
        self.setStyleSheet(f'QLineEdit {{ padding-right: {padding}px; }}')
    
    def _load_icons_or_text(self):
        """加载图标（如果可用），否则使用文本替代"""
        closed_exists = os.path.exists(self.eye_closed_path)
        open_exists = os.path.exists(self.eye_open_path)

        if closed_exists and open_exists:
            closed_pix = QPixmap(self.eye_closed_path)
            open_pix = QPixmap(self.eye_open_path)

            # 缩放图标到16×16
            size = QSize(16, 16)
            self.eye_closed_icon = QIcon(closed_pix.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.eye_open_icon = QIcon(open_pix.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

            self.toggle_button.setIcon(self.eye_closed_icon)
            self.toggle_button.setIconSize(size)
            # 清除可能存在的文本样式
            base_style = "QToolButton { border: none; background: transparent; padding: 0px; }"
            self.toggle_button.setStyleSheet(base_style)
        else:
            # 文本替代
            self.eye_closed_icon = None
            self.eye_open_icon = None
            self.toggle_button.setText("👁")
            self.toggle_button.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: transparent;
                    font-size: 16px; /* 调整字号以适应按钮大小 */
                    padding: 0px;
                }
                QToolButton:hover {
                    background-color: rgba(0, 0, 0, 0.05); /* 更淡的悬停效果 */
                }
            """)

    def on_toggled(self, checked: bool):
        """
        切换按钮被点击时的槽函数
        :param checked: 如果为True，则显示密码
        """
        if checked:
            # 显示密码
            self.setEchoMode(QLineEdit.Normal)
            if hasattr(self, 'eye_open_icon') and self.eye_open_icon:
                self.toggle_button.setIcon(self.eye_open_icon)
            else:
                self.toggle_button.setText("🙈")
        else:
            # 隐藏密码
            self.setEchoMode(QLineEdit.Password)
            if hasattr(self, 'eye_closed_icon') and self.eye_closed_icon:
                self.toggle_button.setIcon(self.eye_closed_icon)
            else:
                self.toggle_button.setText("👁")


class LoginWindow(QWidget):
    # 定义登录成功的信号，携带用户信息
    loginSuccessful = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("MoCo 数据助手 - 登录")
        
        # 创建主布局
        main_layout = QVBoxLayout()
        
        # 用户名行
        username_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        username_label.setFixedWidth(50)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMaximumWidth(400)  # 限制最大宽度
        username_layout.addWidget(username_label)
        username_layout.setAlignment(Qt.AlignCenter)
        username_layout.addWidget(self.username_input)
        
        # 密码行
        password_layout = QHBoxLayout()
        password_label = QLabel("密码:")
        password_label.setFixedWidth(50)
        self.password_input = PasswordLineEdit()
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        username_layout.setAlignment(Qt.AlignCenter) # 应为 password_layout
        
        # 登录按钮居中
        self.login_button = QPushButton("登录")
        self.login_button.setFixedWidth(100)  # 设置固定宽度
        self.login_button.setStyleSheet("""
            QPushButton {
                padding: 5px 0px;
            }
        """)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        button_layout.addWidget(self.login_button)
        button_layout.addStretch(1)
        
        # 添加所有组件到主布局
        main_layout.addStretch(0)
        main_layout.addLayout(username_layout)
        main_layout.addLayout(password_layout)
        main_layout.addSpacing(10)  # 添加小间距
        main_layout.addLayout(button_layout)
        main_layout.addStretch(0)
        self.setLayout(main_layout)
        
        # 连接信号
        self.login_button.clicked.connect(self.attempt_login)

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





