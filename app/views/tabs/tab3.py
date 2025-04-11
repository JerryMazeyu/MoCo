from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QFrame, QComboBox, QGroupBox, QFileDialog, 
                             QMessageBox, QDialog, QTabWidget)
from PyQt5.QtGui import QPixmap
from app.utils.logger import get_logger
from app.services.instances.restaurant import Restaurant, RestaurantsGroup
from app.services.instances.vehicle import Vehicle, VehicleGroup
from app.services.functions.get_receive_record_service import GetReceiveRecordService
from app.services.instances.cp import CP
from app.config.config import CONF
from app.models.receive_record import ReceiveRecordModel
import oss2
from app.views.tabs.tab2 import CPSelectDialog
from app.views.components.xlsxviewer import XlsxViewerWidget  # 导入 XlsxViewerWidget
from app.utils import rp, oss_get_excel_file,oss_put_excel_file,oss_rename_excel_file
import pandas as pd
from PyQt5.QtCore import Qt

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
        self.xlsx_viewer = None  # 初始化为 None
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
        
        # 创建步骤状态布局和按钮布局的容器
        steps_and_buttons_layout = QHBoxLayout()
        
        # 创建左侧的垂直布局，用于放置第一步的状态和按钮
        step1_layout = QVBoxLayout()
        self.step1_status = QLabel()
        self.set_step_image(self.step1_status, "unfinish.png")
        step1_layout.addWidget(self.step1_status, alignment=Qt.AlignCenter)
        self.load_restaurants_button = QPushButton("上传餐厅信息")
        self.load_restaurants_button.clicked.connect(self.upload_restaurant_file)
        self.load_restaurants_button.setEnabled(False)
        self.load_restaurants_button.setFixedWidth(100)
        step1_layout.addWidget(self.load_restaurants_button, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addLayout(step1_layout)
        
        # 添加箭头1
        arrow1 = QLabel("→")
        steps_and_buttons_layout.addWidget(arrow1, alignment=Qt.AlignCenter)
        
        # 创建中间的垂直布局，用于放置第二步的状态和按钮
        step2_layout = QVBoxLayout()
        self.step2_status = QLabel()
        self.set_step_image(self.step2_status, "unfinish.png")
        step2_layout.addWidget(self.step2_status, alignment=Qt.AlignCenter)
        self.load_vehicles_button = QPushButton("载入车辆信息")
        self.load_vehicles_button.clicked.connect(self.load_vehicles)
        self.load_vehicles_button.setEnabled(False)
        self.load_vehicles_button.setFixedWidth(100)
        step2_layout.addWidget(self.load_vehicles_button, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addLayout(step2_layout)
        
        # 添加箭头2
        arrow2 = QLabel("→")
        steps_and_buttons_layout.addWidget(arrow2, alignment=Qt.AlignCenter)
        
        # 创建右侧的垂直布局，用于放置第三步的状态和按钮
        step3_layout = QVBoxLayout()
        self.step3_status = QLabel()
        self.set_step_image(self.step3_status, "unfinish.png")
        step3_layout.addWidget(self.step3_status, alignment=Qt.AlignCenter)
        self.generate_report_button = QPushButton("生成收油表")
        self.generate_report_button.clicked.connect(self.generate_report)
        self.generate_report_button.setEnabled(False)
        self.generate_report_button.setFixedWidth(100)
        step3_layout.addWidget(self.generate_report_button, alignment=Qt.AlignCenter)
        steps_and_buttons_layout.addLayout(step3_layout)
        
        # 添加弹性空间
        steps_and_buttons_layout.addStretch()
        
        # 将步骤和按钮的布局添加到主布局
        self.layout.addLayout(steps_and_buttons_layout)
        
        # 创建带有页签的数据展示区
        self.tab_widget = QTabWidget()
        
        # 初始化XlsxViewerWidget实例为None
        self.restaurant_viewer = None
        self.vehicle_viewer = None
        self.report_viewer = None
        
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
            # 获取配置中的CP ID列表 - 直接使用CONF.BUSINESS.CP，因为它就是一个ID列表
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
                    
                    # 获取配置中的CP ID列表 - 直接使用CONF.BUSINESS.CP，因为它就是一个ID列表
                    conf_cp_ids = []
                    if hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                        conf_cp_ids = CONF.BUSINESS.CP.cp_id  # 直接使用列表
                    
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
                    self.restaurant_file = f"CPs/{cp_data['cp_id']}/restaurant/restaurants.xlsx"
                    self.vehicle_file = f"CPs/{cp_data['cp_id']}/vehicle/vehicles.xlsx"
                    self.receive_record_file = f"CPs/{cp_data['cp_id']}/receive_record/receive_records.xlsx"
                    
                    # 在选择CP后创建XlsxViewerWidget实例
                    self.restaurant_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.restaurant_file)
                    self.vehicle_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.vehicle_file)
                    self.report_viewer = XlsxViewerWidget(use_oss=True, oss_path=self.receive_record_file)
                    
                    # 将XlsxViewerWidget实例添加到tab_widget
                    self.tab_widget.addTab(self.restaurant_viewer, "餐厅信息")
                    self.tab_widget.addTab(self.vehicle_viewer, "车辆信息")
                    self.tab_widget.addTab(self.report_viewer, "收油表")
                    
                    # 更新CP按钮文本
                    self.cp_button.setText(f"已选择CP为：{cp_data['cp_name']}")
                    
                    # 通知主窗口更新CP
                    if self.main_window_ref:
                        self.main_window_ref.set_current_cp(cp_data['cp_id'])
                    
                    # 启用第一步按钮，禁用后续按钮
                    self.load_restaurants_button.setEnabled(True)
                    self.load_vehicles_button.setEnabled(False)
                    self.generate_report_button.setEnabled(False)
                    
                    # 重置所有步骤状态
                    self.update_step_status(1, 'unfinish')
                    self.update_step_status(2, 'unfinish')
                    self.update_step_status(3, 'unfinish')
                
        except Exception as e:
            LOGGER.error(f"选择CP时出错: {str(e)}")
            LOGGER.error(f"CONF.BUSINESS.CP的内容: {getattr(CONF.BUSINESS, 'CP', None)}")
            QMessageBox.critical(self, "选择CP失败", f"选择CP时出错: {str(e)}")
    
    def set_step_image(self, label, image_name):
        """设置步骤状态图片"""
        pixmap = QPixmap(f"app/resources/icons/{image_name}")  # 修改图片路径
        scaled_pixmap = pixmap.scaled(24, 24)  # 设置图片大小
        label.setPixmap(scaled_pixmap)

    def update_step_status(self, step, status):
        """更新步骤状态
        step: 1, 2, 3 表示哪一步
        status: 'dealing', 'finish', 'error', 'unfinish'
        """
        status_label = getattr(self, f"step{step}_status")
        self.set_step_image(status_label, f"{status}.png")
        
        # 更新按钮状态
        if status == 'finish':
            if step == 1:
                self.load_vehicles_button.setEnabled(True)
            elif step == 2:
                self.generate_report_button.setEnabled(True)
        elif status == 'error':
            # 如果当前步骤失败，禁用后续步骤
            if step == 1:
                self.load_vehicles_button.setEnabled(False)
                self.generate_report_button.setEnabled(False)
            elif step == 2:
                self.generate_report_button.setEnabled(False)

    ## 从oss载入餐厅
    def load_restaurants(self):
        """载入餐厅信息"""
        self.update_step_status(1, 'dealing')
        try:
            if not hasattr(self, 'restaurant_file'):
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 从OSS读取数据
            try:
                restaurant_data = oss_get_excel_file(self.restaurant_file)
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
            self.restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dicts()
            filter_restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dataframe()
            # 将数据加载到餐厅信息页签
            self.restaurant_viewer.load_data(data=filter_restaurants)
            
            # 切换到餐厅信息页签
            self.tab_widget.setCurrentIndex(0)
            
            self.logger.info(f"成功载入餐厅信息，共 {len(self.restaurants)} 条记录")
            self.update_step_status(1, 'finish')
        except Exception as e:
            self.logger.error(f"载入餐厅信息时出错: {str(e)}")
            QMessageBox.critical(self, "载入失败", f"载入餐厅信息时出错: {str(e)}")
            self.update_step_status(1, 'error')
    
    def load_vehicles(self):
        """载入车辆信息"""
        self.update_step_status(2, 'dealing')
        try:
            if not hasattr(self, 'vehicle_file'):
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 从OSS读取数据
            try:
                vehicle_data = oss_get_excel_file(self.vehicle_file)
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
            self.vehicles = vehicles_group.filter_by_cp(self.current_cp['cp_id']).to_dicts()
            filter_vehicles = vehicles_group.filter_by_cp(self.current_cp['cp_id']).to_dataframe()
            # 将数据加载到车辆信息页签
            self.vehicle_viewer.load_data(data=filter_vehicles)
            
            # 切换到车辆信息页签
            self.tab_widget.setCurrentIndex(1)
            
            self.logger.info(f"成功载入车辆信息，共 {len(self.vehicles)} 条记录")
            self.update_step_status(2, 'finish')
        except Exception as e:
            self.logger.error(f"载入车辆信息时出错: {str(e)}")
            QMessageBox.critical(self, "载入失败", f"载入车辆信息时出错: {str(e)}")
            self.update_step_status(2, 'error')
    
    def generate_report(self):
        """生成收油表"""
        self.update_step_status(3, 'dealing')
        try:
            service = GetReceiveRecordService(model=ReceiveRecordModel, conf=CONF)
            result, cp_restaurants_df, cp_vehicle_df = service.get_restaurant_oil_records(self.restaurants, self.vehicles, self.current_cp['cp_id'])
            
            # 将结果加载到收油表页签
            self.report_viewer.load_data(data=result)
            
            # 切换到收油表页签
            self.tab_widget.setCurrentIndex(2)
            
            self.logger.info("收油表生成成功")
            self.update_step_status(3, 'finish')
        except Exception as e:
            self.logger.error(f"生成收油表时出错: {str(e)}")
            QMessageBox.critical(self, "生成失败", f"生成收油表时出错: {str(e)}")
            self.update_step_status(3, 'error')
    
    def upload_restaurant_file(self):
        """上传餐厅信息文件"""
        if not hasattr(self, 'vehicle_file'):
            QMessageBox.warning(self, "未选择CP", "请先选择CP")
            return
        
        self.update_step_status(1, 'dealing')
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "选择餐厅信息文件", "", "Excel Files (*.xlsx);;All Files (*)", options=options)
        if file_name:
            try:
            # 直接使用pandas读取本地Excel文件
                restaurant_data = pd.read_excel(file_name)
                if restaurant_data.empty:
                    QMessageBox.warning(self, "文件为空", "所选文件没有数据")
                    self.update_step_status(1, 'error')
                    return
                
                # 转换为Restaurant对象列表
                self.restaurants = [Restaurant(info) for info in restaurant_data.to_dict('records')]
                
                # 使用RestaurantsGroup进行过滤
                restaurants_group = RestaurantsGroup(self.restaurants)
                self.restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dicts()
                filter_restaurants = restaurants_group.filter_by_cp(self.current_cp['cp_id']).to_dataframe()
                
                # 将数据加载到餐厅信息页签
                self.restaurant_viewer.load_data(data=filter_restaurants)
                
                # 切换到餐厅信息页签
                self.tab_widget.setCurrentIndex(0)
                

                
                self.logger.info(f"成功载入餐厅信息，共 {len(self.restaurants)} 条记录")
                self.update_step_status(1, 'finish')
            except Exception as e:
                self.logger.error(f"上传餐厅信息时出错: {str(e)}")
                QMessageBox.critical(self, "上传失败", f"上传餐厅信息时出错: {str(e)}")
                self.update_step_status(1, 'error')

