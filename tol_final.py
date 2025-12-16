import sys
import os
import requests
import torch
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QLabel,
                             QTextEdit, QProgressBar, QMessageBox, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import judge_port
import predict

class DetectionWorker(QThread):
    """检测工作线程"""
    
    # 定义信号
    progress = pyqtSignal(int, str)
    result_ready = pyqtSignal(dict)  # 发送完整结果字典
    error = pyqtSignal(str)
    
    def __init__(self, url, model_path=None):
        super().__init__()
        self.url = url
        self.model_path = model_path
    
    def run(self):
        try:
            # 更新进度
            self.progress.emit(10, "正在检查URL格式...")
            
            # 验证URL格式
            if not self.url.startswith(('http://', 'https://')):
                self.url = 'https://' + self.url
            
            # 检查网络连接
            try:
                requests.head(self.url, timeout=5, verify=False)
            except Exception:
                pass  # 继续尝试，即使无法访问
            
            self.progress.emit(30, "正在提取特征...")
            
            # 提取特征
            features = judge_port.extract_features(self.url)
            self.progress.emit(80, "正在分析...")
            
            # 获取预测结果
            result_str, probability, confidence = predict.predict_phishing_with_accuracy(features)            
            
            # 创建完整的结果字典
            result_dict = {
                'url': self.url,
                'result': result_str,  # 字符串：钓鱼网站/正常网站
                'probability': probability,  # 概率值 (0-1之间的小数)
                'confidence': confidence,  # 置信度
                'illegal_probability': probability,  # 非法概率（与probability相同）
                'risk_level': self._get_risk_level(probability),  # 风险等级
                'warnings': self._generate_warnings(features)  # 警告信息
            }
            
            self.progress.emit(100, "分析完成")
            
            # 发送结果
            self.result_ready.emit(result_dict)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _get_risk_level(self, probability):
        """根据概率确定风险等级"""
        if probability > 0.8:
            return "极高"
        elif probability > 0.6:
            return "高"
        elif probability > 0.5:
            return "中"
        else:
            return "低"
    
    def _generate_warnings(self, features):
        """根据特征值生成警告信息"""
        warnings = []
        
        # 高风险特征检查
        high_risk_indices = [0, 2, 3, 4, 5, 17, 24]
        high_risk_messages = [
            "URL包含IP地址",
            "使用短链接服务",
            "URL包含@符号",
            "存在双斜杠重定向",
            "域名使用连字符",
            "异常WHOIS记录",
            "无DNS记录"
        ]
        
        for idx, msg in zip(high_risk_indices, high_risk_messages):
            if idx < len(features) and features[idx] == 1:
                warnings.append(f"⚠️ {msg}")
        
        # 子域名过多
        if 6 < len(features) and features[6] == 1:
            warnings.append("⚠️ 过多子域名")
        
        # 中度风险特征
        medium_risk_indices = [1, 8, 11, 18, 23]
        medium_risk_messages = [
            "URL长度可疑",
            "域名注册时间短",
            "HTTPS令牌滥用",
            "过多重定向",
            "域名年龄小于6个月"
        ]
        
        for idx, msg in zip(medium_risk_indices, medium_risk_messages):
            if idx < len(features) and features[idx] == 1:
                warnings.append(f"⚠️ {msg}")
        
        # 如果没有警告，添加安全提示
        if not warnings:
            warnings.append("✅ 未检测到明显风险特征")
        
        return warnings

