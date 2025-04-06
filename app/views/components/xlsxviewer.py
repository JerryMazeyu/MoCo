from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
                            QPushButton, QFileDialog, QMessageBox, QHBoxLayout, QApplication, QTableView)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QBrush, QColor
import pandas as pd
import sys
import os
import platform
import subprocess

class PandasModel(QAbstractTableModel):
    """Pandas数据模型，用于在QTableView中显示pandas DataFrame数据"""
    
    def __init__(self, data=None):
        super().__init__()
        self._data = pd.DataFrame() if data is None else data
        self._original_data = self._data.copy()
        self.modified = False
    
    def rowCount(self, parent=None):
        return len(self._data)
    
    def columnCount(self, parent=None):
        return len(self._data.columns)
    
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        
        value = self._data.iloc[index.row(), index.column()]
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if pd.isna(value):
                return ""
            # 根据数据类型返回适当的格式
            if isinstance(value, (int, float)):
                return str(value)
            return str(value)
        
        if role == Qt.BackgroundRole:
            # 如果数据被修改，显示不同的背景颜色
            original_value = self._original_data.iloc[index.row(), index.column()]
            if not pd.isna(value) and not pd.isna(original_value) and value != original_value:
                return QColor(255, 230, 190)  # 浅橙色，表示已修改
            
            # 交替行颜色
            if index.row() % 2 == 0:
                return QColor(245, 245, 245)  # 浅灰色
        
        if role == Qt.FontRole:
            font = QFont()
            # 如果数据被修改，用粗体显示
            original_value = self._original_data.iloc[index.row(), index.column()]
            if not pd.isna(value) and not pd.isna(original_value) and value != original_value:
                font.setBold(True)
            return font
        
        return QVariant()
    
    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        row, col = index.row(), index.column()
        
        # 更新数据
        try:
            # 尝试转换为原数据类型
            current_type = type(self._data.iloc[row, col])
            if current_type == int:
                value = int(value)
            elif current_type == float:
                value = float(value)
            elif pd.isna(self._data.iloc[row, col]) and value.strip() == "":
                # 如果原值是NA且新值是空字符串，保持为NA
                value = pd.NA
            
            # 更新数据
            self._data.iloc[row, col] = value
            
            # 检查是否与原始数据不同
            if self._data.iloc[row, col] != self._original_data.iloc[row, col]:
                self.modified = True
            
            # 发出数据更改信号
            self.dataChanged.emit(index, index)
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
        self.beginResetModel()
        self._data = dataframe
        self._original_data = dataframe.copy()
        self.modified = False
        self.endResetModel()
    
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

class XlsxViewerWidget(QWidget):
    """Excel表格查看器组件，用于展示和编辑Excel数据"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
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
        
        # 创建按钮
        self.open_button = QPushButton("打开文件")
        self.save_button = QPushButton("保存")
        self.save_as_button = QPushButton("另存为")
        self.refresh_button = QPushButton("刷新")
        
        # 连接按钮信号
        self.open_button.clicked.connect(self.open_file)
        self.save_button.clicked.connect(self.save_file)
        self.save_as_button.clicked.connect(self.save_file_as)
        self.refresh_button.clicked.connect(self.refresh)
        
        # 设置按钮等宽
        button_width = 90  # 固定宽度
        for button in [self.open_button, self.save_button, self.save_as_button, self.refresh_button]:
            button.setFixedWidth(button_width)
        
        # 添加按钮到布局，均匀分布
        button_layout.addWidget(self.open_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.save_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.save_as_button)
        button_layout.addStretch(1)
        button_layout.addWidget(self.refresh_button)
        
        # 先添加表格到主布局，再添加按钮
        self.layout.addWidget(self.table_view)
        self.layout.addLayout(button_layout)
    
    def load_data(self, file_path=None, data=None):
        """加载数据，可以是文件路径或pandas DataFrame"""
        try:
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
                # 设置数据模型
                self.model.setDataFrame(data)
                
                # 自动调整列宽
                self.table_view.resizeColumnsToContents()
                
                return True
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
    
    def save_file_as(self):
        """另存为文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel文件", "", "Excel文件 (*.xlsx);;CSV文件 (*.csv)"
        )
        
        if not file_path:
            return False
        
        # 确保文件有正确的扩展名
        if not file_path.endswith(('.xlsx', '.xls', '.csv')):
            file_path += '.xlsx'
        
        self.current_file = file_path
        return self.save_file()
    
    def refresh(self):
        """刷新当前文件数据"""
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
        """获取当前数据"""
        return self.model.getDataFrame()
    
    def set_data(self, data):
        """设置新数据"""
        if isinstance(data, pd.DataFrame):
            self.model.setDataFrame(data)
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
