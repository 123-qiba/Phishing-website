import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, Subset
import pandas as pd
import numpy as np
import os
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import time

# 1. 自定义数据集类
class PhishingDataset(Dataset):
    def __init__(self, csv_path):
        self.data = pd.read_csv(csv_path)
        self.features = self.data.iloc[:, :-1].values.astype(np.float32)
        self.labels = self.data.iloc[:, -1].values.astype(np.float32)
        
        if set(np.unique(self.labels)) == {-1.0, 1.0}:
            self.labels = (self.labels + 1) / 2
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        feature = torch.tensor(self.features[idx], dtype=torch.float32).unsqueeze(0)
        label = torch.tensor(self.labels[idx], dtype=torch.float32)
        return feature, label

# 2. CNN模型定义
class PhishingCNN1D(nn.Module):
    def __init__(self, input_features):
        super(PhishingCNN1D, self).__init__()
        self.conv1 = nn.Conv1d(1, 64, kernel_size=10, padding=5)
        self.pool1 = nn.MaxPool1d(kernel_size=2, stride=2)
        self.conv2 = nn.Conv1d(64, 64, kernel_size=5, padding=2)
        self.pool2 = nn.MaxPool1d(kernel_size=2, stride=2)
        
        length = input_features // 4
        self.fc_input_dim = 64 * length
        
        self.flatten = nn.Flatten()
        self.dropout = nn.Dropout(0.4)
        self.fc1 = nn.Linear(self.fc_input_dim, 8)
        self.fc2 = nn.Linear(8, 4)
        self.fc3 = nn.Linear(4, 1)
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()
    
    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.pool1(x)
        x = self.relu(self.conv2(x))
        x = self.pool2(x)
        x = self.flatten(x)
        x = self.dropout(x)
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.sigmoid(self.fc3(x))
        return x.squeeze()

# 3. 训练一个折的模型
def train_fold(model, train_loader, val_loader, device, epochs=20, fold_idx=1, save_dir='saved_models'):
    model.to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCELoss()
    
    best_val_f1 = 0
    best_epoch = 0
    best_model_state = None
    
    os.makedirs(save_dir, exist_ok=True)
    
    for epoch in range(epochs):
        # 训练阶段
        model.train()
        train_loss = 0
        for data, target in train_loader:
            data, target = data.to(device), target.to(device)
            optimizer.zero_grad()
            output = model(data)
            loss = criterion(output, target)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        # 验证阶段
        model.eval()
        val_preds, val_labels = [], []
        with torch.no_grad():
            for data, target in val_loader:
                data, target = data.to(device), target.to(device)
                output = model(data)
                val_preds.extend((output > 0.5).float().cpu().numpy())
                val_labels.extend(target.cpu().numpy())
        
        # 计算指标
        val_f1 = f1_score(val_labels, val_preds, zero_division=0)
        val_acc = accuracy_score(val_labels, val_preds)
        
        # 保存最佳模型
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_epoch = epoch + 1
            best_model_state = model.state_dict().copy()
            
            # 立即保存最佳模型权重
            model_path = os.path.join(save_dir, f'best_model_fold_{fold_idx}.pth')
            torch.save({
                'fold': fold_idx,
                'epoch': best_epoch,
                'model_state_dict': best_model_state,
                'val_f1': best_val_f1,
                'val_acc': val_acc,
                'input_features': model.fc_input_dim // 64 * 4  # 计算原始输入特征数
            }, model_path)
        
        # 每5个epoch打印进度
        if (epoch + 1) % 5 == 0:
            print(f"    Epoch {epoch+1}/{epochs}: 训练损失={train_loss/len(train_loader):.4f}, "
                  f"验证F1={val_f1:.4f}, 验证准确率={val_acc:.4f}")
    
    return best_val_f1, best_epoch

# 4. 加载和使用保存的模型
def load_and_evaluate_model(model_path, val_loader, device):
    """加载保存的模型并在验证集上评估"""
    checkpoint = torch.load(model_path, map_location=device)
    
    # 重新创建模型
    input_features = checkpoint['input_features']
    model = PhishingCNN1D(input_features)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.to(device)
    model.eval()
    
    # 评估
    val_preds, val_labels = [], []
    with torch.no_grad():
        for data, target in val_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            val_preds.extend((output > 0.5).float().cpu().numpy())
            val_labels.extend(target.cpu().numpy())
    
    acc = accuracy_score(val_labels, val_preds)
    f1 = f1_score(val_labels, val_preds, zero_division=0)
    
    return acc, f1

