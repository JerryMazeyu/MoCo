# 核心开发逻辑

本项目旨在开发一套数据生成系统，其包含了一个收油的流程，收油的流程为：餐厅 -> CP(小工厂) ->贸易场（TP） / 客户，我需要在其中构建整个链条的数据信息。

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
