from PyQt5.QtCore import Qt
import pandas as pd
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QFileDialog, QMessageBox, QHBoxLayout, QApplication, QTableView
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QBrush
import os
import platform
import subprocess

class XlsxViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = None
        self.model = QStandardItemModel()  # 表格数据模型
        self.init_ui()
    
    def get_file_path(self, file_path=None):
        """获取文件路径"""
        self.file_path = file_path

    def init_ui(self):
        layout = QVBoxLayout()

        self.table = QTableView()
        self.table.setModel(self.model)  # 绑定数据模型
        layout.addWidget(self.table)
        
         # 按钮布局
        button_layout = QHBoxLayout()

        # “打开源文件”按钮
        self.open_button = QPushButton("打开源文件")
        self.open_button.clicked.connect(self.open_file)
        button_layout.addWidget(self.open_button)

        # “刷新信息”按钮
        self.refresh_button = QPushButton("刷新信息")
        self.refresh_button.clicked.connect(self.refresh_data)
        button_layout.addWidget(self.refresh_button)

        # “保存信息”按钮
        self.save_button = QPushButton("保存信息")
        self.save_button.clicked.connect(self.save_data)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)


    def save_data(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "另存为", self.file_path, "Excel Files (*.xlsx *.xls)")
        if save_path:
            try:
                data = self.get_data()
                data.to_excel(save_path, index=False)
                self.file_path = save_path
                QMessageBox.information(self, "成功", f"数据已保存到 {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存文件失败：\n{str(e)}")

    

    def open_file(self):
        """打开 Excel 文件并加载数据"""
        if not self.file_path:
            QMessageBox.warning(self, "警告", "请先加载文件后再打开")
            return

        try:
            if platform.system() == "Windows":
                os.startfile(self.file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", self.file_path])
            else:  # Linux
                subprocess.call(["xdg-open", self.file_path])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件：\n{str(e)}")

    def refresh_data(self, df: pd.DataFrame=None):
        """刷新表格中的数据"""
        if not self.file_path:
            QMessageBox.warning(self, "警告", "请先加载文件后再刷新")
            return
        try:
            if df is None:
                data = pd.read_excel(self.file_path)
            self.load_data(df)
            QMessageBox.information(self, "成功", "数据已刷新")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"刷新数据失败：\n{str(e)}")


    def load_data(self, data: pd.DataFrame):
        """加载数据到表格中"""
        self.model.clear()

        # 设置表头
        self.model.setHorizontalHeaderLabels(data.columns)
        # 自定义表头样式
        font = QFont()
        font.setBold(True)  # 字体加粗
        brush = QBrush(Qt.darkBlue)  # 前景色为白色
        background_brush = QBrush(Qt.green)  # 背景色为深蓝色

        for col in range(self.model.columnCount()):
            self.model.setHeaderData(
                col,
                Qt.Horizontal,
                data.columns[col],
                Qt.DisplayRole
            )
            self.model.setHeaderData(col, Qt.Horizontal, font, Qt.FontRole)
            self.model.setHeaderData(col, Qt.Horizontal, brush, Qt.ForegroundRole)
            self.model.setHeaderData(col, Qt.Horizontal, background_brush, Qt.BackgroundRole)


        # 填充数据到 QStandardItemModel
        for row in data.values:
            items = [QStandardItem(str(item)) for item in row]
            self.model.appendRow(items)

        # 可选：调整列宽
        self.table.resizeColumnsToContents()

    def get_data(self) -> pd.DataFrame:
        rows = self.model.rowCount()
        cols = self.model.columnCount()
        headers = [self.model.headerData(col, Qt.Horizontal) for col in range(cols)]

        data = []
        for row in range(rows):
            row_data = ["" if not self.model.item(row, col) else self.model.item(row, col).text() for col in range(cols)]
            data.append(row_data)

        return pd.DataFrame(data, columns=headers)


# Example usage:

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    
    # Create sample data
    df = pd.DataFrame({
        'Name': ['John', 'Alice', 'Bob'],
        'Age': [25, 30, 35],
        'City': ['New York', 'London', 'Paris']
    })
    
    viewer = XlsxViewer()
    viewer.load_data(df)
    viewer.resize(600, 400)
    viewer.show()
    
    sys.exit(app.exec_())
