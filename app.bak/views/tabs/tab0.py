import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QMessageBox, QHBoxLayout
from PyQt5.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter
from PyQt5.QtCore import QRegularExpression
import yaml
from app.views.components.singleton import global_context
from app.controllers import flow0_validate_config
from app.config.config import get_config
from app.utils import rp
from app.views.components import show_markdown_dialog


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
    def __init__(self, config_file=None, parent=None):
        super().__init__(parent)
        config_file = get_config() if config_file is None else config_file
        self.config_service = config_file
        self.original_config = config_file._config
        self.special_config = config_file._special
        self.current_config = self.special_config.copy()
        self.show_full_config = False  # 是否显示完整配置
        global_context.data["config"] = self.current_config
        
        # 初始化布局
        layout = QVBoxLayout()

        # 标题
        title_label = QLabel("编辑 YAML 配置文件")
        layout.addWidget(title_label)

        # Special 配置
        self.special_yaml = self.config_service.get_special_yaml()
        self.full_yaml = yaml.dump(self.original_config, allow_unicode=True)

        # YAML 编辑器
        self.yaml_editor = QTextEdit()
        self.yaml_editor.setPlainText(self.special_yaml)

        # 应用 YAML 语法高亮
        self.highlighter = YAMLHighlighter(self.yaml_editor.document())
        layout.addWidget(self.yaml_editor)

        # 操作按钮行
        button_layout = QHBoxLayout()
        
        # 按钮：显示完整配置/只显示特殊配置
        self.toggle_config_button = QPushButton("显示完整配置")
        self.toggle_config_button.clicked.connect(self.toggle_config_view)
        
        # 按钮：查看配置说明
        show_help_button = QPushButton("配置字段说明")
        show_help_button.clicked.connect(self.show_config_help)
        
        # 将按钮添加到水平布局
        button_layout.addWidget(self.toggle_config_button)
        button_layout.addWidget(show_help_button)
        
        # 添加水平布局到主布局
        layout.addLayout(button_layout)

        # 保存和重置按钮
        save_button = QPushButton("保存更改")
        reset_button = QPushButton("恢复默认")
        save_button.clicked.connect(self.save_changes)
        reset_button.clicked.connect(self.reset_to_default)

        layout.addWidget(save_button)
        layout.addWidget(reset_button)

        self.setLayout(layout)

    def toggle_config_view(self):
        """切换显示完整配置或只显示特殊配置"""
        self.show_full_config = not self.show_full_config
        
        # 保存当前编辑器位置
        cursor_position = self.yaml_editor.textCursor().position()
        
        if self.show_full_config:
            self.yaml_editor.setPlainText(self.full_yaml)
            self.toggle_config_button.setText("只显示特殊配置")
        else:
            self.yaml_editor.setPlainText(self.special_yaml)
            self.toggle_config_button.setText("显示完整配置")
        
        # 如果位置在新文本范围内，尝试恢复位置
        if cursor_position < len(self.yaml_editor.toPlainText()):
            cursor = self.yaml_editor.textCursor()
            cursor.setPosition(cursor_position)
            self.yaml_editor.setTextCursor(cursor)
    
    def show_config_help(self):
        """显示配置字段说明文档"""
        try:
            # 读取说明文档
            readme_path = rp("readme.md", folder="config")
            with open(readme_path, "r", encoding="utf-8") as f:
                markdown_content = f.read()
            
            # 显示Markdown对话框
            show_markdown_dialog(markdown_content, "配置文件字段说明", self)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法加载说明文档：{str(e)}")

    def save_changes(self):
        """保存更改到配置文件"""
        try:
            if self.show_full_config:
                # 如果显示的是完整配置，则直接解析并保存
                updated_config = yaml.safe_load(self.yaml_editor.toPlainText())
                if not isinstance(updated_config, dict):
                    QMessageBox.critical(self, "错误", "编辑器中不是合法的dict结构")
                    return
                
                # 验证配置项
                flag, e = flow0_validate_config(updated_config)
                if not flag:
                    QMessageBox.critical(self, "错误", f"配置项内容错误：\n{str(e)}")
                    return
                
                # 保存完整配置
                with open(rp("config.yaml", folder="config"), "w", encoding="utf-8") as f:
                    yaml.dump(updated_config, f, allow_unicode=True)
                
                # 更新内存中的配置
                self.original_config = updated_config
                self.special_config = {}
                for sp_path in updated_config.get("SPECIAL", []):
                    val = self.config_service._get_value_by_path(sp_path, updated_config)
                    if val is not None:
                        self.config_service._set_value_by_path(sp_path, val, self.special_config)
                
                self.current_config = self.special_config.copy()
                self.special_yaml = yaml.dump(self.special_config, allow_unicode=True)
                self.full_yaml = self.yaml_editor.toPlainText()
            else:
                # 如果只显示特殊配置，则使用原逻辑
                updated_special = yaml.safe_load(self.yaml_editor.toPlainText())
                if not isinstance(updated_special, dict):
                    QMessageBox.critical(self, "错误", "编辑器中不是合法的dict结构")
                    return
                
                updated_config = self._merge_special_into_config(
                    updated_special,
                    self.original_config.copy()
                )
                updated_config['SPECIAL'] = self.config_service.special_list

                # 验证配置项
                flag, e = flow0_validate_config(updated_config)
                if not flag:
                    QMessageBox.critical(self, "错误", f"配置项内容错误：\n{str(e)}")
                    return
                
                # 更新内存中的配置并保存到文件
                self.current_config = updated_special
                with open(rp("config.yaml", folder="config"), "w", encoding="utf-8") as f:
                    yaml.dump(updated_config, f, allow_unicode=True)
                
                # 更新显示内容
                self.special_yaml = self.yaml_editor.toPlainText()
                self.full_yaml = yaml.dump(updated_config, allow_unicode=True)
            
            global_context.data["config"] = self.current_config
            QMessageBox.information(self, "成功", "配置已成功保存")
        except yaml.YAMLError as e:
            QMessageBox.critical(self, "错误", f"YAML 格式错误：\n{str(e)}")

    def reset_to_default(self):
        """恢复默认配置"""
        try:
            os.remove(rp("config.yaml", folder="config"))
        except:
            pass
        
        # 重新加载默认配置
        config_file = get_config()
        self.config_service = config_file
        self.original_config = config_file._config
        self.special_config = config_file._special
        self.current_config = self.special_config.copy()
        global_context.data["config"] = self.current_config
        
        # 更新显示内容
        self.special_yaml = self.config_service.get_special_yaml()
        self.full_yaml = yaml.dump(self.original_config, allow_unicode=True)
        
        # 根据当前显示模式更新编辑器内容
        if self.show_full_config:
            self.yaml_editor.setPlainText(self.full_yaml)
        else:
            self.yaml_editor.setPlainText(self.special_yaml)
        
        QMessageBox.information(self, "提示", "已恢复默认配置")

    def _merge_special_into_config(self, partial: dict, base: dict) -> dict:
        """
        将partial(编辑器修改过的special)合并进base(原完整配置),
        返回合并后的大字典(你想怎么合并具体看需要).
        举个递归dict合并的例子:
        """
        for k, v in partial.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                # 递归合并
                self._merge_special_into_config(v, base[k])
            else:
                base[k] = v
        return base