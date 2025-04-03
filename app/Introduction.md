# 核心开发逻辑

本项目旨在开发一套数据生成系统，其包含了一个收油的流程，收油的流程为：餐厅 -> CP(小工厂) ->贸易场（TP） / 客户，我需要在其中构建整个链条的数据信息。

## 0. 配置（config/config.py）

配置项类指的是涉及到一些配置的信息，其中将会存放两个yaml文件，一个是SYSCONF.yaml，主要包含了系统的整体配置信息，一个是USERCONF.yaml，会根据用户登录的不同账户在云端获得不同的信息，这里可能会出现有重复的内容，那么优先级往往以用户配置更高。

```yaml
# SYSCONF
STREETMAPS:  # 地区街道信息
  huizhou:  # 惠州
    博罗县：
      园洲镇,湖镇镇,石坝镇,麻陂镇,龙溪街道,杨侨镇,杨村镇,观音阁镇,龙华镇,柏塘镇,横河镇,罗阳街道,公庄镇,福田镇,长宁镇,泰美镇,石湾镇
    龙门县：
      龙华镇,龙田镇，龙江镇，蓝田瑶族乡，永汉镇，龙湮镇，麻榨镇，地派镇，龙城街道，平陵街道
KEYS:  # 整个流程中涉及到的一些apikeys
  kimi_keys: # 调用大模型的keys
    - 'xxxx'
    - 'xxxx'
  baidu_keys: # 百度地图的keys
    - '12345678'
    - '87654321'
  gaode_keys: # 高德地图的keys
    - '12345678'
    - '87654321'
  serp_keys: # serp的keys
    - '12345678'
    - '87654321'
  tripadvisor_keys: # tripadvisor的keys
    - '12345678'
    - '87654321'
  oss:  # 云端服务器的配置项目
    access_key_id: 'exampleAccessKeyId' # exampleAccessKeyId
    access_key_secret: 'exampleAccessKeySecret' #exampleAccessKeySecret
    endpoint: 'http://oss-cn-shanghai.aliyuncs.com'
    bucket_name: 'moco-data'
    region: 'cn-shanghai'
SPECIAL:  # 凡是在这里面的将被添加到后面Config类的special_list中，将在前段显示
  - KEYS.oss
  - KEYS.kimi_keys
```

```yaml
# USERCONF
USERNAME: username
BUSINESS:
  CP:
    cp_id:  # 每个用户可能负责多个CP
  	  - id1
  	  - id2
  RESTAURANT:  # 与餐厅相关的内容
    收油关系映射:  # 每种类型餐厅收油的桶数
      小食/小吃/美食/饮食/私房菜: 1,2
      酒楼/酒家/烤鱼: 3,4
      酸菜鱼: 1
      餐厅/餐馆/饭店/饭馆/川菜/湘菜/农庄/山庄/大排档/食府/公司/炸鸡: 2,3
      餐饮/汉堡: 1,3
  REST2CP:  # 餐厅到CP过程中的配置
    吨每桶：0.18
    比率：0.91
    每车收购量范围: 35,44
MISC:  # 一些杂项
  Tab1: 
	last_dir: xxxx  # 上次Tab1页面中保存的路径
  Tab2:
	last_dir: xxxx  # 上次Tab2页面中保存的路径
KEYS:  # 整个流程中涉及到的一些apikeys（用户可以自定义覆盖部分SYSCONF）
  kimi_keys: # 调用大模型的keys
    - 'xxxx'
    - 'xxxx'
  baidu_keys: # 百度地图的keys
    - '12345678'
    - '87654321'
  gaode_keys: # 高德地图的keys
    - '12345678'
    - '87654321'
SPECIAL:  # 凡是在这里面的将被添加到后面Config类的special_list中，将在前段显示
  - BUSINESS.REST2CP
```

最终在config.py中，应该包含一个ConfigService类，其中主要包含的功能是以下部分：

