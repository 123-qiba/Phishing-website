import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, Subset
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import KFold
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# 1. 自定义数据集类
class PhishingDataset(Dataset):
    """钓鱼网站检测数据集"""
    def __init__(self, csv_path, transform=None):
        """
        初始化数据集
        Args:
            csv_path: CSV文件路径
            transform: 数据转换函数
        """
        # 读取数据
        self.data = pd.read_csv(csv_path)
        
        # 分离特征和标签（假设最后一列是标签）
        self.features = self.data.iloc[:, :-1].values.astype(np.float32)
        self.labels = self.data.iloc[:, -1].values.astype(np.float32)
        
        # 如果标签是-1和1，转换为0和1
        if set(np.unique(self.labels)) == {-1.0, 1.0}:
            self.labels = (self.labels + 1) / 2  # -1->0, 1->1
            print("已将标签从{-1, 1}映射到{0, 1}")
        
        # 转换函数
        self.transform = transform
        
        print(f"数据集加载完成: {len(self)} 个样本")
        print(f"特征维度: {self.features.shape[1]}")
        print(f"标签分布: {pd.Series(self.labels).value_counts().to_dict()}")
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        feature = self.features[idx]
        label = self.labels[idx]
        
        # 转换为PyTorch张量
        feature_tensor = torch.tensor(feature, dtype=torch.float32)
        label_tensor = torch.tensor(label, dtype=torch.float32)
        
        # 调整特征形状以匹配1D CNN输入 [特征数] -> [特征数, 1]
        feature_tensor = feature_tensor.unsqueeze(0)
        
        if self.transform:
            feature_tensor = self.transform(feature_tensor)
        
        return feature_tensor, label_tensor

# 2. CNN模型定义
class PhishingCNN1D(nn.Module):
    """1D卷积神经网络用于钓鱼网站检测"""
    def __init__(self, input_features, num_classes=1):
        super(PhishingCNN1D, self).__init__()
        
        self.name = "phWeb-cnn1D"
        self.input_features = input_features
        
        # 卷积层块1
        self.conv1 = nn.Conv1d(
            in_channels=1,  # 输入通道数
            out_channels=64,
            kernel_size=10,
            padding=5  # 'same' padding
        )
        self.pool1 = nn.MaxPool1d(kernel_size=2, stride=2)
        
        # 卷积层块2
        self.conv2 = nn.Conv1d(
            in_channels=64,
            out_channels=64,
            kernel_size=5,
            padding=2  # 'same' padding
        )
        self.pool2 = nn.MaxPool1d(kernel_size=2, stride=2)
        
        # 计算经过卷积和池化后的特征维度
        self._calculate_output_dim(input_features)
        
        # 全连接层
        self.flatten = nn.Flatten()
        self.dropout = nn.Dropout(0.4)
        self.fc1 = nn.Linear(self.fc_input_dim, 8)
        self.fc2 = nn.Linear(8, 4)
        self.fc3 = nn.Linear(4, num_classes)
        
        # 激活函数
        self.relu = nn.ReLU()
        self.sigmoid = nn.Sigmoid()  # 用于二分类输出
        
    def _calculate_output_dim(self, input_length):
        """计算卷积层后的特征维度"""
        # 卷积层1（padding='same'保持长度不变）
        length = input_length
        # 池化层1
        length = length // 2
        # 卷积层2（padding='same'保持长度不变）
        length = length
        # 池化层2
        length = length // 2
        
        # 最终特征维度 = 通道数 * 长度
        self.fc_input_dim = 64 * length
    
    def forward(self, x):
        # 输入形状: [batch_size, 1, input_features]
        
        # 卷积层1 + 激活 + 池化
        x = self.relu(self.conv1(x))
        x = self.pool1(x)
        
        # 卷积层2 + 激活 + 池化
        x = self.relu(self.conv2(x))
        x = self.pool2(x)
        
        # 全连接层
        x = self.flatten(x)
        x = self.dropout(x)
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        
        # 二分类使用sigmoid激活
        x = self.sigmoid(x)
        
        return x.squeeze()  # 去掉多余的维度

