import sys
import os 
# 添加项目根目录到 Python 路径
# sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QSplitter, QStackedWidget)
from PyQt5.QtCore import Qt
# 导入Tab模块
from app.views.tabs.tab1 import Tab1  # 配置界面
from app.views.tabs.tab2 import Tab2  # 餐厅获取
from app.views.components.message_console import MessageConsoleWidget, StdoutRedirector
from app.views.login_window import LoginWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_info = None
        self.current_cp = None  # 当前选择的CP
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("MoCo 数据助手")
        # self.setGeometry(100, 100, 1200, 800)  # 设置初始窗口大小

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
        self.splitter.setSizes([600, 200])  # 调整分割比例
        self.main_layout.addWidget(self.splitter)

        # 将两个页面添加到堆叠窗口
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.main_content)
        
        # 设置stdout重定向
        sys.stdout = StdoutRedirector(self.message_console)

    def on_login_successful(self, user_info):
        """登录成功后的处理"""
        try:
            self.user_info = user_info
            self.setWindowTitle(f"MoCo 数据助手 - 用户: {user_info['username']}")
            self.setup_tabs()
            self.stacked_widget.setCurrentIndex(1)  # 切换到主内容页面
            
            # 打印欢迎信息
            print(f"欢迎使用 MoCo 数据助手！用户: {self.user_info['username']}，角色: {self.user_info['role']}")
            print("所有输出信息将显示在此控制台中。")
            
            # 加载用户配置
            self.load_user_config()
        except Exception as e:
            print(f"登录后初始化失败: {str(e)}")
            # 恢复到登录页面
            self.stacked_widget.setCurrentIndex(0)

    def setup_tabs(self):
        """设置标签页"""
        try:
            # 清空现有标签页
            self.tab_widget.clear()

            # 创建Tab组件
            self.tab1_widget = QWidget()
            self.tab2_widget = QWidget()
            
            # 设置Tab布局
            self.tab1_widget.setLayout(QVBoxLayout())
            self.tab2_widget.setLayout(QVBoxLayout())
            
            # 创建Tab内容
            self.tab1_content = Tab1(self)  # 配置界面
            self.tab2_content = Tab2(self)  # 餐厅获取
            
            # 添加内容到布局
            self.tab1_widget.layout().addWidget(self.tab1_content)
            self.tab2_widget.layout().addWidget(self.tab2_content)
            
            # 添加Tab到标签页控件
            self.tab_widget.addTab(self.tab1_widget, "配置界面")
            self.tab_widget.addTab(self.tab2_widget, "餐厅获取")
        except Exception as e:
            print(f"设置标签页失败: {str(e)}")

    def load_user_config(self):
        """根据用户角色加载配置"""
        try:
            print(f"正在加载 {self.user_info['username']} 的配置...")
            
            # 设置环境变量，用于配置服务加载正确的用户配置
            if self.user_info and 'username' in self.user_info:
                os.environ["MoCo_USERNAME"] = self.user_info['username']
                
            print("配置加载完成")
        except Exception as e:
            print(f"加载配置失败: {str(e)}")
    
    def set_current_cp(self, cp_id):
        """设置当前选择的CP ID"""
        try:
            self.current_cp = cp_id
            print(f"已选择CP: {cp_id}")
            # 通知各个Tab更新CP信息
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if tab:
                    content = tab.findChild(QWidget)
                    if content and hasattr(content, 'update_cp'):
                        content.update_cp(cp_id)
        except Exception as e:
            print(f"设置CP失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭时还原标准输出"""
        try:
            # 确保标准输出被恢复
            if hasattr(sys, "__stdout__"):
                sys.stdout = sys.__stdout__
        except Exception as e:
            print(f"关闭窗口时出错: {str(e)}")
        
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
