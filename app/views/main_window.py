import sys
import os
# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, 
                            QVBoxLayout, QSplitter, QStackedWidget)
from PyQt5.QtCore import Qt
from app.views.components.message_console import MessageConsoleWidget
from app.views.login_window import LoginWindow
from app.utils.logger import get_logger

# 获取全局日志对象
LOGGER = get_logger()

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
        
        # 不再需要设置stdout重定向，因为日志系统已经自动处理

    def on_login_successful(self, user_info):
        """登录成功后的处理"""
        try:
            self.user_info = user_info
            self.setWindowTitle(f"MoCo 数据助手 - 用户: {user_info['username']}")
            # 先加载用户配置，要不然后面页面导入CONF会一直是默认值？
            self.load_user_config()

            # 使用日志记录欢迎信息
            LOGGER.info(f"欢迎使用 MoCo 数据助手！用户: {self.user_info['username']}，角色: {self.user_info['role']}")
            LOGGER.info("所有日志信息将显示在控制台中。")

            self.setup_tabs()
            self.stacked_widget.setCurrentIndex(1)  # 切换到主内容页面
            
            # 设置窗口为全屏
            self.showMaximized()
            
            
        except Exception as e:
            LOGGER.error(f"登录后初始化失败: {str(e)}")
            # 恢复到登录页面
            self.stacked_widget.setCurrentIndex(0)

    def setup_tabs(self):
        """设置标签页"""
        try:
            # 清空现有标签页
            self.tab_widget.clear()

            # 导入Tab模块 - 将导入移到函数内，避免循环依赖
            from app.views.tabs.tab1 import Tab1  # 配置界面
            from app.views.tabs.tab2 import Tab2  # 餐厅获取
            from app.views.tabs.tab3 import Tab3  # 车辆获取
            from app.views.tabs.tab1_new import Tab1New  # 配置界面
            from app.views.tabs.tab4 import Tab4  # 油站获取
            from app.views.tabs.tab5 import Tab5  # 车辆管理

            # 创建Tab组件
            self.tab1_widget = QWidget()
            self.tab2_widget = QWidget()
            self.tab3_widget = QWidget()
            self.tab4_widget = QWidget()
            self.tab5_widget = QWidget()
            # 设置Tab布局
            self.tab1_widget.setLayout(QVBoxLayout())
            self.tab2_widget.setLayout(QVBoxLayout())
            self.tab3_widget.setLayout(QVBoxLayout())
            self.tab4_widget.setLayout(QVBoxLayout())
            self.tab5_widget.setLayout(QVBoxLayout())
            # 创建Tab内容
            # self.tab1_content = Tab1(self)  # 配置界面
            self.tab1_content = Tab1New(self)  # 配置界面
            self.tab2_content = Tab2(self)  # 餐厅获取
            self.tab3_content = Tab3(self)  # 车辆获取
            self.tab4_content = Tab4(self)  # 油站获取
            self.tab5_content = Tab5(self)  # 车辆管理
            # 添加内容到布局
            self.tab1_widget.layout().addWidget(self.tab1_content)
            self.tab2_widget.layout().addWidget(self.tab2_content)
            self.tab3_widget.layout().addWidget(self.tab3_content)
            self.tab4_widget.layout().addWidget(self.tab4_content)
            self.tab5_widget.layout().addWidget(self.tab5_content)
            # 添加Tab到标签页控件
            self.tab_widget.addTab(self.tab1_widget, "配置界面")
            self.tab_widget.addTab(self.tab2_widget, "餐厅获取")
            self.tab_widget.addTab(self.tab3_widget, "收油表获取")
            self.tab_widget.addTab(self.tab4_widget, "CP配置")
            self.tab_widget.addTab(self.tab5_widget, "车辆管理")
        except Exception as e:
            LOGGER.error(f"设置标签页失败: {str(e)}")

    def load_user_config(self):
        """根据用户角色加载配置"""
        try:
            LOGGER.info(f"正在加载 {self.user_info['username']} 的配置...")
            
            # 设置环境变量，用于配置服务加载正确的用户配置
            if self.user_info and 'username' in self.user_info:
                os.environ["MoCo_USERNAME"] = self.user_info['username']
                
            LOGGER.info("配置加载完成")
        except Exception as e:
            LOGGER.error(f"加载配置失败: {str(e)}")
    
    def set_current_cp(self, cp_id):
        """设置当前选择的CP ID"""
        try:
            self.current_cp = cp_id
            LOGGER.info(f"已选择CP: {cp_id}")
            # 通知各个Tab更新CP信息
            for i in range(self.tab_widget.count()):
                tab = self.tab_widget.widget(i)
                if tab:
                    content = tab.findChild(QWidget)
                    if content and hasattr(content, 'update_cp'):
                        content.update_cp(cp_id)
        except Exception as e:
            LOGGER.error(f"设置CP失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        try:
            # 清理临时文件
            LOGGER.info("正在清理应用程序临时文件...")
            
            # 清理Tab2的临时文件
            if hasattr(self, 'tab2_content') and self.tab2_content:
                if hasattr(self.tab2_content, 'cleanup_temp_files'):
                    self.tab2_content.cleanup_temp_files()
            
            # 清理Tab5的临时文件
            if hasattr(self, 'tab5_content') and self.tab5_content:
                if hasattr(self.tab5_content, 'cleanup_temp_files'):
                    self.tab5_content.cleanup_temp_files()
            
            # 如果有其他Tab也有临时文件，可以在这里添加类似的清理代码
            
            LOGGER.info("临时文件清理完成")
        except Exception as e:
            LOGGER.error(f"清理临时文件时出错: {str(e)}")
            
        # 无需还原标准输出，因为我们现在使用的是日志系统
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