# 3. 交叉验证训练器类
class CrossValidationTrainer:
    def __init__(self, config):
        self.config = config
        self.device = torch.device(config['device'] if torch.cuda.is_available() else 'cpu')
        print(f"使用设备: {self.device}")
        
        # 设置随机种子
        self._set_seed(config.get('seed', 42))
        
        # 创建日志目录
        self.log_dir = self._create_log_dir()
        
        # 交叉验证结果
        self.cv_results = {
            'fold': [],
            'train_loss': [], 'val_loss': [],
            'train_acc': [], 'val_acc': [],
            'train_precision': [], 'val_precision': [],
            'train_recall': [], 'val_recall': [],
            'train_f1': [], 'val_f1': [],
            'best_epoch': [], 'best_val_loss': []
        }
    
    def _set_seed(self, seed):
        """设置随机种子以确保可重复性"""
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    
    def _create_log_dir(self):
        """创建日志目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(
            self.config.get('log_dir', 'logs'),
            f"cv_{self.config.get('input_features', 30)}feat_{timestamp}"
        )
        os.makedirs(log_dir, exist_ok=True)
        print(f"日志目录: {log_dir}")
        return log_dir
    
    def calculate_metrics(self, y_true, y_pred, threshold=0.5):
        """计算评估指标"""
        y_pred_binary = (y_pred > threshold).astype(int)
        
        accuracy = accuracy_score(y_true, y_pred_binary)
        precision = precision_score(y_true, y_pred_binary, zero_division=0)
        recall = recall_score(y_true, y_pred_binary, zero_division=0)
        f1 = f1_score(y_true, y_pred_binary, zero_division=0)
        
        return accuracy, precision, recall, f1
    
    def train_fold(self, fold_idx, train_loader, val_loader, epochs):
        """训练一个折"""
        print(f"\n{'='*60}")
        print(f"训练第 {fold_idx+1} 折")
        print(f"{'='*60}")
        
        # 创建新的模型实例
        model = PhishingCNN1D(
            input_features=self.config['input_features'],
            num_classes=1
        ).to(self.device)
        
        # 设置优化器和损失函数
        optimizer = optim.Adam(
            model.parameters(),
            lr=self.config.get('learning_rate', 0.001),
            weight_decay=self.config.get('weight_decay', 1e-4)
        )
        criterion = nn.BCELoss()
        
        # 学习率调度器
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        
        # 训练历史记录
        fold_history = {
            'train_loss': [], 'val_loss': [],
            'train_acc': [], 'val_acc': [],
            'train_precision': [], 'val_precision': [],
            'train_recall': [], 'val_recall': [],
            'train_f1': [], 'val_f1': []
        }
        
        best_val_loss = float('inf')
        best_epoch = 0
        
        start_time = time.time()
        
        for epoch in range(1, epochs + 1):
            print(f"\nEpoch {epoch}/{epochs}")
            
            # 训练阶段
            model.train()
            train_loss = 0
            train_preds = []
            train_labels = []
            
            for batch_idx, (data, target) in enumerate(train_loader):
                data, target = data.to(self.device), target.to(self.device)
                
                # 前向传播
                optimizer.zero_grad()
                output = model(data)
                loss = criterion(output, target)
                
                # 反向传播
                loss.backward()
                
                # 梯度裁剪
                if self.config.get('grad_clip', None):
                    torch.nn.utils.clip_grad_norm_(
                        model.parameters(),
                        self.config['grad_clip']
                    )
                
                optimizer.step()
                
                # 统计信息
                train_loss += loss.item()
                train_preds.extend(output.detach().cpu().numpy())
                train_labels.extend(target.cpu().numpy())
            
            # 计算训练指标
            train_loss = train_loss / len(train_loader)
            train_acc, train_precision, train_recall, train_f1 = self.calculate_metrics(
                np.array(train_labels), np.array(train_preds)
            )
            
            # 验证阶段
            model.eval()
            val_loss = 0
            val_preds = []
            val_labels = []
            
            with torch.no_grad():
                for data, target in val_loader:
                    data, target = data.to(self.device), target.to(self.device)
                    output = model(data)
                    loss = criterion(output, target)
                    
                    val_loss += loss.item()
                    val_preds.extend(output.cpu().numpy())
                    val_labels.extend(target.cpu().numpy())
            
            # 计算验证指标
            val_loss = val_loss / len(val_loader)
            val_acc, val_precision, val_recall, val_f1 = self.calculate_metrics(
                np.array(val_labels), np.array(val_preds)
            )
            
            # 更新学习率
            scheduler.step(val_loss)
            
            # 记录历史
            fold_history['train_loss'].append(train_loss)
            fold_history['val_loss'].append(val_loss)
            fold_history['train_acc'].append(train_acc)
            fold_history['val_acc'].append(val_acc)
            fold_history['train_precision'].append(train_precision)
            fold_history['val_precision'].append(val_precision)
            fold_history['train_recall'].append(train_recall)
            fold_history['val_recall'].append(val_recall)
            fold_history['train_f1'].append(train_f1)
            fold_history['val_f1'].append(val_f1)
            
            # 打印结果
            print(f"训练结果 - 损失: {train_loss:.4f}, 准确率: {train_acc:.4f}, "
                  f"精确率: {train_precision:.4f}, 召回率: {train_recall:.4f}, F1: {train_f1:.4f}")
            print(f"验证结果 - 损失: {val_loss:.4f}, 准确率: {val_acc:.4f}, "
                  f"精确率: {val_precision:.4f}, 召回率: {val_recall:.4f}, F1: {val_f1:.4f}")
            
            # 保存最佳模型
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_epoch = epoch
                # 保存该折的最佳模型
                fold_model_path = os.path.join(self.log_dir, f'best_model_fold_{fold_idx+1}.pth')
                torch.save({
                    'fold': fold_idx + 1,
                    'epoch': epoch,
                    'model_state_dict': model.state_dict(),
                    'val_loss': val_loss,
                    'val_acc': val_acc,
                    'val_f1': val_f1
                }, fold_model_path)
        
        # 记录该折的训练时间
        fold_time = time.time() - start_time
        print(f"\n第 {fold_idx+1} 折训练完成!")
        print(f"训练时间: {fold_time:.2f}秒 ({fold_time/60:.2f}分钟)")
        print(f"最佳验证损失: {best_val_loss:.4f} (第 {best_epoch} 轮)")
        
        # 保存该折的最佳指标
        best_val_acc = max(fold_history['val_acc'])
        best_val_f1 = max(fold_history['val_f1'])
        
        # 记录交叉验证结果
        self.cv_results['fold'].append(fold_idx + 1)
        self.cv_results['train_loss'].append(np.mean(fold_history['train_loss']))
        self.cv_results['val_loss'].append(np.mean(fold_history['val_loss']))
        self.cv_results['train_acc'].append(np.mean(fold_history['train_acc']))
        self.cv_results['val_acc'].append(np.mean(fold_history['val_acc']))
        self.cv_results['train_precision'].append(np.mean(fold_history['train_precision']))
        self.cv_results['val_precision'].append(np.mean(fold_history['val_precision']))
        self.cv_results['train_recall'].append(np.mean(fold_history['train_recall']))
        self.cv_results['val_recall'].append(np.mean(fold_history['val_recall']))
        self.cv_results['train_f1'].append(np.mean(fold_history['train_f1']))
        self.cv_results['val_f1'].append(np.mean(fold_history['val_f1']))
        self.cv_results['best_epoch'].append(best_epoch)
        self.cv_results['best_val_loss'].append(best_val_loss)
        
        return fold_history
    
    def cross_validate(self, csv_path, n_folds=5, epochs=30, batch_size=32):
        """执行交叉验证"""
        print("=" * 60)
        print(f"开始 {n_folds} 折交叉验证")
        print(f"每折训练 {epochs} 轮")
        print("=" * 60)
        
        # 加载完整数据集
        full_dataset = PhishingDataset(csv_path)
        
        # 创建K折交叉验证
        kfold = KFold(n_splits=n_folds, shuffle=True, random_state=self.config.get('seed', 42))
        
        # 存储每个折的训练历史
        all_histories = []
        
        # 执行交叉验证
        for fold_idx, (train_indices, val_indices) in enumerate(kfold.split(full_dataset)):
            print(f"\n{'='*60}")
            print(f"处理第 {fold_idx+1}/{n_folds} 折")
            print(f"{'='*60}")
            
            # 创建训练集和验证集子集
            train_subset = Subset(full_dataset, train_indices)
            val_subset = Subset(full_dataset, val_indices)
            
            print(f"训练集大小: {len(train_subset)}")
            print(f"验证集大小: {len(val_subset)}")
            
            # 创建数据加载器
            train_loader = DataLoader(
                train_subset,
                batch_size=batch_size,
                shuffle=True,
                num_workers=self.config.get('num_workers', 0)
            )
            
            val_loader = DataLoader(
                val_subset,
                batch_size=batch_size,
                shuffle=False,
                num_workers=self.config.get('num_workers', 0)
            )
            
            # 训练当前折
            fold_history = self.train_fold(fold_idx, train_loader, val_loader, epochs)
            all_histories.append(fold_history)
        
        # 计算交叉验证平均结果
        self._calculate_cv_summary()
        
        # 绘制交叉验证结果
        self._plot_cv_results(all_histories)
        
        return all_histories
    
    def _calculate_cv_summary(self):
        """计算交叉验证的统计摘要"""
        print("\n" + "=" * 60)
        print("交叉验证结果摘要")
        print("=" * 60)
        
        # 计算每个指标的平均值和标准差
        metrics_to_show = [
            ('val_loss', '验证损失'),
            ('val_acc', '验证准确率'),
            ('val_precision', '验证精确率'),
            ('val_recall', '验证召回率'),
            ('val_f1', '验证F1分数')
        ]
        
        print("\n各折性能指标:")
        for metric, name in metrics_to_show:
            values = self.cv_results[metric]
            mean_val = np.mean(values)
            std_val = np.std(values)
            print(f"{name}: {mean_val:.4f} ± {std_val:.4f}")
        
        print("\n各折详细结果:")
        for i in range(len(self.cv_results['fold'])):
            print(f"\n第 {self.cv_results['fold'][i]} 折:")
            print(f"  验证损失: {self.cv_results['val_loss'][i]:.4f}")
            print(f"  验证准确率: {self.cv_results['val_acc'][i]:.4f}")
            print(f"  验证F1分数: {self.cv_results['val_f1'][i]:.4f}")
            print(f"  最佳轮次: {self.cv_results['best_epoch'][i]}")
        
        # 保存交叉验证结果到CSV
        cv_df = pd.DataFrame(self.cv_results)
        cv_csv_path = os.path.join(self.log_dir, 'cross_validation_results.csv')
        cv_df.to_csv(cv_csv_path, index=False)
        print(f"\n交叉验证结果已保存到: {cv_csv_path}")
    
    def _plot_cv_results(self, all_histories):
        """绘制交叉验证结果图"""
        n_folds = len(all_histories)
        epochs = len(all_histories[0]['train_loss'])
        
        # 创建大图
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # 1. 各折损失曲线
        ax1 = axes[0, 0]
        for fold_idx, history in enumerate(all_histories):
            ax1.plot(range(1, epochs + 1), history['val_loss'], 
                    label=f'Fold {fold_idx+1}', alpha=0.7, linewidth=1.5)
        ax1.set_xlabel('Epoch')
        ax1.set_ylabel('Validation Loss')
        ax1.set_title('各折验证损失曲线')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        
        # 2. 各折准确率曲线
        ax2 = axes[0, 1]
        for fold_idx, history in enumerate(all_histories):
            ax2.plot(range(1, epochs + 1), history['val_acc'], 
                    label=f'Fold {fold_idx+1}', alpha=0.7, linewidth=1.5)
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Validation Accuracy')
        ax2.set_title('各折验证准确率曲线')
        ax2.legend(loc='lower right')
        ax2.grid(True, alpha=0.3)
        
        # 3. 各折F1分数曲线
        ax3 = axes[0, 2]
        for fold_idx, history in enumerate(all_histories):
            ax3.plot(range(1, epochs + 1), history['val_f1'], 
                    label=f'Fold {fold_idx+1}', alpha=0.7, linewidth=1.5)
        ax3.set_xlabel('Epoch')
        ax3.set_ylabel('Validation F1 Score')
        ax3.set_title('各折验证F1分数曲线')
        ax3.legend(loc='lower right')
        ax3.grid(True, alpha=0.3)
        
        # 4. 平均性能指标条形图
        ax4 = axes[1, 0]
        metrics = ['准确率', '精确率', '召回率', 'F1分数']
        mean_values = [
            np.mean(self.cv_results['val_acc']),
            np.mean(self.cv_results['val_precision']),
            np.mean(self.cv_results['val_recall']),
            np.mean(self.cv_results['val_f1'])
        ]
        std_values = [
            np.std(self.cv_results['val_acc']),
            np.std(self.cv_results['val_precision']),
            np.std(self.cv_results['val_recall']),
            np.std(self.cv_results['val_f1'])
        ]
        
        colors = ['blue', 'green', 'orange', 'red']
        bars = ax4.bar(metrics, mean_values, color=colors, alpha=0.7, 
                      yerr=std_values, capsize=5)
        ax4.set_ylabel('分数')
        ax4.set_title('交叉验证平均性能指标 (±标准差)')
        ax4.set_ylim([0, 1.1])
        
        # 在条形图上添加数值标签
        for bar, value, std in zip(bars, mean_values, std_values):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                    f'{value:.3f}±{std:.3f}', ha='center', va='bottom', fontsize=9)
        
        # 5. 各折最佳验证损失对比
        ax5 = axes[1, 1]
        folds = self.cv_results['fold']
        best_losses = self.cv_results['best_val_loss']
        ax5.bar([str(f) for f in folds], best_losses, color='purple', alpha=0.7)
        ax5.set_xlabel('折')
        ax5.set_ylabel('最佳验证损失')
        ax5.set_title('各折最佳验证损失')
        ax5.grid(True, alpha=0.3, axis='y')
        
        # 在条形图上添加数值标签
        for i, (fold, loss) in enumerate(zip(folds, best_losses)):
            ax5.text(i, loss + 0.005, f'{loss:.4f}', ha='center', va='bottom')
        
        # 6. 各折最佳轮次对比
        ax6 = axes[1, 2]
        best_epochs = self.cv_results['best_epoch']
        ax6.bar([str(f) for f in folds], best_epochs, color='teal', alpha=0.7)
        ax6.set_xlabel('折')
        ax6.set_ylabel('达到最佳性能的轮次')
        ax6.set_title('各折最佳轮次')
        ax6.grid(True, alpha=0.3, axis='y')
        
        # 在条形图上添加数值标签
        for i, (fold, epoch) in enumerate(zip(folds, best_epochs)):
            ax6.text(i, epoch + 0.5, f'{epoch}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # 保存图像
        plot_path = os.path.join(self.log_dir, 'cross_validation_summary.png')
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        print(f"交叉验证结果图已保存到: {plot_path}")

# 4. 主函数
def main():
    """主训练函数"""
    # 配置参数
    config = {
        'seed': 42,
        'device': 'cuda' if torch.cuda.is_available() else 'cpu',
        'input_features': 30,  # 根据你的数据集特征数量调整
        'learning_rate': 0.001,
        'weight_decay': 1e-4,
        'grad_clip': 5.0,
        'log_dir': 'logs',
        'num_workers': 2
    }
    
    # 创建交叉验证训练器
    trainer = CrossValidationTrainer(config)
    
    # 执行5折交叉验证，每折30轮
    csv_path = "C:/Users/MI/Phishing-website/data/train.csv"
    all_histories = trainer.cross_validate(
        csv_path=csv_path,
        n_folds=5,
        epochs=30,
        batch_size=32
    )
    
    print("\n" + "=" * 60)
    print("交叉验证完成!")
    print("=" * 60)
    
    # 保存最终汇总报告
    summary_report = {
        'cross_validation_completed': True,
        'n_folds': 5,
        'epochs_per_fold': 30,
        'total_training_epochs': 5 * 30,
        'average_val_acc': np.mean(trainer.cv_results['val_acc']),
        'average_val_f1': np.mean(trainer.cv_results['val_f1']),
        'average_val_loss': np.mean(trainer.cv_results['val_loss']),
        'log_directory': trainer.log_dir
    }
    
    # 保存汇总报告
    report_path = os.path.join(trainer.log_dir, 'training_summary.json')
    import json
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(summary_report, f, indent=2, ensure_ascii=False)
    
    print(f"训练汇总报告已保存到: {report_path}")
    
    # 创建集成模型（可选）
    # 你可以加载每个折的最佳模型，创建模型集成
    print("\n" + "=" * 60)
    print("建议的后续步骤:")
    print("=" * 60)
    print("1. 查看 logs/ 目录下的交叉验证结果")
    print("2. 选择性能最好的模型用于预测")
    print("3. 或者创建模型集成，结合所有5个模型")
    print("4. 使用 eval.py 脚本评估集成模型的性能")

if __name__ == "__main__":
    main()