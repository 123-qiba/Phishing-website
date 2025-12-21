/**
 * ============================================
 * 模块5：拦截页面核心逻辑
 * 职责：显示拦截页面，处理用户操作
 * 依赖：模块1通过URL参数提供拦截信息
 * ============================================
 */

// ============ 配置 ============
const CONFIG = {
    // 威胁类型配置
    threatTypes: {
        phishing: {
            title: "已拦截：网络钓鱼网站",
            type: "网络钓鱼",
            level: "critical",
            icon: "fas fa-fish",
            description: "此网站伪装成合法服务（如银行、邮箱、社交媒体），试图窃取您的登录凭证和个人信息。",
            advice: [
                "不要在此页面输入任何用户名、密码或个人信息",
                "检查网址是否正确 - 钓鱼网站通常使用相似的域名",
                "如需登录相关服务，请通过官方应用或直接输入正确网址访问",
                "启用双因素认证以增加账户安全性"
            ],
            risks: [
                "个人信息被盗",
                "账户被入侵",
                "财务损失",
                "身份盗用风险"
            ]
        },
        
        malware: {
            title: "已拦截：恶意软件网站",
            type: "恶意软件",
            level: "critical",
            icon: "fas fa-biohazard",
            description: "此网站可能传播病毒、木马、勒索软件等恶意程序，访问可能导致设备感染或数据泄露。",
            advice: [
                "立即关闭此标签页，不要下载任何文件",
                "运行杀毒软件进行全面扫描",
                "确保操作系统和所有软件都是最新版本",
                "定期备份重要文件"
            ],
            risks: [
                "设备感染恶意软件",
                "文件被加密勒索",
                "系统被远程控制",
                "数据永久丢失"
            ]
        },
        
        fraud: {
            title: "已拦截：欺诈网站",
            type: "欺诈",
            level: "high",
            icon: "fas fa-user-secret",
            description: "此网站通过虚假产品、投资骗局或技术支持诈骗等方式诱骗用户付款或提供敏感信息。",
            advice: [
                "不要在此网站进行任何交易或付款",
                "如果已付款，立即联系银行或支付平台",
                "检查网站的真实性和用户评价",
                "使用信誉良好的支付方式"
            ],
            risks: [
                "经济损失",
                "信用卡信息被盗",
                "陷入诈骗陷阱",
                "后续骚扰电话"
            ]
        },
        
        suspicious: {
            title: "已拦截：可疑网站",
            type: "可疑内容",
            level: "medium",
            icon: "fas fa-question-circle",
            description: "此网站表现出可疑特征，可能传播误导信息或存在安全风险，建议保持警惕。",
            advice: [
                "谨慎对待网站上的所有信息",
                "不要下载不明来源的文件",
                "注意网站的SSL证书有效性",
                "考虑使用隐私浏览模式"
            ],
            risks: [
                "接触到误导信息",
                "潜在隐私泄露",
                "可能的重定向风险",
                "广告骚扰"
            ]
        },
        
        blacklisted: {
            title: "已拦截：恶意网站",
            type: "黑名单命中",
            level: "high",
            icon: "fas fa-ban",
            description: "此网站在安全黑名单中，已被确认存在安全威胁或恶意行为。",
            advice: [
                "立即离开此页面",
                "不要与此网站进行任何交互",
                "清理浏览器缓存和cookies",
                "运行安全扫描确保设备安全"
            ],
            risks: [
                "多种安全风险",
                "数据泄露",
                "设备安全威胁",
                "隐私侵犯"
            ]
        }
    },
    
    // 威胁等级配置
    severityLevels: {
        critical: { name: "严重威胁", color: "#e74c3c" },
        high: { name: "高风险", color: "#f39c12" },
        medium: { name: "中等风险", color: "#f1c40f" },
        low: { name: "低风险", color: "#3498db" },
        suspicious: { name: "可疑", color: "#95a5a6" }
    },
    
    // 默认值
    defaults: {
        url: "https://example-dangerous-site.com",
        reason: "blacklisted",
        threatLevel: "high"
    }
};

