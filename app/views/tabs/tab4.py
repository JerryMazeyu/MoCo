# ================================ CP管理 ================================

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame, QFormLayout,
                             QLineEdit, QMessageBox, QDialog, QGridLayout, QSpinBox,
                             QListWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from app.services.instances.cp import CP
from app.utils.logger import setup_logger
from app.utils.oss import oss_get_json_file, oss_get_yaml_file, oss_put_yaml_file
from app.config.config import CONF

# 设置日志
LOGGER = setup_logger()

# 账户选择对话框
class AccountSelectDialog(QDialog):
    def __init__(self, account_list, parent=None):
        super().__init__(parent)
        self.account_list = account_list
        self.selected_account = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("选择账户")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # 创建列表控件显示账户
        self.list_widget = QListWidget()
        for account in self.account_list:
            self.list_widget.addItem(account)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addWidget(QLabel("请选择账户:"))
        layout.addWidget(self.list_widget)
        layout.addLayout(button_layout)
    
    def get_selected_account(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            return selected_items[0].text()
        return None

class CPCard(QFrame):
    """CP信息卡片组件"""
    delete_signal = pyqtSignal(str)  # 删除信号，传递CP ID
    edit_signal = pyqtSignal(dict)  # 编辑信号，传递CP数据
    bind_signal = pyqtSignal(str, bool)  # 绑定/解绑信号，传递CP ID和是否绑定
    
    def __init__(self, cp_data, parent=None, is_bound=False):
        super().__init__(parent)
        self.cp_data = cp_data
        self.is_bound = is_bound
        self.setFrameShape(QFrame.NoFrame)  # 移除框架
        self.setStyleSheet("""
            QFrame { 
                background-color: #f9f9f9; 
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 10px; 
                margin: 8px;
            }
            QPushButton {
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 60px;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
        """)
        self.setFixedSize(500, 400)  # 调整卡片大小
        self.setup_ui()
        
    def setup_ui(self):
        """设置卡片UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 标题栏包含CP名称和绑定按钮
        title_bar = QHBoxLayout()
        
        # CP名称作为标题
        title = QLabel(self.cp_data.get('cp_name', '未命名CP'))
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; background: none; border: none;")
        
        # 绑定/解绑按钮
        self.bind_button = QPushButton("解绑" if self.is_bound else "绑定")
        self.bind_button.setStyleSheet(f"""
            background-color: {"#e74c3c" if self.is_bound else "#2ecc71"}; 
            color: white; 
            border: none;
        """)
        self.bind_button.clicked.connect(self.toggle_bind)
        
        title_bar.addWidget(title)
        title_bar.addStretch()
        
        # 只有当有目标用户时才显示绑定按钮
        if hasattr(CONF, 'runtime') and hasattr(CONF.runtime, 'target_manipulate_user'):
            title_bar.addWidget(self.bind_button)
        
        main_layout.addLayout(title_bar)
        
        # CP ID
        id_layout = QHBoxLayout()
        id_label = QLabel("ID:")
        id_label.setStyleSheet("color: #888; font-size: 14px; background: none; border: none;")
        id_value = QLabel(str(self.cp_data.get('cp_id', 'N/A')))
        id_value.setStyleSheet("color: #333; font-weight: bold; font-size: 13px; background: none; border: none;")
        id_layout.addWidget(id_label)
        id_layout.addWidget(id_value)
        id_layout.addStretch()
        main_layout.addLayout(id_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #ddd; border: none;")
        main_layout.addWidget(line)
        
        # CP信息 - 使用表格布局
        info_layout = QGridLayout()
        info_layout.setSpacing(6)
        
        row = 0
        # 省份和城市
        self.add_info_row(info_layout, row, "省份:", self.cp_data.get('cp_province', 'N/A'))
        row += 1
        self.add_info_row(info_layout, row, "城市:", self.cp_data.get('cp_city', 'N/A'))
        row += 1
        self.add_info_row(info_layout, row, "位置:", self.cp_data.get('cp_location', 'N/A'))
        row += 1
        self.add_info_row(info_layout, row, "每日收油量:", self.cp_data.get('cp_barrels_per_day', 'N/A'))
        row += 1
        self.add_info_row(info_layout, row, "总容量:", self.cp_data.get('cp_capacity', 'N/A'))
        row += 1
        self.add_info_row(info_layout, row, "当前库存:", self.cp_data.get('cp_stock', 'N/A'), True)
        
        main_layout.addLayout(info_layout)
        main_layout.addStretch()
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        edit_btn = QPushButton("编辑")
        edit_btn.setStyleSheet("background-color: #4a86e8; color: white; border: none;")
        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("background-color: #e74c3c; color: white; border: none;")
        
        edit_btn.clicked.connect(self.edit_cp)
        delete_btn.clicked.connect(self.delete_cp)
        
        btn_layout.addStretch()
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        main_layout.addLayout(btn_layout)
    
    def toggle_bind(self):
        """切换CP绑定状态"""
        self.is_bound = not self.is_bound
        self.bind_button.setText("解绑" if self.is_bound else "绑定")
        self.bind_button.setStyleSheet(f"""
            background-color: {"#e74c3c" if self.is_bound else "#2ecc71"}; 
            color: white; 
            border: none;
        """)
        self.bind_signal.emit(self.cp_data.get('cp_id'), self.is_bound)
    
    def add_info_row(self, layout, row, label_text, value_text, highlight=False):
        """添加信息行，使用统一的样式"""
        label = QLabel(label_text)
        label.setStyleSheet("color: #666; font-size: 13px; background: none; border: none;")
        
        value = QLabel(str(value_text))
        if highlight:
            value.setStyleSheet("color: #e67e22; font-size: 13px; font-weight: bold; background: none; border: none;")
        else:
            value.setStyleSheet("color: #333; font-size: 13px; background: none; border: none;")
        
        layout.addWidget(label, row, 0, Qt.AlignLeft)
        layout.addWidget(value, row, 1, Qt.AlignLeft)
    
    def update_bind_status(self, is_bound):
        """更新绑定状态"""
        self.is_bound = is_bound
        self.bind_button.setText("解绑" if self.is_bound else "绑定")
        self.bind_button.setStyleSheet(f"""
            background-color: {"#e74c3c" if self.is_bound else "#2ecc71"}; 
            color: white; 
            border: none;
        """)
        
        # 只有当有目标用户时才显示绑定按钮
        if hasattr(CONF, 'runtime') and hasattr(CONF.runtime, 'target_manipulate_user'):
            self.bind_button.setVisible(True)
        else:
            self.bind_button.setVisible(False)
    
    def edit_cp(self):
        """编辑CP信息"""
        self.edit_signal.emit(self.cp_data)
        
    def delete_cp(self):
        """删除CP"""
        # 创建一个原始样式的确认对话框
        msg_box = QMessageBox()
        msg_box.setStyleSheet("")  # 清除所有样式，使用系统默认样式
        msg_box.setWindowTitle("确认删除")
        msg_box.setText(f"确定要删除CP '{self.cp_data.get('cp_name')}'吗？")
        msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg_box.setDefaultButton(QMessageBox.No)
        
        reply = msg_box.exec_()
                                   
        if reply == QMessageBox.Yes:
            self.delete_signal.emit(self.cp_data.get('cp_id'))


class CPEditDialog(QDialog):
    """CP编辑对话框"""
    def __init__(self, cp_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑CP" if cp_data else "新增CP")
        self.cp_data = cp_data or {}
        self.result_data = {}
        self.setup_ui()
        
    def setup_ui(self):
        """设置对话框UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # CP ID（如果是编辑模式则显示但不可编辑）
        self.cp_id_edit = QLineEdit(self.cp_data.get('cp_id', ''))
        if 'cp_id' in self.cp_data:
            self.cp_id_edit.setReadOnly(True)
        form_layout.addRow("CP ID:", self.cp_id_edit)
        
        # CP名称（必填）
        self.cp_name_edit = QLineEdit(self.cp_data.get('cp_name', ''))
        form_layout.addRow("CP名称 *:", self.cp_name_edit)
        
        # 省份
        self.province_edit = QLineEdit(self.cp_data.get('cp_province', ''))
        form_layout.addRow("省份:", self.province_edit)
        
        # 城市
        self.city_edit = QLineEdit(self.cp_data.get('cp_city', ''))
        form_layout.addRow("城市:", self.city_edit)
        
        # 位置
        self.location_edit = QLineEdit(self.cp_data.get('cp_location', ''))
        form_layout.addRow("位置 (纬度,经度):", self.location_edit)
        
        # 每日收油量
        self.barrels_edit = QSpinBox()
        self.barrels_edit.setRange(0, 1000000)
        self.barrels_edit.setValue(int(self.cp_data.get('cp_barrels_per_day', 0)))
        form_layout.addRow("每日收油量:", self.barrels_edit)
        
        # 总容量
        self.capacity_edit = QSpinBox()
        self.capacity_edit.setRange(0, 1000000)
        self.capacity_edit.setValue(int(self.cp_data.get('cp_capacity', 0)))
        form_layout.addRow("总容量:", self.capacity_edit)
        
        # 当前库存
        self.stock_edit = QSpinBox()
        self.stock_edit.setRange(0, 1000000)
        self.stock_edit.setValue(int(self.cp_data.get('cp_stock', 0)))
        form_layout.addRow("当前库存:", self.stock_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        
        save_btn.clicked.connect(self.save_data)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def save_data(self):
        """保存CP数据"""
        # 验证必填字段
        if not self.cp_name_edit.text().strip():
            QMessageBox.warning(self, "验证失败", "CP名称为必填项！")
            return
            
        # 收集表单数据
        self.result_data = {
            'cp_id': self.cp_id_edit.text(),
            'cp_name': self.cp_name_edit.text(),
            'cp_province': self.province_edit.text(),
            'cp_city': self.city_edit.text(),
            'cp_location': self.location_edit.text(),
            'cp_barrels_per_day': self.barrels_edit.value(),
            'cp_capacity': self.capacity_edit.value(),
            'cp_stock': self.stock_edit.value()
        }
        
        # 保留原有数据中的其他字段
        for key, value in self.cp_data.items():
            if key not in self.result_data:
                self.result_data[key] = value
                
        self.accept()


class Tab4(QWidget):
    """CP管理标签页"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cp_cards = {}  # 存储CP卡片的字典，键为CP ID
        self.current_account = None  # 当前选择的账户
        self.setStyleSheet("""
            QWidget { 
                background-color: white; 
            }
            QScrollArea { 
                border: none;
                background-color: white;
            }
            QWidget#scrollContent { 
                background-color: white;
            }
        """)
        self.setup_ui()
        self.load_cps()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 顶部布局 - 包含账户选择按钮
        top_layout = QHBoxLayout()
        
        # 标题
        title_label = QLabel("CP管理")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        # 账户按钮 - 放在最右上角
        self.account_button = QPushButton("未选择账号")
        self.account_button.clicked.connect(self.select_account)
        self.account_button.setFixedWidth(150)
        self.account_button.setStyleSheet("""
            QPushButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        
        top_layout.addWidget(title_label)
        top_layout.addStretch(1)  # 将账户按钮推到右侧
        top_layout.addWidget(self.account_button)
        
        layout.addLayout(top_layout)
        
        # 顶部按钮区
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加CP")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        
        self.add_btn.clicked.connect(self.add_cp)
        self.refresh_btn.clicked.connect(self.load_cps)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # 滚动区域显示CP卡片
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")
        
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scrollContent")
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # 左上对齐
        
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)
    
    def select_account(self):
        """选择/切换账户"""
        try:
            # 从login_info.json获取账户列表
            login_info = oss_get_json_file('login_info.json')
            
            if not login_info:
                QMessageBox.warning(self, "账户列表为空", "未找到任何账户数据。")
                return
            
            # 获取账户列表
            account_list = list(login_info.keys())
            
            if not account_list:
                QMessageBox.warning(self, "账户列表为空", "未找到任何账户数据。")
                return
                
            # 显示账户选择对话框
            dialog = AccountSelectDialog(account_list, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_account = dialog.get_selected_account()
                if selected_account:
                    # 保存选择的账户到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                    
                    CONF.runtime.target_manipulate_user = selected_account
                    
                    # 获取用户配置
                    user_config = oss_get_yaml_file(f"configs/{selected_account}.yaml")
                    if user_config:
                        CONF.runtime.target_manipulate_user_conf = user_config
                        
                        # 更新账户按钮文本
                        self.account_button.setText(f"已选择账号：{selected_account}")
                        
                        # 刷新CP卡片显示，以更新绑定状态
                        self.current_account = selected_account
                        self.load_cps()
                    else:
                        QMessageBox.warning(self, "获取配置失败", f"无法获取用户 {selected_account} 的配置文件。")
        except Exception as e:
            LOGGER.error(f"选择账户时出错: {str(e)}")
            QMessageBox.critical(self, "选择账户失败", f"选择账户时出错: {str(e)}")
    
    def is_cp_bound(self, cp_id):
        """检查CP是否已绑定到当前账户"""
        if not hasattr(CONF, 'runtime') or not hasattr(CONF.runtime, 'target_manipulate_user_conf'):
            return False
            
        user_conf = CONF.runtime.target_manipulate_user_conf
        
        # 检查BUSINESS.CP.cp_id是否存在且包含此CP
        if ('BUSINESS' in user_conf and 
            'CP' in user_conf['BUSINESS'] and 
            'cp_id' in user_conf['BUSINESS']['CP']):
            bound_cp_ids = user_conf['BUSINESS']['CP']['cp_id']
            if isinstance(bound_cp_ids, list):
                return cp_id in bound_cp_ids
            else:
                return cp_id == bound_cp_ids
                
        return False
        
    def toggle_cp_binding(self, cp_id, is_bind):
        """切换CP绑定状态"""
        if not hasattr(CONF, 'runtime') or not hasattr(CONF.runtime, 'target_manipulate_user_conf'):
            QMessageBox.warning(self, "操作失败", "未选择账户。")
            return False
            
        try:
            user_name = CONF.runtime.target_manipulate_user
            user_conf = CONF.runtime.target_manipulate_user_conf
            
            # 确保BUSINESS.CP.cp_id存在
            if 'BUSINESS' not in user_conf:
                user_conf['BUSINESS'] = {}
            if 'CP' not in user_conf['BUSINESS']:
                user_conf['BUSINESS']['CP'] = {}
            if 'cp_id' not in user_conf['BUSINESS']['CP']:
                user_conf['BUSINESS']['CP']['cp_id'] = []
                
            # 获取当前绑定的CP ID列表
            cp_ids = user_conf['BUSINESS']['CP']['cp_id']
            if not isinstance(cp_ids, list):
                cp_ids = [cp_ids] if cp_ids else []
                
            # 根据操作修改列表
            if is_bind and cp_id not in cp_ids:
                cp_ids.append(cp_id)
            elif not is_bind and cp_id in cp_ids:
                cp_ids.remove(cp_id)
                
            # 更新配置
            user_conf['BUSINESS']['CP']['cp_id'] = cp_ids
            
            # 保存回OSS
            if oss_put_yaml_file(f"configs/{user_name}.yaml", user_conf):
                # 更新本地配置
                CONF.runtime.target_manipulate_user_conf = user_conf
                QMessageBox.information(self, "操作成功", f"CP已{'绑定到' if is_bind else '从'}账户 {user_name} {'解绑' if not is_bind else ''}")
                return True
            else:
                QMessageBox.warning(self, "操作失败", f"保存配置失败。")
                return False
                
        except Exception as e:
            LOGGER.error(f"切换CP绑定状态时出错: {str(e)}")
            QMessageBox.critical(self, "操作失败", f"切换CP绑定状态时出错: {str(e)}")
            return False
    
    def load_cps(self):
        """加载所有CP"""
        # 清空现有卡片
        for card in self.cp_cards.values():
            card.deleteLater()
        self.cp_cards.clear()
        
        # 清空网格布局
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 获取CP列表
        cp_list = CP.list()
        
        # 创建CP卡片
        row, col = 0, 0
        max_cols = 3  # 每行最多显示的卡片数
        
        for cp_data in cp_list:
            # 检查CP是否已绑定
            cp_id = cp_data.get('cp_id')
            is_bound = self.is_cp_bound(cp_id)
            
            # 创建卡片
            card = CPCard(cp_data, is_bound=is_bound)
            card.delete_signal.connect(self.delete_cp)
            card.edit_signal.connect(self.edit_cp)
            card.bind_signal.connect(self.toggle_cp_binding)
            
            self.grid_layout.addWidget(card, row, col, Qt.AlignTop | Qt.AlignLeft)  # 左上对齐
            self.cp_cards[cp_id] = card
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        LOGGER.info(f"已加载 {len(cp_list)} 个CP")
        
    def add_cp(self):
        """添加新CP"""
        dialog = CPEditDialog()
        if dialog.exec_():
            # 创建CP并注册
            try:
                cp = CP(dialog.result_data)
                if cp.register():
                    QMessageBox.information(self, "成功", f"CP '{cp.inst.cp_name}' 添加成功！")
                    self.load_cps()  # 刷新显示
                else:
                    QMessageBox.warning(self, "失败", f"CP添加失败！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建CP时发生错误: {e}")
    
    def edit_cp(self, cp_data):
        """编辑CP"""
        dialog = CPEditDialog(cp_data)
        if dialog.exec_():
            try:
                # 获取CP实例
                cp = CP.get_by_id(cp_data.get('cp_id'))
                if not cp:
                    QMessageBox.warning(self, "失败", f"无法找到ID为 {cp_data.get('cp_id')} 的CP！")
                    return
                
                # 更新CP实例数据
                for key, value in dialog.result_data.items():
                    setattr(cp.inst, key, value)
                
                # 保存更新
                if cp.update():
                    QMessageBox.information(self, "成功", f"CP '{cp.inst.cp_name}' 更新成功！")
                    self.load_cps()  # 刷新显示
                else:
                    QMessageBox.warning(self, "失败", f"CP更新失败！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新CP时发生错误: {e}")
    
    def delete_cp(self, cp_id):
        """删除CP"""
        try:
            # 获取CP实例
            cp = CP.get_by_id(cp_id)
            if not cp:
                QMessageBox.warning(self, "失败", f"无法找到ID为 {cp_id} 的CP！")
                return
            
            # 删除CP
            if cp.delete():
                QMessageBox.information(self, "成功", f"CP '{cp.inst.cp_name}' 已删除！")
                
                # 移除对应的卡片
                if cp_id in self.cp_cards:
                    self.cp_cards[cp_id].deleteLater()
                    del self.cp_cards[cp_id]
                
                self.load_cps()  # 刷新显示
            else:
                QMessageBox.warning(self, "失败", f"CP删除失败！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除CP时发生错误: {e}")
