# ================================ 车辆管理 ================================

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QComboBox, QGroupBox, QGridLayout,
                            QFileDialog, QMessageBox, QLayout, QListWidget, QDialog, QLineEdit,
                            QApplication, QFormLayout)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect
from PyQt5.QtGui import QColor, QIcon, QPixmap,QIntValidator
import pandas as pd
from app.views.components.xlsxviewer import XlsxViewerWidget
from app.views.components.singleton import global_context
from app.utils.logger import get_logger
from app.services.instances.vehicle import Vehicle, VehicleGroup
from app.services.instances.cp import CP
from app.config.config import CONF
from app.utils import oss_get_excel_file, oss_put_excel_file
import os
import datetime
import sys

# 获取全局日志对象
LOGGER = get_logger()

# CP选择对话框
class CPSelectDialog(QDialog):
    def __init__(self, cp_list, parent=None):
        super().__init__(parent)
        self.cp_list = cp_list
        self.selected_cp = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("选择CP")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # 创建列表控件显示CP
        self.list_widget = QListWidget()
        for cp in self.cp_list:
            # 使用字典访问方式而不是 get 方法
            cp_name = cp['cp_name'] if isinstance(cp, dict) else cp.cp_name
            cp_id = cp['cp_id'] if isinstance(cp, dict) else cp.cp_id
            self.list_widget.addItem(f"{cp_name} (ID: {cp_id})")
        
        # 添加按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addWidget(QLabel("请选择CP:"))
        layout.addWidget(self.list_widget)
        layout.addLayout(button_layout)
    
    def get_selected_cp(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            index = self.list_widget.row(selected_items[0])
            if 0 <= index < len(self.cp_list):
                return self.cp_list[index]
        return None

class VehicleAddDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("添加车辆")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # 创建表单
        form_layout = QFormLayout()
        
        # 车牌号（必填）
        self.plate_input = QLineEdit()
        self.plate_input.setPlaceholderText("请输入车牌号")
        plate_label = QLabel("车牌号<span style='color: red;'>*</span>:")
        plate_label.setStyleSheet("QLabel { color: black; }")
        form_layout.addRow(plate_label, self.plate_input)
        
        # 司机姓名（必填）
        self.driver_input = QLineEdit()
        self.driver_input.setPlaceholderText("请输入司机姓名")
        driver_label = QLabel("司机姓名<span style='color: red;'>*</span>:")
        driver_label.setStyleSheet("QLabel { color: black; }")
        form_layout.addRow(driver_label, self.driver_input)
        
        # 车辆类型（必填）
        self.type_combo = QComboBox()
        self.type_combo.addItem("餐厅收集车(to_rest)", "to_rest")  # 餐厅收集车对应to_rest类型
        self.type_combo.addItem("销售运输车(to_sale)", "to_sale")  # 销售运输车对应to_sale类型
        self.type_combo.currentIndexChanged.connect(self.update_cooldown_days)  # 添加类型改变事件处理
        type_label = QLabel("车辆类型<span style='color: red;'>*</span>:")
        type_label.setStyleSheet("QLabel { color: black; }")
        type_label.setToolTip("车辆类型（目前有餐厅收集车to_rest、销售运输车to_sale两种）")
        form_layout.addRow(type_label, self.type_combo)

        # 车辆冷却时间（可选）
        self.cooldown_input = QLineEdit()
        self.cooldown_input.setText("1")  # 设置默认值为1
        self.cooldown_input.setPlaceholderText("请输入冷却天数")
        # 只允许输入数字
        self.cooldown_input.setValidator(QIntValidator(1, 99))
        cooldown_label = QLabel("冷却时间(天):")
        cooldown_label.setToolTip("车辆完成一次任务后需要等待的冷却时间")
        form_layout.addRow(cooldown_label, self.cooldown_input)
        
        layout.addLayout(form_layout)
        
        # 添加说明文字
        note_label = QLabel("<span style='color: red;'>*</span> 为必填项")
        note_label.setStyleSheet("font-size: 12px; color: #666; margin-top: 10px;")
        layout.addWidget(note_label)
        
        # 添加按钮
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def update_cooldown_days(self):
        """根据车辆类型更新冷却天数"""
        vehicle_type = self.type_combo.currentData()
        if vehicle_type == "to_rest":  # 餐厅收集车
            self.cooldown_input.setText("1")
        else:  # 销售运输车
            self.cooldown_input.setText("3")
    
    def get_vehicle_info(self):
        """获取填写的车辆信息"""
        plate = self.plate_input.text().strip()
        driver = self.driver_input.text().strip()
        vehicle_type = self.type_combo.currentData()
        cooldown_days = self.cooldown_input.text().strip()
        cooldown_days = int(cooldown_days) if cooldown_days else 1

        # 验证必填项
        if not plate:
            QMessageBox.warning(self, "输入错误", "车牌号不能为空")
            return None
            
        if not driver:
            QMessageBox.warning(self, "输入错误", "司机姓名不能为空")
            return None
            
        if not vehicle_type:
            QMessageBox.warning(self, "输入错误", "请选择车辆类型")
            return None
            
        # 返回车辆信息字典
        return {
            "vehicle_license_plate": plate,
            "vehicle_driver_name": driver,
            "vehicle_type": vehicle_type,
            "vehicle_cooldown_days": cooldown_days,
            "vehicle_belonged_cp": None  # CP ID会在外部设置
        }

class Tab5(QWidget):
    """车辆管理Tab，实现车辆信息管理功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 先保存parent引用，但不直接使用主窗口的方法
        self.main_window_ref = parent
        self.current_cp = None  # 当前选择的CP
        self.temp_files = []  # 用于跟踪临时文件
        self.vehicles_data = None  # 存储当前加载的车辆数据
        self.oss_path = None  # OSS路径
        self.initUI()
    
    def __del__(self):
        """析构函数，清理资源"""
        try:
            # 检查Python是否正在关闭
            if sys.meta_path is None:
                return
                
            # 清理临时文件
            self.cleanup_temp_files()
            
            # 强制垃圾回收
            try:
                import gc
                gc.collect()
            except Exception:
                pass
            
        except Exception:
            # 在析构函数中不记录错误，因为日志系统可能已经关闭
            pass
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        import os
        
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    LOGGER.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                LOGGER.error(f"删除临时文件时出错: {str(e)}")
                
        # 清空列表
        self.temp_files = []
    
    def initUI(self):
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)  # 减小组件间距
        
        # 顶部布局 - 包含CP选择按钮
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("车辆管理")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        # CP按钮 - 放在最右上角
        self.cp_button = QPushButton("未选择CP")
        self.cp_button.clicked.connect(self.select_cp)
        self.cp_button.setFixedWidth(150)
        self.cp_button.setStyleSheet("""
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
        top_layout.addStretch(1)  # 将CP按钮推到右侧
        top_layout.addWidget(self.cp_button)
        
        self.layout.addLayout(top_layout)
        
        # 车辆信息区域
        excel_group = QGroupBox("车辆信息")
        excel_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        excel_layout = QVBoxLayout(excel_group)
        self.xlsx_viewer = XlsxViewerWidget(
            show_open=False, 
            show_save=False, 
            show_save_as=True, 
            show_refresh=True,
            display_columns=[
                'vehicle_id', 'vehicle_license_plate', 'vehicle_driver_name', 
                'vehicle_type', 'vehicle_belonged_cp', 'vehicle_status',
                'vehicle_rough_weight', 'vehicle_tare_weight', 'vehicle_net_weight',
                'vehicle_last_use', 'vehicle_cooldown_days'
            ],
            datetime_columns=[
                'vehicle_last_use'
            ]
        )
        excel_layout.addWidget(self.xlsx_viewer)
        
        # 添加到主布局
        self.layout.addWidget(excel_group, 1)  # 给表格区域分配更多空间
        
        # 控制区域
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 4px;
                border: 1px solid #ddd;
                padding: 10px;
            }
        """)
        
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(10, 10, 10, 10)
        
        # 添加车辆按钮
        add_button_layout = QHBoxLayout()
        self.add_vehicle_button = QPushButton("添加车辆")
        self.add_vehicle_button.clicked.connect(self.add_vehicle)
        self.add_vehicle_button.setEnabled(False)  # 默认禁用，需要先选择CP
        self.add_vehicle_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #46b8da;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        # 下载车辆模板按钮
        self.download_template_button = QPushButton("下载车辆模板")
        self.download_template_button.clicked.connect(self.download_template)
        self.download_template_button.setToolTip("下载车辆数据录入模板文件，包含必填字段：车牌号、司机姓名、车辆类型")
        self.download_template_button.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        # 批量上传按钮
        self.batch_upload_button = QPushButton("批量上传")
        self.batch_upload_button.clicked.connect(self.batch_upload)
        self.batch_upload_button.setEnabled(False)  # 默认禁用，需要先选择CP
        self.batch_upload_button.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #ec971f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        # 保存到OSS按钮
        self.save_to_oss_button = QPushButton("保存到OSS")
        self.save_to_oss_button.clicked.connect(self.save_to_oss)
        self.save_to_oss_button.setEnabled(False)  # 默认禁用，需要先选择CP
        self.save_to_oss_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        # 删除车辆按钮
        self.delete_vehicle_button = QPushButton("删除车辆")
        self.delete_vehicle_button.clicked.connect(self.delete_vehicle)
        self.delete_vehicle_button.setEnabled(False)  # 默认禁用，需要先选择CP
        self.delete_vehicle_button.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        
        add_button_layout.addWidget(self.add_vehicle_button)
        add_button_layout.addWidget(self.download_template_button)
        add_button_layout.addWidget(self.batch_upload_button)
        add_button_layout.addWidget(self.delete_vehicle_button)
        add_button_layout.addStretch()
        add_button_layout.addWidget(self.save_to_oss_button)
        
        control_layout.addLayout(add_button_layout)
        
        # 添加控制区域到主布局
        self.layout.addWidget(control_frame)
        
        # 初始消息
        LOGGER.info("车辆管理模块已初始化")
        LOGGER.info("请选择CP后操作")
    
    def select_cp(self):
        """选择/切换CP"""
        try:
            # 获取OSS上的CP列表
            cp_list = CP.list()
            
            if not cp_list:
                QMessageBox.warning(self, "CP列表为空", "未找到任何CP数据，请先添加CP。")
                return
            
            # 获取配置中的CP ID列表
            conf_cp_ids = []
            if hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                conf_cp_ids = CONF.BUSINESS.CP.cp_id  # 直接使用列表

            available_cp_list = [cp for cp in cp_list if cp['cp_id'] in conf_cp_ids]
            
            # 显示CP选择对话框
            dialog = CPSelectDialog(available_cp_list, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_cp = dialog.get_selected_cp()
                if selected_cp:
                    # 将列表中的字典转换为对象
                    cp_data = {
                        'cp_id': selected_cp['cp_id'] if isinstance(selected_cp, dict) else selected_cp.cp_id,
                        'cp_name': selected_cp['cp_name'] if isinstance(selected_cp, dict) else selected_cp.cp_name
                    }
                    
                    # 保存选择的CP到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', {})
                    
                    CONF.runtime.CP = cp_data
                    self.current_cp = cp_data
                    
                    # 更新CP按钮文本
                    self.cp_button.setText(f"已选择CP为：{cp_data['cp_name']}")
                    
                    # 启用按钮
                    self.add_vehicle_button.setEnabled(True)
                    self.save_to_oss_button.setEnabled(True)
                    self.batch_upload_button.setEnabled(True)
                    self.delete_vehicle_button.setEnabled(True)
                    
                    # 加载车辆数据
                    self.load_vehicles_data()
                    
                    # 通知主窗口更新CP
                    if self.main_window_ref:
                        self.main_window_ref.set_current_cp(cp_data['cp_id'])
        except Exception as e:
            LOGGER.error(f"选择CP时出错: {str(e)}")
            QMessageBox.critical(self, "选择CP失败", f"选择CP时出错: {str(e)}")
    
    def load_vehicles_data(self):
        """从OSS加载车辆数据"""
        try:
            if not self.current_cp:
                LOGGER.warning("未选择CP，无法加载车辆数据")
                return
                
            cp_id = self.current_cp['cp_id']
            self.oss_path = f"CPs/{cp_id}/vehicle/vehicles.xlsx"
            
            LOGGER.info(f"正在从OSS加载车辆数据: {self.oss_path}")
            
            # 尝试从OSS获取数据
            try:
                data = oss_get_excel_file(self.oss_path)
                if data is not None and not data.empty:
                    self.vehicles_data = data
                    self.xlsx_viewer.load_data(data=data)
                    LOGGER.info(f"成功加载 {len(data)} 条车辆记录")
                else:
                    # 如果没有数据，创建空DataFrame
                    LOGGER.info(f"OSS路径 {self.oss_path} 中没有数据，创建空表")
                    self.vehicles_data = pd.DataFrame(columns=[
                        "vehicle_id", "vehicle_license_plate", "vehicle_driver_name", 
                        "vehicle_type", "vehicle_belonged_cp", "vehicle_status",
                        "vehicle_rough_weight", "vehicle_tare_weight", "vehicle_net_weight",
                        "vehicle_last_use", "vehicle_cooldown_days", "vehicle_historys", "vehicle_other_info"
                    ])
                    self.xlsx_viewer.load_data(data=self.vehicles_data)
            except Exception as e:
                LOGGER.warning(f"从OSS加载数据失败，创建空表: {str(e)}")
                # 创建空DataFrame
                self.vehicles_data = pd.DataFrame(columns=[
                    "vehicle_id", "vehicle_license_plate", "vehicle_driver_name", 
                    "vehicle_type", "vehicle_belonged_cp", "vehicle_status",
                    "vehicle_rough_weight", "vehicle_tare_weight", "vehicle_net_weight",
                    "vehicle_last_use", "vehicle_cooldown_days", "vehicle_historys", "vehicle_other_info"
                ])
                self.xlsx_viewer.load_data(data=self.vehicles_data)
                
        except Exception as e:
            LOGGER.error(f"加载车辆数据时出错: {str(e)}")
            QMessageBox.critical(self, "加载失败", f"加载车辆数据时出错: {str(e)}")
    
    def add_vehicle(self):
        """添加新车辆"""
        try:
            if not self.current_cp:
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
                
            # 显示添加对话框
            dialog = VehicleAddDialog(self)
            if dialog.exec_() == QDialog.Accepted:
                vehicle_info = dialog.get_vehicle_info()
                if vehicle_info:
                    # 检查车牌号是否已存在
                    if self.vehicles_data is not None and not self.vehicles_data.empty:
                        existing_plate = self.vehicles_data[
                            self.vehicles_data['vehicle_license_plate'] == vehicle_info['vehicle_license_plate']
                        ]
                        if not existing_plate.empty:
                            QMessageBox.warning(
                                self, 
                                "车牌号重复", 
                                f"车牌号 {vehicle_info['vehicle_license_plate']} 已存在，请检查输入"
                            )
                            return
                    # 设置所属CP
                    vehicle_info["vehicle_belonged_cp"] = self.current_cp['cp_id']
                    
                    # 创建Vehicle实例并生成其他字段
                    try:
                        vehicle = Vehicle(vehicle_info)
                        
                        # 先生成ID
                        vehicle._generate_id()
                        
                        # 检查ID是否已存在
                        if self.vehicles_data is not None and not self.vehicles_data.empty and 'vehicle_id' in self.vehicles_data.columns:
                            existing_id = self.vehicles_data[
                                self.vehicles_data['vehicle_id'] == vehicle.inst.vehicle_id
                            ]
                            if not existing_id.empty:
                                QMessageBox.warning(
                                    self, 
                                    "车辆ID重复", 
                                    f"生成的车辆ID {vehicle.inst.vehicle_id} 已存在，可能是相同车牌号和司机姓名组合"
                                )
                                return
                        
                        # 继续生成其他字段
                        vehicle.generate()
                        
                        LOGGER.info(f"已创建新车辆: {str(vehicle)}")
                        
                        vehicle_info = vehicle.to_dict()
                        # 更新数据
                        if self.vehicles_data is None:
                            # 如果没有数据，创建新DataFrame
                            self.vehicles_data = pd.DataFrame([vehicle_info])
                        else:
                            # 添加到现有数据
                            self.vehicles_data = pd.concat([self.vehicles_data, pd.DataFrame([vehicle_info])], ignore_index=True)
                        
                        # 更新UI
                        self.xlsx_viewer.load_data(data=self.vehicles_data)
                        
                        QMessageBox.information(self, "添加成功", f"已成功添加车辆: {vehicle_info['vehicle_license_plate']}")
                    except Exception as e:
                        LOGGER.error(f"生成车辆信息时出错: {str(e)}")
                        QMessageBox.critical(self, "添加失败", f"生成车辆信息时出错: {str(e)}")
                        
        except Exception as e:
            LOGGER.error(f"添加车辆时出错: {str(e)}")
            QMessageBox.critical(self, "添加失败", f"添加车辆时出错: {str(e)}")
    
    def save_to_oss(self):
        """保存车辆数据到OSS"""
        try:
            if not self.current_cp:
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
                
            if self.vehicles_data is None or self.vehicles_data.empty:
                QMessageBox.warning(self, "没有数据", "没有车辆数据可以保存")
                return
                
            # 获取当前数据
            current_data = self.xlsx_viewer.get_data()
            
            # 确认保存
            reply = QMessageBox.question(
                self, '确认保存', 
                f'确定要将当前车辆数据保存到OSS路径 {self.oss_path} 吗？',
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 保存到临时文件
                import tempfile
                import os
                import datetime
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_dir = tempfile.gettempdir()
                temp_file = os.path.join(temp_dir, f"vehicles_{self.current_cp['cp_id']}_{timestamp}.xlsx")
                
                # 保存到临时文件
                current_data.to_excel(temp_file, index=False)
                self.temp_files.append(temp_file)  # 记录临时文件，用于清理
                
                # 上传到OSS
                LOGGER.info(f"正在将车辆数据上传到OSS: {self.oss_path}")
                oss_put_excel_file(self.oss_path, current_data)
                
                QMessageBox.information(self, "保存成功", f"车辆数据已成功保存到OSS路径: {self.oss_path}")
                LOGGER.info(f"车辆数据已成功保存到OSS路径: {self.oss_path}")
                
        except Exception as e:
            LOGGER.error(f"保存车辆数据到OSS时出错: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存车辆数据到OSS时出错: {str(e)}")
    
    def download_template(self):
        """下载车辆模板文件"""
        try:
            # 获取保存位置
            save_path, _ = QFileDialog.getSaveFileName(
                self, "保存车辆模板文件", "vehicle_template.xlsx", "Excel文件 (*.xlsx)"
            )
            
            if not save_path:
                return  # 用户取消
            
            # 获取车辆模板文件路径
            template_path = "CPs/template/vehicle_template.xlsx"
            try:
                file = oss_get_excel_file(template_path)
                if file is not None:
                    file.to_excel(save_path, index=False)
                    QMessageBox.information(self, "下载成功", f"车辆模板文件已保存到: {save_path}")
                    LOGGER.info(f"车辆模板文件已下载到: {save_path}")
                else:
                    QMessageBox.warning(self, "模板文件不存在", f"OSS中未找到车辆模板文件: {template_path}")
                    LOGGER.warning(f"OSS中未找到车辆模板文件: {template_path}")
            except Exception as e:
                LOGGER.error(f"下载车辆模板文件时出错: {str(e)}")
                QMessageBox.critical(self, "下载失败", f"下载车辆模板文件时出错: {str(e)}")
                
        except Exception as e:
            LOGGER.error(f"下载车辆模板时出错: {str(e)}")
            QMessageBox.critical(self, "下载失败", f"下载车辆模板时出错: {str(e)}")
    
    def batch_upload(self):
        """批量上传车辆数据"""
        try:
            if not self.current_cp:
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
                
            # 选择Excel文件
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择Excel文件", "", "Excel文件 (*.xlsx *.xls)"
            )
            
            if not file_path:
                return  # 用户取消
                
            # 读取Excel文件
            import pandas as pd
            try:
                upload_data = pd.read_excel(file_path)
                
                # 获取列名映射关系
                reverse_mapping = {v: k for k, v in self.xlsx_viewer.column_mapping.items() if k.startswith('vehicle_')}
                
                # 检查并转换中文列名到英文字段名
                columns_to_rename = {}
                for col in upload_data.columns:
                    if col in reverse_mapping:
                        columns_to_rename[col] = reverse_mapping[col]
                
                # 如果有需要重命名的列，进行重命名
                if columns_to_rename:
                    upload_data = upload_data.rename(columns=columns_to_rename)
                
                # 检查数据
                if upload_data.empty:
                    QMessageBox.warning(self, "数据为空", "上传的Excel文件中没有数据")
                    return
                    
                # 使用Vehicle类的批量验证方法验证数据
                from app.services.instances.vehicle import Vehicle
                valid_records, invalid_records = Vehicle.batch_validate(
                    upload_data.to_dict('records'), 
                    self.current_cp['cp_id'],
                    self.vehicles_data  # 传递现有车辆数据
                )
                
                # 如果有无效记录，显示警告
                if invalid_records:
                    invalid_msg = "\n".join([f"行 {i+1}: {reason}" for i, (_, reason) in enumerate(invalid_records)])
                    QMessageBox.warning(
                        self, 
                        "数据验证警告", 
                        f"以下 {len(invalid_records)} 条记录无效，将被跳过:\n{invalid_msg}"
                    )
                
                # 如果没有有效记录，退出
                if not valid_records:
                    QMessageBox.warning(self, "无有效数据", "上传的Excel文件中没有有效的车辆数据")
                    return
                
                # 批量生成车辆对象并添加到现有数据
                new_vehicles = []
                skipped_count = 0
                for i, record in enumerate(valid_records):
                    try:
                        # 设置所属CP
                        record["vehicle_belonged_cp"] = self.current_cp['cp_id']
                        
                        # 创建Vehicle实例
                        vehicle = Vehicle(record)
                        
                        # 先生成ID
                        vehicle._generate_id()
                        
                        # 检查车牌号是否已存在（在现有数据和已处理的新车辆中）
                        existing_plates = []
                        if self.vehicles_data is not None and not self.vehicles_data.empty:
                            existing_plates.extend(self.vehicles_data['vehicle_license_plate'].tolist())
                        existing_plates.extend([v['vehicle_license_plate'] for v in new_vehicles])
                        
                        if record.get('vehicle_license_plate') in existing_plates:
                            LOGGER.warning(f"第{i+1}行车牌号 {record.get('vehicle_license_plate')} 已存在，跳过")
                            skipped_count += 1
                            continue
                        
                        # 检查ID是否已存在（在现有数据和已处理的新车辆中）
                        existing_ids = []
                        if self.vehicles_data is not None and not self.vehicles_data.empty and 'vehicle_id' in self.vehicles_data.columns:
                            existing_ids.extend(self.vehicles_data['vehicle_id'].tolist())
                        existing_ids.extend([v['vehicle_id'] for v in new_vehicles])
                        
                        if vehicle.inst.vehicle_id in existing_ids:
                            LOGGER.warning(f"第{i+1}行生成的车辆ID {vehicle.inst.vehicle_id} 已存在，跳过")
                            skipped_count += 1
                            continue
                        
                        # 继续生成其他字段
                        vehicle.generate()
                        new_vehicles.append(vehicle.to_dict())
                        
                    except Exception as e:
                        LOGGER.error(f"处理第{i+1}行车辆数据时出错: {str(e)}")
                        skipped_count += 1
                        continue
                
                # 添加到现有数据
                if self.vehicles_data is None:
                    self.vehicles_data = pd.DataFrame(new_vehicles)
                else:
                    self.vehicles_data = pd.concat([self.vehicles_data, pd.DataFrame(new_vehicles)], ignore_index=True)
                
                # 更新UI
                self.xlsx_viewer.load_data(data=self.vehicles_data)
                
                # 计算跳过的数量提示
                success_msg = f"成功添加 {len(new_vehicles)} 条车辆记录"
                if skipped_count > 0:
                    success_msg += f"，跳过 {skipped_count} 条重复或无效记录"
                success_msg += "，请点击「保存到OSS」按钮保存更改"
                
                QMessageBox.information(
                    self, 
                    "上传成功", 
                    f"成功添加 {len(new_vehicles)} 条车辆记录，请点击「保存到OSS」按钮保存更改"
                )
                
            except Exception as e:
                LOGGER.error(f"处理上传文件时出错: {str(e)}")
                QMessageBox.critical(self, "处理失败", f"处理上传文件时出错: {str(e)}")
                
        except Exception as e:
            LOGGER.error(f"批量上传车辆数据时出错: {str(e)}")
            QMessageBox.critical(self, "上传失败", f"批量上传车辆数据时出错: {str(e)}")
    
    def delete_vehicle(self):
        """删除选中的车辆"""
        try:
            if not self.current_cp:
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
                
            if self.vehicles_data is None or self.vehicles_data.empty:
                QMessageBox.warning(self, "没有数据", "没有车辆数据可以删除")
                return
            
            # 获取当前选中的行索引
            selected_rows = self.xlsx_viewer.table_view.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(self, "未选择车辆", "请先选择要删除的车辆")
                return
            
            # 获取选中的行索引
            row_indices = [index.row() for index in selected_rows]
            
            # 获取选中车辆的车牌号用于显示
            selected_plates = []
            for idx in row_indices:
                if idx < len(self.vehicles_data):
                    plate = self.vehicles_data.iloc[idx].get('vehicle_license_plate', f'未知车辆 #{idx}')
                    selected_plates.append(plate)
            
            # 确认删除
            plates_text = "\n".join(selected_plates)
            reply = QMessageBox.question(
                self, '确认删除', 
                f'确定要删除以下车辆吗？删除后需点击「保存到OSS」按钮同步更改。\n\n{plates_text}',
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # 从DataFrame中删除选中的行
                self.vehicles_data = self.vehicles_data.drop(self.vehicles_data.index[row_indices]).reset_index(drop=True)
                
                # 更新UI
                self.xlsx_viewer.load_data(data=self.vehicles_data)
                
                QMessageBox.information(
                    self, 
                    "删除成功", 
                    f"已成功删除 {len(row_indices)} 辆车，请点击「保存到OSS」按钮同步更改到OSS"
                )
                
                LOGGER.info(f"已删除 {len(row_indices)} 辆车: {', '.join(selected_plates)}")
                
        except Exception as e:
            LOGGER.error(f"删除车辆时出错: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"删除车辆时出错: {str(e)}")
    
    def update_cp(self, cp_id):
        """更新CP选择按钮的文本并更新车辆列表"""
        try:
            if cp_id:
                # 尝试从OSS获取CP信息
                cp = CP.get_by_id(cp_id)
                if cp:
                    cp_name = cp.inst.cp_name
                    self.cp_button.setText(f"已选择CP为：{cp_name}")
                    
                    # 保存到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', {})
                    
                    # 从CP实例创建字典
                    cp_data = {}
                    for key, value in cp.inst.__dict__.items():
                        if not key.startswith('_'):
                            cp_data[key] = value
                    
                    CONF.runtime.CP = cp_data
                    self.current_cp = cp_data
                    
                    # 启用按钮
                    self.add_vehicle_button.setEnabled(True)
                    self.save_to_oss_button.setEnabled(True)
                    self.batch_upload_button.setEnabled(True)
                    self.delete_vehicle_button.setEnabled(True)
                    
                    # 加载车辆数据
                    self.load_vehicles_data()
                else:
                    LOGGER.error(f"未找到ID为{cp_id}的CP")
                    self.cp_button.setText("未选择CP")
                    self.add_vehicle_button.setEnabled(False)
                    self.save_to_oss_button.setEnabled(False)
                    self.batch_upload_button.setEnabled(False)
                    self.delete_vehicle_button.setEnabled(False)
            else:
                self.cp_button.setText("未选择CP")
                self.add_vehicle_button.setEnabled(False)
                self.save_to_oss_button.setEnabled(False)
                self.batch_upload_button.setEnabled(False)
                self.delete_vehicle_button.setEnabled(False)
        except Exception as e:
            LOGGER.error(f"更新CP时出错: {str(e)}")
            self.cp_button.setText("未选择CP")
            self.add_vehicle_button.setEnabled(False)
            self.save_to_oss_button.setEnabled(False)
            self.batch_upload_button.setEnabled(False)
            self.delete_vehicle_button.setEnabled(False)