// ============ 状态 ============
const State = {
    // 拦截信息（来自模块1的URL参数）
    interception: null,
    
    // 当前威胁配置
    threatConfig: null,
    
    // 页面状态
    isInitialized: false,
    isDemoMode: false
};

// ============ 核心函数 ============

/**
 * 初始化拦截页面
 */
function initBlockedPage() {
    console.log("初始化拦截页面...");
    
    try {
        // 1. 解析URL参数（模块1传递的信息）
        State.interception = parseUrlParameters();
        State.isDemoMode = State.interception.demo === "true";
        
        // 2. 获取威胁配置
        State.threatConfig = getThreatConfig(State.interception.reason);
        
        // 3. 更新页面UI
        updatePageUI();
        
        // 4. 设置事件监听器
        setupEventListeners();
        
        // 5. 标记初始化完成
        State.isInitialized = true;
        
        console.log("拦截页面初始化完成", State.interception);
        
    } catch (error) {
        console.error("初始化失败:", error);
        showError("页面初始化失败，请刷新重试");
    }
}

/**
 * 解析URL参数
 * 模块1通过URL传递拦截信息
 */
function parseUrlParameters() {
    const params = new URLSearchParams(window.location.search);
    
    // 必需参数
    const url = decodeURIComponent(params.get('url') || CONFIG.defaults.url);
    const reason = params.get('reason') || CONFIG.defaults.reason;
    
    // 解析hostname
    let hostname;
    try {
        hostname = new URL(url).hostname;
    } catch {
        hostname = url.split('/')[2] || url;
    }
    
    return {
        // 必需参数
        url: url,
        reason: reason,
        hostname: hostname,
        
        // 可选参数
        threatLevel: params.get('threatLevel') || CONFIG.defaults.threatLevel,
        interceptId: params.get('interceptId') || generateInterceptId(),
        timestamp: params.get('timestamp') || new Date().toISOString(),
        
        // 扩展参数（模块1可添加）
        source: params.get('source'),
        category: params.get('category'),
        matchedPattern: params.get('matchedPattern'),
        
        // 演示模式
        demo: params.get('demo') || "false"
    };
}

/**
 * 生成拦截ID
 */
function generateInterceptId() {
    const time = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2, 6);
    return `BLOCK-${time}-${random}`.toUpperCase();
}

/**
 * 获取威胁配置
 */
function getThreatConfig(reason) {
    return CONFIG.threatTypes[reason] || CONFIG.threatTypes.blacklisted;
}

/**
 * 更新页面UI
 */
function updatePageUI() {
    const { interception, threatConfig } = State;
    
    // 更新头部
    updateHeader(threatConfig);
    
    // 更新威胁详情
    updateThreatDetails(interception, threatConfig);
    
    // 更新威胁描述
    updateThreatDescription(threatConfig);
    
    // 更新建议列表
    updateAdviceList(threatConfig);
    
    // 更新对话框内容
    updateDialogContent(interception, threatConfig);
    
    // 更新文档标题
    document.title = `${threatConfig.title} - 网站安全卫士`;
}

/**
 * 更新头部
 */
function updateHeader(threatConfig) {
    const header = document.getElementById('warning-header');
    const title = document.getElementById('threat-title');
    const icon = document.getElementById('threat-icon');
    const subtitle = document.getElementById('subtitle-text');
    
    // 标题和图标
    title.textContent = threatConfig.title;
    icon.className = threatConfig.icon;
    
    // 副标题
    if (State.isDemoMode) {
        subtitle.textContent = "演示模式 - 安全拦截系统";
    }
    
    // 头部颜色
    header.className = 'warning-header';
    header.classList.add(threatConfig.level);
}

/**
 * 更新威胁详情
 */
