import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import seaborn as sns

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

# 3. 训练器类
class Trainer:
    def __init__(self, config):
        self.config = config
        self.device = torch.device(config['device'] if torch.cuda.is_available() else 'cpu')
        print(f"使用设备: {self.device}")
        
        # 设置随机种子
        self._set_seed(config.get('seed', 42))
        
        # 创建模型
        self.model = PhishingCNN1D(
            input_features=config['input_features'],
            num_classes=1
        ).to(self.device)
        
        # 设置优化器和损失函数
        self._setup_optimizer()
        self._setup_criterion()
        
        # 学习率调度器
        self.scheduler = None
        if config.get('use_scheduler', True):
            self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer, mode='min', factor=0.5, patience=5
            )
        
        # 创建日志目录
        self.log_dir = self._create_log_dir()
        
        # 训练历史记录
        self.history = {
            'train_loss': [], 'val_loss': [],
            'train_acc': [], 'val_acc': [],
            'train_precision': [], 'val_precision': [],
            'train_recall': [], 'val_recall': [],
            'train_f1': [], 'val_f1': []
        }
        
        # 最佳模型信息
        self.best_val_loss = float('inf')
        self.best_model_path = None
    
    def _set_seed(self, seed):
        """设置随机种子以确保可重复性"""
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    
    def _setup_optimizer(self):
        """设置优化器"""
        optimizer_name = self.config.get('optimizer', 'adam').lower()
        lr = self.config.get('learning_rate', 0.001)
        
        if optimizer_name == 'adam':
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=lr,
                weight_decay=self.config.get('weight_decay', 1e-4)
            )
        elif optimizer_name == 'sgd':
            self.optimizer = optim.SGD(
                self.model.parameters(),
                lr=lr,
                momentum=0.9,
                weight_decay=self.config.get('weight_decay', 1e-4)
            )
        else:
            raise ValueError(f"不支持的优化器: {optimizer_name}")
    
    def _setup_criterion(self):
        """设置损失函数"""
        self.criterion = nn.BCELoss()  # 二元交叉熵损失
    
    def _create_log_dir(self):
        """创建日志目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(
            self.config.get('log_dir', 'logs'),
            f"{self.model.name}_{timestamp}"
        )
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建checkpoint目录
        checkpoint_dir = os.path.join(log_dir, 'checkpoints')
        os.makedirs(checkpoint_dir, exist_ok=True)
        
        print(f"日志目录: {log_dir}")
        return log_dir
    
    def load_data(self, csv_path, val_split=0.2, batch_size=32):
        """加载数据集"""
        # 创建完整数据集
        full_dataset = PhishingDataset(csv_path)
        
        # 划分训练集和验证集
        val_size = int(len(full_dataset) * val_split)
        train_size = len(full_dataset) - val_size
        
        train_dataset, val_dataset = random_split(
            full_dataset, [train_size, val_size]
        )
        
        # 创建数据加载器
        self.train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=self.config.get('num_workers', 0),
            pin_memory=self.device.type == 'cuda'
        )
        
        self.val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=self.config.get('num_workers', 0),
            pin_memory=self.device.type == 'cuda'
        )
        
        print(f"数据加载完成:")
        print(f"  训练集: {len(train_dataset)} 样本")
        print(f"  验证集: {len(val_dataset)} 样本")
        print(f"  批大小: {batch_size}")
        
        return self.train_loader, self.val_loader
    
    def calculate_metrics(self, y_true, y_pred, threshold=0.5):
        """计算评估指标"""
        y_pred_binary = (y_pred > threshold).astype(int)
        
        accuracy = accuracy_score(y_true, y_pred_binary)
        precision = precision_score(y_true, y_pred_binary, zero_division=0)
        recall = recall_score(y_true, y_pred_binary, zero_division=0)
        f1 = f1_score(y_true, y_pred_binary, zero_division=0)
        
        return accuracy, precision, recall, f1
    
    def train_epoch(self, epoch):
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        all_preds = []
        all_labels = []
        
        for batch_idx, (data, target) in enumerate(self.train_loader):
            data, target = data.to(self.device), target.to(self.device)
            
            # 前向传播
            self.optimizer.zero_grad()
            output = self.model(data)
            loss = self.criterion(output, target)
            
            # 反向传播
            loss.backward()
            
            # 梯度裁剪
            if self.config.get('grad_clip', None):
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config['grad_clip']
                )
            
            self.optimizer.step()
            
            # 统计信息
            total_loss += loss.item()
            all_preds.extend(output.detach().cpu().numpy())
            all_labels.extend(target.cpu().numpy())
            
            # 打印进度
            if batch_idx % self.config.get('log_interval', 10) == 0:
                print(f'  Batch [{batch_idx}/{len(self.train_loader)}] '
                      f'Loss: {loss.item():.4f}')
        
        # 计算epoch指标
        epoch_loss = total_loss / len(self.train_loader)
        accuracy, precision, recall, f1 = self.calculate_metrics(
            np.array(all_labels), np.array(all_preds)
        )
        
        return epoch_loss, accuracy, precision, recall, f1
    
    def validate(self):
        """验证模型"""
        self.model.eval()
        total_loss = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for data, target in self.val_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = self.model(data)
                loss = self.criterion(output, target)
                
                total_loss += loss.item()
                all_preds.extend(output.cpu().numpy())
                all_labels.extend(target.cpu().numpy())
        
        # 计算验证指标
        val_loss = total_loss / len(self.val_loader)
        accuracy, precision, recall, f1 = self.calculate_metrics(
            np.array(all_labels), np.array(all_preds)
        )
        
        return val_loss, accuracy, precision, recall, f1, all_preds, all_labels
    
    def save_checkpoint(self, epoch, is_best=False):
        """保存检查点"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict() if self.scheduler else None,
            'history': self.history,
            'config': self.config,
            'best_val_loss': self.best_val_loss
        }
        
        # 保存常规检查点
        checkpoint_path = os.path.join(
            self.log_dir, 'checkpoints', f'checkpoint_epoch_{epoch:03d}.pth'
        )
        torch.save(checkpoint, checkpoint_path)
        
        # 如果是最佳模型，额外保存
        if is_best:
            self.best_model_path = os.path.join(self.log_dir, 'best_model.pth')
            torch.save(checkpoint, self.best_model_path)
    
    def plot_training_history(self):
        """绘制训练历史图"""
        epochs = range(1, len(self.history['train_loss']) + 1)
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # 损失图
        axes[0, 0].plot(epochs, self.history['train_loss'], 'b-', label='训练损失')
        axes[0, 0].plot(epochs, self.history['val_loss'], 'r-', label='验证损失')
        axes[0, 0].set_xlabel('Epoch')
        axes[0, 0].set_ylabel('Loss')
        axes[0, 0].set_title('训练和验证损失')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 准确率图
        axes[0, 1].plot(epochs, self.history['train_acc'], 'b-', label='训练准确率')
        axes[0, 1].plot(epochs, self.history['val_acc'], 'r-', label='验证准确率')
        axes[0, 1].set_xlabel('Epoch')
        axes[0, 1].set_ylabel('Accuracy')
        axes[0, 1].set_title('训练和验证准确率')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        # 精确率-召回率图
        axes[1, 0].plot(epochs, self.history['train_precision'], 'b-', label='训练精确率')
        axes[1, 0].plot(epochs, self.history['val_precision'], 'r-', label='验证精确率')
        axes[1, 0].plot(epochs, self.history['train_recall'], 'b--', label='训练召回率')
        axes[1, 0].plot(epochs, self.history['val_recall'], 'r--', label='验证召回率')
        axes[1, 0].set_xlabel('Epoch')
        axes[1, 0].set_ylabel('Score')
        axes[1, 0].set_title('精确率和召回率')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # F1分数图
        axes[1, 1].plot(epochs, self.history['train_f1'], 'b-', label='训练F1分数')
        axes[1, 1].plot(epochs, self.history['val_f1'], 'r-', label='验证F1分数')
        axes[1, 1].set_xlabel('Epoch')
        axes[1, 1].set_ylabel('F1 Score')
        axes[1, 1].set_title('F1分数')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        history_path = os.path.join(self.log_dir, 'training_history.png')
        plt.savefig(history_path, dpi=300, bbox_inches='tight')
        plt.show()
        
        # 保存历史数据到CSV
        history_df = pd.DataFrame({
            'epoch': list(epochs),
            'train_loss': self.history['train_loss'],
            'val_loss': self.history['val_loss'],
            'train_acc': self.history['train_acc'],
            'val_acc': self.history['val_acc'],
            'train_precision': self.history['train_precision'],
            'val_precision': self.history['val_precision'],
            'train_recall': self.history['train_recall'],
            'val_recall': self.history['val_recall'],
            'train_f1': self.history['train_f1'],
            'val_f1': self.history['val_f1']
        })
        history_csv_path = os.path.join(self.log_dir, 'training_history.csv')
        history_df.to_csv(history_csv_path, index=False)
        
        return history_path
    
    def train(self, epochs):
        """训练模型"""
        print("=" * 60)
        print(f"开始训练模型: {self.model.name}")
        print("=" * 60)
        
        start_time = time.time()
        
        for epoch in range(1, epochs + 1):
            print(f"\nEpoch {epoch}/{epochs}")
            
            # 训练阶段
            train_loss, train_acc, train_precision, train_recall, train_f1 = self.train_epoch(epoch)
            
            # 验证阶段
            val_loss, val_acc, val_precision, val_recall, val_f1, _, _ = self.validate()
            
            # 更新学习率
            if self.scheduler:
                self.scheduler.step(val_loss)
            
            # 记录历史
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['train_acc'].append(train_acc)
            self.history['val_acc'].append(val_acc)
            self.history['train_precision'].append(train_precision)
            self.history['val_precision'].append(val_precision)
            self.history['train_recall'].append(train_recall)
            self.history['val_recall'].append(val_recall)
            self.history['train_f1'].append(train_f1)
            self.history['val_f1'].append(val_f1)
            
            # 打印结果
            print(f"训练结果 - 损失: {train_loss:.4f}, 准确率: {train_acc:.4f}, "
                  f"精确率: {train_precision:.4f}, 召回率: {train_recall:.4f}, F1: {train_f1:.4f}")
            print(f"验证结果 - 损失: {val_loss:.4f}, 准确率: {val_acc:.4f}, "
                  f"精确率: {val_precision:.4f}, 召回率: {val_recall:.4f}, F1: {val_f1:.4f}")
            
            # 保存检查点
            if epoch % self.config.get('save_interval', 5) == 0:
                self.save_checkpoint(epoch)
            
            # 保存最佳模型
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_checkpoint(epoch, is_best=True)
                print(f"新的最佳验证损失: {self.best_val_loss:.4f}")
        
        # 训练完成
        total_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("训练完成!")
        print(f"总训练时间: {total_time:.2f}秒 ({total_time/60:.2f}分钟)")
        print(f"最佳验证损失: {self.best_val_loss:.4f}")
        print(f"日志保存到: {self.log_dir}")
        
        # 绘制训练历史
        self.plot_training_history()
        
        # 保存最终模型
        final_path = os.path.join(self.log_dir, 'final_model.pth')
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'history': self.history,
            'best_val_loss': self.best_val_loss
        }, final_path)
        print(f"最终模型已保存到: {final_path}")
        
        return self.history