class SimpleDetectorWindow(QMainWindow):
    """简洁检测窗口"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.model_path = None
    
    def init_ui(self):
        """初始化界面"""
        # 窗口设置
        self.setWindowTitle('钓鱼网站检测器')
        self.setGeometry(100, 100, 600, 500)
        
        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QLineEdit {
                padding: 10px;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #007bff;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
            QLabel#titleLabel {
                color: #343a40;
                font-size: 24px;
                font-weight: bold;
            }
            QLabel#resultLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
            QProgressBar {
                border: 1px solid #ced4da;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 2px;
            }
        """)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel('钓鱼网站检测器')
        title_label.setObjectName('titleLabel')
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("color: #dee2e6;")
        layout.addWidget(line)
        
        # URL输入区域
        url_layout = QVBoxLayout()
        
        url_label = QLabel('输入要检测的网站URL:')
        url_label.setStyleSheet("font-weight: bold; color: #495057;")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('例如: https://www.example.com')
        url_layout.addWidget(self.url_input)
        
        layout.addLayout(url_layout)
        
        # 检测按钮
        self.detect_button = QPushButton('开始检测')
        self.detect_button.clicked.connect(self.start_detection)
        layout.addWidget(self.detect_button)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 分隔线
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        line2.setStyleSheet("color: #dee2e6;")
        layout.addWidget(line2)
        
        # 结果区域标题
        result_title = QLabel('检测结果:')
        result_title.setStyleSheet("font-weight: bold; color: #495057; font-size: 16px;")
        layout.addWidget(result_title)
        
        # 主要结果标签
        self.result_label = QLabel('等待检测...')
        self.result_label.setObjectName('resultLabel')
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("""
            background-color: #e9ecef;
            color: #6c757d;
        """)
        layout.addWidget(self.result_label)
        
        # 概率信息
        self.probability_label = QLabel('非法概率: --')
        self.probability_label.setStyleSheet("font-size: 14px; color: #343a40;")
        layout.addWidget(self.probability_label)
        
        # 风险等级
        self.risk_label = QLabel('风险等级: --')
        self.risk_label.setStyleSheet("font-size: 14px; color: #343a40;")
        layout.addWidget(self.risk_label)
        
        # 分隔线
        line3 = QFrame()
        line3.setFrameShape(QFrame.HLine)
        line3.setFrameShadow(QFrame.Sunken)
        line3.setStyleSheet("color: #dee2e6;")
        layout.addWidget(line3)
        
        # 警告信息区域
        warning_title = QLabel('安全警告:')
        warning_title.setStyleSheet("font-weight: bold; color: #495057; font-size: 16px;")
        layout.addWidget(warning_title)
        
        self.warning_text = QTextEdit()
        self.warning_text.setReadOnly(True)
        self.warning_text.setMaximumHeight(150)
        self.warning_text.setText('检测完成后将显示警告信息...')
        layout.addWidget(self.warning_text)
        
        # 状态栏
        self.statusBar().showMessage('就绪')
    
    def start_detection(self):
        """开始检测"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, '输入错误', '请输入要检测的URL地址')
            return
        
        # 禁用按钮
        self.detect_button.setEnabled(False)
        self.detect_button.setText('检测中...')
        
        # 显示进度条
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 清空之前的结果
        self.clear_results()
        
        # 更新状态
        self.statusBar().showMessage(f'正在检测: {url}')
        
        # 创建并启动工作线程
        self.worker = DetectionWorker(url, self.model_path)
        self.worker.progress.connect(self.update_progress)
        self.worker.result_ready.connect(self.show_result)
        self.worker.error.connect(self.show_error)
        self.worker.start()
    
    def update_progress(self, value, message):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.statusBar().showMessage(message)
    
    def show_result(self, result_dict):
        """显示检测结果"""
        # 恢复按钮状态
        self.detect_button.setEnabled(True)
        self.detect_button.setText('开始检测')
        self.progress_bar.setVisible(False)
        
        # 更新状态
        self.statusBar().showMessage(f'检测完成: {result_dict["url"]}')
        
        # 显示主要结果
        if result_dict['result'] == "钓鱼网站":
            # 钓鱼网站 - 红色警告
            color = "#721c24"
            bg_color = "#f8d7da"
            border_color = "#f5c6cb"
            risk_text = f"钓鱼网站 (风险等级: {result_dict['risk_level']})"
            icon = "⚠️ "
        else:
            # 正常网站 - 绿色安全
            color = "#155724"
            bg_color = "#d4edda"
            border_color = "#c3e6cb"
            risk_text = "正常网站"
            icon = "✅ "
        
        self.result_label.setText(f"{icon} {risk_text}")
        self.result_label.setStyleSheet(f"""
            background-color: {bg_color};
            color: {color};
            border: 2px solid {border_color};
        """)
        
        # 显示概率信息
        probability = result_dict['probability']
        confidence = result_dict['confidence']
        
        self.probability_label.setText(f"非法概率: {probability:.2%}")
        self.risk_label.setText(f"风险等级: {result_dict['risk_level']}")
        
        # 显示警告信息
        warnings = result_dict.get('warnings', [])
        if warnings:
            warning_text = "\n".join(warnings)
            self.warning_text.setText(warning_text)
            
            # 如果有高风险警告，设置为红色
            if "⚠️" in warning_text:
                self.warning_text.setStyleSheet("color: #dc3545;")
            else:
                self.warning_text.setStyleSheet("color: #28a745;")
        else:
            self.warning_text.setText("未检测到明显的风险特征。")
            self.warning_text.setStyleSheet("color: #6c757d;")
        
        # 如果是高概率钓鱼网站，显示警告对话框
        if result_dict['result'] == "钓鱼网站" and probability > 0.7:
            self.show_alert_dialog(result_dict, probability)
    
    def show_alert_dialog(self, result_dict, probability):
        """显示警告对话框"""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("⚠️ 严重安全警告")
        
        msg_box.setText(f"检测到高概率钓鱼网站！")
        
        detailed_text = f"""
        检测到非法概率高达 {probability:.2%} 的钓鱼网站！
        
        URL: {result_dict['url'][:100]}...
        
        📋 <b>安全建议：</b>
        1. 立即关闭此网页
        2. 不要输入任何个人信息
        3. 不要点击任何链接
        4. 不要下载任何文件
        5. 清理浏览器缓存和cookies
        6. 运行杀毒软件进行扫描
        
        🛡️ <b>防护措施：</b>
        • 使用安全浏览器
        • 安装反钓鱼插件
        • 定期更新安全软件
        • 谨慎对待可疑链接
        """
        
        msg_box.setInformativeText(detailed_text)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    
    def show_error(self, error_msg):
        """显示错误信息"""
        # 恢复按钮状态
        self.detect_button.setEnabled(True)
        self.detect_button.setText('开始检测')
        self.progress_bar.setVisible(False)
        
        # 显示错误信息
        self.statusBar().showMessage(f'错误: {error_msg}')
        
        # 显示错误对话框
        QMessageBox.critical(self, '检测错误', f'检测过程中发生错误:\n\n{error_msg}')
        
        # 在结果区域显示错误
        self.result_label.setText('❌ 检测失败')
        self.result_label.setStyleSheet("""
            background-color: #f8d7da;
            color: #721c24;
            border: 2px solid #f5c6cb;
        """)
        
        self.probability_label.setText('非法概率: --')
        self.risk_label.setText('风险等级: --')
        
        self.warning_text.setText(f'错误详情: {error_msg}\n\n请检查URL格式或网络连接后重试。')
        self.warning_text.setStyleSheet("color: #dc3545;")
    
    def clear_results(self):
        """清空结果"""
        self.result_label.setText('等待检测...')
        self.result_label.setStyleSheet("""
            background-color: #e9ecef;
            color: #6c757d;
        """)
        
        self.probability_label.setText('非法概率: --')
        self.risk_label.setText('风险等级: --')
        
        self.warning_text.setText('检测完成后将显示警告信息...')
        self.warning_text.setStyleSheet("color: #6c757d;")
        
        self.statusBar().showMessage('就绪')

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName('钓鱼网站检测器')
    
    window = SimpleDetectorWindow()
    window.show()  
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()