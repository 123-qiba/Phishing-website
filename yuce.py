import torch
import numpy as np
from train import PhishingCNN1D

def predict_phishing(features, model_path='C:/Users/MI/Phishing-website/best_model.pth'):
    """
    预测网站是否为钓鱼网站
    
    参数:
        features: 30个特征值的列表，取值为-1, 0, 1
        model_path: 模型文件路径
        
    返回:
        str: "钓鱼网站" 或 "正常网站"
    """
    # 加载模型
    checkpoint = torch.load(model_path, map_location='cpu')
    model = PhishingCNN1D(input_features=30)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # 准备输入数据
    features_tensor = torch.tensor(features, dtype=torch.float32)
    features_tensor = features_tensor.unsqueeze(0).unsqueeze(0)  # [1, 1, 30]
    
    # 预测
    with torch.no_grad():
        prediction = model(features_tensor)
        probability = prediction.item()
    
    # 返回结果
    if probability > 0.5:
        return "钓鱼网站"
    else:
        return "正常网站"


# 使用示例
if __name__ == "__main__":
    # 输入30个特征值
    features = [1, 1, 1, 1, 1, 1, 0, 1, 0, 0,
                1, 1, 1, -1, -1, 1, 1, -1, 1, 1,
                1, 1, 0, 1, 0, 0, 0, 0, 0, 0]
    
    result = predict_phishing(features)
    print(f"预测结果: {result}")