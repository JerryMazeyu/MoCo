import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QHeaderView

)
from pydantic import ValidationError
from PyQt5.QtCore import Qt
from app.controllers import flow2
from app.models.vehicle_model import Vehicle
from app.utils import rp
from app.config import get_config
from components.singleton import global_context


class Tab3(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        pass