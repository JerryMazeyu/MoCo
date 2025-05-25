import os
import sys
import tempfile
import json
import uuid
import subprocess
import time
import pandas as pd

# ============导入包============
import gc
import traceback
from datetime import datetime
from pathlib import Path
# ============导入包============

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFrame, QComboBox, QGroupBox, QGridLayout,
                            QFileDialog, QMessageBox, QLayout, QListWidget, QDialog, QLineEdit, 
                            QApplication, QCheckBox, QSpinBox, QRadioButton, QToolButton)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QThread, pyqtSignal, QEvent, QTimer
from PyQt5.QtGui import QColor, QIcon, QPixmap, QPainter
import pandas as pd
import random
import time
from app.views.components.xlsxviewer import XlsxViewerWidget
from app.views.components.singleton import global_context
from app.utils.logger import get_logger
from app.services.instances.restaurant import youdao_translate, kimi_restaurant_type_analysis
from app.services.instances.restaurant import query_gaode
from app.services.instances.cp import CP
from app.config.config import CONF
import oss2
from app.services.functions.get_restaurant_service import GetRestaurantService
from app.services.instances.restaurant import RestaurantModel, Restaurant, RestaurantsGroup
from app.utils import oss_get_excel_file, oss_put_excel_file
import concurrent.futures
import copy
import re
import shutil
# 获取全局日志对象
LOGGER = get_logger()




# 自定义流式布局类，用于自适应地排列API测试项
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)
        
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        
        self.setSpacing(spacing)
        
        self.itemList = []
    
    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)
    
    def addItem(self, item):
        self.itemList.append(item)
    
    def count(self):
        return len(self.itemList)
    
    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]
        return None
    
    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)
        return None
    
    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))
    
    def hasHeightForWidth(self):
        return True
    
    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height
    
    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)
    
    def sizeHint(self):
        return self.minimumSize()
    
    def minimumSize(self):
        size = QSize()
        
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
            
        margin = self.contentsMargins().left() + self.contentsMargins().right()
        margin += self.contentsMargins().top() + self.contentsMargins().bottom()
        
        size += QSize(margin, margin)
        return size
    
    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        
        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing() + wid.style().layoutSpacing(
                wid.sizePolicy().controlType(), 
                wid.sizePolicy().controlType(), 
                Qt.Horizontal
            )
            spaceY = self.spacing() + wid.style().layoutSpacing(
                wid.sizePolicy().controlType(), 
                wid.sizePolicy().controlType(), 
                Qt.Vertical
            )
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
                
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
            
        return y + lineHeight - rect.y()