function updateThreatDetails(interception, threatConfig) {
    // 威胁类型
    const threatTypeEl = document.getElementById('threat-type');
    threatTypeEl.textContent = threatConfig.type;
    threatTypeEl.className = `threat-badge ${threatConfig.level}`;
    
    // URL信息
    document.getElementById('blocked-url').textContent = interception.url;
    document.getElementById('blocked-hostname').textContent = interception.hostname;
    
    // 威胁等级
    const severityDot = document.getElementById('severity-dot');
    const severityText = document.getElementById('severity-text');
    const level = interception.threatLevel || threatConfig.level;
    const levelConfig = CONFIG.severityLevels[level] || CONFIG.severityLevels.high;
    
    severityDot.className = `severity-dot ${level}`;
    severityText.textContent = levelConfig.name;
    
    // 时间和ID
    const time = new Date(interception.timestamp);
    document.getElementById('intercept-time').textContent = time.toLocaleString('zh-CN');
    document.getElementById('intercept-id').textContent = interception.interceptId;
}

/**
 * 更新威胁描述
 */
function updateThreatDescription(threatConfig) {
    document.getElementById('threat-description').textContent = threatConfig.description;
}

/**
 * 更新建议列表
 */
function updateAdviceList(threatConfig) {
    const adviceList = document.getElementById('advice-list');
    adviceList.innerHTML = '';
    
    threatConfig.advice.forEach((advice, index) => {
        const item = document.createElement('div');
        item.className = 'advice-item';
        item.innerHTML = `
            <i class="fas fa-check-circle"></i>
            <span>${advice}</span>
        `;
        adviceList.appendChild(item);
    });
}

/**
 * 更新对话框内容
 */
function updateDialogContent(interception, threatConfig) {
    // 对话框中的URL
    document.getElementById('dialog-url').textContent = interception.url;
    document.getElementById('dialog-threat').textContent = threatConfig.type;
    
    // 威胁等级
    const level = interception.threatLevel || threatConfig.level;
    const levelConfig = CONFIG.severityLevels[level] || CONFIG.severityLevels.high;
    document.getElementById('dialog-level').textContent = levelConfig.name;
    
    // 风险列表
    const riskList = document.getElementById('risk-list');
    riskList.innerHTML = '';
    
    threatConfig.risks.forEach(risk => {
        const li = document.createElement('li');
        li.textContent = risk;
        riskList.appendChild(li);
    });
}

/**
 * 设置事件监听器
 */
function setupEventListeners() {
    // 返回安全页面按钮
    document.getElementById('go-back-btn').addEventListener('click', handleGoBack);
    
    // 仍要访问按钮
    document.getElementById('proceed-btn').addEventListener('click', handleProceedClick);
    
    // 对话框相关
    document.getElementById('dialog-close-btn').addEventListener('click', closeRiskDialog);
    document.getElementById('cancel-btn').addEventListener('click', closeRiskDialog);
    document.getElementById('risk-acknowledge').addEventListener('change', handleRiskAcknowledge);
    document.getElementById('confirm-proceed-btn').addEventListener('click', handleConfirmProceed);
    
    // 快速链接
    document.getElementById('learn-more-link').addEventListener('click', handleLearnMore);
    document.getElementById('report-link').addEventListener('click', handleReport);
    document.getElementById('more-info-link').addEventListener('click', handleMoreInfo);
    
    // 页脚链接
    document.getElementById('privacy-link').addEventListener('click', handlePrivacy);
    document.getElementById('help-link').addEventListener('click', handleHelp);
    document.getElementById('feedback-link').addEventListener('click', handleFeedback);
    
    // 下拉菜单项
    document.getElementById('view-details-item').addEventListener('click', handleViewDetails);
    document.getElementById('whitelist-item').addEventListener('click', handleWhitelist);
    document.getElementById('security-center-item').addEventListener('click', handleSecurityCenter);
    document.getElementById('refresh-item').addEventListener('click', handleRefresh);
    document.getElementById('copy-url-item').addEventListener('click', handleCopyUrl);
    
    // 关闭下拉菜单（点击页面其他地方）
    document.addEventListener('click', closeDropdownMenu);
    
    // 键盘快捷键
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

// ============ 事件处理函数 ============

/**
 * 返回安全页面
 */
function handleGoBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        // 如果没有历史记录，重定向到安全页面
        window.location.href = 'https://www.google.com';
    }
}

