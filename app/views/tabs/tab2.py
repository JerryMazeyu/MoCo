import sys
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox
)
from pydantic import ValidationError
from PyQt5.QtCore import Qt
from PyQt5.QtCore import Qt
from app.controllers import flow2
from app.models.vehicle_model import Vehicle
        
class Tab2(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("车辆库管理（多选示例 - 使用flow2）")
        flow2.flow2_init_service()
        # 1. 主布局
        main_layout = QVBoxLayout(self)

        # 2. 车辆列表（QTableWidget）
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # license_plate, driver_name, district, max_barrels, allocated_barrels, other_info
        self.table.setHorizontalHeaderLabels(["车牌号", "司机姓名", "所属区域", "最大收油桶数", "已分配油桶数", "其他信息"])

        # 多选设置
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        main_layout.addWidget(self.table)

        # 3. 信息输入区域
        form_layout = QHBoxLayout()
        main_layout.addLayout(form_layout)

        self.plate_number_edit = QLineEdit()
        self.plate_number_edit.setPlaceholderText("车牌号")
        form_layout.addWidget(self.plate_number_edit)

        self.driver_name_edit = QLineEdit()
        self.driver_name_edit.setPlaceholderText("司机姓名")
        form_layout.addWidget(self.driver_name_edit)

        self.district_edit = QLineEdit()
        self.district_edit.setPlaceholderText("所属区域")
        form_layout.addWidget(self.district_edit)

        self.max_barrels_edit = QLineEdit()
        self.max_barrels_edit.setPlaceholderText("最大收油桶数")
        form_layout.addWidget(self.max_barrels_edit)

        self.allocated_barrels_edit = QLineEdit()
        self.allocated_barrels_edit.setPlaceholderText("已分配油桶数")
        form_layout.addWidget(self.allocated_barrels_edit)

        self.other_info_edit = QLineEdit()
        self.other_info_edit.setPlaceholderText("其他信息")
        form_layout.addWidget(self.other_info_edit)

        # 4. 按钮区域
        button_layout = QHBoxLayout()
        main_layout.addLayout(button_layout)

        self.add_btn = QPushButton("增加车辆")
        self.add_btn.clicked.connect(self.add_vehicle)
        button_layout.addWidget(self.add_btn)

        self.import_btn = QPushButton("导入车辆(Excel)")
        self.import_btn.clicked.connect(self.import_vehicles)
        button_layout.addWidget(self.import_btn)

        self.delete_btn = QPushButton("删除选中车辆(多选)")
        self.delete_btn.clicked.connect(self.delete_selected_vehicles)
        button_layout.addWidget(self.delete_btn)

        self.edit_btn = QPushButton("编辑选中车辆(仅限单选)")
        self.edit_btn.clicked.connect(self.edit_vehicle)
        button_layout.addWidget(self.edit_btn)

        self.next_btn = QPushButton("下一步")
        self.next_btn.clicked.connect(self.on_next_step)
        button_layout.addWidget(self.next_btn)

        # 初始化表格数据
        self.refresh_table()

    def refresh_table(self):
        """刷新表格数据显示"""
        vehicles = flow2.flow2_get_vehicles()
        self.table.setRowCount(len(vehicles))

        for row, v in enumerate(vehicles):
            self.table.setItem(row, 0, QTableWidgetItem(v.license_plate))
            self.table.setItem(row, 1, QTableWidgetItem(v.driver_name))
            self.table.setItem(row, 2, QTableWidgetItem(v.district))
            self.table.setItem(row, 3, QTableWidgetItem(str(v.max_barrels)))
            self.table.setItem(row, 4, QTableWidgetItem(str(v.allocated_barrels)))
            self.table.setItem(row, 5, QTableWidgetItem(str(v.other_info) if v.other_info else ""))

    def clear_input_fields(self):
        self.plate_number_edit.clear()
        self.driver_name_edit.clear()
        self.district_edit.clear()
        self.max_barrels_edit.clear()
        self.allocated_barrels_edit.clear()
        self.other_info_edit.clear()

    def add_vehicle(self):
        """增加新车辆"""
        plate_number = self.plate_number_edit.text().strip()
        if not plate_number:
            QMessageBox.warning(self, "警告", "车牌号不能为空！")
            return

        driver_name = self.driver_name_edit.text().strip()
        district = self.district_edit.text().strip()
        max_barrels_str = self.max_barrels_edit.text().strip()
        allocated_barrels_str = self.allocated_barrels_edit.text().strip()
        other_info = self.other_info_edit.text().strip()

        try:
            max_barrels = int(max_barrels_str) if max_barrels_str else 0
            allocated_barrels = int(allocated_barrels_str) if allocated_barrels_str else 0
        except ValueError:
            QMessageBox.warning(self, "警告", "最大/已分配油桶数应为整数！")
            return

        try:
            vehicle = Vehicle(
                license_plate=plate_number,
                driver_name=driver_name,
                district=district,
                max_barrels=max_barrels,
                allocated_barrels=allocated_barrels,
                other_info=other_info if other_info else None
            )
            flow2.flow2_add_vehicle(vehicle)
        except ValidationError as ve:
            QMessageBox.warning(self, "数据错误", f"输入数据有误: {ve}")
            return
        except ValueError as e:
            QMessageBox.warning(self, "重复错误", str(e))
            return

        self.refresh_table()
        self.clear_input_fields()

    def import_vehicles(self):
        """从外部Excel导入车辆"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择Excel文件", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            try:
                flow2.flow2_import_from_excel(file_path)
                QMessageBox.information(self, "提示", "导入成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败：{str(e)}")
            self.refresh_table()

    def delete_selected_vehicles(self):
        """批量删除选中的车辆"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选中要删除的车辆！")
            return

        ret = QMessageBox.question(self, "确认删除",
                                   f"确认删除选中的 {len(selected_rows)} 条车辆信息吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        if ret != QMessageBox.Yes:
            return

        plates_to_delete = []
        for index in selected_rows:
            row = index.row()
            plate_item = self.table.item(row, 0)
            if plate_item:
                plates_to_delete.append(plate_item.text())

        for plate in plates_to_delete:
            try:
                flow2.flow2_remove_vehicle(plate)
            except Exception as e:
                print(f"删除 {plate} 时异常: {e}")

        self.refresh_table()

    def edit_vehicle(self):
        """
        编辑选中车辆（仅限单选）。
        """
        selected_rows = self.table.selectionModel().selectedRows()
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "警告", "请仅选中一条车辆进行编辑！")
            return

        row = selected_rows[0].row()
        old_plate_item = self.table.item(row, 0)
        if not old_plate_item:
            QMessageBox.warning(self, "警告", "选中行无车牌信息！")
            return

        old_plate_number = old_plate_item.text()

        new_plate_number = self.plate_number_edit.text().strip()
        if not new_plate_number:
            QMessageBox.warning(self, "警告", "车牌号不能为空！")
            return

        driver_name = self.driver_name_edit.text().strip()
        district = self.district_edit.text().strip()
        max_barrels_str = self.max_barrels_edit.text().strip()
        allocated_barrels_str = self.allocated_barrels_edit.text().strip()
        other_info = self.other_info_edit.text().strip()

        try:
            max_barrels = int(max_barrels_str) if max_barrels_str else 0
            allocated_barrels = int(allocated_barrels_str) if allocated_barrels_str else 0
        except ValueError:
            QMessageBox.warning(self, "警告", "最大/已分配油桶数应为整数！")
            return

        try:
            new_vehicle = Vehicle(
                license_plate=new_plate_number,
                driver_name=driver_name,
                district=district,
                max_barrels=max_barrels,
                allocated_barrels=allocated_barrels,
                other_info=other_info if other_info else None
            )
            flow2.flow2_update_vehicle(old_plate_number, new_vehicle)
        except ValidationError as ve:
            QMessageBox.warning(self, "数据错误", f"输入数据有误: {ve}")
            return
        except ValueError as e:
            QMessageBox.warning(self, "错误", str(e))
            return

        self.refresh_table()
        self.clear_input_fields()

    def on_next_step(self):
        """示例：点击“下一步”时，获取已选车辆。"""
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "提示", "你尚未选择车辆，无法进行下一步。")
            return

        selected_plates = []
        for index in selected_rows:
            row = index.row()
            plate_item = self.table.item(row, 0)
            if plate_item:
                selected_plates.append(plate_item.text())

        QMessageBox.information(
            self, "下一步",
            f"你已选择以下车辆车牌 (共{len(selected_plates)}条)：\n" + "\n".join(selected_plates)
        )
        # TODO: 这里可以把选中的车辆信息带到下一个流程