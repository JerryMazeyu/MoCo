from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox
from PyQt5.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter
from PyQt5.QtCore import QRegularExpression
import yaml
from app.controllers import flow0_validate_config
from app.config.config import CONF, default_config
from app.utils import rp
import os, shutil


class YAMLHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        # 定义不同层级的键名格式
        self.key_formats = [
            QTextCharFormat(),  # 一级键名
            QTextCharFormat(),  # 二级键名
            QTextCharFormat(),  # 三级键名
            QTextCharFormat(),  # 四级键名
            QTextCharFormat(),  # 五级键名
            QTextCharFormat(),  # 六级键名
            QTextCharFormat()   # 七级键名
        ]

        # 分配颜色
        colors = [
            "#d73a49",  # 红色：一级键名
            "#22863a",  # 绿色：二级键名
            "#b36b00",  # 橙色：三级键名
            "#005cc5",  # 蓝色：四级键名
            "#e36209",  # 深橙色：五级键名
            "#6f42c1",  # 紫色：六级键名
            "#0366d6"   # 深蓝色：七级键名
        ]

        # 应用颜色到格式
        for i, color in enumerate(colors):
            self.key_formats[i].setForeground(QColor(color))

        # 定义值的高亮格式
        self.value_format = QTextCharFormat()
        self.value_format.setForeground(QColor("#032f62"))  # 蓝色：值（字符串）

        # 定义正则表达式规则
        self.rules = []

        # 动态生成正则表达式规则，每层对应不同缩进
        for level in range(7):
            pattern = rf"^(\s{{{level * 2}}})(\S+):"
            # pattern = rf"^(\s*)[\w\-]+:"
            self.rules.append((pattern, self.key_formats[level]))

        # 添加值的规则
        self.rules += [
            (r":\s*\".*?\"", self.value_format),  # 双引号字符串
            (r":\s*\'.*?\'", self.value_format),  # 单引号字符串
            (r":\s*\d+(\.\d+)?", self.value_format),  # 数字
            (r":\s*(true|false|yes|no)", self.value_format)  # 布尔值
        ]

    def highlightBlock(self, text):
        """应用高亮规则"""
        for pattern, fmt in self.rules:
            expression = QRegularExpression(pattern)
            match_iterator = expression.globalMatch(text)  # 使用 globalMatch 获取匹配项
            while match_iterator.hasNext():
                match = match_iterator.next()
                start, length = match.capturedStart(), match.capturedLength()
                self.setFormat(start, length, fmt)


class Tab0(QWidget):
    def __init__(self, config_file=CONF, parent=None):
        super().__init__(parent)
        self.original_config = config_file._config
        self.current_config = self.original_config.copy()

        # 初始化布局
        layout = QVBoxLayout()

        # 标题
        title_label = QLabel("编辑 YAML 配置文件")
        layout.addWidget(title_label)

        # YAML 编辑器
        self.yaml_editor = QTextEdit()
        self.yaml_editor.setPlainText(yaml.dump(self.current_config, allow_unicode=True))

        # 应用 YAML 语法高亮
        self.highlighter = YAMLHighlighter(self.yaml_editor.document())
        layout.addWidget(self.yaml_editor)

        # 按钮布局
        save_button = QPushButton("保存更改")
        reset_button = QPushButton("恢复默认")
        save_button.clicked.connect(self.save_changes)
        reset_button.clicked.connect(self.reset_to_default)

        layout.addWidget(save_button)
        layout.addWidget(reset_button)

        self.setLayout(layout)

    def save_changes(self):
        """保存更改到配置文件"""
        try:
            # 获取编辑器中的 YAML 内容并解析为字典
            updated_config = yaml.safe_load(self.yaml_editor.toPlainText())
            flag, e = flow0_validate_config(updated_config)
            if not flag:
                QMessageBox.critical(self, "错误", f"配置项内容错误：\n{str(e)}")
                return
            # 更新内存中的配置并保存到文件
            self.current_config = updated_config
            with open(rp("config.yaml", folder="config"), "w", encoding="utf-8") as f:
                yaml.dump(updated_config, f, allow_unicode=True)
            QMessageBox.information(self, "成功", "配置已成功保存")
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "错误", f"YAML 格式错误：\n{str(e)}")

    def reset_to_default(self):
        """恢复默认配置"""
        try:
            os.remove(rp("config.yaml", folder="config"))
        except:
            pass
        self.current_config = default_config._config.copy()
        self.yaml_editor.setPlainText(yaml.dump(self.current_config, allow_unicode=True))
        QMessageBox.information(self, "提示", "已恢复默认配置")
