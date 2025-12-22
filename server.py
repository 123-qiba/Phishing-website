# server.py

from flask import Flask, request, jsonify
from flask_cors import CORS
from judge_port import extract_features, _load_blacklist, check_fixed_blacklist
from predicting import predict_phishing_with_accuracy
import os

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

    # 1. 优先检查黑名单 (Module 1 / Feature 29)
    # judge_port.py: return 1 if domain in bl else -1
    if 29 < len(features) and features[29] == 1:
        warnings.append("⚠️ 网站在黑名单中")

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

    # 模块 3: DOM/内容欺诈风险 (Indices correspond to judge.py feature list)
    # 9: Favicon, 12: Request_URL, 13: URL_of_Anchor, 14: Links_in_tags, 15: SFH, 16: Submitting_to_email
    # 19: on_mouseover, 20: RightClick, 21: popUpWidnow, 22: Iframe
    
    dom_risk_indices = [15, 16, 19, 21, 22]
    dom_risk_messages = [
        "SFH: 异常表单提交地址",
        "Email: 网页尝试发送邮件",
        "MouseOver: 状态栏伪造",
        "Popup: 存在弹出窗口",
        "Iframe: 存在隐蔽框架"
    ]
    for idx, msg in zip(dom_risk_indices, dom_risk_messages):
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

        # --- 新增: 手动黑名单 (Manual Blacklist) ---
        # 如果都在黑名单里了，那肯定是高风险，不管模型怎么说
        if len(features) > 29 and features[29] == 1:
            risk_level = "high"


        # --- 新增: 固定黑名单 (Stealth Mode) ---
        # 优先级最高。如果命中，强制覆盖风险等级，并确保警告中不提"黑名单"
        is_fixed_blocked = check_fixed_blacklist(url)
        if is_fixed_blocked:
            print(f"[Stealth Block] URL {url} hit fixed blacklist.")
            risk_level = "critical"  # or "high"
            
            # 如果之前没有警告(或者只有低风险提示)，需要加一些"看起来很严重"的通用警告
            # 以掩盖它是被黑名单拦截的事实
            if not warnings or (len(warnings) == 1 and "✅" in warnings[0]):
                warnings = []
                warnings.append("⚠️ 检测到高危恶意活动")
                warnings.append("⚠️ 域名注册信息异常") # 伪造一个理由
            
            # 确保不要出现 "⚠️ 网站在黑名单中"
            # (理论上 features[29] 是针对 manual blacklist 的，如果不共用文件，这里不应该出现。
            #  但为了双重保险，过滤一下)
            warnings = [w for w in warnings if "黑名单" not in w]
            
            # 确保至少有一个看起来很严重的警告
            has_scary_warning = any("⚠️" in w for w in warnings)
            if not has_scary_warning:
                 warnings.insert(0, "⚠️ 智能检测系统拦截: 极高风险")
        # ---------------------------------------

        # --- Terminal Output for Debugging ---
        print("-" * 50)
        print(f"检测 URL: {url}")
        print(f"钓鱼概率: {probability:.4f} (Score: {int((1-probability)*100)})")
        print(f"风险等级: {risk_level}")
        if warnings:
            print("检测警告:")
            for w in warnings:
                print(f"  {w}")
        print("-" * 50)
        # -------------------------------------

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
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/blacklist", methods=["GET", "POST"])
def manage_blacklist():
    # 黑名单文件路径 (与 judge_port.py 中的逻辑保持一致)
    txt_path = os.path.join(os.path.dirname(__file__), "blacklist.txt")
    
    if request.method == "GET":
        try:
            lines = []
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            return jsonify(lines)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "POST":
        try:
            new_list = request.json
            if not isinstance(new_list, list):
                return jsonify({"error": "Invalid format, expected list"}), 400
            
            # 去重并写入
            unique_list = sorted(list(set(new_list)))
            with open(txt_path, "w", encoding="utf-8") as f:
                for item in unique_list:
                    f.write(item + "\n")
            
            # 关键：清除 LRU 缓存，使 judge_port.py 重新读取文件
            _load_blacklist.cache_clear()
            # 同时也清除固定黑名单缓存，以防万一未来合并管理
            try:
                from judge_port import _load_fixed_blacklist
                _load_fixed_blacklist.cache_clear()
            except:
                pass
            print("黑名单已更新，缓存已清除")
            
            return jsonify({"status": "ok", "count": len(unique_list)})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 这段一定要保留，否则不会启动服务
    print("启动 Flask 服务，监听 http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)
