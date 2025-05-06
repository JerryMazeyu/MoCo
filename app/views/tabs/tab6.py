import os
import json
import tempfile
import yaml
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QTableWidget, QTableWidgetItem, QFrame, 
                            QLineEdit, QMessageBox, QHeaderView, QComboBox,
                            QFormLayout, QGroupBox, QApplication)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
import oss2
from app.config.config import CONF
from app.utils.logger import get_logger
from app.services.instances.cp import CP
from app.utils.hash import hash_text

# 获取全局日志对象
LOGGER = get_logger()


class Tab6(QWidget):
    """账号管理Tab，实现账号的注册、查看和删除功能"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window_ref = parent
        self.conf = CONF
        
        # 用于存储账号信息
        self.accounts = {}
        # 用于存储用户CP绑定信息
        self.user_cp_bindings = {}
        # 用于存储CP信息
        self.cp_list = []
        # 临时文件路径
        self.temp_files = []
        
        # 初始化UI
        self.initUI()
        
        # 加载账号数据
        self.load_accounts()
        
        # 加载CP列表
        self.load_cp_list()
    
    def initUI(self):
        # 主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("账号管理")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.layout.addWidget(title_label)
        
        # 创建水平分割布局
        content_layout = QHBoxLayout()
        
        # 左侧 - 账号列表
        accounts_group = QGroupBox("现有账号")
        accounts_layout = QVBoxLayout(accounts_group)
        
        # 账号表格
        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(3)  # 用户名, 绑定CP, 操作
        self.accounts_table.setHorizontalHeaderLabels(["用户名", "绑定CP", "操作"])
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.accounts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        accounts_layout.addWidget(self.accounts_table)
        
        # 刷新按钮
        refresh_button = QPushButton("刷新账号列表")
        refresh_button.clicked.connect(self.load_accounts)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #46b8da;
            }
        """)
        accounts_layout.addWidget(refresh_button)
        
        # 右侧 - 注册新账号
        register_group = QGroupBox("注册新账号")
        register_layout = QFormLayout(register_group)
        
        # 用户名输入
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        register_layout.addRow("用户名:", self.username_input)
        
        # 密码输入
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        register_layout.addRow("密码:", self.password_input)
        
        # 确认密码
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请再次输入密码")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        register_layout.addRow("确认密码:", self.confirm_password_input)
        
        # CP选择下拉框
        self.cp_combo = QComboBox()
        register_layout.addRow("绑定CP:", self.cp_combo)
        
        # 注册按钮
        self.register_button = QPushButton("注册账号")
        self.register_button.clicked.connect(self.register_account)
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        register_layout.addRow("", self.register_button)
        
        # 添加左右两侧到水平布局
        content_layout.addWidget(accounts_group, 2)  # 账号列表占2/3
        content_layout.addWidget(register_group, 1)  # 注册表单占1/3
        
        # 添加内容布局到主布局
        self.layout.addLayout(content_layout)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; margin-top: 5px;")
        self.layout.addWidget(self.status_label)
    
    def load_accounts(self):
        """从OSS加载账号信息"""
        try:
            # 显示加载状态
            self.status_label.setText("正在加载账号信息...")
            QApplication.processEvents()
            
            # 获取OSS配置
            oss_conf = CONF.KEYS.oss
            auth = oss2.Auth(oss_conf.get('access_key_id'), oss_conf.get('access_key_secret'))
            bucket = oss2.Bucket(auth, oss_conf.get('endpoint'), oss_conf.get('bucket_name'), region=oss_conf.get('region'))
            
            # 下载login_info_base.json
            login_info_base_path = 'login_info_base.json'
            temp_dir = tempfile.gettempdir()
            local_file = os.path.join(temp_dir, 'login_info_base.json')
            
            try:
                # 下载文件
                bucket.get_object_to_file(login_info_base_path, local_file)
                self.temp_files.append(local_file)
                
                # 读取账号信息
                with open(local_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                
                # 记录日志
                LOGGER.info(f"成功从OSS加载账号信息: {len(self.accounts)} 个账号")
                
                # 移除admin账号（不显示）
                if 'admin' in self.accounts:
                    del self.accounts['admin']
                
                # 加载每个用户的CP绑定信息
                self.load_user_cp_bindings()
                
                # 更新表格
                self.update_accounts_table()
                
                # 更新状态
                self.status_label.setText(f"成功加载 {len(self.accounts)} 个账号")
                
            except Exception as e:
                LOGGER.error(f"下载账号信息文件失败: {str(e)}")
                self.status_label.setText("加载账号信息失败，请检查网络连接或OSS配置")
                
                # 如果文件不存在，则创建一个空的账号信息
                self.accounts = {}
                self.update_accounts_table()
        
        except Exception as e:
            LOGGER.error(f"加载账号信息时出错: {str(e)}")
            self.status_label.setText(f"加载账号信息时出错: {str(e)}")
    
    def load_user_cp_bindings(self):
        """从用户YAML配置文件加载CP绑定信息"""
        try:
            self.user_cp_bindings = {}
            
            # 获取OSS配置
            oss_conf = CONF.KEYS.oss
            auth = oss2.Auth(oss_conf.get('access_key_id'), oss_conf.get('access_key_secret'))
            bucket = oss2.Bucket(auth, oss_conf.get('endpoint'), oss_conf.get('bucket_name'), region=oss_conf.get('region'))
            
            # 临时目录
            temp_dir = tempfile.gettempdir()
            
            # 为每个用户下载并解析YAML配置
            for username in self.accounts.keys():
                if username == 'admin':
                    continue
                
                yaml_path = f'configs/{username}.yaml'
                local_yaml_file = os.path.join(temp_dir, f'{username}.yaml')
                
                try:
                    # 检查文件是否存在
                    if not bucket.object_exists(yaml_path):
                        LOGGER.warning(f"用户 {username} 的YAML配置文件不存在")
                        continue
                    
                    # 下载YAML文件
                    bucket.get_object_to_file(yaml_path, local_yaml_file)
                    self.temp_files.append(local_yaml_file)
                    
                    # 读取YAML配置
                    with open(local_yaml_file, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f)
                    
                    # 提取CP信息
                    if config and 'BUSINESS' in config and 'CP' in config['BUSINESS'] and 'cp_id' in config['BUSINESS']['CP']:
                        cp_ids = config['BUSINESS']['CP']['cp_id']
                        self.user_cp_bindings[username] = cp_ids
                        LOGGER.info(f"用户 {username} 绑定的CP IDs: {cp_ids}")
                    else:
                        LOGGER.info(f"用户 {username} 没有绑定CP")
                
                except Exception as e:
                    LOGGER.error(f"处理用户 {username} 的YAML配置时出错: {str(e)}")
            
            LOGGER.info(f"成功加载了 {len(self.user_cp_bindings)} 个用户的CP绑定信息")
        
        except Exception as e:
            LOGGER.error(f"加载用户CP绑定信息时出错: {str(e)}")
    
    def load_cp_list(self):
        """加载CP列表用于账号绑定"""
        try:
            # 显示加载状态
            self.status_label.setText("正在加载CP列表...")
            QApplication.processEvents()
            
            # 获取CP列表
            self.cp_list = CP.list()
            
            # 清空下拉框
            self.cp_combo.clear()
            
            # 添加一个空选项
            self.cp_combo.addItem("-- 不绑定CP --", None)
            
            # 添加CP到下拉框
            for cp in self.cp_list:
                cp_name = cp.get('cp_name', '')
                cp_id = cp.get('cp_id', '')
                if cp_name and cp_id:
                    self.cp_combo.addItem(f"{cp_name} (ID: {cp_id})", cp_id)
            
            # 记录日志
            LOGGER.info(f"成功加载CP列表: {len(self.cp_list)} 个CP")
            
            # 更新状态
            self.status_label.setText(f"成功加载 {len(self.cp_list)} 个CP")
        
        except Exception as e:
            LOGGER.error(f"加载CP列表时出错: {str(e)}")
            self.status_label.setText(f"加载CP列表时出错: {str(e)}")
    
    def update_accounts_table(self):
        """更新账号表格"""
        try:
            # 清空表格
            self.accounts_table.setRowCount(0)
            
            # 添加账号到表格
            for username, info in self.accounts.items():
                if username == 'admin':
                    continue  # 跳过admin账号
                
                row = self.accounts_table.rowCount()
                self.accounts_table.insertRow(row)
                
                # 用户名
                username_item = QTableWidgetItem(username)
                self.accounts_table.setItem(row, 0, username_item)
                
                # 绑定CP - 从用户YAML配置中获取
                bound_cp_text = "未绑定"
                cp_ids = self.user_cp_bindings.get(username, [])
                
                if cp_ids:
                    if isinstance(cp_ids, list):
                        # 如果是列表，收集所有CP名称
                        cp_names = []
                        for cp_id in cp_ids:
                            cp_name = self.get_cp_name(cp_id)
                            if cp_name:
                                cp_names.append(cp_name)
                        
                        if cp_names:
                            bound_cp_text = ", ".join(cp_names)
                    elif isinstance(cp_ids, str):
                        # 如果是单个字符串
                        cp_name = self.get_cp_name(cp_ids)
                        if cp_name:
                            bound_cp_text = cp_name
                
                cp_item = QTableWidgetItem(bound_cp_text)
                self.accounts_table.setItem(row, 1, cp_item)
                
                # 删除按钮
                delete_button = QPushButton("删除")
                delete_button.setStyleSheet("""
                    QPushButton {
                        background-color: #d9534f;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 3px 10px;
                    }
                    QPushButton:hover {
                        background-color: #c9302c;
                    }
                """)
                delete_button.clicked.connect(lambda checked, u=username: self.delete_account(u))
                
                # 将按钮添加到单元格
                self.accounts_table.setCellWidget(row, 2, delete_button)
        
        except Exception as e:
            LOGGER.error(f"更新账号表格时出错: {str(e)}")
            self.status_label.setText(f"更新账号表格时出错: {str(e)}")
    
    def get_cp_name(self, cp_id):
        """通过CP ID获取CP名称"""
        if not cp_id:
            return ""
        
        for cp in self.cp_list:
            if cp.get('cp_id') == cp_id:
                return cp.get('cp_name', '')
        
        return ""
    
    def register_account(self):
        """注册新账号"""
        try:
            # 获取输入
            username = self.username_input.text().strip()
            password = self.password_input.text()
            confirm_password = self.confirm_password_input.text()
            
            # 获取选中的CP ID
            cp_index = self.cp_combo.currentIndex()
            cp_id = self.cp_combo.itemData(cp_index)
            
            # 验证输入
            if not username:
                QMessageBox.warning(self, "输入错误", "请输入用户名")
                return
            
            if not password:
                QMessageBox.warning(self, "输入错误", "请输入密码")
                return
            
            if password != confirm_password:
                QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
                return
            
            # 检查用户名是否已存在
            if username in self.accounts:
                QMessageBox.warning(self, "用户名已存在", f"用户名 '{username}' 已被使用，请选择其他用户名")
                return
            
            # 准备新账号信息
            new_account = {
                "username": username,
                "password": password
            }
            
            # 显示确认对话框
            confirm_msg = f"确定要注册以下账号吗？\n\n用户名: {username}\n"
            
            if cp_id:
                # 如果选择了CP，提示将生成配置文件
                cp_name = self.get_cp_name(cp_id)
                confirm_msg += f"将为用户创建配置文件并绑定CP: {cp_name} (ID: {cp_id})"
            else:
                confirm_msg += "用户将没有绑定任何CP"
            
            reply = QMessageBox.question(self, "确认注册", confirm_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # 添加到账号列表
                self.accounts[username] = new_account
                
                # 保存到OSS
                self.save_accounts()
                
                # 如果选择了CP，创建用户YAML配置文件
                if cp_id:
                    self.create_user_yaml_config(username, cp_id)
                
                # 清空输入
                self.username_input.clear()
                self.password_input.clear()
                self.confirm_password_input.clear()
                self.cp_combo.setCurrentIndex(0)
                
                # 更新表格
                self.load_user_cp_bindings()
                self.update_accounts_table()
                
                # 显示成功消息
                QMessageBox.information(self, "注册成功", f"账号 '{username}' 已成功注册")
        
        except Exception as e:
            LOGGER.error(f"注册账号时出错: {str(e)}")
            QMessageBox.critical(self, "注册失败", f"注册账号时出错: {str(e)}")
    
    def create_user_yaml_config(self, username, cp_id):
        """为新用户创建YAML配置文件并上传到OSS"""
        try:
            # 获取OSS配置
            oss_conf = CONF.KEYS.oss
            auth = oss2.Auth(oss_conf.get('access_key_id'), oss_conf.get('access_key_secret'))
            bucket = oss2.Bucket(auth, oss_conf.get('endpoint'), oss_conf.get('bucket_name'), region=oss_conf.get('region'))
            
            # 临时目录
            temp_dir = tempfile.gettempdir()
            
            # 先下载default.yaml作为模板
            default_yaml_path = 'configs/default.yaml'
            local_default_yaml = os.path.join(temp_dir, 'default.yaml')
            local_yaml_file = os.path.join(temp_dir, f"{username}.yaml")
            
            # 检查default.yaml是否存在
            if bucket.object_exists(default_yaml_path):
                # 下载default.yaml
                bucket.get_object_to_file(default_yaml_path, local_default_yaml)
                self.temp_files.append(local_default_yaml)
                
                # 读取default配置
                with open(local_default_yaml, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 如果配置为None（空文件），初始化为空字典
                if config is None:
                    config = {}
                
                # 确保有BUSINESS和CP部分
                if 'BUSINESS' not in config:
                    config['BUSINESS'] = {}
                if 'CP' not in config['BUSINESS']:
                    config['BUSINESS']['CP'] = {}
                
                # 修改CP:cp_id部分
                config['BUSINESS']['CP']['cp_id'] = [cp_id]
                
                LOGGER.info(f"已从default.yaml创建配置并设置CP绑定: {cp_id}")
            else:
                # 如果没有default.yaml，创建一个基本配置
                LOGGER.warning("未找到default.yaml，将创建基本配置")
                config = {
                    "BUSINESS": {
                        "CP": {
                            "cp_id": [cp_id]
                        }
                    }
                }
            
            # 保存YAML文件
            with open(local_yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            self.temp_files.append(local_yaml_file)
            
            # 上传到OSS
            yaml_path = f'configs/{username}.yaml'
            bucket.put_object_from_file(yaml_path, local_yaml_file)
            
            # 更新本地缓存
            self.user_cp_bindings[username] = [cp_id]
            
            LOGGER.info(f"已为用户 {username} 创建配置文件并绑定CP: {cp_id}")
            
        except Exception as e:
            LOGGER.error(f"创建用户YAML配置文件时出错: {str(e)}")
            raise
    
    def delete_account(self, username):
        """删除账号"""
        try:
            # 显示确认对话框
            confirm_msg = f"确定要删除账号 '{username}' 吗？此操作将同时删除用户配置文件，不可恢复。"
            reply = QMessageBox.question(self, "确认删除", confirm_msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # 从账号列表中移除
                if username in self.accounts:
                    del self.accounts[username]
                
                # 保存账号信息到OSS
                self.save_accounts()
                
                # 删除用户YAML配置文件
                self.delete_user_yaml_config(username)
                
                # 从本地缓存中删除
                if username in self.user_cp_bindings:
                    del self.user_cp_bindings[username]
                
                # 更新表格
                self.update_accounts_table()
                
                # 显示成功消息
                self.status_label.setText(f"账号 '{username}' 已成功删除")
                LOGGER.info(f"账号 '{username}' 已成功删除")
        
        except Exception as e:
            LOGGER.error(f"删除账号时出错: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"删除账号 '{username}' 时出错: {str(e)}")
    
    def delete_user_yaml_config(self, username):
        """删除用户的YAML配置文件"""
        try:
            # 获取OSS配置
            oss_conf = CONF.KEYS.oss
            auth = oss2.Auth(oss_conf.get('access_key_id'), oss_conf.get('access_key_secret'))
            bucket = oss2.Bucket(auth, oss_conf.get('endpoint'), oss_conf.get('bucket_name'), region=oss_conf.get('region'))
            
            # 检查并删除配置文件
            yaml_path = f'configs/{username}.yaml'
            if bucket.object_exists(yaml_path):
                bucket.delete_object(yaml_path)
                LOGGER.info(f"已删除用户 {username} 的配置文件")
            else:
                LOGGER.info(f"用户 {username} 的配置文件不存在")
                
        except Exception as e:
            LOGGER.error(f"删除用户配置文件时出错: {str(e)}")
            raise
    
    def save_accounts(self):
        """保存账号信息到OSS"""
        try:
            # 显示保存状态
            self.status_label.setText("正在保存账号信息...")
            QApplication.processEvents()
            
            # 获取OSS配置
            oss_conf = CONF.KEYS.oss
            auth = oss2.Auth(oss_conf.get('access_key_id'), oss_conf.get('access_key_secret'))
            bucket = oss2.Bucket(auth, oss_conf.get('endpoint'), oss_conf.get('bucket_name'), region=oss_conf.get('region'))
            
            # 1. 保存明文密码到login_info_base.json
            login_info_base_path = 'login_info_base.json'
            temp_dir = tempfile.gettempdir()
            local_base_file = os.path.join(temp_dir, 'login_info_base_new.json')
            
            # 临时保存明文密码文件
            with open(local_base_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=4)
            
            # 上传到OSS
            bucket.put_object_from_file(login_info_base_path, local_base_file)
            self.temp_files.append(local_base_file)
            
            # 2. 创建带哈希密码的login_info.json
            login_info_path = 'login_info.json'
            local_hash_file = os.path.join(temp_dir, 'login_info_new.json')
            
            # 创建哈希密码版本
            hashed_accounts = {}
            for username, info in self.accounts.items():
                hashed_info = info.copy()
                # 对密码进行哈希
                if 'password' in hashed_info:
                    hashed_info['password'] = hash_text(hashed_info['password'])
                hashed_accounts[username] = hashed_info
            
            # 临时保存哈希密码文件
            with open(local_hash_file, 'w', encoding='utf-8') as f:
                json.dump(hashed_accounts, f, ensure_ascii=False, indent=4)
            
            # 上传到OSS
            bucket.put_object_from_file(login_info_path, local_hash_file)
            self.temp_files.append(local_hash_file)
            
            # 记录日志
            LOGGER.info(f"成功保存账号信息到OSS: {len(self.accounts)} 个账号")
            
            # 更新状态
            self.status_label.setText(f"成功保存 {len(self.accounts)} 个账号")
        
        except Exception as e:
            LOGGER.error(f"保存账号信息时出错: {str(e)}")
            self.status_label.setText(f"保存账号信息时出错: {str(e)}")
            QMessageBox.critical(self, "保存失败", f"保存账号信息时出错: {str(e)}")
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    LOGGER.info(f"已删除临时文件: {file_path}")
            except Exception as e:
                LOGGER.error(f"删除临时文件时出错: {str(e)}")
    
    def __del__(self):
        """析构函数，清理资源"""
        self.cleanup_temp_files()
