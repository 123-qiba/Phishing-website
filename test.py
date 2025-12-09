import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import pandas as pd
import numpy as np
import os
import glob
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve, auc
)

# 导入训练脚本中的模型类
from train import PhishingCNN1D, PhishingDataset

class MultiModelEvaluator:
    """多模型评估器 - 评估5个保存的模型并找出最佳模型"""
    def __init__(self, model_dir='saved_models'):
        self.model_dir = model_dir
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.models = {}
        self.results = {}
        
    def load_all_models(self):
        """加载目录中的所有模型"""
        model_files = glob.glob(os.path.join(self.model_dir, 'best_model_fold_*.pth'))
        
        if not model_files:
            print(f"错误：在 {self.model_dir} 目录中未找到模型文件")
            print("模型文件名应类似: best_model_fold_1.pth, best_model_fold_2.pth 等")
            return 0
        
        print(f"找到 {len(model_files)} 个模型文件")
        
        for model_path in sorted(model_files):
            # 从文件名提取折数
            filename = os.path.basename(model_path)
            fold_num = int(filename.split('_fold_')[1].split('.')[0])
            print(f"加载第 {fold_num} 折模型...")
            
            # 加载检查点
            checkpoint = torch.load(model_path, map_location='cpu')
            
            # 创建模型实例
            model = PhishingCNN1D(input_features=checkpoint.get('input_features', 30))
            model.load_state_dict(checkpoint['model_state_dict'])
            model.to(self.device)
            model.eval()
            
            self.models[fold_num] = {
                'model': model,
                'path': model_path,
                'checkpoint': checkpoint
            }
        
        return len(self.models)
    
    def evaluate_single_model(self, model_dict, test_loader, threshold=0.5):
        """评估单个模型"""
        model = model_dict['model']
        model.eval()
        
        all_predictions = []
        all_probabilities = []
        all_labels = []
        
        with torch.no_grad():
            for data, target in test_loader:
                data, target = data.to(self.device), target.to(self.device)
                output = model(data)
                all_probabilities.extend(output.cpu().numpy())
                all_labels.extend(target.cpu().numpy())
        
        # 转换为二进制预测
        all_predictions = (np.array(all_probabilities) > threshold).astype(int)
        all_labels = np.array(all_labels)
        
        # 计算指标
        metrics = {
            'accuracy': accuracy_score(all_labels, all_predictions),
            'precision': precision_score(all_labels, all_predictions, zero_division=0),
            'recall': recall_score(all_labels, all_predictions, zero_division=0),
            'f1': f1_score(all_labels, all_predictions, zero_division=0)
        }
        
        # 计算混淆矩阵
        cm = confusion_matrix(all_labels, all_predictions)
        metrics['confusion_matrix'] = cm
        metrics['tn'], metrics['fp'], metrics['fn'], metrics['tp'] = cm.ravel()
        
        # 计算ROC AUC
        if len(np.unique(all_labels)) > 1:
            fpr, tpr, _ = roc_curve(all_labels, all_probabilities)
            metrics['roc_auc'] = auc(fpr, tpr)
        
        return metrics
    
    def evaluate_all_models(self, test_csv_path, batch_size=32):
        """评估所有模型并找出最佳模型"""
        print("=" * 70)
        print(f"开始评估 {len(self.models)} 个模型")
        print(f"测试集: {test_csv_path}")
        print("=" * 70)
        
        # 检查测试集是否存在
        if not os.path.exists(test_csv_path):
            print(f"错误：测试集文件不存在: {test_csv_path}")
            return None
        
        # 加载测试数据
        test_dataset = PhishingDataset(test_csv_path)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        
        print(f"测试集大小: {len(test_dataset)} 样本")
        print(f"正样本数: {sum(test_dataset.labels == 1)}, 负样本数: {sum(test_dataset.labels == 0)}")
        print("-" * 70)
        
        # 评估每个模型
        for fold_num, model_dict in self.models.items():
            print(f"评估第 {fold_num} 折模型...")
            metrics = self.evaluate_single_model(model_dict, test_loader)
            self.results[fold_num] = metrics
            
            # 打印结果
            print(f"  📊 F1分数:    {metrics['f1']:.4f}")
            print(f"  ✅ 准确率:    {metrics['accuracy']:.4f}")
            print(f"  🎯 精确率:    {metrics['precision']:.4f}")
            print(f"  🔍 召回率:    {metrics['recall']:.4f}")
            if 'roc_auc' in metrics:
                print(f"  📈 ROC AUC:   {metrics['roc_auc']:.4f}")
            print()
        
        # 找出最佳模型（基于F1分数）
        if self.results:
            best_fold = max(self.results, key=lambda x: self.results[x]['f1'])
            return best_fold
        return None
    
    def print_summary(self, best_fold):
        """打印评估汇总"""
        print("\n" + "=" * 70)
        print("模型评估汇总")
        print("=" * 70)
        
        # 打印各模型结果表格
        print("\n各模型性能对比 (按F1分数排序):")
        print("-" * 70)
        print(f"{'折数':^5} | {'F1分数':^8} | {'准确率':^8} | {'精确率':^8} | {'召回率':^8}")
        print("-" * 70)
        
        sorted_folds = sorted(self.results.items(), key=lambda x: x[1]['f1'], reverse=True)
        
        for fold_num, metrics in sorted_folds:
            is_best = "⭐" if fold_num == best_fold else " "
            print(f"{is_best}{fold_num:^4} | {metrics['f1']:^8.4f} | "
                  f"{metrics['accuracy']:^8.4f} | {metrics['precision']:^8.4f} | "
                  f"{metrics['recall']:^8.4f}")
        print("-" * 70)
        
        # 打印最佳模型详情
        best_metrics = self.results[best_fold]
        print(f"\n🏆 最佳模型: 第 {best_fold} 折")
        print(f"   模型文件: {os.path.basename(self.models[best_fold]['path'])}")
        print(f"   F1分数:   {best_metrics['f1']:.4f}")
        print(f"   准确率:   {best_metrics['accuracy']:.4f}")
        print(f"   精确率:   {best_metrics['precision']:.4f}")
        print(f"   召回率:   {best_metrics['recall']:.4f}")
        if 'roc_auc' in best_metrics:
            print(f"   ROC AUC:  {best_metrics['roc_auc']:.4f}")
        
        # 显示混淆矩阵详情
        print(f"\n混淆矩阵分析:")
        print(f"  真阴性(TN): {best_metrics['tn']} - 正常网站被正确识别")
        print(f"  假阳性(FP): {best_metrics['fp']} - 正常网站被误判为钓鱼网站")
        print(f"  假阴性(FN): {best_metrics['fn']} - 钓鱼网站被误判为正常网站")
        print(f"  真阳性(TP): {best_metrics['tp']} - 钓鱼网站被正确识别")
        
        # 计算统计量
        all_f1_scores = [m['f1'] for m in self.results.values()]
        avg_f1 = np.mean(all_f1_scores)
        std_f1 = np.std(all_f1_scores)
        
        print(f"\n📊 统计信息:")
        print(f"  平均F1分数: {avg_f1:.4f} ± {std_f1:.4f}")
        print(f"  F1分数范围: [{min(all_f1_scores):.4f} - {max(all_f1_scores):.4f}]")
        print(f"  模型稳定性: {'高' if std_f1 < 0.02 else '中等' if std_f1 < 0.05 else '较低'}")
    
    def get_best_model_info(self, best_fold):
        """获取最佳模型信息"""
        if best_fold in self.models:
            return {
                'fold': best_fold,
                'path': self.models[best_fold]['path'],
                'metrics': self.results[best_fold]
            }
        return None

