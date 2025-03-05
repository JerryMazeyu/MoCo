import sys
from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QTextCursor, QColor

class MessageSignals(QObject):
    """消息信号类，用于发送消息更新信号"""
    message_received = pyqtSignal(str, str)  # 参数：消息内容，消息类型

class MessageConsole(QTextEdit):
    """消息控制台组件，用于显示和更新应用中的所有输出消息"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMinimumHeight(100)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                font-family: Consolas, Monaco, monospace;
                font-size: 12px;
            }
        """)
        
    def append_message(self, message, msg_type="info"):
        """
        添加消息到控制台
        
        参数:
            message (str): 要显示的消息
            msg_type (str): 消息类型，可选值：info, warning, error, success
        """
        color_map = {
            "info": "#000000",      # 黑色
            "warning": "#FF8C00",   # 暗橙色
            "error": "#FF0000",     # 红色
            "success": "#008000",   # 绿色
            "debug": "#808080"      # 灰色
        }
        
        # 设置颜色
        color = color_map.get(msg_type, "#000000")
        
        # 获取光标并移到文档末尾
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        
        # 设置文本颜色
        self.setTextColor(QColor(color))
        
        # 添加消息
        self.insertPlainText(message)
        if not message.endswith("\n"):
            self.insertPlainText("\n")
            
        # 滚动到最新内容
        self.ensureCursorVisible()


class MessageManager(QObject):
    """消息管理器，单例模式，用于全局管理消息"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageManager, cls).__new__(cls)
            cls._instance.signals = MessageSignals()
            cls._instance.console = None
        return cls._instance
    
    def set_console(self, console):
        """设置消息控制台实例"""
        self.console = console
        
    def print(self, message, msg_type="info"):
        """打印消息到控制台"""
        if self.console:
            self.signals.message_received.emit(str(message), msg_type)
            
    def connect_console(self, console):
        """将控制台连接到信号"""
        self.set_console(console)
        self.signals.message_received.connect(lambda msg, type: console.append_message(msg, type))


class StdoutRedirector:
    """标准输出重定向器，用于捕获和重定向标准输出"""
    def __init__(self, msg_type="info"):
        self.msg_manager = MessageManager()
        self.msg_type = msg_type
        self.buffer = ""
        
    def write(self, text):
        # 保存原始输出
        sys.__stdout__.write(text)
        
        # 添加到缓冲区
        self.buffer += text
        
        # 如果有换行符，发送完整的行
        if '\n' in self.buffer:
            lines = self.buffer.split('\n')
            self.buffer = lines.pop()  # 最后一行可能不完整
            
            for line in lines:
                self.msg_manager.print(line + '\n', self.msg_type)
    
    def flush(self):
        # 如果缓冲区有内容，也发送出去
        if self.buffer:
            self.msg_manager.print(self.buffer, self.msg_type)
            self.buffer = ""
        sys.__stdout__.flush()


class MessageConsoleWidget(QWidget):
    """包含消息控制台的widget，方便添加到布局中"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.console = MessageConsole()
        self.layout.addWidget(self.console)
        self.setLayout(self.layout)
        
        # 设置为全局消息管理器的控制台
        msg_manager = MessageManager()
        msg_manager.connect_console(self.console)
        
    def get_console(self):
        """获取控制台实例"""
        return self.console 