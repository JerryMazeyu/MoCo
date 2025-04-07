from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QTreeView, QMessageBox, QLabel, QFrame, QHeaderView,
                            QSplitter)
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QColor
import yaml
from app.views.components.singleton import global_context
import app
import copy  # 导入深拷贝模块
from app.utils.logger import get_logger

# 获取全局日志对象
LOGGER = get_logger()

def _get_value_by_path(path: str, data: dict):
    keys = path.split(".")
    current = data
    for k in keys:
        if not isinstance(current, dict) or k not in current:
            return None
        current = current[k]
    return current


class ConfigTreeModel(QStandardItemModel):
    """配置树模型，用于展示YAML配置的层级结构"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.show_special_only = True
        self.config_data = {}
    
    def load_config(self, config_data):
        """加载配置数据"""
        self.config_data = config_data
        self.refresh()
    
    def refresh(self):
        """刷新模型数据"""
        try:
            self.clear()
            
            if not self.config_data:
                return
            
            if self.show_special_only and "SPECIAL" in self.config_data:
                # 展示SPECIAL中引用的键值对
                tmp_data = {}
                special_keys = self.config_data.get("SPECIAL", {})
                for key in special_keys:  # TODO
                    tmp_data[key] = _get_value_by_path(key, self.config_data)
                self._add_items(self.invisibleRootItem(), tmp_data, "SPECIAL")
                
            else:
                # 显示全部内容
                self._add_items(self.invisibleRootItem(), self.config_data)
        except Exception as e:
            LOGGER.error(f"刷新模型数据时出错: {e}")
    
    def _get_reference_content(self, path):
        """从路径获取引用的内容"""
        try:
            current = self.config_data
            
            # 遍历路径的每一部分
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                elif isinstance(current, list) and key.isdigit() and int(key) < len(current):
                    # 支持列表索引
                    current = current[int(key)]
                else:
                    LOGGER.error(f"引用路径 {'.'.join(path)} 无效，在 {key} 处中断")
                    return None
            
            return current
        except Exception as e:
            LOGGER.error(f"获取引用内容时出错: {e}")
            return None
    
    def _add_items(self, parent_item, config_dict, parent_key=""):
        """递归添加配置项到树模型"""
        if not isinstance(config_dict, dict):
            return
        
        for key, value in config_dict.items():
            key_item = QStandardItem(str(key))
            
            # 设置不同级别的字体和颜色
            font = QFont()
            if not parent_key:  # 顶级节点
                font.setBold(True)
                font.setPointSize(11)
                key_item.setForeground(QColor("#0078D7"))
            elif parent_key == "SPECIAL":  # SPECIAL子节点
                font.setBold(True)
                font.setPointSize(10)
                key_item.setForeground(QColor("#2E7D32"))
            elif parent_key == "REFERENCE":  # 引用内容
                font.setPointSize(9)
                key_item.setForeground(QColor("#6A1B9A"))
            
            key_item.setFont(font)
            
            # 创建值项
            if isinstance(value, dict):
                value_item = QStandardItem("")  # 字典不在值列显示内容
                parent_item.appendRow([key_item, value_item])
                # 递归添加子节点
                self._add_items(key_item, value, key)
            else:
                value_item = QStandardItem(str(value))
                value_item.setEditable(True)  # 值可编辑
                parent_item.appendRow([key_item, value_item])


class Tab1(QWidget):
    """配置界面Tab，用于查看和修改配置"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent
        self.config_file = None
        self.default_config_file = None
        self.config_data = {}
        self.initUI()
        
        # 加载配置
        self.load_my_config()
    
    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题和说明
        title_label = QLabel("配置界面")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        
        description_label = QLabel(
            "此界面用于查看和修改系统配置。默认显示SPECIAL字段内容，点击'显示全部字段'可查看所有配置。"
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
            }
            QTreeView::item {
                padding: 6px;
                min-width: 250px; /* 增加项的最小宽度 */
            }
            QTreeView::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: url(vline.png) 0;
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-image: url(branch-more.png) 0;
            }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(branch-end.png) 0;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(branch-closed.png);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(branch-open.png);
            }
        """)
        
        # 设置树模型
        self.config_model = ConfigTreeModel()
        self.tree_view.setModel(self.config_model)
        
        # 隐藏表头，但设置列宽
        self.tree_view.header().hide()
        
        # 直接设置更大的列宽以确保键名完整显示
        self.tree_view.setColumnWidth(0, 600)  # 进一步增加第一列宽度避免省略号
        
        # 允许用户手动调整列宽
        self.tree_view.header().setStretchLastSection(True)  # 最后一列自动拉伸填充
        self.tree_view.header().setMinimumSectionSize(500)  # 设置最小宽度
        
        # 启用自动展开
        self.tree_view.setAutoExpandDelay(0)  # 自动展开延迟为0
        
        # 按钮区域
        button_frame = QFrame()
        button_frame.setFrameShape(QFrame.StyledPanel)
        button_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
            }
            QPushButton {
                padding: 6px 12px;
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
        self.show_all_button = QPushButton("显示全部字段")
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
        self.show_all_button.clicked.connect(self.toggle_show_all)
        self.save_button.clicked.connect(self.save_config)
        self.reset_button.clicked.connect(self.reset_config)
        
        # 添加按钮到布局
        button_layout.addWidget(self.show_all_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        
        # 添加组件到主布局
        self.layout.addWidget(title_label)
        self.layout.addWidget(description_label)
        self.layout.addWidget(self.tree_view)
        self.layout.addWidget(button_frame)
    
    def load_my_config(self):
        """加载配置数据"""
        try:
            # 尝试从配置模块导入
            from app.config.config import CONF
            
            self.config_data = CONF._config_dict
            LOGGER.info("成功从CONF加载配置")
        except Exception as e:
            LOGGER.error(f"加载配置模块失败: {e}，使用默认配置")
            raise ValueError(f"加载配置数据失败。\n错误详情: {str(e)}")
            # # 使用默认配置
            # self.config_data = self.get_default_config()
            # QMessageBox.warning(self, "加载配置失败", 
            #                     f"加载配置数据失败，已加载默认配置。\n错误详情: {str(e)}")
        
        # 将配置深拷贝到global_context中
        global_context.data['CONF'] = copy.deepcopy(self.config_data)
        global_context.data['CONF_OBJ'] = CONF
        
        # 更新模型
        self.config_model.load_config(self.config_data)
        
        # 展开树视图
        self.tree_view.expandAll()
    
    def get_default_config(self):
        """获取默认配置数据"""
        return {
            "SPECIAL": {
                "API_KEYS": {
                    "GAODE_KEY": "your_gaode_api_key_here",
                    "KIMI_KEY": "your_kimi_api_key_here",
                    "YOUDAO_KEY": "your_youdao_api_key_here",
                    "AIQICHA_KEY": "your_aiqicha_api_key_here"
                },
                "PATHS": {
                    "EXPORT_DIR": "exports",
                    "LOGS_DIR": "logs",
                    "TEMP_DIR": "temp"
                }
            },
            "BUSINESS": {
                "CP": {
                    "cp_id": ["CP001", "CP002", "CP003", "CP004"],
                    "CP001": {
                        "name": "某某物流公司",
                        "cities": ["北京", "上海", "广州", "深圳"]
                    },
                    "CP002": {
                        "name": "XX快递",
                        "cities": ["成都", "重庆", "武汉", "长沙"]
                    },
                    "CP003": {
                        "name": "XX物流",
                        "cities": ["杭州", "南京", "苏州", "宁波"]
                    },
                    "CP004": {
                        "name": "XX货运",
                        "cities": ["西安", "郑州", "济南", "青岛"]
                    }
                }
            },
            "SYSTEM": {
                "LOG_LEVEL": "INFO",
                "MAX_THREADS": 4,
                "TIMEOUT": 30,
                "RETRY_COUNT": 3
            }
        }
    
    def toggle_show_all(self):
        """切换显示全部字段/只显示SPECIAL字段"""
        if self.config_model.show_special_only:
            self.config_model.show_special_only = False
            self.show_all_button.setText("只显示SPECIAL字段")
        else:
            self.config_model.show_special_only = True
            self.show_all_button.setText("显示全部字段")
        
        self.config_model.refresh()
        self.tree_view.expandAll()  # 展开所有节点
    
    def save_config(self):
        """保存配置到文件"""
        try:
            global_context.data['CONF_OBJ'].save()
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存配置时出错：{str(e)}")
    
    def extract_values_from_model(self):
        """从模型中提取修改后的值到配置数据，并同步到global_context"""
        try:
            # 实现配置提取的基本逻辑
            self._extract_from_item(self.config_model.invisibleRootItem(), self.config_data)
        except Exception as e:
            LOGGER.error(f"提取配置值时出错: {e}")
    
    def _extract_from_item(self, item, config_dict):
        """递归从模型项提取数据到配置字典"""
        try:
            row_count = item.rowCount()
            
            for i in range(row_count):
                key_item = item.child(i, 0)
                value_item = item.child(i, 1)
                
                if key_item is None or value_item is None:
                    continue
                    
                key = key_item.text()
                
                # 处理引用项的特殊情况
                if " (引用: " in key:
                    key = key.split(" (引用: ")[0]
                
                if key_item.hasChildren():
                    # 如果是字典节点，递归提取
                    if key not in config_dict:
                        config_dict[key] = {}
                    self._extract_from_item(key_item, config_dict[key])
                else:
                    # 如果是叶节点，提取值
                    value = value_item.text()
                    
                    # 尝试转换为适当的类型
                    try:
                        # 尝试转换为整数
                        if value.isdigit():
                            value = int(value)
                        # 尝试转换为浮点数
                        elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                            value = float(value)
                        # 尝试转换为布尔值
                        elif value.lower() in ('true', 'false'):
                            value = value.lower() == 'true'
                    except:
                        # 保持为字符串
                        pass
                    
                    config_dict[key] = value
        except Exception as e:
            LOGGER.error(f"从项提取数据时出错: {e}")
    
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
                self.load_my_config()
                
                QMessageBox.information(self, "重置成功", "配置已恢复为默认值并同步到全局上下文。")
            except Exception as e:
                QMessageBox.critical(self, "重置失败", f"恢复默认配置时出错：{str(e)}") 