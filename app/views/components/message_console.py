import sys
from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat, QFont
import datetime
import logging

class MessageManager(QObject):
    """消息管理器单例，用于全局管理消息"""
    
    _instance = None
    message_received = pyqtSignal(str, str)  # 消息内容，消息类型
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageManager, cls).__new__(cls)
            cls._instance.init()
        return cls._instance
    
    def init(self):
        """初始化消息管理器"""
        self.console_widgets = []
    
    def add_console(self, console):
        """添加控制台组件"""
        if console not in self.console_widgets:
            self.console_widgets.append(console)
    
    def remove_console(self, console):
        """移除控制台组件"""
        if console in self.console_widgets:
            self.console_widgets.remove(console)
    
    def send_message(self, message, msg_type="info"):
        """发送消息到所有控制台"""
        # 移除时间戳前缀（如果已经由日志格式化器添加）
        if " - " in message and message.startswith("20"):
            # 日志格式为"YYYY-MM-DD HH:MM:SS,MS - LEVEL - MESSAGE"
            # 我们只保留最后的MESSAGE部分
            parts = message.split(" - ", 2)
            if len(parts) >= 3:
                message = parts[2]  # 只保留消息内容
        
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        for console in self.console_widgets:
            console.append_message(formatted_message, msg_type)


class MessageConsoleWidget(QWidget):
    """消息控制台组件，用于显示和更新应用中的所有输出消息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

        self.setFixedHeight(150)
        
        # 将此控制台添加到消息管理器
        self.message_manager = MessageManager()
        self.message_manager.add_console(self)
    
    def initUI(self):
        """初始化UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        
        # 创建文本区域
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Consolas", 10))
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 清除按钮
        self.clear_button = QPushButton("清除消息")
        self.clear_button.clicked.connect(self.clear_messages)
        
        # 保存按钮
        self.save_button = QPushButton("保存日志")
        self.save_button.clicked.connect(self.save_log)
        
        # 日志级别控制按钮
        self.log_level_button = QPushButton("显示调试信息")
        self.log_level_button.setCheckable(True)
        self.log_level_button.clicked.connect(self.toggle_debug_level)
        
        # 添加按钮到布局
        button_layout.addWidget(self.clear_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.log_level_button)
        button_layout.addStretch()
        
        # 添加组件到主布局
        self.layout.addWidget(self.text_edit)
        self.layout.addLayout(button_layout)
        
        # 设置样式
        self.setStyleSheet("""
            QTextEdit {
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #3c3c3c;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
            QPushButton:checked {
                background-color: #5E81AC;
            }
        """)
    
    def append_message(self, message, msg_type="info"):
        """添加消息到控制台"""
        cursor = self.text_edit.textCursor()
        format = QTextCharFormat()
        
        # 根据消息类型设置颜色
        if msg_type == "error":
            format.setForeground(QColor("#ff6b6b"))
        elif msg_type == "warning":
            format.setForeground(QColor("#feca57"))
        elif msg_type == "success":
            format.setForeground(QColor("#1dd1a1"))
        else:  # info
            format.setForeground(QColor("#f0f0f0"))
        
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(message + "\n", format)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
    
    def clear_messages(self):
        """清除所有消息"""
        self.text_edit.clear()
        self.append_message("消息已清除", "info")
    
    def save_log(self):
        """保存日志到文件"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"log_{timestamp}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.text_edit.toPlainText())
            self.append_message(f"日志已保存到 {filename}", "success")
        except Exception as e:
            self.append_message(f"保存日志失败: {str(e)}", "error")
    
    def toggle_debug_level(self, checked):
        """切换日志级别"""
        try:
            # 获取根日志记录器
            root_logger = logging.getLogger()
            
            if checked:
                # 设置为DEBUG级别
                root_logger.setLevel(logging.DEBUG)
                self.log_level_button.setText("隐藏调试信息")
                self.append_message("已切换到调试级别，将显示更详细的日志信息", "info")
            else:
                # 设置为INFO级别
                root_logger.setLevel(logging.INFO)
                self.log_level_button.setText("显示调试信息")
                self.append_message("已切换到信息级别，调试信息将被隐藏", "info")
                
            # 同时也更新moco.log日志器的级别
            moco_logger = logging.getLogger("moco.log")
            moco_logger.setLevel(logging.DEBUG if checked else logging.INFO)
        except Exception as e:
            self.append_message(f"切换日志级别失败: {str(e)}", "error")
    
    def __del__(self):
        """析构函数，从消息管理器中移除此控制台"""
        self.message_manager.remove_console(self) 