from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextBrowser, 
                            QPushButton, QFileDialog, QHBoxLayout)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QFont, QDesktopServices
import markdown
import os


class MarkdownReviewerWidget(QWidget):
    """Markdown渲染器组件，用于显示Markdown格式的文档"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.markdown_content = ""
        self.initUI()
    
    def initUI(self):
        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建文本浏览器
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenLinks(False)  # 禁止自动打开链接
        self.text_browser.anchorClicked.connect(self.open_link)
        self.text_browser.setFont(QFont("Segoe UI", 10))
        self.text_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        # 设置支持的Markdown样式
        self.css = """
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 100%;
                margin: 0;
                padding: 0;
            }
            h1, h2, h3, h4, h5, h6 {
                color: #0078d7;
                margin-top: 24px;
                margin-bottom: 16px;
                font-weight: 600;
            }
            h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
            h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; }
            h3 { font-size: 1.25em; }
            h4 { font-size: 1em; }
            p, ul, ol { margin-bottom: 16px; }
            a { color: #0366d6; text-decoration: none; }
            a:hover { text-decoration: underline; }
            code {
                font-family: Consolas, monospace;
                background-color: #f6f8fa;
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-size: 85%;
            }
            pre {
                background-color: #f6f8fa;
                border-radius: 3px;
                padding: 16px;
                overflow: auto;
                font-family: Consolas, monospace;
                font-size: 85%;
                line-height: 1.45;
                margin-bottom: 16px;
            }
            blockquote {
                padding: 0 1em;
                color: #6a737d;
                border-left: 0.25em solid #dfe2e5;
                margin: 0 0 16px 0;
            }
            img { max-width: 100%; }
            table {
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 16px;
            }
            table th, table td {
                padding: 6px 13px;
                border: 1px solid #dfe2e5;
            }
            table tr:nth-child(2n) {
                background-color: #f6f8fa;
            }
            hr {
                height: 0.25em;
                padding: 0;
                margin: 24px 0;
                background-color: #e1e4e8;
                border: 0;
            }
        </style>
        """
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 打开文件按钮
        self.open_button = QPushButton("打开Markdown文件")
        self.open_button.clicked.connect(self.open_markdown_file)
        
        # 刷新按钮
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        
        # 添加按钮到布局
        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        
        # 添加组件到主布局
        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.text_browser)
    
    def set_markdown(self, markdown_text):
        """设置并渲染Markdown文本"""
        self.markdown_content = markdown_text
        self.render_markdown()
    
    def render_markdown(self):
        """渲染Markdown内容为HTML并显示"""
        if not self.markdown_content:
            return
        
        # 使用Python-Markdown库渲染Markdown
        html_content = markdown.markdown(
            self.markdown_content,
            extensions=[
                'markdown.extensions.extra',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code'
            ]
        )
        
        # 添加CSS样式
        html_with_style = f"""
        <!DOCTYPE html>
        <html>
        <head>
            {self.css}
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # 设置HTML内容
        self.text_browser.setHtml(html_with_style)
    
    def open_markdown_file(self):
        """打开Markdown文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开Markdown文件", "", "Markdown文件 (*.md);;文本文件 (*.txt);;所有文件 (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    self.markdown_content = file.read()
                self.current_file = file_path
                self.render_markdown()
            except Exception as e:
                self.text_browser.setHtml(f"<p style='color: red;'>加载文件失败: {str(e)}</p>")
    
    def refresh(self):
        """刷新当前文件"""
        if self.current_file and os.path.exists(self.current_file):
            try:
                with open(self.current_file, 'r', encoding='utf-8') as file:
                    self.markdown_content = file.read()
                self.render_markdown()
            except Exception as e:
                self.text_browser.setHtml(f"<p style='color: red;'>刷新文件失败: {str(e)}</p>")
    
    def open_link(self, url):
        """处理链接点击事件"""
        url_string = url.toString()
        
        # 如果是本地锚点链接，在内部处理
        if url_string.startswith('#'):
            self.text_browser.scrollToAnchor(url_string[1:])
        else:
            # 否则使用系统默认浏览器打开
            QDesktopServices.openUrl(QUrl(url_string)) 