# 主函数
def main():
    """主评估函数"""
    # 配置
    model_dir = 'C:/Users/MI/Phishing-website/saved_models'  # 模型保存目录
    test_csv_path = "C:/Users/MI/Phishing-website/data/independent_test.csv"  # 测试集路径
    
    # 创建评估器
    evaluator = MultiModelEvaluator(model_dir)
    
    # 加载所有模型
    model_count = evaluator.load_all_models()
    if model_count == 0:
        return
    
    # 评估所有模型并找出最佳模型
    best_fold = evaluator.evaluate_all_models(test_csv_path)
    
    if best_fold is not None:
        # 打印汇总结果
        evaluator.print_summary(best_fold)
        
        # 获取最佳模型信息
        best_model_info = evaluator.get_best_model_info(best_fold)
        
        # 提供使用最佳模型的示例
        print("\n" + "=" * 70)
        print("如何使用最佳模型进行预测")
        print("=" * 70)
        
        if best_model_info:
            print(f"最佳模型文件: {best_model_info['path']}")
            print(f"\n加载和使用代码示例:")
            print("```python")
            print(f"# 加载最佳模型")
            print(f"checkpoint = torch.load(r'{best_model_info['path']}', map_location='cpu')")
            print(f"")
            print(f"# 创建模型并加载权重")
            print(f"model = PhishingCNN1D(input_features=checkpoint.get('input_features', 30))")
            print(f"model.load_state_dict(checkpoint['model_state_dict'])")
            print(f"model.eval()")
            print(f"")
            print(f"# 预测单个样本（30个特征）")
            print(f"def predict_phishing(features):")
            print(f"    # features: 包含30个特征的列表或numpy数组")
            print(f"    features_tensor = torch.tensor(features, dtype=torch.float32)")
            print(f"    features_tensor = features_tensor.unsqueeze(0).unsqueeze(0)  # [1, 1, 30]")
            print(f"    with torch.no_grad():")
            print(f"        prediction = model(features_tensor)")
            print(f"    # 预测值 > 0.5 表示钓鱼网站，≤ 0.5 表示正常网站")
            print(f"    return '钓鱼网站' if prediction.item() > 0.5 else '正常网站'")
            print("```")
            
            print(f"\n💡 提示:")
            print(f"1. 最佳模型在第 {best_fold} 折训练中获得")
            print(f"2. 在测试集上F1分数为 {best_model_info['metrics']['f1']:.4f}")
            print(f"3. 可以调整阈值（默认0.5）来平衡精确率和召回率")
    else:
        print("评估失败，请检查测试集文件")

if __name__ == "__main__":
    main()