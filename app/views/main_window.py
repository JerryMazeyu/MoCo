import sys
import os 
# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QSplitter
from PyQt5.QtCore import Qt
from tabs import Tab0, Tab1, Tab2, Tab5, Tab6
from app.views.components.message_console import MessageConsoleWidget, StdoutRedirector, MessageManager
from app.views.login_window import LoginWindow  # 导入登录窗口


class MainWindow(QMainWindow):
    def __init__(self, user_info=None):
        super().__init__()
        
        # 保存用户信息
        self.user_info = user_info

        self.setWindowTitle(f"MoCo 数据助手 - 用户: {user_info['username']}")
        self.setGeometry(100, 100, 1000, 600)

        # 创建一个中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主垂直布局
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 创建分割器，用于调整标签页和消息控制台的高度比例
        self.splitter = QSplitter(Qt.Vertical)
        
        # 创建标签页窗口部件
        self.tab_widget = QTabWidget()
        
        # 创建消息控制台
        self.message_console = MessageConsoleWidget()
        
        # 添加部件到分割器
        self.splitter.addWidget(self.tab_widget)
        self.splitter.addWidget(self.message_console)
        
        # 设置初始大小比例（标签页占更多空间）
        self.splitter.setSizes([500, 100])
        
        # 将分割器添加到主布局
        self.main_layout.addWidget(self.splitter)

        # 设置stdout重定向
        sys.stdout = StdoutRedirector()
        
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
        
        # 打印欢迎信息到控制台
        print(f"欢迎使用 MoCo 数据助手！用户: {self.user_info['username']}，角色: {self.user_info['role']}")
        print("所有输出信息将显示在此控制台中。")
        
        # 根据用户角色加载不同的配置
        self.load_user_config()

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
    
    # 首先显示登录窗口
    login_window = LoginWindow()
    
    # 创建主窗口但不显示
    main_window = None
    
    # 连接登录成功信号
    def on_login_successful(user_info):
        global main_window
        main_window = MainWindow(user_info)
        main_window.show()
    
    login_window.loginSuccessful.connect(on_login_successful)
    login_window.show()
    
    sys.exit(app.exec_())
