from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
import os

class StepIndicator(QFrame):
    def __init__(self, steps, parent=None):
        super().__init__(parent)
        self.steps = steps
        self.current_step = 0
        self.completed_steps = set()
        self.error_steps = set()
        
        layout = QHBoxLayout()
        self.step_labels = []
        self.step_icons = []
        
        # 图标路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))  # 向上三级到 MoCo 目录
        resources_dir = os.path.join(project_root, 'MoCo', 'app', 'resources', 'icons')
        self.icons = {
            'finish': os.path.join(resources_dir, 'finish.png'),
            'dealing': os.path.join(resources_dir, 'dealing.png'),
            'unfinish': os.path.join(resources_dir, 'unfinish.png'),
            'error': os.path.join(resources_dir, 'error.png')
        }
        
        for i, step in enumerate(steps):
            step_frame = QFrame()
            step_layout = QHBoxLayout()
            
            # 图标标签
            icon_label = QLabel()
            icon_label.setFixedSize(24, 24)
            icon_pixmap = QPixmap(self.icons['unfinish'])
            icon_label.setPixmap(icon_pixmap.scaled(24, 24, Qt.KeepAspectRatio))
            
            # 步骤文本标签
            text_label = QLabel(f"步骤 {i+1}: {step}")
            text_label.setStyleSheet("color: gray; padding: 5px;")
            
            step_layout.addWidget(icon_label, alignment=Qt.AlignCenter)
            step_layout.addWidget(text_label, alignment=Qt.AlignCenter)
            step_frame.setLayout(step_layout)
            
            if i > 0:
                separator = QLabel("→")
                layout.addWidget(separator)
            
            layout.addWidget(step_frame)
            self.step_labels.append(text_label)
            self.step_icons.append(icon_label)
            
        layout.addStretch()
        self.setLayout(layout)
        
    def update_progress(self, current_step, completed_steps, error_steps=None):
        self.current_step = current_step
        self.completed_steps = completed_steps
        self.error_steps = error_steps or set()
        
        for i, (label, icon) in enumerate(zip(self.step_labels, self.step_icons)):
            if i in self.error_steps:
                icon_file = self.icons['error']
                label.setStyleSheet("color: red; padding: 5px;")
            elif i in completed_steps:
                icon_file = self.icons['finish']
                label.setStyleSheet("color: green; padding: 5px;")
            elif i == current_step:
                icon_file = self.icons['dealing']
                label.setStyleSheet("color: black; padding: 5px;")
            else:
                icon_file = self.icons['unfinish']
                label.setStyleSheet("color: gray; opacity: 0.5; padding: 5px;")
            
            icon.setPixmap(QPixmap(icon_file).scaled(24, 24, Qt.KeepAspectRatio))