class ApiTestWidget(QWidget):
    """API测试组件，用于测试各种API连接"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_status = {
            "高德API": False,
            "有道API": False,
            "KIMI API": False,
            "阿里OSS": False,
            "爱企查API": False
        }
        self.initUI()
    
    def initUI(self):
        # 使用流式布局，自动适应一行显示多少个API测试项
        self.layout = FlowLayout(self, margin=5, spacing=10)
        
        # 为每个API创建一个小的组合控件
        for api_name in self.api_status.keys():
            # 创建一个容器小部件来容纳每个API测试项的控件
            api_widget = QWidget()
            api_layout = QHBoxLayout(api_widget)
            api_layout.setContentsMargins(0, 0, 0, 0)
            api_layout.setSpacing(5)
            
            # 创建标签
            label = QLabel(api_name + ":")
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # 创建测试按钮
            test_button = QPushButton("测试")
            test_button.setProperty("api_name", api_name)
            test_button.clicked.connect(self.test_api)
            test_button.setFixedWidth(60)
            
            # 创建状态指示灯
            status_label = QLabel()
            status_label.setFixedSize(16, 16)
            self.update_status_light(status_label, None)
            
            # 保存状态指示灯引用
            setattr(self, f"{api_name.replace(' ', '_')}_light", status_label)
            
            # 添加到此API项的布局
            api_layout.addWidget(label)
            api_layout.addWidget(test_button)
            api_layout.addWidget(status_label)
            
            # 将整个API项添加到流式布局
            self.layout.addWidget(api_widget)
    
    def update_status_light(self, label, status):
        """更新状态指示灯"""
        # 确保在主线程执行UI更新
        if QApplication.instance().thread() != QThread.currentThread():
            # 如果在非主线程中调用，推迟到主线程执行
            QApplication.instance().postEvent(self, QEvent(QEvent.Type.User))
            return
            
        if status is None:
            color = QColor(150, 150, 150)  # 灰色，表示未测试
        elif status:
            color = QColor(0, 200, 0)  # 绿色，表示成功
        else:
            color = QColor(255, 0, 0)  # 红色，表示失败
        
        # 创建一个填充的圆形图标
        pixmap = QPixmap(QSize(16, 16))
        pixmap.fill(Qt.transparent)
        
        try:
            # 使用 QPainter 直接绘制
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(2, 2, 12, 12)
            painter.end()
            
            label.setPixmap(pixmap)
        except Exception as e:
            LOGGER.error(f"绘制状态指示灯失败: {str(e)}")
            # 创建一个备用的纯色pixmap以防绘制失败
            fallback = QPixmap(QSize(16, 16))
            fallback.fill(color)
            label.setPixmap(fallback)
    
    def test_api(self):
        """测试API连通性"""
        button = self.sender()
        if not button:
            return
        
        api_name = button.property("api_name")
        if not api_name:
            return
        
        LOGGER.info(f"正在测试 {api_name} 连通性...")
        
        success = False
        try:
            # 根据API类型进行相应的测试
            if api_name == "高德API":
                # 测试高德地图API
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'gaode_keys') and CONF.KEYS.gaode_keys:
                    key = CONF.KEYS.gaode_keys[0]
                    result = query_gaode(key, "北京")
                    success = result is not None and 'name' in result
                    LOGGER.info(f"高德API测试结果: {result}")
                else:
                    LOGGER.error("未找到高德地图API密钥")
            
            elif api_name == "有道API":
                # 测试有道翻译API
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'youdao_keys') and CONF.KEYS.youdao_keys:
                    key = CONF.KEYS.youdao_keys[0]
                    result = youdao_translate("测试文本", 'zh', 'en', key)
                    success = result is not None
                    LOGGER.info(f"有道API测试结果: {result}")
                else:
                    LOGGER.error("未找到有道翻译API密钥")
            
            elif api_name == "KIMI API":
                # 测试KIMI API
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'kimi_keys') and CONF.KEYS.kimi_keys:
                    key = CONF.KEYS.kimi_keys[0]
                    rest_info = {
                        'name': '测试餐厅',
                        'address': '北京市海淀区',
                        'rest_type': '中餐/快餐'
                    }
                    result = kimi_restaurant_type_analysis(rest_info, key)
                    success = result is not None
                    LOGGER.info(f"KIMI API测试结果: {result}")
                else:
                    LOGGER.error("未找到KIMI API密钥")
            
            elif api_name == "阿里OSS":
                # 测试阿里云OSS连接
                if hasattr(CONF, 'KEYS') and hasattr(CONF.KEYS, 'oss'):
                    oss_conf = CONF.KEYS.oss
                    access_key_id = oss_conf.get('access_key_id')
                    access_key_secret = oss_conf.get('access_key_secret')
                    endpoint = oss_conf.get('endpoint')
                    bucket_name = oss_conf.get('bucket_name')
                    region = oss_conf.get('region')
                    
                    if all([access_key_id, access_key_secret, endpoint, bucket_name]):
                        auth = oss2.Auth(access_key_id, access_key_secret)
                        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
                        # 尝试列出前缀为CPs的对象
                        result = list(oss2.ObjectIterator(bucket, prefix='CPs/', max_keys=1))
                        success = True  # 如果没有异常，则认为连接成功
                        LOGGER.info(f"阿里OSS测试结果: 成功")
                    else:
                        LOGGER.error("阿里云OSS配置不完整")
                else:
                    LOGGER.error("未找到阿里云OSS配置")
            
            elif api_name == "爱企查API":
                # 爱企查API测试 - 暂未实现，可以根据实际情况添加
                LOGGER.warning("爱企查API测试功能尚未实现")
                success = False
        
        except Exception as e:
            LOGGER.error(f"{api_name} 测试失败: {e}")
            success = False
        
        # 更新状态
        self.api_status[api_name] = success
        
        # 更新状态指示灯
        status_light = getattr(self, f"{api_name.replace(' ', '_')}_light", None)
        if status_light:
            self.update_status_light(status_light, success)
        
        # 输出结果
        result = "成功" if success else "失败"
        LOGGER.info(f"{api_name} 测试{result}")
        
        return success


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


# 餐厅获取工作线程类
class RestaurantWorker(QThread):
    # 定义信号
    finished = pyqtSignal(pd.DataFrame, str)  # 完成信号，携带查询结果和文件路径
    error = pyqtSignal(str)  # 错误信号，携带错误信息
    progress = pyqtSignal(str)  # 进度信号，用于实时更新进度
    
    def __init__(self, city, cp_id, use_llm=True, if_gen_info=False):
        super().__init__()
        # 预先导入必要的模块
        import tempfile
        import multiprocessing
        import os
        import datetime
        import gc
        from app.services.instances.restaurant import RestaurantModel, Restaurant, RestaurantsGroup 
        from app.services.functions.get_restaurant_service import GetRestaurantService
        
        self.city = city
        self.cp_id = cp_id
        self.use_llm = use_llm
        self.if_gen_info = if_gen_info
        self.running = True
        
        # 用于资源跟踪和清理的属性
        self._restaurant_service = None
        self._restaurant_group = None
        
        # 创建临时目录
        self.temp_dir = tempfile.gettempdir()
        
        # 动态调整线程数，根据系统CPU核心数
        # 使用CPU核心数的一半，但最少2个，最多4个
        self.num_workers = max(2, min(4, multiprocessing.cpu_count() // 2))
        LOGGER.info(f"设置工作线程数为: {self.num_workers}")
    
    def stop(self):
        """停止线程执行"""
        self.running = False
        
        # 强制中断当前线程中的长时间操作
        try:
            # 记录终止请求
            LOGGER.info("收到线程终止请求，正在强制停止...")
            
            # 尝试终止或清理进行中的任何操作
            import gc
            
            # 释放可能存在的大型对象引用，帮助垃圾回收
            if hasattr(self, '_restaurant_service') and self._restaurant_service:
                self._restaurant_service = None
                
            if hasattr(self, '_restaurant_group') and self._restaurant_group:
                self._restaurant_group = None
                
            # 强制执行垃圾回收
            gc.collect()
            
            # 发送取消信息到进度
            self.progress.emit("操作已被用户取消")
            
            # 在Python中不能真正"杀死"线程，但可以通过标志位和清理资源来让线程尽快退出
            LOGGER.info("线程资源已清理，等待线程自行退出...")
            
        except Exception as e:
            LOGGER.error(f"停止线程时出错: {str(e)}")
    
    def run(self):
        try:
            LOGGER.info(f"线程开始: 正在获取 {self.city} 的餐厅信息...")
            self.progress.emit(f"开始获取 {self.city} 的餐厅信息...")
            
            # 创建服务实例
            restaurant_service = GetRestaurantService()
            self._restaurant_service = restaurant_service  # 保存引用用于取消时清理
            
            # 检查线程是否仍在运行
            if not self.running:
                LOGGER.info("线程被用户中断")
                return
                
            # 获取基础餐厅信息
            self.progress.emit(f"正在从API获取餐厅基础信息...")
            try:
                restaurant_service.run(cities=self.city, cp_id=self.cp_id, model_class=RestaurantModel, 
                                      file_path=None, use_api=True, if_gen_info=self.if_gen_info, use_llm=self.use_llm)
            except Exception as e:
                LOGGER.error(f"获取餐厅基础信息时出错: {str(e)}")
                self.error.emit(f"获取餐厅基础信息时出错: {str(e)}")
                return
            
            # 检查是否有餐厅信息
            if not restaurant_service.restaurants:
                LOGGER.warning(f"未找到 {self.city} 的餐厅信息")
                self.error.emit(f"未找到 {self.city} 的餐厅信息")
                return
                
            restaurants_count = len(restaurant_service.restaurants)
            
            if self.if_gen_info:
                self.progress.emit(f"已找到 {restaurants_count} 家餐厅，正在生成详细信息...")
                
                # 为大量餐厅进行分批处理
                if restaurants_count > 500:
                    LOGGER.warning(f"餐厅数量过多 ({restaurants_count})，正在分批处理...")
                    self.progress.emit(f"餐厅数量较多 ({restaurants_count})，正在分批处理...")
                    
                    # 实现分批处理
                    batch_size = 200  # 每批处理200家餐厅
                    restaurant_group = restaurant_service.get_restaurants_group()
                    self._restaurant_group = restaurant_group  # 保存引用用于取消时清理
                    all_restaurants = restaurant_group.members.copy()
                    processed_restaurants = []
                    
                    for i in range(0, len(all_restaurants), batch_size):
                        if not self.running:
                            LOGGER.info("线程被用户中断")
                            break
                            
                        batch = all_restaurants[i:i+batch_size]
                        self.progress.emit(f"正在处理第 {i//batch_size + 1} 批 (共 {(len(all_restaurants)-1)//batch_size + 1} 批)...")
                        
                        # 为当前批次创建一个临时组
                        batch_group = RestaurantsGroup(batch, group_type=restaurant_group.group_type)
                        
                        try:
                            # 使用动态计算的线程数
                            batch_group = restaurant_service.gen_info(batch_group, num_workers=self.num_workers)
                            processed_restaurants.extend(batch_group.members)
                            
                            # 强制执行垃圾回收
                            import gc
                            gc.collect()
                            
                        except Exception as e:
                            LOGGER.error(f"处理批次 {i//batch_size + 1} 时出错: {str(e)}")
                            self.progress.emit(f"处理批次 {i//batch_size + 1} 时出错，但会继续处理")
                            # 添加未处理的批次数据，确保不丢失
                            processed_restaurants.extend(batch)
                    
                    # 创建最终结果
                    restaurant_group = RestaurantsGroup(processed_restaurants, group_type=restaurant_group.group_type)
                    self._restaurant_group = restaurant_group  # 更新引用
                    
                else:
                    # 对于小数据量，使用原始方法但调整线程数
                    restaurant_group = restaurant_service.get_restaurants_group()
                    self._restaurant_group = restaurant_group  # 保存引用用于取消时清理
                    self.progress.emit(f"使用 {self.num_workers} 个工作线程生成餐厅详细信息...")
                    restaurant_group = restaurant_service.gen_info(restaurant_group, num_workers=self.num_workers)
                    self._restaurant_group = restaurant_group  # 更新引用
            else:
                self.progress.emit(f"已找到 {restaurants_count} 家餐厅，跳过生成详细信息...")
                restaurant_group = restaurant_service.get_restaurants_group()
                self._restaurant_group = restaurant_group  # 保存引用
            
            # 检查线程是否仍在运行
            if not self.running:
                LOGGER.info("线程被用户中断")
                return
                
            # 转换为DataFrame并发送结果
            try:
                self.progress.emit(f"正在将餐厅信息转换为表格数据...")
                restaurant_data = restaurant_group.to_dataframe()
                
                # 保存完整数据到临时文件
                import os
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                file_path = os.path.join(self.temp_dir, f"restaurants_{self.city}_{timestamp}.xlsx")
                
                self.progress.emit(f"正在保存完整数据到临时文件: {file_path}")
                restaurant_data.to_excel(file_path, index=False)
                LOGGER.info(f"已将完整数据({len(restaurant_data)}条记录)保存到: {file_path}")
                
                # 清理内存中的大对象，确保发送前已经释放资源
                self._restaurant_group = None
                self._restaurant_service = None
                restaurant_group = None
                restaurant_service = None
                
                # 强制垃圾回收
                import gc
                gc.collect()
                
                LOGGER.info(f"{self.city} 餐厅信息获取完成，共 {len(restaurant_data)} 条记录")
                self.progress.emit(f"餐厅信息获取完成，共 {len(restaurant_data)} 条记录")
                self.finished.emit(restaurant_data, file_path)
            except Exception as e:
                LOGGER.error(f"转换餐厅数据为DataFrame时出错: {str(e)}")
                self.error.emit(f"处理餐厅数据时出错: {str(e)}")
        except Exception as e:
            LOGGER.error(f"获取餐厅信息时出错: {str(e)}")
            self.error.emit(str(e))

## 补全餐厅信息多线程类
class RestaurantCompleteWorker(QThread):
    # 定义信号
    finished = pyqtSignal(pd.DataFrame, str, int, int)  # 完成信号，携带更新数据、文件路径、完成数量和总数量
    error = pyqtSignal(str)  # 错误信号
    progress = pyqtSignal(str)  # 进度信号
    
    def __init__(self, restaurant_data, cp_location=None, num_workers=None):
        super().__init__()
        # 预先导入必要的模块
        import multiprocessing
        import gc
        import os
        import tempfile
        import datetime
        from app.services.instances.restaurant import Restaurant, RestaurantsGroup
        from app.services.functions.get_restaurant_service import GetRestaurantService
        
        # 创建数据的一个安全副本，避免引用原始数据
        try:
            # 仅保留必要的列以减少内存使用
            necessary_columns = [
                'rest_chinese_name', 'rest_chinese_address', 'rest_contact_phone',
                'rest_location', 'rest_type', 'rest_type_gaode', 'adname', 'rest_city'
            ]
            
            # 获取餐厅数据中实际存在的列
            existing_columns = [col for col in necessary_columns if col in restaurant_data.columns]
            
            # 只保留这些列
            if existing_columns:
                self.restaurant_data = restaurant_data[existing_columns].copy(deep=True)
            else:
                # 如果没有任何必要的列存在，则使用完整数据
                self.restaurant_data = restaurant_data.copy(deep=True)
            
            LOGGER.info(f"创建RestaurantCompleteWorker，数据大小: {len(self.restaurant_data)}行")
        except Exception as e:
            LOGGER.error(f"创建餐厅数据副本时出错: {str(e)}")
            # 仍然必须设置属性，即使发生错误
            if restaurant_data is not None:
                self.restaurant_data = restaurant_data.copy(deep=True)
            else:
                # 如果输入数据为None，创建一个空DataFrame
                self.restaurant_data = pd.DataFrame()
        
        self.cp_location = cp_location
        
        # 动态调整线程数
        import multiprocessing
        # 使用CPU核心数的一半，但最少2个，最多4个
        if num_workers is None:
            self.num_workers = max(2, min(4, multiprocessing.cpu_count() // 2))
        else:
            self.num_workers = num_workers
            
        self.running = True
        
        # 内部状态跟踪
        self._batch_size = 30  # 减小批处理大小，降低内存压力
        self._current_batch = 0
        self._batches_processed = 0
        
        # 追踪的资源，用于安全释放
        self._resources = {
            'interim_df': None,
            'current_batch': None,
            'current_group': None,
            'service': None,
            'all_processed_records': []
        }
        
        # 创建临时文件路径（在初始化时就创建）
        import datetime
        import tempfile
        import os
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = tempfile.gettempdir()
        self.file_path = os.path.join(temp_dir, f"restaurants_completed_{timestamp}.xlsx")
        LOGGER.info(f"临时文件将保存到: {self.file_path}")
    
    def stop(self):
        """停止线程执行"""
        self.running = False
        LOGGER.info("餐厅信息补全线程收到停止信号")
        
    def __del__(self):
        """析构函数，确保安全清理资源"""
        try:
            # 释放所有引用的数据
            if hasattr(self, '_resources'):
                for key in self._resources:
                    self._resources[key] = None
            
            # 释放DataFrame
            if hasattr(self, 'restaurant_data'):
                self.restaurant_data = None
                
            # 强制垃圾回收
            import gc
            gc.collect()
        except Exception as e:
            LOGGER.error(f"RestaurantCompleteWorker析构时出错: {str(e)}")
            
    def _clean_batch_resources(self):
        """清理单个批次的资源"""
        try:
            # 清理当前批次资源
            if self._resources['current_batch'] is not None:
                self._resources['current_batch'] = None
                
            if self._resources['current_group'] is not None:
                self._resources['current_group'] = None
                
            if self._resources['service'] is not None:
                self._resources['service'] = None
                
            # 强制垃圾回收
            import gc
            gc.collect()
        except Exception as e:
            LOGGER.error(f"清理批次资源时出错: {str(e)}")
    
    def run(self):
        """运行线程 - 完全改写为单批次处理模式"""
        # 预先导入所有需要的模块，避免运行时导入
        import pandas as pd
        import numpy as np
        import time
        import os
        import tempfile
        import gc
        import copy
        
        # 必要的类
        from app.services.instances.restaurant import Restaurant, RestaurantsGroup
        from app.services.functions.get_restaurant_service import GetRestaurantService
        
        # 检查运行状态
        if not self.running:
            self.error.emit("线程在启动前被取消")
            return
            
        # 检查数据有效性
        if self.restaurant_data is None or len(self.restaurant_data) == 0:
            self.error.emit("没有餐厅数据可以处理")
            return
            
        try:
            # 状态变量
            total_restaurants = len(self.restaurant_data)
            completed_count = 0
            all_processed_records = []  # 最终结果列表
            
            # 计算总批次数
            total_batches = (total_restaurants + self._batch_size - 1) // self._batch_size
            self.progress.emit(f"准备处理 {total_restaurants} 家餐厅信息，共 {total_batches} 批")
            
            # 批次索引列表 - 预先计算所有批次的起始索引
            batch_indices = list(range(0, total_restaurants, self._batch_size))
            
            # 每隔5个批次保存一次中间结果
            save_interval = 2
            
            # 逐批处理
            for batch_idx, start_idx in enumerate(batch_indices):
                # 检查是否取消
                if not self.running:
                    self.progress.emit("用户取消了操作")
                    break
                    
                # 计算批次范围
                end_idx = min(start_idx + self._batch_size, total_restaurants)
                self.progress.emit(f"处理第 {batch_idx+1}/{total_batches} 批 ({start_idx+1}-{end_idx})")
                
                try:
                    # ==== 第1步：提取批次数据 ====
                    # 使用iloc切片获取批次数据，并立即创建深拷贝
                    batch_data = self.restaurant_data.iloc[start_idx:end_idx].copy(deep=True)
                    self._resources['current_batch'] = batch_data
                    
                    # ==== 第2步：转换为记录 ====
                    batch_records = batch_data.to_dict('records')
                    # 立即释放批次数据
                    batch_data = None
                    self._resources['current_batch'] = None
                    
                    # ==== 第3步：创建餐厅实例 ====
                    restaurant_instances = []
                    for idx, restaurant_info in enumerate(batch_records):
                        if not self.running:
                            break
                            
                        try:
                            # 创建餐厅实例，为每个实例使用信息的副本
                            restaurant = Restaurant(copy.deepcopy(restaurant_info), cp_location=self.cp_location)
                            restaurant_instances.append(restaurant)
                        except Exception as e:
                            LOGGER.error(f"创建餐厅实例时出错({idx}): {str(e)}")
                            continue
                    
                    # 释放记录列表
                    batch_records = None
                    gc.collect()
                    
                    # 检查是否取消
                    if not self.running:
                        self.progress.emit("用户取消了操作")
                        # 清理资源
                        restaurant_instances = None
                        gc.collect()
                        break
                    
                    # ==== 第4步：创建餐厅组并生成信息 ====
                    if restaurant_instances:
                        try:
                            # 创建餐厅组
                            restaurant_group = RestaurantsGroup(restaurant_instances)
                            self._resources['current_group'] = restaurant_group
                            
                            # 释放实例列表
                            restaurant_instances = None
                            
                            # 创建服务实例
                            service = GetRestaurantService()
                            self._resources['service'] = service
                            
                            # 生成信息
                            self.progress.emit(f"正在补全第 {batch_idx+1}/{total_batches} 批的详细信息...")
                            processed_group = service.gen_info(restaurant_group, num_workers=self.num_workers)
                            
                            # 清理旧组和服务
                            restaurant_group = None
                            service = None
                            self._resources['current_group'] = processed_group
                            self._resources['service'] = None
                            
                            # ==== 第5步：提取结果 ====
                            # 处理结果并添加到总结果列表
                            batch_processed_records = []
                            batch_completed = 0
                            
                            for restaurant in processed_group.members:
                                if hasattr(restaurant, 'inst') and restaurant.inst:
                                    try:
                                        # 安全地提取字典并创建副本
                                        restaurant_dict = restaurant.to_dict()
                                        if restaurant_dict:
                                            batch_processed_records.append(restaurant_dict.copy())
                                            batch_completed += 1
                                    except Exception as e:
                                        LOGGER.error(f"提取餐厅数据时出错: {str(e)}")
                            
                            # 更新总完成数
                            completed_count += batch_completed
                            
                            # 将此批次结果添加到总结果（使用extend避免嵌套列表）
                            all_processed_records.extend(batch_processed_records)
                            
                            # 释放批次结果和处理组
                            batch_processed_records = None
                            processed_group = None
                            self._resources['current_group'] = None
                            
                            # 强制垃圾回收
                            gc.collect()
                            
                            # 定期保存中间结果
                            if (batch_idx + 1) % save_interval == 0 or batch_idx == total_batches - 1:
                                try:
                                    # 创建临时DataFrame保存结果
                                    if all_processed_records:
                                        interim_df = pd.DataFrame(copy.deepcopy(all_processed_records))
                                        self._resources['interim_df'] = interim_df
                                        
                                        # 保存到文件
                                        interim_df.to_excel(self.file_path, index=False)
                                        
                                        # 进度更新
                                        self.progress.emit(f"已保存中间结果，目前完成 {completed_count}/{total_restaurants} 家")
                                        
                                        # 释放interim_df
                                        interim_df = None
                                        self._resources['interim_df'] = None
                                except Exception as e:
                                    LOGGER.error(f"保存中间结果时出错: {str(e)}")
                            
                        except Exception as e:
                            LOGGER.error(f"处理餐厅组时出错: {str(e)}")
                            # 清理资源但继续处理下一批
                            self._clean_batch_resources()
                    
                except Exception as e:
                    LOGGER.error(f"处理批次 {batch_idx+1} 时出错: {str(e)}")
                    # 清理但继续处理
                    self._clean_batch_resources()
                
                # 每个批次结束时都强制进行垃圾回收
                gc.collect()
            
            # 所有批次处理完毕
            # 检查是否取消
            if not self.running:
                self.progress.emit("用户取消了操作，已完成部分将被保存")
            
            # 创建最终结果
            if all_processed_records:
                try:
                    # 确保创建的是全新的副本
                    result_records = copy.deepcopy(all_processed_records)
                    
                    # 创建结果DataFrame
                    result_df = pd.DataFrame(result_records)
                    
                    # 保存最终结果
                    result_df.to_excel(self.file_path, index=False)
                    
                    # 发送完成信号
                    self.progress.emit(f"补全完成，已处理 {completed_count}/{total_restaurants} 家餐厅")
                    self.finished.emit(result_df, self.file_path, completed_count, total_restaurants)
                    
                    # 不要在这里删除result_df，它需要传递给信号处理函数
                    # 让Python的GC自行处理
                    
                except Exception as e:
                    LOGGER.error(f"创建最终结果时出错: {str(e)}")
                    self.error.emit(f"创建最终结果时出错: {str(e)}")
            else:
                self.error.emit("没有成功处理任何餐厅记录")
                
        except Exception as e:
            LOGGER.error(f"补全餐厅信息过程中发生错误: {str(e)}")
            self.error.emit(f"补全餐厅信息过程中发生错误: {str(e)}")
            
        finally:
            # 清理所有资源
            try:
                # 清理资源字典
                for key in self._resources:
                    self._resources[key] = None
                
                # 清理数据引用
                if hasattr(self, 'restaurant_data'):
                    self.restaurant_data = None
                
                # 强制垃圾回收
                gc.collect()
                
                LOGGER.info("餐厅信息补全线程清理完成")
            except Exception as e:
                LOGGER.error(f"清理资源时出错: {str(e)}")
                
            # 无论如何，都标记为已完成
            self.progress.emit("处理已完成")

class Tab2(QWidget):
    """餐厅获取Tab，实现餐厅信息获取功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 先保存parent引用，但不直接使用主窗口的方法
        self.main_window_ref = parent
        self.cp_cities = []  # 当前CP的城市列表
        self.current_cp = None  # 当前选择的CP
        self.conf = CONF
        
        # 用于跟踪临时文件
        self.temp_files = []
        # 确保CONF.runtime有temp_files属性
        if not hasattr(self.conf.runtime, 'temp_files'):
            setattr(self.conf.runtime, 'temp_files', [])
        # 记录最后一次查询生成的文件路径
        self.last_query_file = None
        
        # 内存监控标志
        self.memory_debug = False
        
        # 添加标志位，用于标记是否已经通过closeEvent处理过临时文件
        self.cleaned_in_close_event = False
        
        self.conf.runtime.SEARCH_RADIUS = 50
        self.conf.runtime.STRICT_MODE = False
        # 高级配置默认值
        self.search_radius = 50  # 默认搜索半径
        self.strict_mode = False  # 默认非严格模式

        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        self.initUI()
    
    def __del__(self):
        """析构函数，清理资源"""
        try:
            # 检查Python是否正在关闭
            if sys.meta_path is None:
                return
                
            # 停止所有工作线程
            if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
                try:
                    self.worker.stop()
                    self.worker.wait(2000)  # 等待最多2秒
                except Exception:
                    pass
            
            if hasattr(self, 'complete_worker') and self.complete_worker is not None and self.complete_worker.isRunning():
                try:
                    self.complete_worker.stop()
                    self.complete_worker.wait(2000)  # 等待最多2秒
                except Exception:
                    pass
            
            # 检查是否已经在closeEvent中处理过
            if hasattr(self, 'cleaned_in_close_event') and self.cleaned_in_close_event:
                # 已经处理过，就不再显示确认对话框
                pass
            # 如果有临时文件，显示确认对话框询问是否保存数据
            elif hasattr(self.conf.runtime, 'temp_files') and self.conf.runtime.temp_files:
                try:
                    from PyQt5.QtWidgets import QMessageBox
                    # 使用QMessageBox确认是否需要保存数据
                    reply = QMessageBox.question(
                        None, 
                        '保存数据确认', 
                        '是否需要保存临时数据文件？\n选择"是"将打开相关文件，"否"则删除所有临时文件。',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Yes:
                        # 打开最后一次查询的文件和结果文件
                        if hasattr(self, 'last_query_file') and self.last_query_file and os.path.exists(self.last_query_file):
                            self.open_file_external(self.last_query_file)
                        
                        # 查找result文件并打开
                        for file_path in self.conf.runtime.temp_files:
                            if os.path.exists(file_path) and 'result_' in file_path and file_path.endswith('.xlsx'):
                                self.open_file_external(file_path)
                                break
                    else:
                        # 清理临时文件
                        self.cleanup_temp_files()
                except Exception as e:
                    # 尝试记录异常，但不阻止程序关闭
                    if LOGGER:
                        LOGGER.error(f"析构函数中显示确认对话框时出错: {str(e)}")
            else:
                # 如果没有临时文件，直接清理
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
        
        # 合并self.temp_files和CONF.runtime.temp_files
        temp_files_to_clean = set(self.temp_files + self.conf.runtime.temp_files if hasattr(self.conf.runtime, 'temp_files') else [])
        
        for file_path in temp_files_to_clean:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    LOGGER.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                LOGGER.error(f"删除临时文件时出错: {str(e)}")
                
        # 清空列表
        self.temp_files = []
        # 清空CONF.runtime.temp_files
        if hasattr(self.conf.runtime, 'temp_files'):
            self.conf.runtime.temp_files = []
            
        # 清理临时文件夹（例如：C:\Users\H3C\AppData\Local\Temp\20250506_091058）
        try:
            temp_dir = tempfile.gettempdir()
            # 获取临时目录下所有子目录
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                # 检查是否是目录且匹配日期格式（YYYYMMDD_HHMMSS）
                if os.path.isdir(item_path) and re.match(r"^\d{8}_\d{6}$", item):
                    try:
                        # 先尝试删除目录中的所有文件
                        for sub_item in os.listdir(item_path):
                            sub_item_path = os.path.join(item_path, sub_item)
                            if os.path.isfile(sub_item_path):
                                os.remove(sub_item_path)
                            elif os.path.isdir(sub_item_path):
                                shutil.rmtree(sub_item_path, ignore_errors=True)
                        
                        # 删除空目录
                        os.rmdir(item_path)
                        LOGGER.info(f"已删除临时文件夹: {item_path}")
                    except Exception as e:
                        LOGGER.error(f"删除临时文件夹时出错: {item_path}, {str(e)}")
        except Exception as e:
            LOGGER.error(f"清理临时文件夹时出错: {str(e)}")
            
        # 设置标志位，防止__del__方法再次处理
        self.cleaned_in_close_event = True
    
    def initUI(self):
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)  # 减小组件间距
        
        # 顶部布局 - 包含CP选择按钮
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title_label = QLabel("餐厅获取")
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
        
        # API测试区
        api_group = QGroupBox("API连通性测试")
        api_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        api_layout = QVBoxLayout(api_group)
        api_layout.setContentsMargins(5, 10, 5, 5)
        api_layout.setSpacing(0)
        
        self.api_test_widget = ApiTestWidget()
        api_layout.addWidget(self.api_test_widget)
        
        # 减小API测试区域的高度
        api_group.setMaximumHeight(100)  # 限制最大高度
        self.layout.addWidget(api_group)
        
        # 主体区域 - 使用Splitter分隔日志和餐厅信息
        main_content = QVBoxLayout()
        
        # 餐厅信息区域
        excel_group = QGroupBox("餐厅信息")
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
        self.xlsx_viewer = XlsxViewerWidget(show_open=False, show_save=False, show_save_as=True, show_refresh=False)
        excel_layout.addWidget(self.xlsx_viewer)
        
        # 添加到主内容区域
        main_content.addWidget(excel_group)
        
        
        # 添加主内容区域到主布局
        self.layout.addLayout(main_content, 1)
        
        # 底部控制区
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding-top: 5px;
            }
        """)
        
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(0, 0, 0, 0)
        
        # 城市输入框
        city_label = QLabel("餐厅城市:")
        self.city_input = QLineEdit()  # 创建输入框
        self.city_input.setPlaceholderText("请输入城市名称")  # 设置占位符
        self.city_input.setEnabled(False)  # 启用输入框
        self.city_input.setMinimumWidth(200)  # 设置最小宽度
        self.city_input.setMaximumWidth(250)  # 设置最大宽度
        
        # 根据CP位置搜索按钮
        self.search_by_cp_button = QPushButton("根据CP位置搜索")
        self.search_by_cp_button.clicked.connect(self.search_by_cp_location)
        self.search_by_cp_button.setEnabled(False)
        self.search_by_cp_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #46b8da;
            }
        """)
        
        # 详细配置按钮
        self.advanced_config_button = QToolButton()
        self.advanced_config_button.setText("详细配置 ⬇")
        self.advanced_config_button.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.advanced_config_button.setStyleSheet("""
            QToolButton {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px 10px;
                background-color: #f8f9fa;
            }
            QToolButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.advanced_config_button.setCheckable(True)
        self.advanced_config_button.clicked.connect(self.toggle_advanced_config)
        
        # 添加使用大模型的复选框
        self.use_llm_checkbox = QCheckBox("使用大模型生成餐厅类型")
        self.use_llm_checkbox.setChecked(False)  # 默认选中
        self.use_llm_checkbox.setEnabled(False)  # 默认禁用，需要先选择CP
        
        # 获取餐厅按钮
        self.get_restaurant_button = QPushButton("餐厅获取")
        self.get_restaurant_button.clicked.connect(self.get_restaurants)
        self.get_restaurant_button.setEnabled(False)
        self.get_restaurant_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        
        # 餐厅获取（低资源版）按钮
        self.get_restaurant_low_resource_button = QPushButton("餐厅获取（低资源版）")
        self.get_restaurant_low_resource_button.clicked.connect(self.get_restaurants_low_resource)
        self.get_restaurant_low_resource_button.setEnabled(False)
        self.get_restaurant_low_resource_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        
        # 导入按钮
        self.import_button = QPushButton("导入已有餐厅")
        self.import_button.clicked.connect(self.import_restaurants)
        self.import_button.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
        """)
        
        # 补全餐厅信息按钮
        self.complete_info_button = QPushButton("补全餐厅信息")
        self.complete_info_button.clicked.connect(self.complete_restaurant_info)
        self.complete_info_button.setStyleSheet("""
            QPushButton {
                background-color: #f0ad4e;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #ec971f;
            }
            QPushButton:disabled {
                background-color: #d9d9d9;
                color: #a6a6a6;
            }
        """)
        
        # 验证餐厅营业状态按钮
        self.verify_status_button = QPushButton("验证营业状态")
        self.verify_status_button.clicked.connect(self.verify_restaurant_status)
        self.verify_status_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #31b0d5;
            }
        """)
        
        # 下载模版按钮
        self.download_template_button = QPushButton("下载模版")
        self.download_template_button.clicked.connect(self.download_template)
        self.download_template_button.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
        """)
        
        control_layout.addWidget(city_label)
        control_layout.addWidget(self.city_input)  # 使用输入框
        control_layout.addWidget(self.search_by_cp_button)  # 添加根据CP位置搜索按钮
        control_layout.addSpacing(10)
        control_layout.addWidget(self.advanced_config_button)  # 添加详细配置按钮
        control_layout.addSpacing(10)
        control_layout.addWidget(self.use_llm_checkbox)  # 添加复选框
        control_layout.addSpacing(10)
        control_layout.addWidget(self.get_restaurant_button)
        control_layout.addWidget(self.get_restaurant_low_resource_button)
        control_layout.addWidget(self.import_button)
        control_layout.addWidget(self.complete_info_button)
        control_layout.addWidget(self.verify_status_button)
        control_layout.addWidget(self.download_template_button)  # 添加下载模版按钮
        
        # 创建加载搜索结果按钮（初始隐藏）
        self.load_search_results_button = QPushButton("加载搜索结果")
        self.load_search_results_button.clicked.connect(self.load_low_resource_results)
        self.load_search_results_button.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
        """)
        self.load_search_results_button.setVisible(False)  # 初始隐藏
        control_layout.addWidget(self.load_search_results_button)
        
        control_layout.addStretch()
        
        self.layout.addWidget(control_frame)
        
        # 创建高级配置面板（默认隐藏）
        self.create_advanced_config_panel()
        
        # 使用全局日志记录器记录信息，不需要重定向标准输出
        # 获取全局logger
        from app.utils.logger import get_logger
        self.logger = get_logger()
        
        # 加载示例数据
        # self.load_sample_data()
    
    def create_advanced_config_panel(self):
        """创建高级配置面板"""
        self.advanced_config_frame = QFrame()
        self.advanced_config_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                margin-top: 5px;
            }
        """)
        
        # 使用水平布局替代网格布局
        advanced_layout = QHBoxLayout(self.advanced_config_frame)
        advanced_layout.setContentsMargins(10, 10, 10, 10)
        advanced_layout.setSpacing(15)
        
        # 搜索半径配置
        radius_label = QLabel("搜索半径(KM):")
        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(1, 999)
        self.radius_spinbox.setValue(self.search_radius)
        self.radius_spinbox.setSuffix(" KM")
        # 设置为只能容纳4位数字的宽度
        self.radius_spinbox.setFixedWidth(80)
        self.radius_spinbox.valueChanged.connect(self.update_search_radius)
        
        # 严格模式选项
        strict_mode_label = QLabel("是否严格模式:")
        self.strict_mode_yes = QRadioButton("是")
        self.strict_mode_no = QRadioButton("否")
        self.strict_mode_no.setChecked(True)  # 默认为否
        
        # 将单选按钮连接到更新函数
        self.strict_mode_yes.toggled.connect(self.update_strict_mode)
        
        # 创建一个水平布局来容纳单选按钮
        strict_radio_layout = QHBoxLayout()
        strict_radio_layout.setSpacing(5)
        strict_radio_layout.setContentsMargins(0, 0, 0, 0)
        strict_radio_layout.addWidget(self.strict_mode_yes)
        strict_radio_layout.addWidget(self.strict_mode_no)
        strict_radio_layout.addStretch()
        
        # 添加到水平布局中
        advanced_layout.addWidget(radius_label)
        advanced_layout.addWidget(self.radius_spinbox)
        advanced_layout.addSpacing(20)
        advanced_layout.addWidget(strict_mode_label)
        advanced_layout.addLayout(strict_radio_layout)
        advanced_layout.addStretch(1)
        
        # 隐藏高级配置面板
        self.advanced_config_frame.setVisible(False)
        
        # 添加到主布局
        self.layout.addWidget(self.advanced_config_frame)
    
    def toggle_advanced_config(self):
        """切换高级配置面板显示状态"""
        is_visible = self.advanced_config_frame.isVisible()
        self.advanced_config_frame.setVisible(not is_visible)
        
        # 更新按钮文本
        if is_visible:
            self.advanced_config_button.setText("详细配置 ⬇")
        else:
            self.advanced_config_button.setText("详细配置 ⬆")
    
    def update_search_radius(self, value):
        """更新搜索半径配置"""
        self.conf.runtime.SEARCH_RADIUS = value
        self.search_radius = value
        LOGGER.info(f"搜索半径已更新为: {value} KM")
    
    def update_strict_mode(self, checked):
        """更新严格模式设置"""
        if checked:
            self.conf.runtime.STRICT_MODE = True
            self.strict_mode = True
            LOGGER.info("严格模式已启用")
        else:
            self.conf.runtime.STRICT_MODE = False
            self.strict_mode = False
            LOGGER.info("严格模式已禁用")
    
    def search_by_cp_location(self):
        """根据CP位置进行搜索"""
        try:
            if not self.current_cp:
                QMessageBox.warning(self, "未选择CP", "请先选择CP")
                return
            
            # 获取CP位置信息
            cp_city, cp_location = self.get_cp_location()
            self.conf.runtime.CP_LOCATION = cp_location
            self.conf.runtime.CP_CITY = cp_city
            if not cp_location:
                QMessageBox.warning(self, "位置信息缺失", "当前CP没有可用的位置信息")
                return
            
            # 使用CP位置信息进行搜索，传递搜索半径和严格模式参数
            LOGGER.info(f"使用CP位置进行搜索: {cp_location}, 半径: {self.search_radius}KM, 严格模式: {'是' if self.strict_mode else '否'}")
            
            # 将城市信息设置到城市输入框
            self.city_input.setText(cp_location)
            
            # 直接调用餐厅获取函数
            self.get_restaurants(city=cp_city)
            
        except Exception as e:
            LOGGER.error(f"根据CP位置搜索时出错: {str(e)}")
            QMessageBox.critical(self, "搜索失败", f"根据CP位置搜索时出错: {str(e)}")
    
    def get_cp_location(self):
        """获取当前CP的位置信息"""
        try:
            current_cp_city = self.conf.runtime.CP.get('cp_city', None)
            current_cp_location = self.conf.runtime.CP.get('cp_location', None)
            LOGGER.info(f"当前CP城市: {current_cp_city}, 当前CP位置: {current_cp_location}")
            return current_cp_city, current_cp_location
        except Exception as e:
            LOGGER.error(f"获取CP位置信息时出错: {str(e)}")
            return None
    
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
                    
                    
                    # 保存选择的CP到运行时配置
                    if not hasattr(CONF, 'runtime'):
                        setattr(CONF, 'runtime', type('RuntimeConfig', (), {}))
                    
                    CONF.runtime.CP = cp_data
                    self.current_cp = cp_data
                    
                    # 更新CP按钮文本
                    self.cp_button.setText(f"已选择CP为：{cp_data['cp_name']}")
                    
                    # 启用城市输入框、复选框和获取餐厅按钮
                    self.city_input.setEnabled(True)  # 启用城市输入框
                    self.use_llm_checkbox.setEnabled(True)  # 启用复选框
                    self.get_restaurant_button.setEnabled(True)  # 启用获取餐厅按钮
                    self.get_restaurant_low_resource_button.setEnabled(True)  # 启用低资源版按钮
                    self.search_by_cp_button.setEnabled(True)  # 启用根据CP位置搜索按钮
                    
                    # 通知主窗口更新CP
                    if self.main_window_ref:
                        self.main_window_ref.set_current_cp(cp_data['cp_id'])
        except Exception as e:
            LOGGER.error(f"选择CP时出错: {str(e)}")
            LOGGER.error(f"CONF.BUSINESS.CP的内容: {getattr(CONF.BUSINESS, 'CP', None)}")
            QMessageBox.critical(self, "选择CP失败", f"选择CP时出错: {str(e)}")
    
    def update_cities(self, cp_id):
        """根据CP ID更新城市列表"""
        try:
            # 获取当前选择的CP中的城市信息
            cities = []
            
            # 首先尝试从CONF.runtime.CP获取城市列表
            if hasattr(CONF, 'runtime') and hasattr(CONF.runtime, 'CP'):
                # 使用字典访问方式而不是get方法
                if isinstance(CONF.runtime.CP, dict):
                    cities = CONF.runtime.CP.get('cities', [])
                    
                    # 如果cities为空，尝试从其他字段构建城市列表
                    if not cities and 'cp_city' in CONF.runtime.CP:
                        cities = [CONF.runtime.CP['cp_city']]
            
            # 如果未获取到，则尝试从CONF.BUSINESS.CP获取
            if not cities and hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                cp_data = getattr(CONF.BUSINESS.CP, str(cp_id), None)
                if cp_data:
                    if hasattr(cp_data, 'cities'):
                        cities = cp_data.cities
                    elif hasattr(cp_data, 'cp_city'):
                        cities = [cp_data.cp_city]
            
            # 如果还是未获取到，尝试从配置字典中获取
            if not cities and hasattr(CONF, 'BUSINESS') and hasattr(CONF.BUSINESS, 'CP'):
                cp_cities_map = {}
                config_dict = getattr(CONF.BUSINESS.CP, '_config_dict', {})
                
                for cp_key, cp_value in config_dict.items():
                    if cp_key != 'cp_id' and isinstance(cp_value, dict):
                        if 'cities' in cp_value:
                            cp_cities_map[cp_key] = cp_value['cities']
                        elif 'cp_city' in cp_value:
                            cp_cities_map[cp_key] = [cp_value['cp_city']]
                
                # 如果配置中有此CP的城市列表
                cities = cp_cities_map.get(str(cp_id), [])
            
            # 记录调试信息
            LOGGER.info(f"更新城市列表: CP ID = {cp_id}")
            LOGGER.info(f"获取到的城市列表: {cities}")
            
            # 更新城市列表
            self.cp_cities = cities
            
            # 更新下拉框
            self.city_combo.clear()
            if cities:
                self.city_combo.addItems(self.cp_cities)
                # 启用相关控件
                self.city_combo.setEnabled(True)
                self.get_restaurant_button.setEnabled(True)
            else:
                LOGGER.warning(f"CP {cp_id} 没有关联的城市")
                self.city_combo.setEnabled(False)
                self.get_restaurant_button.setEnabled(False)
            
        except Exception as e:
            LOGGER.error(f"更新城市列表时出错: {str(e)}")
            LOGGER.error(f"CONF.runtime.CP的内容: {getattr(CONF.runtime, 'CP', None)}")
            self.cp_cities = []
            self.city_combo.clear()
            self.city_combo.setEnabled(False)
            self.get_restaurant_button.setEnabled(False)
    
    def get_restaurants(self, city=None):
        """获取餐厅信息"""
        try:
            # 检查是否已经有一个正在运行的线程
            if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
                # 线程正在运行，则强制停止它
                try:
                    LOGGER.info("用户取消了正在运行的餐厅获取操作，正在强制终止线程...")
                    
                    # 先调用线程的stop方法，设置停止标志
                    self.worker.stop()
                    
                    # 显示取消状态
                    self.get_restaurant_button.setText("餐厅获取")
                    if hasattr(self, 'progress_label'):
                        self.progress_label.setText("正在取消操作...")
                    
                    # 设置超时时间，防止无限等待
                    max_wait_time = 3  # 等待最多3秒
                    if not self.worker.wait(max_wait_time * 1000):  # wait方法接受毫秒为单位
                        LOGGER.warning(f"线程未在{max_wait_time}秒内退出，将强制终止")
                        
                        # 断开信号连接，避免已中断的线程仍然发送信号
                        try:
                            self.worker.finished.disconnect()
                            self.worker.error.disconnect()
                            self.worker.progress.disconnect()
                        except Exception:
                            pass
                        
                        # 强制线程终止并释放 - 不建议在实际生产环境中使用，但这里我们需要确保线程停止
                        self.worker.terminate()
                        self.worker = None
                    
                    # 更新UI状态
                    if hasattr(self, 'progress_label'):
                        self.progress_label.setText("操作已取消")
                        QTimer.singleShot(2000, lambda: self.progress_label.setVisible(False))
                        
                    LOGGER.info("餐厅获取操作已成功取消")
                    
                except Exception as e:
                    LOGGER.error(f"取消餐厅获取操作时出错: {str(e)}")
                    self.get_restaurant_button.setText("餐厅获取")
                    if hasattr(self, 'progress_label'):
                        self.progress_label.setVisible(False)
                
                return
            
            # 如果没有传入城市名，从输入框获取
            if not city:
                city = self.city_input.text().strip()  # 获取输入框中的城市名称
                
            if not city:
                QMessageBox.warning(self, "请输入城市", "请先输入餐厅城市")
                return
            
            # 获取是否使用大模型
            use_llm = self.use_llm_checkbox.isChecked()
            self.conf.runtime.USE_LLM = use_llm
            LOGGER.info(f"用户选择{'使用' if use_llm else '不使用'}大模型生成餐厅类型")
            
            # 检查API连通性
            api_ok = self.check_apis()
            if not api_ok:
                reply = QMessageBox.question(
                    self, 'API连接问题', 
                    '一个或多个API测试未通过。是否继续？',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # 禁用获取按钮，防止重复点击
            self.get_restaurant_button.setText("取消获取")
            
            # 添加进度提示
            if not hasattr(self, 'progress_label'):
                self.progress_label = QLabel("正在准备...")
                self.progress_label.setStyleSheet("color: #666; margin-top: 5px;")
                self.layout.addWidget(self.progress_label)
            else:
                self.progress_label.setText("正在准备...")
                self.progress_label.setVisible(True)
            
            # 创建工作线程，传递使用大模型的选项和高级配置
            self.worker = RestaurantWorker(
                city=city, 
                cp_id=self.current_cp['cp_id'], 
                use_llm=use_llm,
                if_gen_info=False  # 不在查询阶段生成详细信息
            )
            
            # 将搜索半径和严格模式设置到工作线程中（如果Worker类支持这些参数）
            self.worker.search_radius = self.search_radius
            self.worker.strict_mode = self.strict_mode
            
            # 连接信号
            self.worker.finished.connect(self.on_restaurant_search_finished)
            self.worker.error.connect(self.on_restaurant_search_error)
            self.worker.progress.connect(self.update_progress)
            
            # 启动线程
            LOGGER.info(f"启动餐厅获取线程，搜索城市: {city}，{'使用' if use_llm else '不使用'}大模型，搜索半径: {self.search_radius}KM，严格模式: {'是' if self.strict_mode else '否'}")
            self.worker.start()
            
        except Exception as e:
            LOGGER.error(f"启动餐厅获取线程时出错: {str(e)}")
            QMessageBox.critical(self, "获取失败", f"启动餐厅获取线程时出错: {str(e)}")
            self.get_restaurant_button.setText("餐厅获取")
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
    
    def update_progress(self, message):
        """更新进度信息"""
        try:
            # 防止在非主线程中更新UI
            if QApplication.instance().thread() != QThread.currentThread():
                # 使用QTimer在主线程中安排更新
                QTimer.singleShot(0, lambda msg=message: self.update_progress_safe(msg))
                return
            
            if hasattr(self, 'progress_label'):
                self.progress_label.setText(message)
                self.progress_label.setVisible(True)
                # 确保UI更新
                QApplication.processEvents()
        except Exception as e:
            LOGGER.error(f"更新进度信息时出错: {str(e)}")
        
    def update_progress_safe(self, message):
        """在主线程中安全地更新进度信息"""
        try:
            if hasattr(self, 'progress_label'):
                self.progress_label.setText(message)
                self.progress_label.setVisible(True)
                # 确保UI更新
                QApplication.processEvents()
        except Exception as e:
            LOGGER.error(f"安全更新进度信息时出错: {str(e)}")
    
    def on_restaurant_search_finished(self, restaurant_data, file_path):
        """餐厅搜索完成的回调函数"""
        try:
            # 记录临时文件，用于程序退出时清理
            self.temp_files.append(file_path)
            # 同时添加到CONF.runtime.temp_files
            if hasattr(self.conf.runtime, 'temp_files'):
                self.conf.runtime.temp_files.append(file_path)
            
            # 保存最后一次查询的文件路径
            self.last_query_file = file_path
            
            # 检查数据量大小
            row_count = len(restaurant_data)
            LOGGER.info(f"收到餐厅数据，共 {row_count} 条记录")
            
            # 限制显示的数据量，无论多大只显示前100行
            max_display_rows = 10
            if row_count > max_display_rows:
                LOGGER.warning(f"数据量过大 ({row_count} 行)，将只显示前 {max_display_rows} 行")
                restaurant_data_display = restaurant_data.head(max_display_rows).copy()
                warning_msg = f"数据量过大，仅显示前 {max_display_rows} 条记录（共 {row_count} 条）"
            else:
                restaurant_data_display = restaurant_data
                warning_msg = ""
            
            # 确保在主线程中更新UI
            QApplication.processEvents()
            
            # 更新Excel查看器 - 只显示有限的数据
            self.xlsx_viewer.load_data(data=restaurant_data_display)
            
            # 显示成功消息，包含文件路径信息
            success_msg = f"餐厅信息获取完成，共 {row_count} 条记录"
            if warning_msg:
                success_msg += "\n" + warning_msg
            success_msg += f"\n\n完整数据已保存到文件：\n{file_path}"
            success_msg += "\n\n您可以点击 补全餐厅信息 按钮来补全餐厅的详细数据。"
            
            # 创建一个带有"打开文件"按钮的消息框
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("获取成功")
            msg_box.setText(success_msg)
            msg_box.setIcon(QMessageBox.Information)
            
            # 添加打开文件按钮
            open_button = msg_box.addButton("打开完整数据", QMessageBox.ActionRole)
            close_button = msg_box.addButton("关闭", QMessageBox.RejectRole)
            
            # 显示消息框并处理响应
            msg_box.exec_()
            
            # 如果点击了打开文件按钮
            if msg_box.clickedButton() == open_button:
                self.open_file_external(file_path)
            
            # 恢复按钮状态
            self.get_restaurant_button.setText("餐厅获取")
            
            # 隐藏进度标签
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 清理线程
            if hasattr(self, 'worker'):
                try:
                    # 断开信号连接
                    self.worker.finished.disconnect()
                    self.worker.error.disconnect()
                    self.worker.progress.disconnect()
                except Exception:
                    pass
                    
                # 确保线程终止
                if self.worker.isRunning():
                    # 先尝试正常停止
                    self.worker.stop()
                    # 等待短暂时间
                    if not self.worker.wait(1000):  # 等待1秒
                        # 如果没有正常终止，则强制终止
                        self.worker.terminate()
                        
                # 清除引用
                self.worker = None
                
                # 强制垃圾回收
                import gc
                gc.collect()
            
        except Exception as e:
            LOGGER.error(f"处理餐厅搜索结果时出错: {str(e)}")
            QMessageBox.critical(self, "处理失败", f"处理餐厅搜索结果时出错: {str(e)}")
            self.get_restaurant_button.setText("餐厅获取")
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 清理线程
            if hasattr(self, 'worker'):
                try:
                    self.worker.disconnect()
                    if self.worker.isRunning():
                        self.worker.terminate()
                except Exception:
                    pass
                self.worker = None
    
    def open_file_external(self, file_path):
        """使用系统默认程序打开文件"""
        try:
            LOGGER.info(f"尝试打开文件: {file_path}")
            if os.path.exists(file_path):
                if sys.platform == 'win32':
                    os.startfile(file_path)
                elif sys.platform == 'darwin':  # macOS
                    subprocess.call(['open', file_path])
                else:  # Linux
                    subprocess.call(['xdg-open', file_path])
                LOGGER.info(f"成功打开文件: {file_path}")
            else:
                LOGGER.error(f"文件不存在: {file_path}")
                QMessageBox.warning(self, "文件不存在", f"找不到文件: {file_path}")
        except Exception as e:
            LOGGER.error(f"打开文件失败: {str(e)}")
            QMessageBox.warning(self, "打开失败", f"无法打开文件: {str(e)}")
    
    def on_restaurant_search_error(self, error_msg):
        """餐厅搜索出错的回调函数"""
        QMessageBox.critical(self, "获取失败", f"获取餐厅信息时出错: {error_msg}")
        self.get_restaurant_button.setText("餐厅获取")
        if hasattr(self, 'progress_label'):
            self.progress_label.setVisible(False)
            
        # 清理线程
        if hasattr(self, 'worker'):
            try:
                # 断开信号连接
                self.worker.finished.disconnect()
                self.worker.error.disconnect()
                self.worker.progress.disconnect()
            except Exception:
                pass
                
            # 确保线程终止
            if self.worker.isRunning():
                # 先尝试正常停止
                self.worker.stop()
                # 等待短暂时间
                if not self.worker.wait(1000):  # 等待1秒
                    # 如果没有正常终止，则强制终止
                    self.worker.terminate()
                    
            # 清除引用
            self.worker = None
            
            # 强制垃圾回收
            import gc
            gc.collect()
    
    def check_apis(self):
        """检查所有API连通性"""
        all_ok = True
        for api_name, status in self.api_test_widget.api_status.items():
            if not status:
                LOGGER.warning(f"{api_name} 未通过测试")
                all_ok = False
        
        return all_ok
    
    def import_restaurants(self):
        """导入已有餐厅"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "导入餐厅数据", "", "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv);;所有文件 (*.*)"
            )
            
            if not file_path:
                return
            
            try:
                # 加载选择的文件
                self.xlsx_viewer.load_data(file_path)
                LOGGER.info(f"餐厅数据已从 {file_path} 导入")
                QMessageBox.information(self, "导入成功", f"已成功导入餐厅数据文件：\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "导入错误", f"导入数据时出错：{str(e)}")
        except Exception as e:
            LOGGER.error(f"导入餐厅数据时出错: {str(e)}")
            QMessageBox.critical(self, "导入失败", f"导入餐厅数据时出错: {str(e)}")    
    
    def complete_restaurant_info(self):
        """补全餐厅信息"""
        try:
            # 禁用按钮，防止重复点击
            self.complete_info_button.setEnabled(False)
            
            # 是否使用大模型
            use_llm = self.use_llm_checkbox.isChecked()
            self.conf.runtime.USE_LLM = use_llm
            LOGGER.info(f"用户选择{'使用' if use_llm else '不使用'}大模型生成餐厅类型")
            
            # 显示进度信息
            if not hasattr(self, 'progress_label'):
                self.progress_label = QLabel("正在准备补全餐厅信息...")
                self.progress_label.setStyleSheet("color: #666; margin-top: 5px;")
                self.layout.addWidget(self.progress_label)
            else:
                self.progress_label.setText("正在准备补全餐厅信息...")
                self.progress_label.setVisible(True)
            
            # 确保UI更新
            QApplication.processEvents()
            
            # 数据准备
            restaurant_data = None
            
            # 检查是否有一个最近查询的文件
            if hasattr(self, 'last_query_file') and self.last_query_file and os.path.exists(self.last_query_file):
                # 如果有最近查询的文件，优先使用它
                input_file = self.last_query_file
                LOGGER.info(f"使用最近查询的餐厅数据文件: {input_file}")
            else:
                # 从当前显示的数据中获取并保存到临时文件
                LOGGER.info("从当前显示的数据中获取餐厅信息")
                
                # 检查是否有数据
                if not hasattr(self.xlsx_viewer, 'model') or self.xlsx_viewer.model is None or not hasattr(self.xlsx_viewer.model, '_data') or self.xlsx_viewer.model._data is None or len(self.xlsx_viewer.model._data) == 0:
                    QMessageBox.warning(self, "无数据", "请先获取或导入餐厅数据")
                    self.complete_info_button.setEnabled(True)
                    if hasattr(self, 'progress_label'):
                        self.progress_label.setVisible(False)
                    return
                
                # 使用当前表格中的数据并保存到临时文件
                try:
                    restaurant_data = self.xlsx_viewer.model._original_data.copy()
                    LOGGER.info(f"从当前表格中获取 {len(restaurant_data)} 条餐厅记录")
                    
                    # 保存到临时文件
                    temp_dir = tempfile.gettempdir()
                    temp_dir = os.path.join(temp_dir, self.timestamp)
                    os.makedirs(temp_dir, exist_ok=True)
                    input_file = os.path.join(temp_dir, f"restaurant_data_{self.timestamp}.xlsx")
                    restaurant_data.to_excel(input_file, index=False)
                    LOGGER.info(f"已将餐厅数据保存到临时文件: {input_file}")
                    
                    # 记录临时文件以便清理
                    self.temp_files.append(input_file)
                    # 同时添加到CONF.runtime.temp_files
                    if hasattr(self.conf.runtime, 'temp_files'):
                        self.conf.runtime.temp_files.append(input_file)
                    
                except Exception as e:
                    LOGGER.error(f"复制当前表格数据时出错: {str(e)}")
                    QMessageBox.critical(self, "数据错误", f"无法处理当前表格数据: {str(e)}")
                    
                    # 设置定时器在2秒后恢复按钮
                    QTimer.singleShot(2000, lambda: self.complete_info_button.setEnabled(True))
                    
                    if hasattr(self, 'progress_label'):
                        self.progress_label.setVisible(False)
                    return
            
            # 获取当前CP的位置信息用于计算距离
            cp_location = None
            if hasattr(self, 'current_cp') and self.current_cp:
                cp_location = self.current_cp.get('cp_location', None)
                
                # 如果current_cp中没有cp_location，尝试从CONF.runtime.CP获取
                if not cp_location and hasattr(CONF, 'runtime') and hasattr(CONF.runtime, 'CP'):
                    cp_location = CONF.runtime.CP.get('cp_location', None)
                
                # 如果还是没有找到，尝试通过CP ID获取位置信息
                if not cp_location and self.current_cp.get('cp_id'):
                    try:
                        cp_data = CP.get(self.current_cp['cp_id'])
                        if cp_data and 'cp_location' in cp_data:
                            cp_location = cp_data['cp_location']
                            
                            # 更新current_cp和CONF.runtime.CP
                            self.current_cp['cp_location'] = cp_location
                            if hasattr(CONF, 'runtime') and hasattr(CONF.runtime, 'CP'):
                                CONF.runtime.CP['cp_location'] = cp_location
                    except Exception as e:
                        LOGGER.error(f"获取CP位置信息时出错: {str(e)}")
            
            LOGGER.info(f"使用CP位置: {cp_location}")
            
            # 创建输出目录
            try:
                temp_dir = tempfile.gettempdir()
                output_dir = os.path.join(temp_dir, self.timestamp)
                os.makedirs(output_dir, exist_ok=True)
                LOGGER.info(f"已创建输出目录: {output_dir}")
            except Exception as e:
                LOGGER.error(f"创建输出目录时出错: {str(e)}")
                temp_dir = tempfile.gettempdir()
                output_dir = os.path.join(temp_dir, self.timestamp)
                os.makedirs(output_dir, exist_ok=True)
                LOGGER.info(f"已创建备用输出目录: {output_dir}")
            
            # 生成任务ID
            task_id = str(uuid.uuid4()) + "_" + self.timestamp
            
            # 创建日志文件路径
            log_file = os.path.join(output_dir, f"log_{task_id}.txt")
            
            # 存储当前任务信息
            self.current_task = {
                'task_id': task_id,
                'output_dir': output_dir,
                'log_file': log_file,
                'start_time': datetime.now().isoformat()
            }
            
            # 构建命令行参数
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'services', 'scripts', 'complete_restaurants_info.py')
            
            # 创建临时配置文件，保存当前runtime配置
            runtime_config_file = os.path.join(output_dir, f"runtime_config.json")
            try:
                # 确保输出目录存在
                os.makedirs(output_dir, exist_ok=True)
                
                # 提取runtime配置
                runtime_config = {}
                if hasattr(self.conf, 'runtime'):
                    # 将runtime对象的所有非私有属性保存到字典
                    for attr in dir(self.conf.runtime):
                        if not attr.startswith('_'):  # 跳过私有属性
                            try:
                                value = getattr(self.conf.runtime, attr)
                                # 跳过方法和复杂对象
                                if callable(value):
                                    continue
                                
                                # 尝试将值转换为JSON可序列化的格式
                                if isinstance(value, (int, float, bool, str, list, dict)) or value is None:
                                    runtime_config[attr] = value
                                elif hasattr(value, '__dict__'):
                                    # 对于有__dict__属性的对象，尝试转换为字典
                                    runtime_config[attr] = value.__dict__
                                else:
                                    # 尝试转换为字符串
                                    runtime_config[attr] = str(value)
                            except Exception as e:
                                LOGGER.warning(f"无法序列化属性 {attr}: {str(e)}")
                                continue
                            
                # 保存到临时文件
                with open(runtime_config_file, 'w', encoding='utf-8') as f:
                    json.dump(runtime_config, f, ensure_ascii=False, indent=2, default=str)
                LOGGER.info(f"已将运行时配置保存到临时文件: {runtime_config_file}")
                
                # 记录临时文件以便清理
                self.temp_files.append(runtime_config_file)
                # 同时添加到CONF.runtime.temp_files
                if hasattr(self.conf.runtime, 'temp_files'):
                    self.conf.runtime.temp_files.append(runtime_config_file)
            except Exception as e:
                LOGGER.error(f"保存运行时配置失败: {e}")
                runtime_config_file = None
            
            cmd = [
                sys.executable,  # Python解释器
                script_path,
                f"--input_file={input_file}",
                f"--output_dir={output_dir}",
                f"--task_id={task_id}",
                f"--num_workers=3",  # 使用3个工作线程
                f"--batch_size=20",   # 批次大小为20
                f"--log_file={log_file}"  # 指定日志文件
            ]
            
            # 添加运行时配置文件参数
            if runtime_config_file and os.path.exists(runtime_config_file):
                cmd.append(f"--config_file={runtime_config_file}")
            
            # 如果有CP位置，添加到命令行
            if cp_location:
                cmd.append(f"--cp_location={cp_location}")
            
            # 状态文件路径
            status_file = os.path.join(output_dir, f"status_{task_id}.json")
            result_file = os.path.join(output_dir, f"result_{task_id}.xlsx")
            
            # 记录到临时文件列表
            self.temp_files.append(status_file)
            self.temp_files.append(result_file)
            self.temp_files.append(log_file)
            
            # 同时添加到CONF.runtime.temp_files
            if hasattr(self.conf.runtime, 'temp_files'):
                self.conf.runtime.temp_files.append(status_file)
                self.conf.runtime.temp_files.append(result_file)
                self.conf.runtime.temp_files.append(log_file)
            
            # 添加查看日志按钮（如果不存在）
            if not hasattr(self, 'view_log_button'):
                self.view_log_button = QPushButton("打开文件目录")
                self.view_log_button.setStyleSheet("margin-left: 10px;")
                self.view_log_button.clicked.connect(self.view_current_log)
                # 添加到合适的布局中，根据您的UI结构调整
                if hasattr(self, 'complete_button_layout') and self.complete_button_layout:
                    self.complete_button_layout.addWidget(self.view_log_button)
                else:
                    # 尝试创建一个水平布局放置在现有进度标签下方
                    if not hasattr(self, 'log_layout'):
                        self.log_layout = QHBoxLayout()
                        self.layout.addLayout(self.log_layout)
                    self.log_layout.addWidget(self.view_log_button)
            
            # 显示日志按钮
            self.view_log_button.setVisible(True)
            
            # 将命令转换为字符串
            cmd_str = ' '.join(cmd)
            
            # 根据平台使用不同的启动方式
            if sys.platform == 'win32':  # Windows
                # 在Windows上使用start命令打开新的CMD窗口
                start_cmd = f'start cmd /k "{cmd_str}"'
                os.system(start_cmd)
                LOGGER.info(f"已在Windows新窗口启动命令: {cmd_str}")
            elif sys.platform == 'darwin':  # macOS
                # 在Mac上使用Terminal运行
                script_content = f"""
                #!/bin/bash
                cd "{os.getcwd()}"
                {cmd_str}
                echo "按任意键关闭窗口..."
                read -n 1
                """
                
                # 创建临时脚本文件
                script_file = os.path.join(output_dir, f"run_script_{task_id}.sh")
                with open(script_file, 'w') as f:
                    f.write(script_content)
                
                # 添加执行权限
                os.chmod(script_file, 0o755)
                
                # 使用Terminal运行脚本
                mac_cmd = f"open -a Terminal {script_file}"
                os.system(mac_cmd)
                
                # 记录临时文件
                self.temp_files.append(script_file)
                if hasattr(self.conf.runtime, 'temp_files'):
                    self.conf.runtime.temp_files.append(script_file)
                
                LOGGER.info(f"已在macOS新窗口启动命令: {cmd_str}")
            else:  # Linux等其他系统
                # 使用终端模拟器
                linux_cmd = f"xterm -e '{cmd_str}; echo \"按回车键关闭窗口...\"; read'"
                os.system(linux_cmd)
                LOGGER.info(f"已在Linux新窗口启动命令: {cmd_str}")
            
            # 记录日志
            LOGGER.info(f"已在新窗口启动命令: {cmd_str}")
            
            # 隐藏进度标签
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 设置定时器在2秒后恢复按钮
            QTimer.singleShot(2000, lambda: self.complete_info_button.setEnabled(True))
            
        except Exception as e:
            LOGGER.error(f"启动餐厅信息补全时出错: {str(e)}")
            QMessageBox.critical(self, "操作失败", f"启动餐厅信息补全时出错: {str(e)}")
            
            # 设置定时器在2秒后恢复按钮
            QTimer.singleShot(2000, lambda: self.complete_info_button.setEnabled(True))
            
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            if hasattr(self, 'view_log_button'):
                self.view_log_button.setVisible(False)
    
    def check_complete_status(self):
        """检查补全任务状态"""
        try:
            # 如果取消标志被设置，停止轮询
            if hasattr(self, 'cancel_complete_task') and self.cancel_complete_task:
                if hasattr(self, 'monitor_timer'):
                    self.monitor_timer.stop()
                
                # 终止进程
                if hasattr(self, 'complete_process') and self.complete_process:
                    try:
                        self.complete_process.terminate()
                    except:
                        pass
                
                self.complete_task_running = False
                self.complete_info_button.setText("补全餐厅信息")
                if hasattr(self, 'progress_label'):
                    self.progress_label.setText("操作已取消")
                    self.progress_label.setVisible(False)
                
                LOGGER.info("补全任务已取消")
                return
            
            # 检查进程是否仍在运行
            if hasattr(self, 'complete_process') and self.complete_process:
                returncode = self.complete_process.poll()
                
                # 检查状态文件
                output_dir = tempfile.gettempdir()
                output_dir = os.path.join(output_dir, self.timestamp)
                if hasattr(self, 'complete_start_time'):
                    # 检查是否超时
                    elapsed_time = time.time() - self.complete_start_time
                    if elapsed_time > self.complete_timeout:
                        LOGGER.warning("补全任务超时")
                        self.monitor_timer.stop()
                        self.complete_process.terminate()
                        self.complete_task_running = False
                        self.complete_info_button.setText("补全餐厅信息")
                        if hasattr(self, 'progress_label'):
                            self.progress_label.setText("操作已超时")
                            self.progress_label.setVisible(False)
                        QMessageBox.warning(self, "任务超时", "补全餐厅信息任务运行时间过长，已自动终止")
                        return
                
                # 查找状态文件
                status_files = [f for f in os.listdir(output_dir) if f.startswith("status_") and f.endswith(".json")]
                
                if status_files:
                    # 找到最新的状态文件
                    status_file = os.path.join(output_dir, sorted(status_files)[-1])
                    
                    try:
                        with open(status_file, 'r', encoding='utf-8') as f:
                            status_data = json.load(f)
                            
                            # 更新进度
                            if 'message' in status_data:
                                self.update_progress(status_data['message'])
                            
                            # 检查任务是否完成
                            if 'status' in status_data:
                                if status_data['status'] == 'completed':
                                    # 任务成功完成
                                    self.on_complete_process_finished(status_data)
                                    return
                                elif status_data['status'] == 'failed':
                                    # 任务失败
                                    error_msg = status_data.get('error', '未知错误')
                                    self.on_complete_process_error(error_msg)
                                    return
                    except Exception as e:
                        LOGGER.error(f"读取状态文件失败: {e}")
                
                # 如果进程已结束但未找到状态文件或状态不是成功/失败
                if returncode is not None:
                    if returncode == 0:
                        # 进程正常结束，但可能没有状态文件
                        # 尝试查找结果文件
                        result_files = [f for f in os.listdir(output_dir) if f.startswith("result_") and f.endswith(".xlsx")]
                        if result_files:
                            result_file = os.path.join(output_dir, sorted(result_files)[-1])
                            status_data = {
                                "status": "completed",
                                "result_file": result_file,
                                "message": "处理完成",
                                "progress": 100
                            }
                            self.on_complete_process_finished(status_data)
                        else:
                            # 没有找到结果文件，认为失败
                            self.on_complete_process_error("处理完成，但未找到结果文件")
                    else:
                        # 进程异常结束
                        stderr_output = self.complete_process.stderr.read().decode('utf-8', errors='ignore') if self.complete_process.stderr else "未知错误"
                        self.on_complete_process_error(f"进程异常结束，返回码: {returncode}\n{stderr_output[:500]}")
                    
                    # 停止计时器
                    self.monitor_timer.stop()
                    return
            else:
                # 没有进程对象，停止计时器
                self.monitor_timer.stop()
                self.complete_task_running = False
                self.complete_info_button.setText("补全餐厅信息")
                if hasattr(self, 'progress_label'):
                    self.progress_label.setVisible(False)
                
        except Exception as e:
            LOGGER.error(f"检查补全任务状态时出错: {str(e)}")
            # 出错时停止计时器
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()
            
            self.complete_task_running = False
            self.complete_info_button.setText("补全餐厅信息")
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
    
    def on_complete_process_finished(self, status_data):
        """补全进程成功完成"""
        try:
            # 停止计时器
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()
            
            # 清理标志
            self.complete_task_running = False
            
            # 恢复按钮文本
            self.complete_info_button.setText("补全餐厅信息")
            
            # 隐藏进度标签
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 获取结果文件路径
            result_file = status_data.get('result_file')
            if not result_file and 'task_id' in status_data:
                # 尝试构造结果文件路径
                result_file = os.path.join(tempfile.gettempdir(), f"result_{status_data['task_id']}.xlsx")
            
            # 保存为最后一次查询的文件
            if result_file and os.path.exists(result_file):
                self.last_query_file = result_file
                
                # 尝试加载结果
                try:
                    # 从文件加载数据
                    result_data = pd.read_excel(result_file)
                    
                    # 更新UI
                    if len(result_data) > 0:
                        # 限制显示行数
                        max_display_rows = 10
                        if len(result_data) > max_display_rows:
                            display_data = result_data.head(max_display_rows).copy()
                            display_message = f"数据量过大，只显示前 {max_display_rows} 行"
                        else:
                            display_data = result_data.copy()
                            display_message = None
                        
                        # 更新表格
                        self.xlsx_viewer.load_data(data=display_data)
                        
                        # 显示成功消息
                        completed = status_data.get('completed', '未知')
                        total = status_data.get('total', '未知')
                        total_time = status_data.get('total_process_time', '未知')
                        
                        message = f"已补全 {completed}/{total} 家餐厅的信息。\n"
                        if total_time != '未知':
                            message += f"总耗时: {total_time}\n\n"
                        else:
                            message += "\n"
                            
                        if display_message:
                            message += display_message + "\n\n"
                        message += f"补全后的数据已保存到文件：\n{result_file}"
                        
                        # 创建带"打开文件"按钮的消息框
                        msg_box = QMessageBox(self)
                        msg_box.setWindowTitle("补全完成")
                        msg_box.setText(message)
                        msg_box.setIcon(QMessageBox.Information)
                        
                        # 添加打开文件按钮
                        open_button = msg_box.addButton("打开完整数据", QMessageBox.ActionRole)
                        view_log_button = msg_box.addButton("打开输出目录", QMessageBox.ActionRole)
                        close_button = msg_box.addButton("关闭", QMessageBox.RejectRole)
                        
                        # 显示消息框并处理响应
                        msg_box.exec_()
                        
                        # 处理按钮点击
                        clicked_button = msg_box.clickedButton()
                        if clicked_button == open_button:
                            self.open_file_external(result_file)
                        elif clicked_button == view_log_button:
                            # 查看日志文件
                            log_file = status_data.get('log_file')
                            if log_file and os.path.exists(log_file):
                                self.open_file_external(log_file)
                            else:
                                QMessageBox.warning(self, "日志不存在", "未找到处理日志文件")
                                self.view_current_log()  # 尝试查找其他日志文件
                    else:
                        QMessageBox.warning(self, "补全结果为空", "补全操作完成，但结果为空")
                        
                except Exception as e:
                    LOGGER.error(f"加载补全结果时出错: {str(e)}")
                    QMessageBox.warning(self, "加载结果失败", f"补全操作完成，但加载结果时出错: {str(e)}")
            else:
                QMessageBox.warning(self, "结果文件丢失", "补全操作完成，但找不到结果文件")
            
            # 清理进程
            if hasattr(self, 'complete_process') and self.complete_process:
                try:
                    if self.complete_process.poll() is None:
                        self.complete_process.terminate()
                except:
                    pass
                
                self.complete_process = None
        
        except Exception as e:
            LOGGER.error(f"处理补全完成事件时出错: {str(e)}")
            QMessageBox.critical(self, "处理错误", f"处理补全完成事件时出错: {str(e)}")
    
    def on_complete_process_error(self, error_msg):
        """补全进程出错"""
        try:
            # 停止计时器
            if hasattr(self, 'monitor_timer'):
                self.monitor_timer.stop()
            
            # 清理标志
            self.complete_task_running = False
            
            # 恢复按钮文本
            self.complete_info_button.setText("补全餐厅信息")
            
            # 隐藏进度标签
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 隐藏日志按钮
            if hasattr(self, 'view_log_button'):
                self.view_log_button.setVisible(False)
            
            # 显示错误信息和查看日志选项
            error_box = QMessageBox(self)
            error_box.setWindowTitle("补全失败")
            error_box.setText(f"补全餐厅信息时出错: {error_msg}")
            error_box.setIcon(QMessageBox.Critical)
            
            # 添加查看日志按钮
            view_log_button = error_box.addButton("打开输出目录", QMessageBox.ActionRole)
            close_button = error_box.addButton("关闭", QMessageBox.RejectRole)
            
            error_box.exec_()
            
            # 处理按钮点击
            if error_box.clickedButton() == view_log_button:
                self.view_current_log()
            
            # 清理进程
            if hasattr(self, 'complete_process') and self.complete_process:
                try:
                    if self.complete_process.poll() is None:
                        self.complete_process.terminate()
                except:
                    pass
                
                self.complete_process = None
                
        except Exception as e:
            LOGGER.error(f"处理补全错误事件时出错: {str(e)}")
    
    def verify_restaurant_status(self):
        """验证餐厅营业状态"""
        try:
            # 检查是否有数据
            if not hasattr(self.xlsx_viewer.model, '_original_data') or self.xlsx_viewer.model._original_data is None or len(self.xlsx_viewer.model._original_data) == 0:
                QMessageBox.warning(self, "无数据", "请先获取或导入餐厅数据")
                return
            
            # 显示进度信息
            if not hasattr(self, 'progress_label'):
                self.progress_label = QLabel("正在验证餐厅营业状态...")
                self.progress_label.setStyleSheet("color: #666; margin-top: 5px;")
                self.layout.addWidget(self.progress_label)
            else:
                self.progress_label.setText("正在验证餐厅营业状态...")
                self.progress_label.setVisible(True)
            
            # 更新UI
            QApplication.processEvents()
            
            # 禁用验证按钮，防止重复点击
            self.verify_status_button.setEnabled(False)
            
            # 百度地图API密钥
            baidu_ak = "IL2u8jUMS7mTa57VDISCAxXeYbDpihKs"
            
            # 准备数据统计
            import requests
            import json
            import time
            rows_count = len(self.xlsx_viewer.model._original_data)
            verified_count = 0
            open_count = 0
            closed_count = 0
            not_found_count = 0
            
            # 获取数据
            restaurant_data = self.xlsx_viewer.model._original_data.copy()
            
            # 添加状态列
            if 'operating_status' not in restaurant_data.columns:
                restaurant_data['operating_status'] = None
            
            # 进度更新间隔
            update_interval = max(1, min(10, rows_count // 10))  # 每处理10%的数据更新一次，但最少1个，最多10个
            
            # 设置超时和重试次数
            timeout = 5  # 请求超时时间(秒)
            max_retries = 2  # 最大重试次数
            
            # 批处理以避免API限制
            batch_size = 20  # 每批处理20条
            wait_time = 1  # 每批之间等待1秒
            
            # 创建会话对象
            session = requests.Session()
            
            # 开始验证
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            for i in range(0, rows_count, batch_size):
                # 处理当前批次
                end_idx = min(i + batch_size, rows_count)
                
                for j in range(i, end_idx):
                    try:
                        # 获取餐厅信息
                        restaurant = restaurant_data.iloc[j]
                        rest_name = restaurant.get('rest_chinese_name', '')
                        rest_city = restaurant.get('rest_city', '')
                        
                        if not rest_name or not rest_city:
                            # 跳过无效数据
                            LOGGER.warning(f"跳过第{j+1}行：餐厅名称或城市为空")
                            continue
                        
                        # 更新进度
                        if j % update_interval == 0 or j == rows_count - 1:
                            self.progress_label.setText(f"正在验证：{j+1}/{rows_count} - {rest_name}")
                            QApplication.processEvents()
                        
                        # 构建API请求URL
                        url = f"https://api.map.baidu.com/place/v2/search?query={rest_name}&tag=美食&region={rest_city}&output=json&ak={baidu_ak}"
                        
                        # 发送请求并重试
                        response = None
                        for attempt in range(max_retries + 1):
                            try:
                                response = session.get(url, timeout=timeout)
                                if response.status_code == 200:
                                    break
                            except requests.RequestException as e:
                                if attempt < max_retries:
                                    time.sleep(1)  # 重试前等待1秒
                                else:
                                    LOGGER.error(f"API请求失败: {e}")
                                    continue
                        
                        if not response or response.status_code != 200:
                            LOGGER.error(f"验证 {rest_name} 失败: 无法连接到API")
                            continue
                        
                        # 解析响应
                        result = response.json()
                        
                        if result.get('status') != 0:
                            LOGGER.warning(f"API返回错误: {result.get('message', '未知错误')}")
                            continue
                        
                        results = result.get('results', [])
                        verified_count += 1
                        
                        if not results:
                            # 没有找到结果
                            LOGGER.info(f"未找到餐厅 {rest_name} 的信息")
                            not_found_count += 1
                            restaurant_data.at[restaurant_data.index[j], 'operating_status'] = "非营业状态"
                            continue

                        if len(results) > 0:
                            results = results[0]
                        
                        # 检查营业状态
                        is_open = True
                        flag = results.get('status', '')
                        if flag == '':
                            is_open = True
                        else:
                            LOGGER.info(f"找到餐厅 {rest_name} 的信息: {flag} => 非营业状态")
                            is_open = False
                        
                        
                        # 更新计数和数据
                        if is_open:
                            open_count += 1
                            restaurant_data.at[restaurant_data.index[j], 'operating_status'] = "正常营业"
                        else:
                            closed_count += 1
                            restaurant_data.at[restaurant_data.index[j], 'operating_status'] = "非营业状态"
                        
                    except Exception as e:
                        LOGGER.error(f"处理第{j+1}行数据时出错: {str(e)}")
                        continue
                
                # 批次间等待
                if i + batch_size < rows_count:
                    time.sleep(wait_time)
            
            # 恢复光标
            QApplication.restoreOverrideCursor()
            
            # 更新表格
            self.xlsx_viewer.load_data(data=restaurant_data)
            
            # 显示验证结果
            QMessageBox.information(
                self, 
                "验证完成", 
                f"已验证 {verified_count}/{rows_count} 家餐厅的营业状态：\n\n"
                f"• 正常营业: {open_count} 家\n"
                f"• 非营业状态: {closed_count} 家\n"
                f"• 未找到: {not_found_count} 家\n"
                f"• 未验证: {rows_count - verified_count} 家"
            )
            
            LOGGER.info(f"验证了 {verified_count} 家餐厅的营业状态，{open_count} 家正常营业，{closed_count} 家非营业状态，{not_found_count} 家未找到")
            
            # 关闭会话
            session.close()
            
            # 保存验证结果
            try:
                # 创建临时目录
                temp_dir = tempfile.gettempdir()
                if not hasattr(self, 'timestamp'):
                    self.timestamp = time.strftime("%Y%m%d_%H%M%S")
                temp_dir = os.path.join(temp_dir, self.timestamp)
                os.makedirs(temp_dir, exist_ok=True)
                
                # 保存文件
                result_file = os.path.join(temp_dir, f"restaurant_status_{time.strftime('%Y%m%d_%H%M%S')}.xlsx")
                restaurant_data.to_excel(result_file, index=False)
                
                # 记录临时文件
                self.temp_files.append(result_file)
                if hasattr(self.conf.runtime, 'temp_files'):
                    self.conf.runtime.temp_files.append(result_file)
                
                LOGGER.info(f"验证结果已保存到: {result_file}")
                
                # 询问是否打开文件
                reply = QMessageBox.question(
                    self, 
                    "已保存验证结果", 
                    f"验证结果已保存到:\n{result_file}\n\n是否打开此文件？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.open_file_external(result_file)
            except Exception as e:
                LOGGER.error(f"保存验证结果时出错: {str(e)}")
                QMessageBox.warning(self, "保存失败", f"保存验证结果时出错: {str(e)}")
            
        except Exception as e:
            QApplication.restoreOverrideCursor()
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            LOGGER.error(f"验证餐厅营业状态时出错: {str(e)}")
            QMessageBox.critical(self, "操作失败", f"验证餐厅营业状态时出错: {str(e)}")
        finally:
            # 隐藏进度标签
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            
            # 重新启用验证按钮
            self.verify_status_button.setEnabled(True)
    
    def view_current_log(self):
        """打开当前任务的输出目录"""
        try:
            # 检查是否有当前任务
            if hasattr(self, 'current_task') and self.current_task and 'output_dir' in self.current_task:
                output_dir = self.current_task['output_dir']
                if os.path.exists(output_dir):
                    # 使用系统文件浏览器打开目录
                    self.open_file_external(output_dir)
                else:
                    QMessageBox.warning(self, "目录不存在", "任务输出目录不存在")
            else:
                # 使用时间戳目录
                if hasattr(self, 'timestamp'):
                    temp_dir = os.path.join(tempfile.gettempdir(), self.timestamp)
                    if os.path.exists(temp_dir):
                        self.open_file_external(temp_dir)
                    else:
                        QMessageBox.warning(self, "目录不存在", "临时输出目录不存在")
                else:
                    # 尝试打开临时目录
                    self.open_file_external(tempfile.gettempdir())
        except Exception as e:
            LOGGER.error(f"打开任务输出目录时出错: {str(e)}")
            QMessageBox.warning(self, "打开目录失败", f"无法打开输出目录: {str(e)}")
    
    def download_template(self):
        """下载餐厅模版数据"""
        try:
            # 获取保存位置
            save_path, _ = QFileDialog.getSaveFileName(
                self, "保存餐厅模版文件", "restaurant_template.xlsx", "Excel文件 (*.xlsx)"
            )
            
            if not save_path:
                return  # 用户取消
            
            # 从OSS获取模版文件路径
            template_path = f"CPs/template/restaurant_example.xlsx"
            try:
                file = oss_get_excel_file(template_path)
                file.to_excel(save_path, index=False)
                QMessageBox.information(self, "下载成功", f"餐厅模版文件已保存到: {save_path}")
                LOGGER.info(f"餐厅模版文件已下载到: {save_path}")
            except Exception as e:
                LOGGER.error(f"下载餐厅模版文件时出错: {str(e)}")
                QMessageBox.critical(self, "下载失败", f"下载餐厅模版文件时出错: {str(e)}")
                
        except Exception as e:
            LOGGER.error(f"下载餐厅模版数据时出错: {str(e)}")
            QMessageBox.critical(self, "下载失败", f"下载餐厅模版数据时出错: {str(e)}")
    
    def set_cleaned_in_close_event(self):
        """设置已在关闭事件中处理过临时文件的标志"""
        self.cleaned_in_close_event = True
    
    def get_restaurants_low_resource(self):
        """低资源版餐厅获取 - 在独立进程中运行"""
        try:
            # 获取城市名称
            city = self.city_input.text().strip()
            if not city:
                QMessageBox.warning(self, "请输入城市", "请先输入餐厅城市")
                return
            
            # 获取是否使用大模型
            use_llm = self.use_llm_checkbox.isChecked()
            
            # 创建临时目录 - 每次都创建新的唯一目录
            temp_base_dir = tempfile.gettempdir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]  # 添加唯一ID确保目录唯一
            city_safe = city.replace(" ", "_").replace("/", "_")
            output_dir = os.path.join(temp_base_dir, f"restaurants_{city_safe}_{timestamp}_{unique_id}")
            os.makedirs(output_dir, exist_ok=True)  # 立即创建目录
            
            # 检查是否存在同城市的已有结果
            existing_dirs = self.check_existing_city_results(city, temp_base_dir)
            
            keywords_to_search = []
            loaded_keywords = set()
            
            if existing_dirs:
                # 显示选择对话框
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("发现已有数据")
                msg_box.setText(f"发现 {len(existing_dirs)} 个同城市的已有搜索结果，是否加载？")
                msg_box.setIcon(QMessageBox.Question)
                
                # 列出已有目录信息
                details = "\n".join([f"- {d['name']} ({len(d['keywords'])} 个关键词)" for d in existing_dirs])
                msg_box.setDetailedText(details)
                
                load_button = msg_box.addButton("加载已有数据", QMessageBox.AcceptRole)
                skip_button = msg_box.addButton("跳过", QMessageBox.RejectRole)
                cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)
                
                msg_box.exec_()
                
                if msg_box.clickedButton() == cancel_button:
                    return
                elif msg_box.clickedButton() == load_button:
                    # 加载已有关键词
                    for dir_info in existing_dirs:
                        loaded_keywords.update(dir_info['keywords'])
                    LOGGER.info(f"已加载 {len(loaded_keywords)} 个已搜索的关键词")
            
            # 获取要搜索的关键词（这里暂时使用一些默认关键词，实际应该从配置或用户输入获取）
            all_keywords = self.get_search_keywords()  # 需要实现这个方法
            
            # 过滤掉已经搜索过的关键词
            keywords_to_search = [kw for kw in all_keywords if kw not in loaded_keywords]
            
            if not keywords_to_search and not loaded_keywords:
                # 如果没有关键词，执行全量搜索
                keywords_to_search = None
                LOGGER.info("执行全量餐厅搜索")
            else:
                LOGGER.info(f"需要搜索 {len(keywords_to_search)} 个新关键词")
            
            # 创建运行时配置文件
            runtime_config = {}
            if hasattr(self.conf, 'runtime'):
                for attr in dir(self.conf.runtime):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(self.conf.runtime, attr)
                            if not callable(value) and (isinstance(value, (int, float, bool, str, list, dict)) or value is None):
                                runtime_config[attr] = value
                        except:
                            pass
            
            config_file = os.path.join(output_dir, "runtime_config.json")
            os.makedirs(output_dir, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(runtime_config, f, ensure_ascii=False, indent=2)
            
            # 记录临时文件
            self.temp_files.append(output_dir)
            self.temp_files.append(config_file)
            if hasattr(self.conf.runtime, 'temp_files'):
                self.conf.runtime.temp_files.append(output_dir)
                self.conf.runtime.temp_files.append(config_file)
            
            # 构建命令
            script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     'services', 'scripts', 'search_restaurants.py')
            
            cmd = [
                sys.executable,
                script_path,
                f"--city={city}",
                f"--cp_id={self.current_cp['cp_id']}",
                f"--use_llm={use_llm}",
                f"--output_dir={output_dir}",
                f"--config_file={config_file}"
            ]
            
            # 添加关键词参数
            if keywords_to_search:
                cmd.append("--keywords")
                cmd.extend(keywords_to_search)
            
            # 将命令转换为字符串
            cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)
            
            # 保存任务信息
            self.current_low_resource_task = {
                'output_dir': output_dir,
                'city': city,
                'keywords': keywords_to_search,
                'loaded_dirs': [d['path'] for d in existing_dirs] if existing_dirs else [],
                'timestamp': timestamp
            }
            
            # 根据平台启动命令
            if sys.platform == 'win32':
                # Windows
                title = f"餐厅搜索 - {city}"
                start_cmd = f'start "{title}" cmd /k "{cmd_str} & echo. & echo 搜索完成，按任意键关闭窗口... & pause > nul"'
                os.system(start_cmd)
            elif sys.platform == 'darwin':
                # macOS
                script_content = f"""#!/bin/bash
cd "{os.getcwd()}"
{cmd_str}
echo ""
echo "搜索完成，按任意键关闭窗口..."
read -n 1
"""
                script_file = os.path.join(output_dir, "run_search.sh")
                with open(script_file, 'w') as f:
                    f.write(script_content)
                os.chmod(script_file, 0o755)
                os.system(f"open -a Terminal {script_file}")
                self.temp_files.append(script_file)
            else:
                # Linux
                os.system(f"xterm -e '{cmd_str}; echo \"搜索完成，按回车键关闭窗口...\"; read'")
            
            LOGGER.info(f"已启动低资源版餐厅搜索: {cmd_str}")
            
            # 显示提示信息
            message = (
                f"餐厅搜索已在新窗口中启动。\n"
                f"搜索城市: {city}\n"
                f"输出目录: {output_dir}\n\n"
                "搜索完成后，点击'加载搜索结果'按钮查看结果。"
            )
            QMessageBox.information(self, "搜索已启动", message)
            
            # 显示加载结果按钮
            if hasattr(self, 'load_search_results_button'):
                self.load_search_results_button.setVisible(True)
            
        except Exception as e:
            LOGGER.error(f"启动低资源版餐厅搜索时出错: {str(e)}")
            QMessageBox.critical(self, "启动失败", f"启动低资源版餐厅搜索时出错: {str(e)}")
    
    def check_existing_city_results(self, city, temp_base_dir):
        """检查临时目录中是否有同城市的已有结果"""
        existing_dirs = []
        
        try:
            if os.path.exists(temp_base_dir):
                for item in os.listdir(temp_base_dir):
                    item_path = os.path.join(temp_base_dir, item)
                    if os.path.isdir(item_path) and f"restaurants_{city}" in item:
                        # 检查目录中的状态文件
                        keywords = set()
                        status_files = [f for f in os.listdir(item_path) if f.startswith("status_") and f.endswith(".json")]
                        
                        for status_file in status_files:
                            try:
                                with open(os.path.join(item_path, status_file), 'r', encoding='utf-8') as f:
                                    status_data = json.load(f)
                                    if status_data.get('keyword'):
                                        keywords.add(status_data['keyword'])
                            except:
                                pass
                        
                        if status_files:  # 只添加有状态文件的目录
                            existing_dirs.append({
                                'path': item_path,
                                'name': item,
                                'keywords': keywords,
                                'file_count': len([f for f in os.listdir(item_path) if f.endswith('.xlsx')])
                            })
        except Exception as e:
            LOGGER.error(f"检查已有结果时出错: {str(e)}")
        
        return existing_dirs
    
    def get_search_keywords(self):
        """获取要搜索的关键词列表"""
        try:
            # 从配置中获取关键词
            keywords = self.conf.get("BUSINESS.RESTAURANT.关键词", default=[])
            if keywords:
                LOGGER.info(f"从配置中获取到 {len(keywords)} 个关键词: {keywords}")
                return keywords
            else:
                # 如果配置中没有关键词，使用默认关键词
                default_keywords = [
                    "火锅", "烧烤", "中餐", "西餐", "快餐", 
                    "面馆", "粉店", "小吃", "咖啡", "茶饮",
                    "日料", "韩餐", "烤肉", "海鲜", "素食"
                ]
                LOGGER.info(f"配置中无关键词，使用默认关键词: {default_keywords}")
                return default_keywords
        except Exception as e:
            LOGGER.error(f"获取搜索关键词时出错: {str(e)}")
            # 返回默认关键词
            return ["火锅", "烧烤", "中餐", "西餐", "快餐"]
    
    def load_low_resource_results(self):
        """加载低资源版搜索结果"""
        try:
            if not hasattr(self, 'current_low_resource_task') or not self.current_low_resource_task:
                QMessageBox.warning(self, "无任务信息", "没有找到搜索任务信息")
                return
            
            task_info = self.current_low_resource_task
            output_dir = task_info['output_dir']
            
            if not os.path.exists(output_dir):
                QMessageBox.warning(self, "目录不存在", f"输出目录不存在: {output_dir}")
                return
            
            # 收集所有结果文件
            all_result_files = []
            
            # 从当前任务目录收集
            for file_name in os.listdir(output_dir):
                if file_name.endswith('.xlsx') and file_name.startswith('restaurants_'):
                    all_result_files.append(os.path.join(output_dir, file_name))
            
            # 从已加载的目录收集
            for loaded_dir in task_info.get('loaded_dirs', []):
                if os.path.exists(loaded_dir):
                    for file_name in os.listdir(loaded_dir):
                        if file_name.endswith('.xlsx') and file_name.startswith('restaurants_'):
                            all_result_files.append(os.path.join(loaded_dir, file_name))
            
            if not all_result_files:
                QMessageBox.warning(self, "无结果文件", "未找到任何搜索结果文件")
                return
            
            LOGGER.info(f"找到 {len(all_result_files)} 个结果文件")
            
            # 合并所有结果
            all_data = []
            for file_path in all_result_files:
                try:
                    data = pd.read_excel(file_path)
                    all_data.append(data)
                    LOGGER.info(f"已加载 {len(data)} 条记录从: {file_path}")
                except Exception as e:
                    LOGGER.error(f"加载文件失败 {file_path}: {e}")
            
            if not all_data:
                QMessageBox.warning(self, "加载失败", "无法加载任何结果文件")
                return
            
            # 合并数据
            merged_data = pd.concat(all_data, ignore_index=True)
            
            # 去重
            if 'rest_chinese_name' in merged_data.columns and 'rest_chinese_address' in merged_data.columns:
                merged_data = merged_data.drop_duplicates(
                    subset=['rest_chinese_name', 'rest_chinese_address'], 
                    keep='first'
                )
            
            LOGGER.info(f"合并后共 {len(merged_data)} 条记录")
            
            # 保存合并结果
            merged_file = os.path.join(output_dir, f"merged_restaurants_{task_info['city']}_{task_info['timestamp']}.xlsx")
            merged_data.to_excel(merged_file, index=False)
            self.temp_files.append(merged_file)
            if hasattr(self.conf.runtime, 'temp_files'):
                self.conf.runtime.temp_files.append(merged_file)
            
            # 显示前10条记录
            display_data = merged_data.head(10).copy()
            self.xlsx_viewer.load_data(data=display_data)
            
            # 保存为最后查询文件
            self.last_query_file = merged_file
            
            # 显示成功消息
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("加载成功")
            msg_box.setText(
                f"餐厅数据加载完成！\n\n"
                f"总记录数: {len(merged_data)}\n"
                f"合并自 {len(all_result_files)} 个文件\n\n"
                f"完整数据已保存到:\n{merged_file}"
            )
            msg_box.setIcon(QMessageBox.Information)
            
            open_button = msg_box.addButton("打开完整数据", QMessageBox.ActionRole)
            view_dir_button = msg_box.addButton("打开输出目录", QMessageBox.ActionRole)
            close_button = msg_box.addButton("关闭", QMessageBox.RejectRole)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == open_button:
                self.open_file_external(merged_file)
            elif msg_box.clickedButton() == view_dir_button:
                self.open_file_external(output_dir)
            
            # 隐藏加载按钮
            if hasattr(self, 'load_search_results_button'):
                self.load_search_results_button.setVisible(False)
            
        except Exception as e:
            LOGGER.error(f"加载搜索结果时出错: {str(e)}")
            QMessageBox.critical(self, "加载失败", f"加载搜索结果时出错: {str(e)}")
