import requests
import time
import logging
from typing import Callable, List, Any, Optional
from app.utils.logger import setup_logger


LOGGER = setup_logger("moco.log")

def robust_query(query_func: Callable, keys: List[str], max_retries: int = 1, 
                interval: float = 1.0, timeout: float = 10.0, **kwargs) -> Optional[Any]:
    """
    健壮的API查询封装，支持多个API密钥轮询和错误重试
    
    :param query_func: 查询函数，接受key作为参数
    :param keys: API密钥列表
    :param max_retries: 每个密钥的最大重试次数
    :param interval: 重试间隔时间(秒)
    :param timeout: 查询超时时间(秒)
    :return: 查询结果或None(如果所有尝试都失败)
    """
    if not keys:
        # LOGGER.error("未提供任何API密钥")
        return None
        
    for key in keys:
        for attempt in range(max_retries):
            try:
                # 设置超时
                start_time = time.time()
                ans = query_func(key, **kwargs)
                
                # 检查结果是否有效
                if ans is not None:
                    return ans
                
                LOGGER.warning(f"使用密钥 {key[:8]}... 查询返回空结果，尝试 {attempt+1}/{max_retries}")
            except Exception as e:
                LOGGER.error(f"查询失败 (密钥: {key[:8]}..., 尝试: {attempt+1}/{max_retries}): {str(e)}")
            
            # 检查是否超时
            if time.time() - start_time > timeout:
                LOGGER.error(f"查询超时 (密钥: {key[:8]}...)")
                break
                
            # 在重试前等待
            if attempt < max_retries - 1:
                time.sleep(interval)
    
    LOGGER.error("所有API密钥和重试次数均已用尽，查询失败")
    return None
