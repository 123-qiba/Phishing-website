import torch
import numpy as np
from train import PhishingCNN1D

def predict_phishing_with_accuracy(features, model_path='best_model.pth'):
    """
    预测网站类型并输出准确率信息
    
    参数:
        features: 30个特征值的列表，取值为-1, 0, 1
        model_path: 模型文件路径
        
    返回:
        tuple: (预测结果, 预测概率, 置信度)
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
    
    # 分类
    if probability > 0.5:
        result = "钓鱼网站"
        confidence = probability
    else:
        result = "正常网站"
        confidence = 1 - probability
    
    # 置信度可以作为模型对当前预测的"准确率"估计
    return result, probability, confidence

# 使用示例
if __name__ == "__main__":
    # 输入30个特征值
    features = [-1,-1,-1,-1,-1,-1,-1,1,0,0,-1,-1,-1,0,1,-1,-1,1,-1,-1,-1,-1,-1,0,-1,-1,-1,-1,0,-1]
    
    result, prob, confidence = predict_phishing_with_accuracy(features)
    print(f"预测结果: {result}")
    print(f"预测概率: {prob:.4f}")
    print(f"置信度（准确率估计）: {confidence:.2%}")