```python
class ConfigService():
    def __init__(self, username: str):
        # 首先加载sys_conf_path，找到其中的OSS部分，这里注意一个逻辑，SYSCONF应该首选本地的config.yaml，如果没有获取到（文件不存在），则获取default.yaml，然后后续保存的时候default.yaml是永远不会动的，只会保存为config.yaml，然后从OSS上拿到用户名对应的<username>.yaml，这里有一个优先级，如果当本地已经有<username>_temp.yaml的时候，是不需要进行加载的，当没有的情况下才需要现在
        # 根据这两个yaml文件进行整合，根据优先级融合求并集
        # 把SPECIAL中的字段拿出来，放到self.special_list中
    
    def save(self):
        # 将配置保存，将user的部分，保存为<username>_temp.yaml，暂时不允许修改SYSCONF的部分
    def upload(self):
        # 将该配置文件上传到OSS中
    def refresh(self):
        # 首先删除<username>_temp.yaml，然后采用SYSTEM的OSS下载<username>.yaml
    
    ... # 剩下的完全参考已有的config.py逻辑即可
```

```python
# 自动的加载ConfigService并实例化，并命名为CONF
# CONF应该支持这几个功能：
# 1. 通过路径获取，例如：CONF.BUSINESS.CP,这里需要考虑是否可以中文索引？
# 2. 通过dict形式获取，例如：CONF._config_dict['BUSINESS']['RESTAURANT']['收油关系映射']
# 3. 保存数据，CONF.save()自动保存为两份：merge_<user_name>.yaml
# 4. 上传配置文件
# 5. 更新配置文件
__all__ = ['CONF']
```

确保在本文件处理后获得CONF这个变量，后续的所有逻辑都可能使用这个CONF。

## 1. 模型（app/models）

采用pydantic定义数据模型，便于管理。注意，在模型字段中不做校验，以便于敏捷开发。

### 3.1 餐厅模型：restaurant_model.py

餐厅一般来自于小工厂CP附近，CP从附近的各个餐厅中进行收油。餐厅模型应包含以下字段：

* rest_id：餐厅id（根据中文名hash后生成，唯一）
* rest_belonged_cp：所属CP（必须有）

* rest_chinese_name：餐厅中文名（必须有）
* rest_english_name：餐厅英文名（可以暂时没有，后续生成）
* rest_city：所在区域（必须有）
* rest_province：所在省份（必须有）
* rest_chinese_address：餐厅中文地址（必须有）
* rest_english_address：餐厅英文地址（可以暂时没有，后续生成）
* rest_district：所属区域（可以暂时没有，后续生成）
* rest_street：所属街道（可以暂时没有，后续生成）
* rest_contact_person：法人信息（可以暂时没有，后续生成）
* rest_contact_phone：法人电话（可以暂时没有，后续生成）
* rest_location：餐厅的经纬度，格式为 '纬度,经度'（例如 '39.9042,116.4074'）
* rest_distance：与所属CP的距离（单位为km）
* rest_type：餐厅类型（可以暂时没有）
* rest_verified_date：上次校验的时间（在没校验过的时候就暂时填写空）
* rest_allocated_barrel：分配的桶数（可以暂时没有）
* rest_other_info：其他信息，可以暂时为空字典

### 3.2 车辆模型：vehicle_model.py

 车辆主要来自于小工厂CP，不同的车辆负责从餐厅收油、给贸易场销售等。车辆模型应包含以下字段：

* vehicle_id：车辆ID（根据车牌号hash后生成）
* vehicle_belonged_cp：所属CP（这里注意，除了CP之外可能还会有贸易场TP，此时为空）

