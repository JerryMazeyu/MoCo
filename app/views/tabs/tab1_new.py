from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTreeView, QMessageBox, QLabel, QFrame, QHeaderView,
                            QSplitter, QGroupBox, QTabWidget)
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QColor
import yaml
from app.views.components.singleton import global_context
import app
import copy
from app.utils.logger import get_logger

# 获取全局日志对象
LOGGER = get_logger()

def _get_value_by_path(path: str, data: dict):
    """根据路径获取字典中的值"""
    keys = path.split(".")
    current = data
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
    return current


class CustomTreeModel(QStandardItemModel):
    """自定义树模型，用于展示YAML配置的指定层级结构"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_data = {}
        self.structure = {}
    
    def load_config(self, config_data, structure):
        """加载配置数据和指定的结构"""
        self.config_data = config_data
        self.structure = structure
        self.refresh()
    
    def refresh(self):
        """刷新模型数据"""
        try:
            self.clear()
            
            if not self.config_data:
                return
            
            # 创建根节点
            for root_key, sub_items in self.structure.items():
                root_item = QStandardItem(root_key)
                root_item.setFont(self._get_font(True, 12))
                root_item.setForeground(QColor("#0078D7"))
                
                self.invisibleRootItem().appendRow([root_item, QStandardItem("")])
                
                # 添加子节点
                self._add_structured_items(root_item, sub_items, self.config_data)
        except Exception as e:
            LOGGER.error(f"刷新模型数据时出错: {e}")
    
    def _get_font(self, bold=False, size=10):
        """获取字体"""
        font = QFont()
        font.setBold(bold)
        font.setPointSize(size)
        return font
    
    def _add_structured_items(self, parent_item, structure, config_data, path=""):
        """递归添加结构化项目到树模型"""
        if isinstance(structure, dict):
            for key, sub_structure in structure.items():
                # 确定实际的配置路径
                config_key = sub_structure.get("path", key) if isinstance(sub_structure, dict) else key
                
                # 从配置中获取值
                current_path = f"{path}.{config_key}" if path else config_key
                current_value = _get_value_by_path(current_path, config_data)
                
                # 创建项目
                key_item = QStandardItem(key)
                key_item.setFont(self._get_font(True, 10))
                key_item.setForeground(QColor("#2E7D32"))
                
                # 不可编辑标记
                readonly = isinstance(sub_structure, dict) and sub_structure.get("readonly", False)
                if readonly:
                    key_item.setEditable(False)
                    key_item.setText(f"{key} [不可修改]")
                    key_item.setForeground(QColor("#9E9E9E"))  # 灰色表示不可修改
                
                if isinstance(current_value, dict) or (isinstance(sub_structure, dict) and "children" in sub_structure):
                    # 字典类型，需要继续添加子项
                    value_item = QStandardItem("")
                    parent_item.appendRow([key_item, value_item])
                    
                    # 如果有明确指定的子结构，使用它
                    if isinstance(sub_structure, dict) and "children" in sub_structure:
                        self._add_structured_items(key_item, sub_structure["children"], config_data, current_path)
                    else:
                        # 否则递归添加所有子项
                        for sub_key, sub_value in current_value.items():
                            sub_key_item = QStandardItem(sub_key)
                            if isinstance(sub_value, dict):
                                sub_value_item = QStandardItem("")
                                key_item.appendRow([sub_key_item, sub_value_item])
                                self._add_structured_items(sub_key_item, {}, config_data, f"{current_path}.{sub_key}")
                            else:
                                sub_value_item = QStandardItem(str(sub_value))
                                sub_value_item.setEditable(not readonly)
                                key_item.appendRow([sub_key_item, sub_value_item])
                elif isinstance(current_value, list):
                    # 列表类型
                    value_item = QStandardItem(str(current_value))
                    value_item.setEditable(not readonly)
                    parent_item.appendRow([key_item, value_item])
                else:
                    # 基本类型
                    value_item = QStandardItem(str(current_value) if current_value is not None else "")
                    value_item.setEditable(not readonly)
                    parent_item.appendRow([key_item, value_item])
        elif structure:
            # 如果结构是简单标记，直接添加对应的值
            current_value = _get_value_by_path(path, config_data)
            if isinstance(current_value, dict):
                for sub_key, sub_value in current_value.items():
                    sub_key_item = QStandardItem(sub_key)
                    if isinstance(sub_value, dict):
                        sub_value_item = QStandardItem("")
                        parent_item.appendRow([sub_key_item, sub_value_item])
                        self._add_structured_items(sub_key_item, {}, config_data, f"{path}.{sub_key}")
                    else:
                        sub_value_item = QStandardItem(str(sub_value))
                        parent_item.appendRow([sub_key_item, sub_value_item])


class Tab1New(QWidget):
    """配置界面Tab，用于查看和修改指定层级的配置"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent
        self.config_data = {}
        self.initUI()
        
        # 定义显示结构
        self.structure = {
            "系统设置": {
                "KEYS": {
                    "path": "KEYS",
                    "children": {
                        "KIMI大模型KEY": {"path": "kimi_keys"},
                        "高德地图KEY": {"path": "gaode_keys"},
                        "有道词典KEY": {"path": "youdao_keys"},
                        "OSS系统设置": {
                            "path": "oss",
                            "readonly": True
                        }
                    }
                }
            },
            "用户设置": {
                "CP信息": {
                    "path": "BUSINESS.CP"
                },
                "餐厅-CP关系": {
                    "path": "BUSINESS.REST2CP"
                },
                "餐厅信息": {
                    "path": "BUSINESS.RESTAURANT"
                }
            }
        }
        
        # 加载配置
        self.load_config()
    
    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        # 标题和说明
        title_label = QLabel("系统配置")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        
        description_label = QLabel(
            "此界面用于查看和修改系统核心配置。双击值单元格可以编辑相应配置项。"
        )
        description_label.setWordWrap(True)
        description_label.setStyleSheet("color: #555; margin-bottom: 15px;")
        
        # 创建树视图
        self.tree_view = QTreeView()
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setEditTriggers(QTreeView.DoubleClicked)
        self.tree_view.setStyleSheet("""
            QTreeView {
                border: 1px solid #d3d3d3;
                background-color: white;
                border-radius: 4px;
            }
            QTreeView::item {
                padding: 8px;
                min-width: 250px;
            }
            QTreeView::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        
        # 设置树模型
        self.config_model = CustomTreeModel()
        self.tree_view.setModel(self.config_model)
        
        # 设置表头
        self.tree_view.header().setDefaultSectionSize(300)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.header().hide()
        # self.tree_view.header().setSectionResizeMode(0, QHeaderView.Interactive)
        
        # 创建表头
        self.config_model.setHorizontalHeaderLabels(["配置项", "值"])
        
        # 按钮区域
        button_frame = QFrame()
        button_frame.setFrameShape(QFrame.StyledPanel)
        button_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 12px;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 4px;
                border: 1px solid #ccc;
                background-color: white;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #e6e6e6;
                border-color: #adadad;
            }
        """)
        
        button_layout = QHBoxLayout(button_frame)
        
        # 创建按钮
        self.save_button = QPushButton("保存配置")
        self.reset_button = QPushButton("恢复默认配置")
        
        # 按钮样式
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border-color: #4cae4c;
            }
            QPushButton:hover {
                background-color: #449d44;
                border-color: #398439;
            }
        """)
        
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border-color: #d43f3a;
            }
            QPushButton:hover {
                background-color: #c9302c;
                border-color: #ac2925;
            }
        """)
        
        # 连接按钮信号
        self.save_button.clicked.connect(self.save_config)
        self.reset_button.clicked.connect(self.reset_config)
        
        # 添加按钮到布局
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        
        # 添加组件到主布局
        self.layout.addWidget(title_label)
        self.layout.addWidget(description_label)
        self.layout.addWidget(self.tree_view, 1)
        self.layout.addWidget(button_frame)
    
    def load_config(self):
        """加载配置数据"""
        try:
            # 尝试从配置模块导入
            from app.config.config import CONF
            
            self.config_data = CONF._config_dict
            LOGGER.info("成功从CONF加载配置")
        except Exception as e:
            LOGGER.error(f"加载配置模块失败: {e}，使用默认配置")
            raise ValueError(f"加载配置数据失败。\n错误详情: {str(e)}")
        
        # 将配置深拷贝到global_context中
        global_context.data['CONF'] = copy.deepcopy(self.config_data)
        global_context.data['CONF_OBJ'] = CONF
        
        # 更新模型
        self.config_model.load_config(self.config_data, self.structure)
        
        # 展开树视图
        self.tree_view.expandAll()
    
    def save_config(self):
        """保存配置到文件"""
        try:
            # 先从页面模型中提取最新的配置数据
            self.extract_values_from_model()
            # 然后保存配置到文件
            global_context.data['CONF_OBJ'].save()
            # 更新全局上下文中的配置
            global_context.data['CONF'] = copy.deepcopy(global_context.data['CONF_OBJ']._config_dict)
            QMessageBox.information(self, "保存成功", "配置已成功保存")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置时出错：{str(e)}")
    
    def extract_values_from_model(self):
        """从模型中提取修改后的值到配置数据，并同步到global_context"""
        try:
            # 实现配置提取的基本逻辑
            self._extract_from_item(self.config_model.invisibleRootItem(), {}, "")
        except Exception as e:
            LOGGER.error(f"提取配置值时出错: {e}")
    
    def _extract_from_item(self, item, current_dict, current_path):
        """递归从模型项提取数据到配置字典"""
        row_count = item.rowCount()
        
        # 处理表头情况
        if item == self.config_model.invisibleRootItem():
            for i in range(row_count):
                section_item = item.child(i, 0)
                self._extract_from_item(section_item, self.config_data, "")
            return
        
        # 获取当前项的键名
        key = item.text()
        if "[不可修改]" in key:
            key = key.split(" [不可修改]")[0]
        
        # 确定实际的配置路径
        if key in ["系统设置", "用户设置"]:
            # 这是根节点，不对应实际配置项
            for i in range(row_count):
                child_item = item.child(i, 0)
                self._extract_from_item(child_item, self.config_data, "")
            return
        
        # 处理KEYS特殊情况
        if key == "KEYS":
            for i in range(row_count):
                child_item = item.child(i, 0)
                child_key = child_item.text()
                if "[不可修改]" in child_key:
                    # 跳过不可修改的项
                    continue
                
                # 映射UI名称到实际配置名称
                config_key = {
                    "KIMI大模型KEY": "kimi_keys",
                    "高德地图KEY": "gaode_keys",
                    "有道词典KEY": "youdao_keys"
                }.get(child_key, child_key)
                
                if child_item.rowCount() == 0:
                    # 叶节点，直接获取值
                    value_item = item.child(i, 1)
                    value = self._parse_value(value_item.text())
                    self.config_data["KEYS"][config_key] = value
                else:
                    # 非叶节点，递归处理
                    self._extract_from_item(child_item, self.config_data, f"KEYS.{config_key}")
            return
        
        # 处理CP信息特殊情况
        if key == "CP信息":
            for i in range(row_count):
                child_item = item.child(i, 0)
                child_key = child_item.text()
                if child_item.rowCount() == 0:
                    # 叶节点，直接获取值
                    value_item = item.child(i, 1)
                    value = self._parse_value(value_item.text())
                    self.config_data["BUSINESS"]["CP"][child_key] = value
                else:
                    # 非叶节点，递归处理
                    self._extract_from_item(child_item, self.config_data, f"BUSINESS.CP.{child_key}")
            return
        
        # 处理餐饮信息特殊情况
        if key == "餐饮信息":
            for i in range(row_count):
                child_item = item.child(i, 0)
                child_key = child_item.text()
                if child_item.rowCount() == 0:
                    # 叶节点，直接获取值
                    value_item = item.child(i, 1)
                    value = self._parse_value(value_item.text())
                    self.config_data["BUSINESS"]["REST2CP"][child_key] = value
                else:
                    # 非叶节点，递归处理
                    self._extract_from_item(child_item, self.config_data, f"BUSINESS.REST2CP.{child_key}")
            return
        
        # 常规项目处理
        for i in range(row_count):
            child_item = item.child(i, 0)
            child_key = child_item.text()
            if "[不可修改]" in child_key:
                # 跳过不可修改的项
                continue
                
            if child_item.rowCount() == 0:
                # 叶节点，直接获取值
                value_item = item.child(i, 1)
                value = self._parse_value(value_item.text())
                
                # 更新配置
                path_parts = current_path.split(".")
                target_dict = self.config_data
                for part in path_parts:
                    if part:  # 忽略空部分
                        if part not in target_dict:
                            target_dict[part] = {}
                        target_dict = target_dict[part]
                
                target_dict[child_key] = value
            else:
                # 非叶节点，递归处理
                new_path = f"{current_path}.{child_key}" if current_path else child_key
                self._extract_from_item(child_item, self.config_data, new_path)
    
    def _parse_value(self, value_str):
        """解析值字符串为适当的类型"""
        try:
            # 尝试解析列表
            if value_str.startswith('[') and value_str.endswith(']'):
                try:
                    # 移除字符串表示的列表格式
                    if value_str.startswith("['") and value_str.endswith("']"):
                        # 尝试将字符串形式的列表转为真实列表
                        import ast
                        return ast.literal_eval(value_str)
                    else:
                        # 其他列表格式，如 [1, 2, 3]
                        return yaml.safe_load(value_str)
                except:
                    pass
            # 尝试转换为整数
            elif value_str.isdigit():
                return int(value_str)
            # 尝试转换为浮点数
            elif value_str.replace('.', '', 1).isdigit() and value_str.count('.') == 1:
                return float(value_str)
            # 尝试解析逗号分隔的数字为列表
            elif ',' in value_str and all(v.strip().isdigit() for v in value_str.split(',')):
                return [int(v.strip()) for v in value_str.split(',')]
            # 尝试转换为布尔值
            elif value_str.lower() in ('true', 'false'):
                return value_str.lower() == 'true'
        except:
            # 保持为字符串
            pass
            
        return value_str
    
    def reset_config(self):
        """恢复默认配置"""
        reply = QMessageBox.question(
            self, '确认重置', 
            '确定要恢复默认配置吗？这将删除您的所有自定义设置。',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 重新加载默认配置
                LOGGER.info("正在重置配置...")
                global_context.data['CONF_OBJ'].refresh()
                self.load_config()
                
                QMessageBox.information(self, "重置成功", "配置已恢复为默认值")
            except Exception as e:
                QMessageBox.critical(self, "重置失败", f"恢复默认配置时出错：{str(e)}")
