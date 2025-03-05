from PyQt5.QtWidgets import QTextBrowser, QDialog, QVBoxLayout, QPushButton, QDialogButtonBox, QDesktopWidget, QSizePolicy
from PyQt5.QtCore import Qt

class MarkdownViewer(QDialog):
    """显示Markdown格式文本的对话框组件"""
    
    def __init__(self, markdown_text, title="文档", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(800, 600)
        
        # 居中显示
        self.center_on_screen()
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 创建文本浏览器
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)  # 允许打开外部链接
        self.text_browser.setMarkdown(markdown_text)  # 设置Markdown内容
        
        # 设置样式
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 10px;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #333333;
                margin-top: 20px;
                margin-bottom: 10px;
            }
            h1 { font-size: 24px; }
            h2 { font-size: 20px; }
            h3 { font-size: 18px; }
            h4 { font-size: 16px; }
            a { color: #0066cc; }
            code {
                background-color: #f5f5f5;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: Consolas, monospace;
            }
            pre {
                background-color: #f5f5f5;
                padding: 10px;
                border-radius: 3px;
                overflow-x: auto;
            }
        """)
        
        # 按钮盒子
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        
        # 添加widgets到布局
        layout.addWidget(self.text_browser)
        layout.addWidget(button_box)
        
        # 设置布局
        self.setLayout(layout)
    
    def center_on_screen(self):
        """将对话框居中显示在屏幕上"""
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

def show_markdown_dialog(markdown_text, title="文档", parent=None):
    """显示Markdown对话框的便捷函数"""
    dialog = MarkdownViewer(markdown_text, title, parent)
    dialog.exec_() 