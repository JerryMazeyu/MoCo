from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                            QPushButton, QFileDialog, QMessageBox, QHBoxLayout, QApplication, QTableView)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QBrush, QColor
import pandas as pd
import sys
import os
import platform
import subprocess
from app.utils import oss_put_excel_file,oss_rename_excel_file, oss_get_excel_file
from datetime import datetime

class PandasModel(QAbstractTableModel):
    """Pandas数据模型，用于在QTableView中显示pandas DataFrame数据"""
    
    def __init__(self, data=None):
        super().__init__()
        self._data = pd.DataFrame() if data is None else data
        self._original_data = None  # 初始化为None，等待外部设置
        self.modified = False
        
        # 数据缓存，用于提高大数据集显示性能
        self._cache = {}
        self._cache_size = 1000  # 最大缓存项数
        
        # 为大型数据集优化
        self._row_limit = 100000  # 处理的最大行数
        self._column_mapping = None  # 添加列映射属性
        self._reverse_mapping = None  # 添加反向映射属性
    
    def rowCount(self, parent=None):
        return len(self._data)
    
    def columnCount(self, parent=None):
        return len(self._data.columns)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        row, col = index.row(), index.column()
        
        # 检查是否超出范围
        if row < 0 or row >= len(self._data) or col < 0 or col >= len(self._data.columns):
            return QVariant()
        
        # 获取单元格的值
        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self._data.iloc[row, col]
            
            try:
                # 处理不同类型的值
                if pd.isna(value):
                    result = "" if role == Qt.EditRole else "NA"
                elif isinstance(value, (float, int)):
                    result = str(value)
                else:
                    result = str(value)
            except:
                result = ""
            
            return result
            
        # 对比原始数据，如果发生变化则显示不同的颜色
        elif role == Qt.BackgroundRole:
            if self.modified:
                try:
                    if str(self._data.iloc[row, col]) != str(self._original_data.iloc[row, col]):
                        return QBrush(QColor(255, 255, 200))  # 淡黄色背景表示修改过的单元格
                except:
                    pass
        
        # 文本对齐
        elif role == Qt.TextAlignmentRole:
            value = self._data.iloc[row, col]
            if isinstance(value, (int, float)):
                return Qt.AlignRight | Qt.AlignVCenter  # 数字右对齐
            return Qt.AlignLeft | Qt.AlignVCenter  # 文本左对齐
                
        return QVariant()
    
    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        row, col = index.row(), index.column()
        
        try:
            # 获取当前列的中文名
            display_col = self._data.columns[col]
            # 获取对应的英文字段名
            original_col = self._reverse_mapping.get(display_col, display_col)
            
            # 尝试转换为原数据类型
            if self._original_data is not None:
                current_type = type(self._original_data.iloc[row, original_col])
                if current_type == int:
                    value = int(value)
                elif current_type == float:
                    value = float(value)
                elif pd.isna(self._original_data.iloc[row, original_col]) and value.strip() == "":
                    value = pd.NA
            
            # 更新显示数据
            self._data.iloc[row, col] = value
            
            # 更新原始数据
            if self._original_data is not None and original_col in self._original_data.columns:
                self._original_data.iloc[row, original_col] = value
            
            # 标记为已修改
            self.modified = True
            
            # 清除缓存
            self._cache.clear()
            
            # 发出数据更改信号
            self.dataChanged.emit(index, index)
            self.layoutChanged.emit()
            
            return True
        except Exception as e:
            print(f"设置数据错误: {str(e)}")
            return False
    
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        
        if orientation == Qt.Horizontal:
            return str(self._data.columns[section])
        else:
            return str(section + 1)  # 行号从1开始
    
    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
    
    def setDataFrame(self, dataframe):
        """设置新的DataFrame数据"""
        try:
            if len(dataframe) > self._row_limit:
                print(f"警告: 数据行数 ({len(dataframe)}) 超过显示限制 ({self._row_limit})，性能可能受影响")
            
            self.beginResetModel()
            self._cache.clear()
            self._data = dataframe
            self.modified = False
            import gc
            gc.collect()
            self.endResetModel()
        except Exception as e:
            print(f"设置DataFrame时出错: {str(e)}")
            self.endResetModel()
            raise
    
    def getDataFrame(self):
        """获取当前DataFrame数据"""
        return self._data
    
    def isModified(self):
        """检查数据是否被修改"""
        return self.modified
    
    def resetModified(self):
        """重置修改状态"""
        self.modified = False
        self._original_data = self._data.copy()

    def set_column_mapping(self, mapping):
        """设置列映射"""
        self._column_mapping = mapping
        self._reverse_mapping = {v: k for k, v in mapping.items()}

    def get_original_data(self):
        """获取原始数据"""
        if self._original_data is None:
            return self._data
        return self._original_data

