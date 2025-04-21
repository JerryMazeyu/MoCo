import os
import json
import requests
import pandas as pd
from typing import Dict, Any, List, Optional, Union
import threading
import time
import sys 
import concurrent.futures
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from app.services.instances.restaurant import Restaurant, RestaurantsGroup
from app.services.instances.receive_record import ReceiveRecord, ReceiveRecordsGroup, ReceiveRecordsBalance,BalanceRecords,BalanceRecordsGroup
from app.utils.logger import setup_logger
from app.utils.file_io import rp
from app.config.config import CONF
from app.utils.query import robust_query
import re
import math
from app.utils.oss import oss_get_json_file
# 设置日志
LOGGER = setup_logger("moco.log")

class UpdateCpStockService:
    """
    更新CP库存的服务
    """
    def __init__(self, balance_records: Union[BalanceRecordsGroup,List[BalanceRecords], pd.DataFrame],conf=CONF):
        self.conf = conf
        self.balance_records = balance_records
        if hasattr(self.conf.runtime, 'r'):
            pass
    
    def run(self, mode='receive'):
        """
        实现油量库存更新，包括收油和送油
        """
        pass
        

        