# 5. 主函数：5折交叉验证
def main():
    # 配置
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    csv_path = "C:/Users/MI/Phishing-website/data/train.csv"
    n_folds = 5
    epochs = 20
    save_dir = 'saved_models'
    
    print("=" * 60)
    print(f"开始 {n_folds} 折交叉验证")
    print(f"每折训练 {epochs} 轮")
    print(f"模型权重将保存到: {save_dir}/")
    print(f"使用设备: {device}")
    print("=" * 60)
    
    # 加载数据集
    dataset = PhishingDataset(csv_path)
    kfold = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    
    # 存储结果
    fold_results = []
    start_time = time.time()
    
    # 交叉验证循环
    for fold, (train_idx, val_idx) in enumerate(kfold.split(dataset)):
        fold_start = time.time()
        print(f"\n第 {fold+1}/{n_folds} 折:")
        print(f"  训练集: {len(train_idx)} 样本")
        print(f"  验证集: {len(val_idx)} 样本")
        
        # 创建数据加载器
        train_loader = DataLoader(
            Subset(dataset, train_idx), 
            batch_size=32, 
            shuffle=True
        )
        val_loader = DataLoader(
            Subset(dataset, val_idx), 
            batch_size=32, 
            shuffle=False
        )
        
        # 创建新模型并训练
        model = PhishingCNN1D(input_features=30)
        best_f1, best_epoch = train_fold(
            model, train_loader, val_loader, device, 
            epochs, fold_idx=fold+1, save_dir=save_dir
        )
        
        # 验证保存的模型
        model_path = os.path.join(save_dir, f'best_model_fold_{fold+1}.pth')
        final_acc, final_f1 = load_and_evaluate_model(model_path, val_loader, device)
        
        fold_time = time.time() - fold_start
        fold_results.append({
            'fold': fold+1,
            'best_f1': best_f1,
            'best_epoch': best_epoch,
            'final_f1': final_f1,
            'final_acc': final_acc,
            'time_seconds': fold_time
        })
        
        print(f"  ✓ 最佳F1分数: {best_f1:.4f} (第 {best_epoch} 轮)")
        print(f"  ✓ 最终验证F1: {final_f1:.4f}")
        print(f"  ✓ 本折用时: {fold_time:.1f}秒")
    
    # 打印汇总结果
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("交叉验证完成!")
    print("=" * 60)
    
    f1_scores = [r['best_f1'] for r in fold_results]
    acc_scores = [r['final_acc'] for r in fold_results]
    
    print(f"\n各折最佳F1分数:")
    for i, result in enumerate(fold_results):
        print(f"  第 {result['fold']} 折: F1={result['best_f1']:.4f}, "
              f"准确率={result['final_acc']:.4f}, "
              f"最佳轮次={result['best_epoch']}")
    
    print(f"\n汇总统计:")
    print(f"  平均F1分数: {np.mean(f1_scores):.4f} ± {np.std(f1_scores):.4f}")
    print(f"  平均准确率: {np.mean(acc_scores):.4f} ± {np.std(acc_scores):.4f}")
    print(f"  最佳F1分数: {np.max(f1_scores):.4f} (第 {np.argmax(f1_scores)+1} 折)")
    print(f"  总训练时间: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
    
    # 保存结果到CSV
    results_df = pd.DataFrame(fold_results)
    summary_row = {
        'fold': '汇总',
        'best_f1': np.mean(f1_scores),
        'best_epoch': '-',
        'final_f1': np.mean(f1_scores),
        'final_acc': np.mean(acc_scores),
        'time_seconds': total_time
    }
    results_df = pd.concat([results_df, pd.DataFrame([summary_row])], ignore_index=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_path = f'logs/cv_results_{timestamp}.csv'
    os.makedirs('logs', exist_ok=True)
    results_df.to_csv(result_path, index=False)
    
    print(f"\n详细结果已保存到: {result_path}")
    print(f"所有模型权重已保存到: {save_dir}/")
    
    # 显示如何加载模型
    print(f"\n如何使用保存的模型:")
    print(f"1. 加载单个模型:")
    print(f"   checkpoint = torch.load('{save_dir}/best_model_fold_1.pth')")
    print(f"   model = PhishingCNN1D(checkpoint['input_features'])")
    print(f"   model.load_state_dict(checkpoint['model_state_dict'])")
    print(f"2. 模型集成（平均预测）:")
    print(f"   加载所有5个模型，对相同输入取平均预测值")

if __name__ == "__main__":
    main()