import pandas as pd

def process_dataframe_with_new_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据给定的步骤处理输入的DataFrame，并返回处理后的DataFrame。
    
    :param df: 输入的DataFrame，至少包含'日期', '车牌号', '榜单净重', '榜单编号', '收集城市'字段
    :return: 处理后的DataFrame
    """
    # 步骤1：新建一个dataframe,从dataframe复制日期、车牌号、榜单净重、榜单编号、收集城市
    new_df = df[['日期', '车牌号', '榜单净重', '榜单编号', '收集城市']].copy()
    
    # 初始化新增的列
    new_df['加工量'] = 0.0
    new_df['毛油库存'] = new_df['榜单净重'].cumsum()  # 初始值为累计榜单净重之和
    new_df['期末库存'] = None
    
    # 步骤2：计算加工量
    for date in new_df['日期'].unique():
        mask = new_df['日期'] == date
        if mask.sum() > 0:  # 确保有数据
            total_weight = new_df.loc[mask, '榜单净重'].sum()
            last_index = new_df[mask].index[-1]
            new_df.at[last_index, '加工量'] = total_weight
            
            # 更新毛油库存
            running_total = 0.0
            for idx in new_df[mask].index:
                current_weight = new_df.at[idx, '榜单净重']
                previous_inventory = running_total if idx != new_df[mask].index[0] else 0
                processing_amount = new_df.at[idx, '加工量']
                new_df.at[idx, '毛油库存'] = current_weight + previous_inventory - processing_amount
                running_total = new_df.at[idx, '毛油库存']
                
    # 计算期末库存
    new_df['期末库存'] = new_df['日期'].ne(new_df['日期'].shift(-1)).astype(int)
    new_df['期末库存'] = new_df['期末库存'].replace({1: 1, 0: None})
    
    return new_df

# 示例用法：
if __name__ == "__main__":
    # 假设df是从某个地方加载的数据
    df_input = pd.DataFrame({
        '日期': ['2025-02-23', '2025-02-23', '2025-02-24', '2025-02-24'],
        '车牌号': ['AB123', 'CD456', 'EF789', 'GH101'],
        '榜单净重': [10, 20, 15, 25],
        '榜单编号': ['B202502001', 'B202502002', 'B202502003', 'B202502004'],
        '收集城市': ['CityA', 'CityB', 'CityC', 'CityD']
    })
    print(df_input)
    result_df = process_dataframe_with_new_columns(df_input)
    print(result_df)