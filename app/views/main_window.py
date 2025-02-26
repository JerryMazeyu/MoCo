import sys
import os 
# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout
from tabs import Tab0, Tab1, Tab2, Tab5, Tab6



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MoCo 数据助手")
        self.setGeometry(100, 100, 1000, 600)

        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        self.initUI()

    def initUI(self):
        # Create tabs
        self.tab0 = QWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tab5 = QWidget()
        self.tab6 = QWidget()

        # Add tabs to the tab widget
        self.tab_widget.addTab(self.tab5, "城市餐厅信息爬取")
        self.tab_widget.addTab(self.tab0, "配置项")
        self.tab_widget.addTab(self.tab1, "查找&确认餐厅信息")
        self.tab_widget.addTab(self.tab2, "配置车辆信息")
        self.tab_widget.addTab(self.tab3, "生成&审核")
        self.tab_widget.addTab(self.tab6, "油品收集和平衡表")
        

        # Set layouts for each tab
        self.tab0.layout = QVBoxLayout()
        self.tab1.layout = QVBoxLayout()
        self.tab2.layout = QVBoxLayout()
        self.tab3.layout = QVBoxLayout()
        self.tab5.layout = QVBoxLayout()
        self.tab6.layout = QVBoxLayout()


        # Add TabContent to tab
        self.tab0_content = Tab0()
        self.tab0.layout.addWidget(self.tab0_content)
        self.tab1_content = Tab1()
        self.tab1.layout.addWidget(self.tab1_content)
        self.tab2_content = Tab2()
        self.tab2.layout.addWidget(self.tab2_content)
        self.tab5_content = Tab5()
        self.tab5.layout.addWidget(self.tab5_content)
        self.tab6_content = Tab6()
        self.tab6.layout.addWidget(self.tab6_content)

        self.tab0.setLayout(self.tab0.layout)
        self.tab1.setLayout(self.tab1.layout)
        self.tab2.setLayout(self.tab2.layout)
        self.tab3.setLayout(self.tab3.layout)
        self.tab5.setLayout(self.tab5.layout)
        self.tab6.setLayout(self.tab6.layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
