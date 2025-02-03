from app.services.config_services import ConfigValidator

def flow0_validate_config(file_path: str):
    """验证配置文件"""
    try:
        ConfigValidator.validate_config(file_path)
        return True, None
    except Exception as e:
        return False, e