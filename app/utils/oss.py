import yaml
import json
import oss2
from app.utils import rp
from app.utils.logger import setup_logger
import pandas as pd
import io


LOGGER = setup_logger()

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

def oss_put_yaml_file(file_path, data):
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        # 将数据转换为YAML格式
        content = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        bucket.put_object(file_path, content)
        LOGGER.info(f"[OSS] 成功上传YAML文件: {file_path}")
        return True
    except Exception as e:
        LOGGER.error(f"[OSS] 上传YAML文件失败: {e}")
        return False

def oss_put_json_file(file_path, data):
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        bucket.put_object(file_path, json.dumps(data, ensure_ascii=False))
        LOGGER.info(f"[OSS] 成功上传文件: {file_path}")
    except Exception as e:
        LOGGER.error(f"[OSS] 上传文件失败: {e}")
        return False
    return True

def oss_get_excel_file(file_path):
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        object_stream = bucket.get_object(file_path)
        # 读取内容并解析Excel
        content = object_stream.read()
        df = pd.read_excel(content)
        LOGGER.info("[OSS] 成功获取Excel文件")
        return df
    except Exception as e:
        LOGGER.error(f"[OSS] 获取Excel文件失败: {e}")
        return None

def oss_put_excel_file(file_path, df):
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        # 将DataFrame写入Excel格式的字节流
        output = io.BytesIO()
        df.to_excel(output, index=False)  # 将DataFrame转换为Excel格式
        output.seek(0)  # 重置流的位置
        bucket.put_object(file_path, output.getvalue())  # 上传到OSS
        LOGGER.info(f"[OSS] 成功上传Excel文件: {file_path}")
    except Exception as e:
        LOGGER.error(f"[OSS] 上传Excel文件失败: {e}")
        return False
    return True

def oss_rename_excel_file(old_file_path, new_file_path):
    try:
        # 获取 OSS 配置
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)

        # 下载旧文件内容
        object_stream = bucket.get_object(old_file_path)
        content = object_stream.read()

        # 上传到新文件名
        bucket.put_object(new_file_path, content)
        LOGGER.info(f"[OSS] 成功将文件重命名为: {new_file_path}")

        # 删除旧文件
        bucket.delete_object(old_file_path)
        LOGGER.info(f"[OSS] 成功删除旧文件: {old_file_path}")

    except Exception as e:
        LOGGER.error(f"[OSS] 重命名文件失败: {e}")
        return False

    return True

def oss_list_objects(prefix):
    """
    列出OSS存储桶中指定前缀的所有对象
    
    Args:
        prefix (str): 对象前缀
        
    Returns:
        list: 对象列表，如果发生错误则返回None
    """
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        
        # 列举所有指定前缀的文件
        objects = []
        for obj in oss2.ObjectIterator(bucket, prefix=prefix):
            objects.append(obj)
        
        LOGGER.info(f"[OSS] 成功列出前缀为 {prefix} 的对象，共 {len(objects)} 个")
        return objects
    except Exception as e:
        LOGGER.error(f"[OSS] 列出对象失败: {e}")
        return None

def oss_delete_object(object_key):
    """
    删除OSS存储桶中的指定对象
    
    Args:
        object_key (str): 要删除的对象的完整路径
        
    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        access_key_id = OSS_CONF['access_key_id']
        access_key_secret = OSS_CONF['access_key_secret']
        endpoint = OSS_CONF['endpoint']
        bucket_name = OSS_CONF['bucket_name']
        region = OSS_CONF['region']
        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
        
        # 删除对象
        bucket.delete_object(object_key)
        LOGGER.info(f"[OSS] 成功删除对象: {object_key}")
        return True
    except Exception as e:
        LOGGER.error(f"[OSS] 删除对象失败: {e}")
        return False