/**
 * 处理"仍要访问"点击
 */
function handleProceedClick() {
    showRiskDialog();
}

/**
 * 显示风险确认对话框
 */
function showRiskDialog() {
    const dialog = document.getElementById('risk-dialog');
    dialog.style.display = 'flex';
    
    // 重置确认复选框
    document.getElementById('risk-acknowledge').checked = false;
    document.getElementById('dont-show-again').checked = false;
    document.getElementById('confirm-proceed-btn').disabled = true;
    
    // 阻止背景滚动
    document.body.style.overflow = 'hidden';
}

/**
 * 关闭风险对话框
 */
function closeRiskDialog() {
    const dialog = document.getElementById('risk-dialog');
    dialog.style.display = 'none';
    
    // 恢复背景滚动
    document.body.style.overflow = '';
}

/**
 * 处理风险确认复选框
 */
function handleRiskAcknowledge(event) {
    const confirmBtn = document.getElementById('confirm-proceed-btn');
    confirmBtn.disabled = !event.target.checked;
}

/**
 * 处理确认继续访问
 */
function handleConfirmProceed() {
    if (!State.interception) return;
    
    const dontShowAgain = document.getElementById('dont-show-again').checked;
    
    // 记录用户选择（发送给模块6）
    sendUserAction('proceed_anyway', {
        dontShowAgain: dontShowAgain,
        acknowledged: true
    });
    
    if (State.isDemoMode) {
        // 演示模式：显示提示
        alert(`演示模式：在实际扩展中，将重定向到：\n\n${State.interception.url}`);
        closeRiskDialog();
    } else {
        // 实际扩展中：重定向到被拦截的URL
        // window.location.href = State.interception.url;
        
        // 临时：在演示中不实际重定向
        alert(`在实际扩展中，将重定向到被拦截的URL。\n\nURL: ${State.interception.url}`);
        closeRiskDialog();
    }
}

/**
 * 了解此威胁
 */
function handleLearnMore(event) {
    event.preventDefault();
    
    const { threatConfig } = State;
    const message = `
${threatConfig.type} - 详细说明：

${threatConfig.description}

常见特征：
• 使用相似的域名欺骗用户
• 页面设计与知名网站相似
• 要求输入敏感信息
• 使用紧急或威胁性语言

防护建议：
${threatConfig.advice.map((advice, i) => `${i + 1}. ${advice}`).join('\n')}
    `;
    
    alert(message);
}

/**
 * 报告误报
 */
function handleReport(event) {
    event.preventDefault();
    
    if (!State.interception) return;
    
    const comment = prompt('请说明为什么您认为这是误报：\n（这将帮助改进我们的安全系统）', '');
    
    if (comment !== null) {
        sendFalseReport(comment);
        alert('感谢您的反馈！误报报告已提交。');
    }
}

/**
 * 更多选项
 */
function handleMoreInfo(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const menu = document.getElementById('options-menu');
    const link = event.currentTarget;
    const rect = link.getBoundingClientRect();
    
    // 定位菜单
    menu.style.left = `${rect.left}px`;
    menu.style.top = `${rect.bottom + 5}px`;
    menu.style.display = 'block';
}

/**
 * 隐私声明
 */
function handlePrivacy(event) {
    event.preventDefault();
    alert('隐私声明：\n\n本扩展仅处理浏览器请求数据用于安全检测，不会收集个人身份信息。所有数据处理均在本地进行。');
}

/**
 * 帮助中心
 */
function handleHelp(event) {
    event.preventDefault();
    alert('帮助中心：\n\n如遇问题，请联系技术支持或查看扩展文档。');
}

