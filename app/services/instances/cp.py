from app.models.cp_model import CPModel
from typing import Dict, List, Any, Optional
from app.services.instances.base import BaseInstance, BaseGroup
from app.utils.oss import oss_get_json_file, oss_put_json_file
from app.utils.logger import setup_logger
import uuid
import json
import oss2
from app.utils import rp, hash_text
import yaml
from app.config.config import CONF

# 设置日志
LOGGER = setup_logger()

OSS_CONF = CONF['KEYS']['oss']

class CP(BaseInstance):
    """
    CP实体类，处理CP模型的业务逻辑
    """
    def __init__(self, info: Dict[str, Any], model=CPModel):
        """
        初始化CP实体
        
        :param info: CP信息字典
        :param model: CP模型类，可选
        """
        super().__init__(model)
        
        # 确保必须的字段存在
        assert info.get('cp_name') is not None, "必须提供CP名称"
        
        
        try:
            self.inst = model(**info)
            self._generate_id()
            self.status = 'pending'  # 初始状态为待处理
        except Exception as e:
            LOGGER.error(f"创建CP实例失败: {e}")
            raise e
        
    
    def _generate_id(self):
        """
        生成唯一ID
        """
        if not hasattr(self.inst, 'cp_id') or not self.inst.cp_id:
            self.inst.cp_id = hash_text(self.inst.cp_name)[:10]
            LOGGER.info(f"生成CP ID: {self.inst.cp_id}")
        else:
            LOGGER.info(f"CP ID已存在: {self.inst.cp_id}")
    
    def register(self) -> bool:
        """
        注册CP到OSS
        
        :return: 是否注册成功
        """
        try:
            # 生成唯一ID（如果不存在）
            if not hasattr(self.inst, 'cp_id') or not self.inst.cp_id:
                self._generate_id()
            
            # 准备要保存的数据
            cp_data = {}
            for key, value in self.inst.__dict__.items():
                if not key.startswith('_'):
                    cp_data[key] = value
            
            # 保存到OSS，新的路径结构：CPs/<id>/<id>.json
            file_path = f"CPs/{self.inst.cp_id}/{self.inst.cp_id}.json"
            oss_put_json_file(file_path, cp_data)
            
            LOGGER.info(f"CP '{self.inst.cp_name}' 已成功注册到OSS，路径: {file_path}")
            self.status = 'registered'
            return True
            
        except Exception as e:
            LOGGER.error(f"注册CP失败: {e}")
            return False
    
    def update(self) -> bool:
        """
        更新CP信息到OSS
        
        :return: 是否更新成功
        """
        try:
            # 准备要保存的数据
            cp_data = {}
            for key, value in self.inst.__dict__.items():
                if not key.startswith('_'):
                    cp_data[key] = value
            
            # 更新到OSS，路径结构：CPs/<id>/<id>.json
            file_path = f"CPs/{self.inst.cp_id}/{self.inst.cp_id}.json"
            oss_put_json_file(file_path, cp_data)
            
            LOGGER.info(f"CP '{self.inst.cp_name}' 已成功更新到OSS，路径: {file_path}")
            self.status = 'updated'
            return True
            
        except Exception as e:
            LOGGER.error(f"更新CP失败: {e}")
            return False
    
    def delete(self) -> bool:
        """
        从OSS删除CP
        
        :return: 是否删除成功
        """
        try:
            # 获取OSS连接
            access_key_id = OSS_CONF['access_key_id']
            access_key_secret = OSS_CONF['access_key_secret']
            endpoint = OSS_CONF['endpoint']
            bucket_name = OSS_CONF['bucket_name']
            region = OSS_CONF['region']
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
            
            # 删除CP文件
            file_path = f"CPs/{self.inst.cp_id}/{self.inst.cp_id}.json"
            bucket.delete_object(file_path)
            
            LOGGER.info(f"CP '{self.inst.cp_name}' 已成功从OSS删除，路径: {file_path}")
            self.status = 'deleted'
            return True
            
        except Exception as e:
            LOGGER.error(f"删除CP失败: {e}")
            return False
    
    @classmethod
    def list(cls) -> List[Dict[str, Any]]:
        """
        获取OSS上所有CP的列表
        
        :return: CP列表
        """
        try:
            # 获取OSS连接
            access_key_id = OSS_CONF['access_key_id']
            access_key_secret = OSS_CONF['access_key_secret']
            endpoint = OSS_CONF['endpoint']
            bucket_name = OSS_CONF['bucket_name']
            region = OSS_CONF['region']
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)
            
            # 列出所有CP文件 - 适应新的目录结构
            cp_list = []
            for obj in oss2.ObjectIterator(bucket, prefix='CPs/'):
                # 检查是否是json文件且符合新的路径结构 CPs/<id>/<id>.json
                if obj.key.endswith('.json'):
                    parts = obj.key.split('/')
                    # 确保路径格式为 CPs/<id>/<id>.json
                    if len(parts) == 3 and parts[0] == 'CPs' and parts[1] + '.json' == parts[2]:
                        # 获取CP数据
                        cp_data = oss_get_json_file(obj.key)
                        if cp_data:
                            cp_list.append(cp_data)
            
            LOGGER.info(f"成功获取{len(cp_list)}个CP列表")
            return cp_list
            
        except Exception as e:
            LOGGER.error(f"获取CP列表失败: {e}")
            return []
    
    @classmethod
    def get_by_id(cls, cp_id: str) -> Optional['CP']:
        """
        通过ID获取CP
        
        :param cp_id: CP ID
        :return: CP实例或None
        """
        try:
            # 构建文件路径 - 新的路径结构
            file_path = f"CPs/{cp_id}/{cp_id}.json"
            
            # 获取CP数据
            cp_data = oss_get_json_file(file_path)
            if not cp_data:
                LOGGER.error(f"未找到ID为{cp_id}的CP")
                return None
            
            # 创建CP实例
            cp = cls(cp_data)
            cp.status = 'loaded'
            LOGGER.info(f"成功加载ID为{cp_id}的CP")
            return cp
            
        except Exception as e:
            LOGGER.error(f"获取CP失败: {e}")
            return None
    
    def __str__(self) -> str:
        """
        返回CP的字符串表示
        
        :return: 字符串表示
        """
        if hasattr(self.inst, 'cp_name') and hasattr(self.inst, 'cp_id'):
            return f"CP(id={self.inst.cp_id}, name={self.inst.cp_name}, status={self.status})"
        return f"CP(未完成初始化, status={self.status})"


class CPsGroup(BaseGroup):
    """
    CP组合类，用于管理多个CP实体
    """
    def __init__(self, cps: List[CP] = None, group_type: str = None):
        """
        初始化CP组合
        
        :param cps: CP列表
        :param group_type: 组合类型，如'city'、'province'等
        """
        super().__init__(cps, group_type)
    
    
    def get_by_id(self, cp_id: str) -> Optional[CP]:
        """
        按ID获取CP
        
        :param cp_id: CP ID
        :return: CP实体或None
        """
        for cp in self.members:
            if hasattr(cp.inst, 'cp_id') and cp.inst.cp_id == cp_id:
                return cp
        return None
    
    def get_by_name(self, name: str) -> Optional[CP]:
        """
        按名称获取CP
        
        :param name: CP名称
        :return: CP实体或None
        """
        for cp in self.members:
            if hasattr(cp.inst, 'cp_name') and cp.inst.cp_name == name:
                return cp
        return None
    
    def __str__(self) -> str:
        """
        返回CP组合的字符串表示
        
        :return: 字符串表示
        """
        return f"CPsGroup(数量={self.count()}, 类型={self.group_type})"