# 4. 主函数
def main():
    """主训练函数"""
    # 配置参数
    config = {
        'seed': 42,
        'device': 'cuda',
        'input_features': 30,  # 根据你的数据集特征数量调整
        'optimizer': 'adam',
        'learning_rate': 0.001,
        'weight_decay': 1e-4,
        'grad_clip': 5.0,
        'log_dir': 'logs',
        'num_workers': 2,
        'log_interval': 10,
        'save_interval': 5,
        'use_scheduler': True
    }
    
    # 创建训练器
    trainer = Trainer(config)
    
    # 加载数据
    csv_path = "C:/Users/MI/Phishing-website/train.csv"
    trainer.load_data(
        csv_path=csv_path,
        val_split=0.2,  # 20%作为验证集
        batch_size=32
    )
    
    # 开始训练
    history = trainer.train(epochs=50)
    
    print(f"\n训练完成！最佳模型保存在: {trainer.best_model_path}")
    
    # 在验证集上评估最佳模型
    if trainer.best_model_path:
        print("\n加载最佳模型进行验证...")
        checkpoint = torch.load(trainer.best_model_path)
        trainer.model.load_state_dict(checkpoint['model_state_dict'])
        
        val_loss, val_acc, val_precision, val_recall, val_f1, _, _ = trainer.validate()
        print(f"最佳模型验证结果:")
        print(f"  损失: {val_loss:.4f}")
        print(f"  准确率: {val_acc:.4f}")
        print(f"  精确率: {val_precision:.4f}")
        print(f"  召回率: {val_recall:.4f}")
        print(f"  F1分数: {val_f1:.4f}")

if __name__ == "__main__":
    main()