/**
 * 意见反馈
 */
function handleFeedback(event) {
    event.preventDefault();
    alert('意见反馈：\n\n感谢您使用网站安全卫士！您可以通过扩展设置页面提交反馈。');
}

/**
 * 查看详细报告
 */
function handleViewDetails(event) {
    event.preventDefault();
    closeDropdownMenu();
    
    const { interception, threatConfig } = State;
    const report = generateDetailedReport();
    
    // 显示报告
    const reportText = `
=== 详细安全报告 ===

拦截ID: ${interception.interceptId}
拦截时间: ${new Date(interception.timestamp).toLocaleString('zh-CN')}

威胁信息：
• 类型: ${threatConfig.type}
• 等级: ${CONFIG.severityLevels[threatConfig.level].name}
• 原因: ${interception.reason}

网站信息：
• URL: ${interception.url}
• 域名: ${interception.hostname}
• 来源: ${interception.source || '本地黑名单'}

技术详情：
• 威胁配置: ${threatConfig.type}
• 建议操作: ${threatConfig.advice.length} 条安全建议
    `;
    
    alert(reportText);
}

/**
 * 添加白名单
 */
function handleWhitelist(event) {
    event.preventDefault();
    closeDropdownMenu();
    
    if (!State.interception) return;
    
    const confirmed = confirm(`您确定要将以下网站添加到白名单吗？\n\n${State.interception.hostname}\n\n添加到白名单后，将不再拦截此网站。`);
    
    if (confirmed) {
        sendWhitelistRequest();
        alert('网站已添加到白名单请求列表。');
    }
}

/**
 * 安全设置
 */
function handleSecurityCenter(event) {
    event.preventDefault();
    closeDropdownMenu();
    alert('安全设置功能由模块6的安全中心提供。');
}

/**
 * 重新检测
 */
function handleRefresh(event) {
    event.preventDefault();
    closeDropdownMenu();
    
    if (State.isDemoMode) {
        alert('演示模式：重新检测将使用新的模拟数据。');
        
        // 模拟重新检测
        const reasons = Object.keys(CONFIG.threatTypes);
        const randomReason = reasons[Math.floor(Math.random() * reasons.length)];
        State.interception.reason = randomReason;
        State.threatConfig = getThreatConfig(randomReason);
        updatePageUI();
    } else {
        alert('重新检测功能在实际扩展中可用。');
    }
}

/**
 * 复制网址
 */
function handleCopyUrl(event) {
    event.preventDefault();
    closeDropdownMenu();
    
    if (!State.interception) return;
    
    navigator.clipboard.writeText(State.interception.url)
        .then(() => {
            alert('网址已复制到剪贴板');
        })
        .catch(() => {
            // 备用方法
            const textarea = document.createElement('textarea');
            textarea.value = State.interception.url;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            alert('网址已复制到剪贴板');
        });
}

/**
 * 关闭下拉菜单
 */
function closeDropdownMenu() {
    document.getElementById('options-menu').style.display = 'none';
}

/**
 * 处理键盘快捷键
 */
function handleKeyboardShortcuts(event) {
    // Esc: 关闭对话框
    if (event.key === 'Escape') {
        const dialog = document.getElementById('risk-dialog');
        if (dialog.style.display === 'flex') {
            closeRiskDialog();
        }
        closeDropdownMenu();
    }
    
    // Ctrl+Enter: 确认继续访问（在对话框中）
    if (event.ctrlKey && event.key === 'Enter') {
        const dialog = document.getElementById('risk-dialog');
        const confirmBtn = document.getElementById('confirm-proceed-btn');
        
        if (dialog.style.display === 'flex' && !confirmBtn.disabled) {
            handleConfirmProceed();
        }
    }
    
    // Alt+B: 返回安全页面
    if (event.altKey && event.key === 'b') {
        handleGoBack();
    }
}

// ============ 通信函数 ============