class XlsxViewerWidget(QWidget):
    """Excel表格查看器组件，用于展示和编辑Excel数据"""
    
    def __init__(self, parent=None,use_oss=False,oss_path=None,show_open=True, show_save=True, 
             show_save_as=True, show_refresh=True, display_columns=None):
        super().__init__(parent)
        self.current_file = None
        self.use_oss = use_oss
        self.oss_path = oss_path
        self.display_columns = display_columns  # 新增：要显示的列配置
        self._original_data = None  # 存储原始数据
        
        # 添加字段映射配置
        self.column_mapping = {
            # 餐厅信息字段映射
            'rest_chinese_name': '餐厅中文名',
            'rest_english_name': '餐厅英文名',
            'rest_city': '城市',
            'rest_chinese_address': '中文地址',
            'rest_district': '区域',
            'rest_street': '街道',
            'rest_contact_person': '联系人',
            'rest_contact_phone': '联系电话',
            'rest_location': '位置',
            'rest_distance': '距离',
            'rest_type': '餐厅类型',
            
            # 车辆信息字段映射
            'vehicle_license_plate': '车牌号',
            'vehicle_driver_name': '司机姓名',
            'vehicle_type': '车辆类型',
            'vehicle_rough_weight': '毛重',
            'vehicle_tare_weight': '皮重',
            'vehicle_cooldown_days': '冷却天数',
            'vehicle_status': '车辆状态',
            'vehicle_last_use': '最后使用日期',
            
            # 收油表字段映射
            'rr_date': '收油日期',
            'rr_restaurant_name': '餐厅名称',
            'rr_restaurant_address': '餐厅地址',
            'rr_district': '区域',
            'rr_contact_person': '联系人',
            'rr_street': '街道',
            'rr_vehicle_license_plate': '车牌号',
            'rr_amount': '桶数180KG/桶',
            'rr_amount_of_day': '当日总数',
            'rr_serial_number': '流水号',
            'rr_sale_number': '销售单号',
            
            # 平衡表字段映射
            'balance_date': '交付日期',
            'balance_oil_type': '货物类型',
            'balance_tranport_type': '运输方式',
            'balance_serial_number': '流水号',
            'balance_vehicle_license_plate': '车牌号',
            'balance_weight_of_order': '榜单净重',
            'balance_order_number': '磅单编号',
            'balance_district': '收集城市',
            'balance_sale_number': '销售合同号',
            'balance_amount_of_day': '当日收油总数',
            
            # 总表字段映射
            'total_sale_number_detail': '合同分配明细',
            'total_supplied_date': '供应日期',
            'total_delivery_trucks_vehicle_registration_no': '车牌号',
            'total_volume_per_trucks': '每车吨量/吨',
            'total_weighbridge_ticket_number': '过磅单编号',
            'total_collection_city': '收集城市',
            'total_iol_mt': '毛油库存',
            'total_processing_quantity': '加工量',
            'total_output_quantity': '产出重量（MT）',
            'total_conversion_coefficient': '转化系数',
            'total_customer': '客户',
            'total_sale_number': '合同分配',
            'total_quantities_sold': '售出数量(MT)',
            'total_ending_inventory': '期末库存(MT)',
            'total_delivery_time': '出厂时间',
            'total_delivery_address': '出厂去向',
            'total_supplied_weight_of_order': '榜单净重',
            
            # 收货确认书字段映射
            'check_belong_cp': '所属CP',
            'check_date': '提货日期',
            'check_name': '名称',
            'check_description_of_material': '描述',
            'check_truck_plate_no': '车牌号',
            'check_weight': '重量',
            'check_quantity': '司机',
            'check_weighbridge_ticket_number': '磅单号',
            'check_gross_weight': '毛重',
            'check_tare_weight': '皮重',
            'check_net_weight': '净重',
            'check_unload_weight': '卸货重量',
            'check_difference': '差值'
        }
        
        # 保存按钮显示状态
        self.show_open = show_open
        self.show_save = show_save
        self.show_save_as = show_save_as
        self.show_refresh = show_refresh
        self.initUI()
    
    def initUI(self):
        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建表格视图
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #d3d3d3;
                gridline-color: #f0f0f0;
                selection-background-color: #0078d7;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d3d3d3;
                font-weight: bold;
            }
        """)
        
        # 初始化空模型
        self.model = PandasModel()
        self.table_view.setModel(self.model)
        
        # 设置表头
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 5, 0, 0)  # 顶部间距，使按钮与表格有一定间隔
        button_width = 90  # 固定宽度
        # 创建按钮
        # 根据设置创建并添加按钮
        if self.show_open:
            self.open_button = QPushButton("打开文件")
            self.open_button.setFixedWidth(button_width)
            self.open_button.clicked.connect(self.open_file)
            button_layout.addWidget(self.open_button)
            button_layout.addStretch(1)
        
        if self.show_save:
            self.save_button = QPushButton("保存")
            self.save_button.setFixedWidth(button_width)
            self.save_button.clicked.connect(self.save_file)
            button_layout.addWidget(self.save_button)
            button_layout.addStretch(1)
        
        if self.show_save_as:
            self.save_as_button = QPushButton("另存为")
            self.save_as_button.setFixedWidth(button_width)
            self.save_as_button.clicked.connect(self.save_file_as)
            button_layout.addWidget(self.save_as_button)
            button_layout.addStretch(1)
        
        if self.show_refresh:
            self.refresh_button = QPushButton("刷新")
            self.refresh_button.setFixedWidth(button_width)
            self.refresh_button.clicked.connect(self.refresh)
            button_layout.addWidget(self.refresh_button)
        
        # 先添加表格到主布局，再添加按钮
        self.layout.addWidget(self.table_view)
        self.layout.addLayout(button_layout)
    
    def load_data(self, file_path=None, data=None):
        """加载数据，可以是文件路径或pandas DataFrame"""
        try:
            # 记录开始时间，用于性能监控
            start_time = datetime.now()
            
            if file_path is not None:
                # 加载Excel文件
                if file_path.endswith(('.xlsx', '.xls')):
                    data = pd.read_excel(file_path)
                # 加载CSV文件
                elif file_path.endswith('.csv'):
                    data = pd.read_csv(file_path)
                else:
                    raise ValueError("不支持的文件类型")
                
                self.current_file = file_path
            
            if data is not None:
                # 保存原始数据
                self._original_data = data.copy()
                
                # 数据行数检查
                row_count = len(data)
                
                # 如果数据超过10000行，给出警告并询问是否继续
                if row_count > 10000:
                    reply = QMessageBox.question(
                        self, '大数据集警告', 
                        f'数据集包含 {row_count} 行，加载可能需要较长时间并消耗大量内存。\n是否继续加载?',
                        QMessageBox.Yes | QMessageBox.No, 
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.No:
                        return False
                
                # 处理大型数据集时使用分批加载机制
                if row_count > 1000:
                    # 确保UI响应
                    QApplication.processEvents()
                    
                # 如果有显示列配置，只显示指定的列
                if self.display_columns and isinstance(data, pd.DataFrame):
                    # 确保所有配置的列都存在
                    valid_columns = [col for col in self.display_columns if col in data.columns]
                    if valid_columns:
                        display_data = data[valid_columns].copy()
                    else:
                        display_data = data.copy()
                else:
                    display_data = data.copy()
                
                # 重命名列名为中文
                display_data = display_data.rename(columns=self.column_mapping)
                
                # 设置数据模型
                self.model = PandasModel(display_data)  # 创建新的模型实例
                self.model.set_column_mapping(self.column_mapping)  # 设置列映射
                self.model._original_data = self._original_data  # 设置原始数据
                self.table_view.setModel(self.model)  # 设置模型到视图
                
                # 记录结束时间并计算耗时
                end_time = datetime.now()
                time_spent = (end_time - start_time).total_seconds()
                
                if time_spent > 1.0:  # 如果加载时间超过1秒，记录性能信息
                    print(f"数据加载耗时: {time_spent:.2f} 秒 (行数: {row_count})")
                
                # 确保UI更新
                QApplication.processEvents()
                
                # 自动调整列宽
                self.table_view.resizeColumnsToContents()
                
                return True
        except MemoryError:
            QMessageBox.critical(self, "内存错误", "数据集太大，内存不足。请尝试减少数据量。")
            return False
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"无法加载数据: {str(e)}")
            return False
    
    def open_file(self):
        """打开文件对话框"""
        if self.model.isModified():
            reply = QMessageBox.question(
                self, '确认', '当前数据已修改，是否保存？',
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开Excel文件", "", "Excel文件 (*.xlsx *.xls);;CSV文件 (*.csv);;所有文件 (*.*)"
        )
        
        if file_path:
            self.load_data(file_path)
    
    def save_file(self):
        """保存文件"""
        if self.use_oss:
            current_time = datetime.now().strftime("%Y%m%d%H%M%S")
            # 分离文件名和扩展名
            path_parts = self.oss_path.split('/')
    
            # 获取最后的文件名
            file_name_with_ext = path_parts[-1]  # 获取最后的文件名（包括扩展名）
            
            # 分离文件名和扩展名
            name, ext = os.path.splitext(file_name_with_ext)  # 分离文件名和扩展名
            
            
            # 创建新的文件名
            new_file_name = f"{name}_{current_time}{ext}"  # 添加当前时间到文件名
            
            # 组合新的文件路径
            oss_rename_file = '/'.join(path_parts[:-1]) + '/' + new_file_name  # 组合路径和新文件名
            
            # 获取最新的数据
            data_to_save = self.model.getDataFrame()
            # print("Saving data to OSS:", data_to_save)  # 调试输出
            
            # 保存到 OSS
            oss_rename_excel_file(self.oss_path, oss_rename_file)
            oss_put_excel_file(self.oss_path, data_to_save)

            self.model.resetModified()
            QMessageBox.information(self, "保存成功", f"文件已保存: {self.oss_path}")
            return True
        
        else:
            if not self.current_file:
                return self.save_file_as()
            
            try:
                data = self.model.getDataFrame()
                
                # 根据文件类型保存
                if self.current_file.endswith(('.xlsx', '.xls')):
                    data.to_excel(self.current_file, index=False)
                elif self.current_file.endswith('.csv'):
                    data.to_csv(self.current_file, index=False)
                
                self.model.resetModified()
                QMessageBox.information(self, "保存成功", f"文件已保存: {self.current_file}")
                return True
            except Exception as e:
                QMessageBox.critical(self, "保存错误", f"无法保存文件: {str(e)}")
                return False
    """另存为文件到本地"""
    def save_file_as(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存Excel文件", "", "Excel文件 (*.xlsx);;CSV文件 (*.csv)"
            )
            
            if not file_path:
                return False
            
            # 确保文件有正确的扩展名
            if not file_path.endswith(('.xlsx', '.xls', '.csv')):
                file_path += '.xlsx'
            
            # 获取当前数据
            data = self.model.getDataFrame()
            if data is None or data.empty:
                QMessageBox.warning(self, "保存失败", "没有数据可以保存")
                return False
                
            # 根据文件扩展名选择保存格式
            try:
                if file_path.endswith('.csv'):
                    data.to_csv(file_path, index=False, encoding='utf-8-sig')
                else:
                    data.to_excel(file_path, index=False)
                
                QMessageBox.information(self, "保存成功", f"文件已保存到：{file_path}")
                return True
                
            except PermissionError:
                QMessageBox.critical(self, "保存失败", "无法保存文件，可能是文件被其他程序占用或没有写入权限")
                return False
            except Exception as e:
                QMessageBox.critical(self, "保存失败", f"保存文件时出错：{str(e)}")
                return False
                
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存文件时出错：{str(e)}")
            return False
    
    def refresh(self):
        """刷新当前文件数据"""
        if self.use_oss:
            # 从 OSS 读取数据
            try:
                if self.model.isModified():
                    reply = QMessageBox.question(
                        self, '确认', '当前数据已修改，是否保存？',
                        QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                    )
                    
                    if reply == QMessageBox.Save:
                        self.save_file()  # 保存数据
                    elif reply == QMessageBox.Cancel:
                        return  # 取消刷新
                
                if self.oss_path:
                    # 读取 OSS 中的数据
                    data = oss_get_excel_file(self.oss_path)
                    if data is not None:
                        self.model.setDataFrame(data)  # 更新数据模型
                        self.table_view.resizeColumnsToContents()  # 自动调整列宽
                        QMessageBox.information(self, "刷新成功", "OSS 数据已刷新。")
                    else:
                        QMessageBox.warning(self, "刷新失败", "无法从 OSS 读取数据。")
                else:
                    QMessageBox.warning(self, "路径错误", "OSS 路径未设置。")
            except Exception as e:
                QMessageBox.critical(self, "刷新错误", f"无法刷新数据: {str(e)}")
        else:
            # 本地文件刷新逻辑
            if self.current_file and os.path.exists(self.current_file):
                if self.model.isModified():
                    reply = QMessageBox.question(
                        self, '确认', '当前数据已修改，刷新将丢失所有更改。确定要继续吗？',
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.No:
                        return
                
                self.load_data(self.current_file)
    
    def get_data(self):
        """获取当前数据，返回原始数据"""
        if self._original_data is not None:
            # 获取模型中的原始数据（已包含所有修改）
            return self.model.get_original_data()
        return None
    
    def set_data(self, data):
        """设置新数据"""
        if isinstance(data, pd.DataFrame):
            self._original_data = data.copy()
            self.load_data(data=data)

    def update_table(self):
        """更新表格视图显示当前数据"""
        # 通知模型数据已变化，触发视图刷新
        self.model.layoutChanged.emit()
        # 调整列宽以适应新数据
        self.table_view.resizeColumnsToContents()
        # 确保UI更新
        QApplication.processEvents()
        # 标记数据已修改
        self.data = self.model.getDataFrame()
    def clear_data(self):
        """清除数据"""
        empty_df = pd.DataFrame()
        self.model.setDataFrame(empty_df)
        self.table_view.resizeColumnsToContents()
# Example usage:

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    
    # Create sample data
    df = pd.DataFrame({
        'Name': ['John', 'Alice', 'Bob'],
        'Age': [25, 30, 35],
        'City': ['New York', 'London', 'Paris']
    })
    
    viewer = XlsxViewerWidget()
    viewer.load_data(df)
    viewer.resize(600, 400)
    viewer.show()
    
    sys.exit(app.exec_())
