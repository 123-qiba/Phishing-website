# server.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from judge_port import extract_features
from predicting import predict_phishing_with_accuracy

app = Flask(__name__)
CORS(app)  # 允许被 Chrome 扩展跨域访问

def get_risk_level(probability: float) -> str:
    """根据非法概率给出风险等级字符串"""
    if probability > 0.8:
        return "critical"
    elif probability > 0.6:
        return "high"
    elif probability > 0.5:
        return "medium"
    else:
        return "low"

def generate_warnings(features):
    """按 tol_final.py 同样规则生成安全警告列表"""
    warnings = []

    # 高风险特征
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

    if not warnings:
        warnings.append("✅ 未检测到明显风险特征")

    return warnings


@app.route("/check", methods=["GET"])
def check_url():
    print("收到检测请求")  # 终端里可以看到
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "missing url"}), 400

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        # 1. 提取特征
        features = extract_features(url)

        # 2. 模型预测
        result, probability, confidence = predict_phishing_with_accuracy(features)

        # 3. 规则警告
        warnings = generate_warnings(features)

        # 4. 风险等级
        risk_level = get_risk_level(probability)

        return jsonify({
            "url": url,
            "result": result,
            "probability": probability,
            "confidence": confidence,
            "risk_level": risk_level,
            "warnings": warnings
        })
    except Exception as e:
        print("检测发生错误:", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 这段一定要保留，否则不会启动服务
    print("启动 Flask 服务，监听 http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)
