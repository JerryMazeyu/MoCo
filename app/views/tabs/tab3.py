import traceback
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QLabel, QLineEdit, QPushButton, QFileDialog, QMessageBox, QHeaderView, QTextEdit, QProgressBar, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from pydantic import ValidationError
from app.controllers import flow2_run_task
from app.models.vehicle_model import Vehicle
from app.utils import rp
from app.config import get_config
from app.views.components.singleton import global_context
import pandas as pd
import os
import json


class Tab3(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        pass