/**
 * 发送用户操作记录
 */
function sendUserAction(action, data = {}) {
    const log = {
        interceptId: State.interception?.interceptId,
        action: action,
        timestamp: new Date().toISOString(),
        data: data,
        demo: State.isDemoMode
    };
    
    console.log('用户操作记录:', log);
    
    // 发送给模块6（通过postMessage）
    window.postMessage({
        type: 'module5_user_action',
        data: log
    }, '*');
    
    // 如果使用chrome.storage，也可以存储
    if (typeof chrome !== 'undefined' && chrome.storage) {
        chrome.storage.local.get(['userActions'], result => {
            const actions = result.userActions || [];
            actions.push(log);
            chrome.storage.local.set({ userActions: actions.slice(-100) });
        });
    }
}

/**
 * 发送误报报告
 */
function sendFalseReport(comment) {
    const report = {
        interceptId: State.interception?.interceptId,
        url: State.interception?.url,
        reportedAt: new Date().toISOString(),
        userComment: comment,
        threatType: State.interception?.reason
    };
    
    console.log('误报报告:', report);
    
    // 发送给模块6
    window.postMessage({
        type: 'module5_false_report',
        data: report
    }, '*');
}

/**
 * 发送白名单请求
 */
function sendWhitelistRequest() {
    const request = {
        interceptId: State.interception?.interceptId,
        hostname: State.interception?.hostname,
        requestedAt: new Date().toISOString(),
        reason: '用户手动添加'
    };
    
    console.log('白名单请求:', request);
    
    // 发送给模块6
    window.postMessage({
        type: 'module5_whitelist_request',
        data: request
    }, '*');
}

// ============ 工具函数 ============

/**
 * 生成详细报告
 */
function generateDetailedReport() {
    const { interception, threatConfig } = State;
    
    return {
        interceptId: interception.interceptId,
        timestamp: interception.timestamp,
        url: interception.url,
        hostname: interception.hostname,
        threatType: interception.reason,
        threatName: threatConfig.type,
        threatLevel: threatConfig.level,
        severity: CONFIG.severityLevels[threatConfig.level].name,
        advice: threatConfig.advice,
        risks: threatConfig.risks,
        source: interception.source || 'local',
        demo: State.isDemoMode
    };
}

/**
 * 显示错误信息
 */
function showError(message) {
    const container = document.querySelector('.container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
        <div style="background: #ffeaea; padding: 20px; border-radius: 8px; border-left: 4px solid #e74c3c;">
            <h3 style="color: #e74c3c; margin-bottom: 10px;">
                <i class="fas fa-exclamation-circle"></i> 错误
            </h3>
            <p>${message}</p>
            <button onclick="location.reload()" style="margin-top: 10px; padding: 8px 16px; background: #3498db; color: white; border: none; border-radius: 4px;">
                刷新页面
            </button>
        </div>
    `;
    
    container.insertBefore(errorDiv, container.firstChild);
}

// ============ 初始化 ============

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initBlockedPage);

// 提供公共API供其他模块调用
window.BlockedPage = {
    // 更新拦截信息（模块1调用）
    updateInterception: function(data) {
        if (!data || !data.url) {
            console.error('无效的拦截数据');
            return false;
        }
        
        State.interception = { ...State.interception, ...data };
        State.threatConfig = getThreatConfig(State.interception.reason);
        
        if (State.isInitialized) {
            updatePageUI();
        }
        
        return true;
    },
    
    // 获取当前状态
    getState: function() {
        return {
            interception: State.interception,
            threatConfig: State.threatConfig,
            isDemoMode: State.isDemoMode
        };
    },
    
    // 获取配置
    getConfig: function() {
        return CONFIG;
    }
};

// 控制台日志
console.log(`
=====================================
网站安全卫士 - 拦截页面 (模块5)
版本: 1.0.0
职责: 显示拦截页面，处理用户操作
依赖: 模块1通过URL参数提供拦截信息
=====================================
`);