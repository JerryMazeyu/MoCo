import sys
import os 
# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QSplitter, QStackedWidget
from PyQt5.QtCore import Qt
from tabs import Tab0, Tab1, Tab2, Tab5, Tab6
from app.views.components.message_console import MessageConsoleWidget, StdoutRedirector, MessageManager
from app.views.login_window import LoginWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_info = None
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("MoCo 数据助手")
        self.setGeometry(100, 100, 1000, 600)

        # 创建堆叠窗口部件用于切换登录前后的界面
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        # 创建登录页面
        self.login_page = LoginWindow()
        self.login_page.loginSuccessful.connect(self.on_login_successful)
        
        # 创建主内容页面
        self.main_content = QWidget()
        self.main_layout = QVBoxLayout(self.main_content)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Vertical)
        self.tab_widget = QTabWidget()
        self.message_console = MessageConsoleWidget()
        
        self.splitter.addWidget(self.tab_widget)
        self.splitter.addWidget(self.message_console)
        self.splitter.setSizes([500, 100])
        self.main_layout.addWidget(self.splitter)

        # 将两个页面添加到堆叠窗口
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.main_content)
        
        # 设置stdout重定向
        sys.stdout = StdoutRedirector()

    def on_login_successful(self, user_info):
        """登录成功后的处理"""
        self.user_info = user_info
        self.setWindowTitle(f"MoCo 数据助手 - 用户: {user_info['username']}")
        self.setup_tabs()
        self.stacked_widget.setCurrentIndex(1)  # 切换到主内容页面
        
        # 打印欢迎信息
        print(f"欢迎使用 MoCo 数据助手！用户: {self.user_info['username']}，角色: {self.user_info['role']}")
        print("所有输出信息将显示在此控制台中。")
        
        # 加载用户配置
        self.load_user_config()

    def setup_tabs(self):
        """设置标签页"""
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
        self.tab_widget.addTab(self.tab3, "查看审核关键信息")
        self.tab_widget.addTab(self.tab6, "油品收集和平衡表")

        # Set layouts for each tab
        self.tab0.layout = QVBoxLayout()
        self.tab5.layout = QVBoxLayout()
        self.tab1.layout = QVBoxLayout()
        self.tab2.layout = QVBoxLayout()
        self.tab3.layout = QVBoxLayout()
        self.tab6.layout = QVBoxLayout()

        # Add TabContent to tab
        self.tab0_content = Tab0()
        self.tab0.layout.addWidget(self.tab0_content)
        self.tab5_content = Tab5()
        self.tab5.layout.addWidget(self.tab5_content)
        self.tab1_content = Tab1()
        self.tab1.layout.addWidget(self.tab1_content)
        self.tab2_content = Tab2()
        self.tab2.layout.addWidget(self.tab2_content)
        self.tab6_content = Tab6()
        self.tab6.layout.addWidget(self.tab6_content)

        self.tab0.setLayout(self.tab0.layout)
        self.tab5.setLayout(self.tab5.layout)
        self.tab1.setLayout(self.tab1.layout)
        self.tab2.setLayout(self.tab2.layout)
        self.tab3.setLayout(self.tab3.layout)
        self.tab6.setLayout(self.tab6.layout)

    def load_user_config(self):
        """根据用户角色从云端加载配置"""
        try:
            # 这里实现从OSS获取配置文件的逻辑
            print(f"正在加载 {self.user_info['role']} 角色的配置...")
            # 实际实现中，可以根据角色下载并应用不同的配置文件
        except Exception as e:
            print(f"加载配置失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭时还原标准输出"""
        sys.stdout = sys.__stdout__
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
