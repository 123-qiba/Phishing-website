import arff
import pandas as pd
import os

def convert_arff_to_csv(arff_path, csv_path=None):
    """
    将 ARFF 文件转换为 CSV 格式
    
    参数:
        arff_path (str): ARFF 文件的完整路径
        csv_path (str, 可选): 输出 CSV 文件的路径。如果为None，则在同一目录下生成同名CSV
    """
    # 1. 检查原始文件是否存在
    if not os.path.exists(arff_path):
        print(f"错误：未找到文件 '{arff_path}'")
        return None
    
    # 2. 设置默认的输出CSV文件路径（如果未提供）
    if csv_path is None:
        base_name = os.path.splitext(arff_path)[0]  # 去掉扩展名
        csv_path = base_name + '.csv'
    
    try:
        # 3. 读取 ARFF 文件
        print(f"正在读取 ARFF 文件: {arff_path}")
        with open(arff_path, 'r', encoding='utf-8') as file:
            dataset = arff.load(file)
        
        # 4. 提取数据并创建 DataFrame
        attributes = [attr[0] for attr in dataset['attributes']]
        df = pd.DataFrame(dataset['data'], columns=attributes)
        
        # 5. 保存为 CSV
        df.to_csv(csv_path, index=False)
        print(f"✓ 转换成功！CSV 文件已保存至: {csv_path}")
        print("-" * 50)
        
        # 6. 显示数据基本信息
        print("数据概览:")
        print(f"  数据集形状: {df.shape[0]} 行, {df.shape[1]} 列")
        print(f"  特征数量: {df.shape[1] - 1} (不含标签列)")
        print(f"  样本数量: {df.shape[0]}")
        print(f"  列名列表: {', '.join(list(df.columns))}")
        
        # 7. 显示标签列分布（假设最后一列是标签）
        label_column = df.columns[-1]
        print(f"  标签列 '{label_column}' 的分布:")
        label_counts = df[label_column].value_counts().sort_index()
        for value, count in label_counts.items():
            percentage = (count / len(df)) * 100
            print(f"    类别 {value}: {count} 个样本 ({percentage:.1f}%)")
        
        # 8. 数据预览
        print("\n数据预览 (前5行):")
        print(df.head())
        
        return df
        
    except FileNotFoundError:
        print(f"错误：找不到文件 '{arff_path}'")
    except Exception as e:
        print(f"转换过程中发生错误: {e}")
        return None

# 使用函数转换你的文件
arff_file = "C:/Users/MI/Phishing-website/.old.arff"
dataframe = convert_arff_to_csv(arff_file)

# 如果你需要进一步处理数据（例如分离特征和标签）
if dataframe is not None:
    print("\n" + "="*60)
    print("后续处理示例（分离特征与标签）:")
    print("="*60)
    
    # 假设最后一列'Result'是标签
    X = dataframe.drop('Result', axis=1)  # 特征
    y = dataframe['Result']               # 标签
    
    print(f"特征 X 的形状: {X.shape}")
    print(f"标签 y 的形状: {y.shape}")
    print(f"\n标签值示例: {y[:5].tolist()}")
    
    # 可选：将标签映射为 0 和 1（如果你的模型需要）
    # y_binary = y.replace({-1: 0, 1: 1})
    # print(f"二值化标签示例: {y_binary[:5].tolist()}")