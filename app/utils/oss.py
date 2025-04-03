import yaml
import json
import oss2
from app.utils import rp
from app.utils.logger import setup_logger


LOGGER = setup_logger("moco.log")

with open(rp("SYSCONF_default.yaml", folder="config"), 'r', encoding='utf-8') as f:
    SYS_CONF = yaml.safe_load(f)
OSS_CONF = SYS_CONF['KEYS']['oss']



def oss_get_yaml_file(file_path):
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        object_stream = bucket.get_object(file_path)
        # 读取内容并解析YAML
        content = object_stream.read().decode('utf-8')
        info = yaml.safe_load(content)
        LOGGER.info("[OSS] 成功获取用户信息文件")
        return info
    except Exception as e:
        LOGGER.error(f"[OSS] 获取文件失败: {e}")
        return None
    
def oss_get_json_file(file_path):
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        object_stream = bucket.get_object(file_path)
        # 读取内容并解析JSON
        content = object_stream.read().decode('utf-8')
        info = json.loads(content)
        LOGGER.info("[OSS] 成功获取用户信息文件")
        return info
    except Exception as e:
        LOGGER.error(f"[OSS] 获取文件失败: {e}")
        return None

