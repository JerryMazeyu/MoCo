from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import pyqtSignal
from app.controllers.flow_login import validate_user_info

class LoginWindow(QWidget):
    # 定义登录成功的信号，携带用户信息
    loginSuccessful = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("MoCo 数据助手 - 登录")
        self.setGeometry(300, 300, 300, 200)
        
        layout = QVBoxLayout()
        
        # 用户名输入
        self.username_label = QLabel("用户名:")
        self.username_input = QLineEdit()
        layout.addWidget(self.username_label)
        layout.addWidget(self.username_input)
        
        # 密码输入
        self.password_label = QLabel("密码:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_input)
        
        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.attempt_login)
        layout.addWidget(self.login_button)
        
        self.setLayout(layout)
    
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