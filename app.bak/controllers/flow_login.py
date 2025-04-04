from app.services.oss_service import OSSService
from app.utils.hash import hash_text
from app.utils.logger import setup_logger

class LoginController:
    def __init__(self):
        self.logger = setup_logger("moco.log")
        self.oss_service = OSSService()
    
    def validate_user_info(self, username, password):
        """
        验证用户信息
        
        Args:
            username (str): 用户名
            password (str): 用户输入的密码（未哈希）
            
        Returns:
            tuple: (bool, str) - (是否验证成功, 用户类型/角色)
        """
        try:
            # 获取用户信息文件
            user_info = self.oss_service.get_user_info()
            if not user_info:
                self.logger.error("无法获取用户信息文件")
                return False, None
            
            # 对输入的密码进行哈希
            hashed_password = hash_text(password)
            
            # 验证用户身份
            for user_key, user_data in user_info.items():
                if user_data["username"] == username and user_data["password"] == hashed_password:
                    self.logger.info(f"用户 {username} 验证成功")
                    return True, user_key
            
            self.logger.info(f"用户 {username} 验证失败")
            return False, None
            
        except Exception as e:
            self.logger.error(f"验证用户信息时发生错误: {e}")
            return False, None

# 提供便捷的函数接口
def validate_user_info(username, password):
    """
    验证用户信息的便捷函数
    
    Args:
        username (str): 用户名
        password (str): 用户输入的密码（未哈希）
        
    Returns:
        tuple: (bool, str) - (是否验证成功, 用户类型/角色)
    """
    controller = LoginController()
    return controller.validate_user_info(username, password) 