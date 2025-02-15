from app.models.restaurant_model import Restaurant
from app.services.restaurant_service import RestaurantService
# from app.services.address_service import extract_town_from_address
from app.services.restaurant_service import RestaurantService
from app.utils.logger import setup_logger
import pandas as pd


restaurant_service = RestaurantService()
# def load_restaurant_data_from_excel(file_path: str) -> list[dict]:
#     """
#     从 Excel 文件中加载餐厅数据
#     :param file_path: Excel 文件路径
#     :return: 餐厅数据列表
#     """
#     logger = setup_logger("moco.log")
#     logger.info(f"正在从 Excel 文件中加载餐厅数据: {file_path}")

#     # 从 Excel 文件中加载餐厅数据
#     restaurants = []
#     try:
#         restaurants, df = RestaurantService.load_from_excel(file_path)
#         return restaurants, df
#     except Exception as e:
#         logger.error(f"加载餐厅数据时出错: {str(e)}")

def flow1_load_df(file_path: str) -> pd.DataFrame:
    """
    从 Excel 文件中加载餐厅数据并返回 DataFrame
    :param file_path: Excel 文件路径
    :return: DataFrame
    """
    logger = setup_logger("moco.log")
    logger.info(f"正在从 Excel 文件中加载餐厅数据: {file_path}。")

    # 从 Excel 文件中加载餐厅数据
    try:
        df = RestaurantService.load_df(file_path)
        global restaurant_service
        restaurant_service.load(file_path)
        return df, restaurant_service.restaurants
    except Exception as e:
        logger.error(f"加载餐厅数据时出错: {str(e)}")

def flow1_generate_candidate_street(file_path: str) -> pd.DataFrame:
    """
    从 DataFrame 中生成街道候选列表
    :param df: DataFrame
    :return: 街道候选列表
    """
    logger = setup_logger("moco.log")
    logger.info(f"正在生成候选街道。")
    global restaurant_service
    # restaurant_service = RestaurantService()
    # restaurant_service.load(file_path)
    # 从 DataFrame 中生成街道候选列表
    try:
        df_with_street, restaurants_with_street = restaurant_service.extract_street_base_batch()
        return df_with_street, restaurants_with_street
    except Exception as e:
        logger.error(f"生成街道候选列表时出错: {str(e)}")

def flow1_generate_restaurant_type(file_path: str) -> pd.DataFrame:
    """
    从 DataFrame 中生成餐厅类型
    :param df: DataFrame
    :return: 餐厅类型
    """
    logger = setup_logger("moco.log")
    logger.info(f"正在生成餐厅类型。")
    global restaurant_service
    # restaurant_service = RestaurantService()
    # restaurant_service.load(file_path)
    # 从 DataFrame 中生成餐厅类型
    try:
        df_with_rest_type, restaurant_with_rest_type = restaurant_service.extract_restaurant_type_batch()
        return df_with_rest_type, restaurant_with_rest_type
    except Exception as e:
        logger.error(f"生成餐厅类型时出错: {str(e)}")


# def flow1_load_from_df(df: pd.DataFrame) -> list[dict]:
#     """
#     从 DataFrame 中加载餐厅数据并返回餐厅数据列表
#     :param df: DataFrame
#     :return: 餐厅数据列表
#     """
#     logger = setup_logger("moco.log")
#     logger.info(f"正在从 DataFrame 中加载餐厅数据。")

#     # 从 DataFrame 中加载餐厅数据
#     try:
#         restaurants = RestaurantService.load_from_df(df)
#         return restaurants
#     except Exception as e:
#         logger.error(f"加载餐厅数据时出错: {str(e)}")
    

# def process_restaurant_data(restaurant_data: dict, config) -> Restaurant:
#     """
#     处理单个餐厅数据，包括：
#     - 填充镇信息
#     - 分配餐厅类型
#     :param restaurant_data: 单个餐厅数据字典
#     :param config: 配置对象
#     :return: 处理后的 Restaurant 对象
#     """
#     # 初始化日志
#     logger = logging.getLogger("moco_logger")

#     # 1. 创建餐厅对象
#     restaurant = Restaurant(**restaurant_data)

#     # 2. 提取镇信息
#     town = extract_town_from_address(
#         address=restaurant.chinese_address,
#         city=restaurant.city,
#         district=restaurant.district,
#         config=config
#     )
#     restaurant.town = town
#     logger.info(f"提取到的镇信息: {town}")

#     # 3. 分配餐厅类型
#     rest_type = assign_restaurant_type(
#         name=restaurant.chinese_name,
#         address=restaurant.chinese_address,
#         config=config
#     )
#     restaurant.rest_type = rest_type
#     logger.info(f"分配到的餐厅类型: {rest_type}")

#     return restaurant

# def process_batch_restaurant_data(restaurant_list: list[dict], config) -> list[Restaurant]:
#     """
#     批量处理餐厅数据
#     :param restaurant_list: 餐厅数据列表
#     :param config: 配置对象
#     :return: 处理后的餐厅对象列表
#     """
#     logger = logging.getLogger("moco_logger")
#     processed_restaurants = []

#     for restaurant_data in restaurant_list:
#         try:
#             processed_restaurant = process_restaurant_data(restaurant_data, config)
#             processed_restaurants.append(processed_restaurant)
#         except Exception as e:
#             logger.error(f"处理餐厅数据时出错: {restaurant_data.get('chinese_name', '')} - {str(e)}")

#     return processed_restaurants
