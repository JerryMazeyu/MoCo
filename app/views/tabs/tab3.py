from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QComboBox, QGroupBox, QFileDialog, 
                             QMessageBox, QDialog, QTabWidget)
from app.utils.logger import get_logger
from app.services.instances.restaurant import Restaurant, RestaurantsGroup
from app.services.instances.vehicle import Vehicle, VehicleGroup
from app.services.functions.get_receive_record_service import GetReceiveRecordService
from app.services.instances.cp import CP
from app.config.config import CONF
import oss2
from app.views.tabs.tab2 import CPSelectDialog
from app.views.components.xlsxviewer import XlsxViewerWidget  # 导入 XlsxViewerWidget

# 获取全局日志对象
LOGGER = get_logger()

class Tab3(QWidget):
    """收油表生成Tab，实现餐厅和车辆信息的加载与收油表生成"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent
        self.current_cp = None
        self.restaurants = []
        self.vehicles = []
        self.xlsx_viewer = XlsxViewerWidget()  # 创建 XlsxViewerWidget 实例
        self.initUI()
    
    def initUI(self):
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        
        # 顶部布局 - 包含CP选择按钮
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # CP选择按钮
        self.cp_button = QPushButton("未选择CP")
        self.cp_button.clicked.connect(self.select_cp)
        self.cp_button.setFixedWidth(150)
        
        top_layout.addStretch(1)
        top_layout.addWidget(self.cp_button)
        
        self.layout.addLayout(top_layout)
        
        # 按钮区
        button_layout = QHBoxLayout()
        
        self.load_restaurants_button = QPushButton("载入餐厅信息")
        self.load_restaurants_button.clicked.connect(self.load_restaurants)
        self.load_restaurants_button.setEnabled(False)
        
        self.load_vehicles_button = QPushButton("载入车辆信息")
        self.load_vehicles_button.clicked.connect(self.load_vehicles)
        self.load_vehicles_button.setEnabled(False)
        
        self.generate_report_button = QPushButton("生成收油表")
        self.generate_report_button.clicked.connect(self.generate_report)
        self.generate_report_button.setEnabled(False)
        
        button_layout.addWidget(self.load_restaurants_button)
        button_layout.addWidget(self.load_vehicles_button)
        button_layout.addWidget(self.generate_report_button)
        
        self.layout.addLayout(button_layout)
        
        # 创建带有页签的数据展示区
        self.tab_widget = QTabWidget()
        
        # 创建三个XlsxViewerWidget实例
        self.restaurant_viewer = XlsxViewerWidget()
        self.vehicle_viewer = XlsxViewerWidget()
        self.report_viewer = XlsxViewerWidget()
        
        # 直接添加XlsxViewerWidget到页签
        self.tab_widget.addTab(self.restaurant_viewer, "餐厅信息")
        self.tab_widget.addTab(self.vehicle_viewer, "车辆信息")
        self.tab_widget.addTab(self.report_viewer, "收油表")
        
        self.layout.addWidget(self.tab_widget)
        
        # 获取全局日志对象
        self.logger = get_logger()
    
    def select_cp(self):
        """选择/切换CP"""
        try:
            # 获取OSS上的CP列表
            cp_list = CP.list()
            
            if not cp_list:
                QMessageBox.warning(self, "CP列表为空", "未找到任何CP数据，请先添加CP。")
                return
            
            # 显示CP选择对话框
            dialog = CPSelectDialog(cp_list, self)
            if dialog.exec_() == QDialog.Accepted:
                selected_cp = dialog.get_selected_cp()
                if selected_cp:
                    # 将列表中的字典转换为对象
                    cp_data = {
                        'cp_id': selected_cp['cp_id'] if isinstance(selected_cp, dict) else selected_cp.cp_id,
                        'cp_name': selected_cp['cp_name'] if isinstance(selected_cp, dict) else selected_cp.cp_name
                    }
                    
                    # 获取配置中的CP ID列表 - 直接使用CONF.BUSINESS.CP，因为它就是一个ID列表
                    conf_cp_ids = []
                    if hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                        conf_cp_ids = CONF.BUSINESS.CP  # 直接使用列表
                    
                    LOGGER.info(f"配置中的CP ID列表: {conf_cp_ids}")
                    
                    if cp_data['cp_id'] in conf_cp_ids:
                        LOGGER.info(f"选择的CP {cp_data['cp_name']} (ID: {cp_data['cp_id']}) 在配置中存在")
                    else:
                        LOGGER.warning(f"选择的CP {cp_data['cp_name']} (ID: {cp_data['cp_id']}) 不在配置中")
                        reply = QMessageBox.question(
                            self, 'CP不在配置中', 
                            f'选择的CP "{cp_data["cp_name"]}" 不在配置列表中。是否继续使用？',
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                        )
                        if reply == QMessageBox.No:
                            return
                    
                    # 保存选择的CP到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                    
                    CONF.runtime.CP = cp_data
                    self.current_cp = cp_data
                    
                    # 生成文件路径
                    self.restaurant_file = f"CPs/{cp_data['cp_id']}/restaurants.xlsx"
                    self.vehicle_file = f"CPs/{cp_data['cp_id']}/vehicles.xlsx"
                    
                    # 更新CP按钮文本
                    self.cp_button.setText(f"已选择CP为：{cp_data['cp_name']}")
                    
                    # 通知主窗口更新CP
                    if self.main_window_ref:
                        self.main_window_ref.set_current_cp(cp_data['cp_id'])
                    
                    # 启用相关按钮
                    self.load_restaurants_button.setEnabled(True)
                    self.load_vehicles_button.setEnabled(True)
                    self.generate_report_button.setEnabled(True)
                
        except Exception as e:
            LOGGER.error(f"选择CP时出错: {str(e)}")
            LOGGER.error(f"CONF.BUSINESS.CP的内容: {getattr(CONF.BUSINESS, 'CP', None)}")
            QMessageBox.critical(self, "选择CP失败", f"选择CP时出错: {str(e)}")
    
    def load_restaurants(self):
        """载入餐厅信息"""
        try:
            if not hasattr(self, 'restaurant_file'):
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 从OSS读取数据
            try:
                restaurant_data = self.read_from_oss(self.restaurant_file)
                if restaurant_data is None:
                    QMessageBox.warning(self, "文件不存在", f"未找到文件: {self.restaurant_file}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "读取失败", f"从OSS读取餐厅信息失败: {str(e)}")
                return
            
            # 转换为Restaurant对象列表
            self.restaurants = [Restaurant(info) for info in restaurant_data.to_dict('records')]
            
            # 使用RestaurantsGroup进行过滤
            restaurants_group = RestaurantsGroup(self.restaurants)
            self.restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_list()
            
            # 将数据加载到餐厅信息页签
            self.restaurant_viewer.load_data(data=restaurant_data)
            
            # 切换到餐厅信息页签
            self.tab_widget.setCurrentIndex(0)
            
            self.logger.info(f"成功载入餐厅信息，共 {len(self.restaurants)} 条记录")
        except Exception as e:
            self.logger.error(f"载入餐厅信息时出错: {str(e)}")
            QMessageBox.critical(self, "载入失败", f"载入餐厅信息时出错: {str(e)}")
    
    def load_vehicles(self):
        """载入车辆信息"""
        try:
            if not hasattr(self, 'vehicle_file'):
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 从OSS读取数据
            try:
                vehicle_data = self.read_from_oss(self.vehicle_file)
                if vehicle_data is None:
                    QMessageBox.warning(self, "文件不存在", f"未找到文件: {self.vehicle_file}")
                    return
            except Exception as e:
                QMessageBox.critical(self, "读取失败", f"从OSS读取车辆信息失败: {str(e)}")
                return
            
            # 转换为Vehicle对象列表
            self.vehicles = [Vehicle(info) for info in vehicle_data.to_dict('records')]
            
            # 使用VehicleGroup进行过滤
            vehicles_group = VehicleGroup(self.vehicles)
            self.vehicles = vehicles_group.filter_by_cp(self.current_cp['cp_id']).to_list()
            
            # 将数据加载到车辆信息页签
            self.vehicle_viewer.load_data(data=vehicle_data)
            
            # 切换到车辆信息页签
            self.tab_widget.setCurrentIndex(1)
            
            self.logger.info(f"成功载入车辆信息，共 {len(self.vehicles)} 条记录")
        except Exception as e:
            self.logger.error(f"载入车辆信息时出错: {str(e)}")
            QMessageBox.critical(self, "载入失败", f"载入车辆信息时出错: {str(e)}")
    
    def generate_report(self):
        """生成收油表"""
        try:
            service = GetReceiveRecordService()
            result,cp_restaurants_df,cp_vehicle_df = service.get_restaurant_oil_records(self.restaurants, self.vehicles, self.current_cp['cp_id'])
            
            # 将结果加载到收油表页签
            self.report_viewer.load_data(data=result)
            
            # 切换到收油表页签
            self.tab_widget.setCurrentIndex(2)
            
            self.logger.info("收油表生成成功")
        except Exception as e:
            self.logger.error(f"生成收油表时出错: {str(e)}")
            QMessageBox.critical(self, "生成失败", f"生成收油表时出错: {str(e)}")
    
    def read_from_oss(self, file_path):
        """从OSS读取数据"""
        try:
            # 获取OSS配置
            if not hasattr(CONF, 'KEYS') or not hasattr(CONF.KEYS, 'oss'):
                raise Exception("未找到OSS配置")
            
            oss_conf = CONF.KEYS.oss
            access_key_id = oss_conf.get('access_key_id')
            access_key_secret = oss_conf.get('access_key_secret')
            endpoint = oss_conf.get('endpoint')
            bucket_name = oss_conf.get('bucket_name')
            region = oss_conf.get('region')
            
            if not all([access_key_id, access_key_secret, endpoint, bucket_name]):
                raise Exception("OSS配置不完整")
            
            # 创建OSS客户端
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
            
            # 检查文件是否存在
            if not bucket.object_exists(file_path):
                return None
            
            # 下载文件到临时目录
            import tempfile
            import os
            
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, os.path.basename(file_path))
            
            # 下载文件
            bucket.get_object_to_file(file_path, temp_file)
            
            # 读取Excel文件
            import pandas as pd
            data = pd.read_excel(temp_file)
            
            # 删除临时文件
            os.remove(temp_file)
            
            return data
        except Exception as e:
            self.logger.error(f"从OSS读取文件失败: {str(e)}")
            raise