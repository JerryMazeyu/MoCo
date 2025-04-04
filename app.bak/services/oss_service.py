import oss2
from app.config import CONF
from app.utils.logger import setup_logger
import json

class OSSService:
    def __init__(self):
        self.logger = setup_logger("moco.log")
        try:
            oss_conf = CONF.SYSTEM.oss
            self.oss_conf = oss_conf
            access_key_id = oss_conf.access_key_id
            access_key_secret = oss_conf.access_key_secret
            auth = oss2.Auth(access_key_id, access_key_secret)
            endpoint = oss_conf.endpoint
            bucket_name = oss_conf.bucket_name
            region = oss_conf.region
            self.bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
            self.logger.info(f"[OSS] 初始化成功")
        except Exception as e:
            self.logger.info(f"[OSS] 初始化失败: {e}")

    def upload_file(self, file_path, file_name):
        pass

    def download_file(self, file_name):
        pass

    def delete_file(self, file_name):
        pass

    def list_files(self):
        pass

    def get_user_info(self):
        """
        从OSS存储桶中获取用户信息文件
        
        Returns:
            dict: 包含用户信息的字典
            None: 如果获取失败
        """
        try:
            # 指定要下载的文件名
            file_name = 'login_info.json'
            
            # 获取文件对象
            object_stream = self.bucket.get_object(file_name)
            
            # 读取内容并解析JSON
            content = object_stream.read()
            user_info = json.loads(content)
            
            self.logger.info("[OSS] 成功获取用户信息文件")
            return user_info
        except Exception as e:
            self.logger.error(f"[OSS] 获取用户信息文件失败: {e}")
            return None
    