* vehicle_license_plate：车牌号信息（必须有）
* vehicle_driver_name：司机姓名（必须有）
* vehicle_type：车辆类型（目前有餐厅收集车to_rest、销售运输车to_sale两种）
* vehicle_rough_weight：毛重（根据不同的类型有计算公式，后续会给出）
* vehicle_tare_weight：皮重（根据不同的类型有计算公式，后续会给出）
* vehicle_net_weight：净重（根据不同的）
* vehicle_historys：每次收油的记录，是一个列表，注意这里仅仅维护过去5次的
* vehicle_status：状态（分为可用available和不可用unavailable）
* vehicle_last_use：上次使用的日期
* vehicle_other_info：其他信息，可以暂时为空字典

### 3.3 小工厂CP：cp_models.py

小工厂CP是收油的中转站，一方面从附近的餐厅中收油，另一方面将收来的油发货给贸易场TP或者直接发送给客户。CP模型应包含以下字段：

* cp_id：CP的ID（自动随机生成，但也可以指定）
* cp_name：CP的名称（必须有）
* cp_province：CP所属的省份
* cp_city：CP所属的城市
* cp_location：CP的经纬度
* cp_barrels_per_day：每天收油量
* cp_capacity：总容量
* cp_recieve_raw：CP会自动的收油，这里是一个列表，存放着所有的收油记录，注意到这里的记录并不一定被确认

* cp_sales_record：CP发货的记录
* cp_recieve_record：CP收油确认的记录
* cp_stock：CP的库存
* cp_vehicle_to_rest：CP所属的面向餐厅收油的车辆列表
* cp_vehicle_to_sale：CP所属的面向销售的车辆列表

### 3.4 收油记录：receive_record.py

收油记录是指从餐厅到CP的一条记录，由CP的车辆进行收集，模型应包含以下字段：

* rr_id：收油合同号
* rr_cp：记录所属的CP
* rr_date：收油日期
* rr_vehicle：收油对应的车辆
* rr_restaurant：收油对应的餐厅
* rr_amount：单次收油量

### 3.5 发货记录：sale_record.py

发货记录是指CP到TP或者客户的发货记录，该模型应该包含以下字段：

* sr_contract_id：销售合同号
* sr_quantities：售出数量
* sr_date：出货时间
* sr_to：TP或者客户Cus

### 3.6 集合：groups.py

在真实的业务中，经常涉及到将同类的对象组合成一个组的问题。例如餐厅，最终需要是一个表，这个表中包含多个餐厅；而收油记录，最终多条收油记录组合成一天的收油记录，而多天的记录则组合成一个平衡表，因此，这里我需要你涉及一个group_model。这里是比较复杂的，首先，不同的对象组合应该有一个不同的类型，比如餐厅的组合，我可能会将其命名为RestaurantsGroup类，其中可以存在一个self.members作为列表；其次，每个类可能会有一些共有的特性，比如同天的收油记录，可能其ReceiveRrecordsGroup的类中应该有一个多个属性能表现这件事；最后，这个集合应该是可以将之前的集合类作为参数进行组合的，比如同一天的多条收油记录是一个集合，而不同天的收油记录集合又是一个集合。

## 2. 业务（app/services）

业务逻辑主要是指对于关键的数据类型进行操作，其中又分成两个部分，第一是和模型相关的业务逻辑（services/models），其中主要承载的对于各类模型的数值的变换以及保存，一般与模型相对应；而另外是业务服务（service/functions)，主要承载的则是一些业务逻辑。

### 2.1 模型业务逻辑基类（services/models/base.py）

这里主要包含关于业务逻辑的基础操作，如Excel以及JSON的IO等内容，针对模型的Service类都应该继承这个基类。

```python
import abc, abstractmethod

class BaseService(abc):
    def __init__(self, conf, model):
        pass
    @abstractmethod
    def load_from_excel(self):
        pass
    @abstrctmethod
    def save_to_excel(self):
        pass
```

### 2.1 餐厅获取业务(service/functions/get_restaurant_service.py)

这里主要的功能是希望能从各种api渠道获取这些餐厅信息，然后进行整合。

```python
class GetRestaurantsService():
    def __init__(self, conf):
        self.restaurants = xxx  # 创造一个Restaurant的集合类
        self.backends = []
```

