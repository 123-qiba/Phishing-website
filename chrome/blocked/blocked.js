/**
 * ============================================
 * 模块5：拦截页面核心逻辑 (最终完整版)
 * 特性：
 * 1. 修复了变量未定义的 BUG
 * 2. 支持解析 URL 中的 warnings 参数
 * 3. 支持同时展示多个威胁的详细解释（拼接显示）
 * 4. 支持合并并去重多个威胁的安全建议
 * ============================================
 */

// ============ 1. 特定警告的详细解释与建议配置 ============
const SPECIFIC_WARNING_DETAILS = {
    "⚠️ 异常WHOIS记录": {
        desc: "该网站的域名注册信息（WHOIS）被隐藏、缺失或显示异常。合法的商业网站通常会公开其注册信息，而攻击者往往隐藏身份以逃避追踪。",
        advice: [
            "无法验证网站所有者身份，请勿进行交易",
            "不要输入银行卡号或密码",
            "检查域名拼写是否与官方域名有细微差别"
        ]
    },
    "⚠️ URL长度可疑": {
        desc: "该网页的网址（URL）长度异常，远超正常标准。攻击者常通过极长的URL来隐藏其中的恶意代码、重定向指令或伪造的域名信息。",
        advice: [
            "不要点击长链接，尽量手动输入官方网址",
            "注意地址栏中是否有奇怪的字符或填充内容",
            "立即关闭页面，不要下载任何内容"
        ]
    },
    "⚠️ 使用短链接服务": {
        desc: "该链接使用了短链接服务（如bit.ly等）进行跳转。虽然短链接很常见，但在涉及敏感信息的场景中，攻击者常利用它来掩盖真实的恶意目标地址。",
        advice: [
            "不要在跳转后的页面输入任何个人信息",
            "使用URL还原工具查看其真实目的地址",
            "如果是陌生邮件发来的短链，切勿点击"
        ]
    },
    "⚠️ URL包含IP地址": {
        desc: "该网址直接使用IP地址（如 192.168.x.x）而不是域名。合法的公共服务网站几乎总是使用域名。这极有可能是恶意服务器或被黑客控制的设备。",
        advice: [
            "绝对不要在此类页面输入账号密码",
            "立即离开，该服务器可能正在尝试通过漏洞攻击您的设备",
            "不要下载页面上的任何插件"
        ]
    },
    "⚠️ URL包含@符号": {
        desc: "网址中包含 '@' 符号。这是一种古老的欺骗手段，浏览器可能会忽略 '@' 之前的内容，直接访问 '@' 之后的恶意地址，从而误导用户。",
        advice: [
            "注意观察浏览器地址栏最终显示的域名",
            "不要信任包含 '@' 的登录链接",
            "立即关闭网页"
        ]
    },
    "⚠️ 存在双斜杠重定向": {
        desc: "URL路径中包含 '//'（双斜杠）。这种结构常被用于在URL内部通过重定向将用户引导至另一个未经验证的恶意站点。",
        advice: [
            "仔细检查地址栏，确认当前所在的实际域名",
            "不要点击页面上的任何确认按钮"
        ]
    },
    "⚠️ 域名使用连字符": {
        desc: "域名中包含连字符（-）。虽然合法，但攻击者常用它来伪造类似 'secure-bank.com' 的域名来冒充 'securebank.com'，以此进行钓鱼。",
        advice: [
            "仔细比对域名与官方域名是否完全一致",
            "警惕类似 'paypal-secure' 之类的组合词"
        ]
    },
    "⚠️ 无DNS记录": {
        desc: "该域名在DNS系统中没有有效的解析记录。这通常意味着该域名刚刚注册、已被注销，或者是一个临时搭建用于短期攻击的黑站。",
        advice: [
            "网站极不稳定且不可信，立即离开",
            "不要相信页面上显示的任何内容"
        ]
    },
    "⚠️ 过多子域名": {
        desc: "该网址使用了过多层级的子域名（如 a.b.c.d.example.com）。这是为了在移动设备上隐藏真实的主域名，让用户误以为是合法网站。",
        advice: [
            "在电脑端查看完整域名后缀",
            "只信任主域名（如 example.com）部分的信誉"
        ]
    },
    "⚠️ 域名注册时间短": {
        desc: "该域名的注册时间非常短（通常少于一年）。许多钓鱼网站都是“日抛型”的，注册后立即用于攻击，随后被废弃。",
        advice: [
            "对于新注册的网站，不要进行金钱交易",
            "保持高度警惕，不要轻信其声誉"
        ]
    },
    "⚠️ HTTPS令牌滥用": {
        desc: "URL中的HTTPS标记位置可疑。攻击者可能在子域名中使用 'https' 字符（如 https-bank.com），试图让用户误以为连接是安全的。",
        advice: [
            "看到小锁图标不代表网站是合法的，只代表传输加密",
            "务必检查根域名是否正确"
        ]
    },
    "⚠️ 过多重定向": {
        desc: "访问此页面经历了过多次数的跳转。这通常是为了绕过安全检测机制，或者将用户层层过滤筛选，最终导向恶意页面。",
        advice: [
            "浏览器可能已被劫持，建议清理缓存",
            "不要在最终落地的页面输入信息"
        ]
    },
    "⚠️ 域名年龄小于6个月": {
        desc: "该域名非常年轻（小于6个月）。虽然可能是新业务，但在没有信誉积累的情况下，通过该网站进行敏感操作风险极高。",
        advice: [
            "建议等待该网站建立信誉后再访问",
            "寻找该服务的替代官方渠道"
        ]
    }
};

// ============ 2. 基础配置 ============
const CONFIG = {
    threatTypes: {
        phishing: {
            title: "已拦截：网络钓鱼网站",
            type: "网络钓鱼",
            level: "critical",
            icon: "🎣",
            description: "此网站伪装成合法服务，试图窃取您的信息。",
            advice: ["不要输入密码", "检查网址", "立即离开"],
            risks: ["个人信息被盗", "账户被入侵", "财务损失"]
        },
        malware: {
            title: "已拦截：恶意软件网站",
            type: "恶意软件",
            level: "critical",
            icon: "☣️",
            description: "此网站可能传播病毒、木马，访问可能导致设备感染。",
            advice: ["立即关闭标签页", "运行杀毒软件", "不要下载文件"],
            risks: ["设备感染", "文件丢失", "系统被控"]
        },
        fraud: {
            title: "已拦截：欺诈网站",
            type: "欺诈",
            level: "high",
            icon: "🕵️",
            description: "此网站涉及虚假产品或投资骗局。",
            advice: ["不要付款", "联系银行", "核实信誉"],
            risks: ["经济损失", "信息泄露", "诈骗陷阱"]
        },
        suspicious: {
            title: "已拦截：可疑网站",
            type: "可疑内容",
            level: "medium",
            icon: "❓",
            description: "此网站表出可疑特征，建议保持警惕。",
            advice: ["谨慎浏览", "不要下载", "检查证书"],
            risks: ["误导信息", "隐私泄露", "广告骚扰"]
        },
        blacklisted: {
            title: "已拦截：高风险网站",
            type: "安全威胁",
            level: "high",
            icon: "🚫",
            description: "此网站被检测出存在安全隐患。",
            advice: ["立即离开", "清理缓存", "运行扫描"],
            risks: ["安全风险", "数据泄露", "隐私侵犯"]
        }
    },
    severityLevels: {
        critical: { name: "严重威胁", color: "#e74c3c" },
        high: { name: "高风险", color: "#f39c12" },
        medium: { name: "中等风险", color: "#f1c40f" },
        low: { name: "低风险", color: "#3498db" },
        suspicious: { name: "可疑", color: "#95a5a6" }
    },
    defaults: {
        url: "https://example.com",
        reason: "blacklisted",
        threatLevel: "high"
    }
};

// ============ 3. 状态管理 ============
const State = {
    interception: null,
    threatConfig: null,
    isInitialized: false,
    isDemoMode: false
};

// ============ 4. 核心初始化与解析 ============

function initBlockedPage() {
    try {
        console.log("初始化拦截页面...");

        // 1. 解析URL参数
        State.interception = parseUrlParameters();
        State.isDemoMode = State.interception.demo === "true";

        // 2. 获取威胁配置
        State.threatConfig = getThreatConfig(State.interception.reason);

        // 3. 更新界面
        updatePageUI();

        // 4. 绑定事件
        setupEventListeners();

        State.isInitialized = true;
        console.log("初始化完成", State.interception);

    } catch (error) {
        console.error("初始化失败:", error);
        showError("页面初始化失败，请刷新重试");
    }
}

document.addEventListener("DOMContentLoaded", initBlockedPage);

function parseUrlParameters() {
    const params = new URLSearchParams(window.location.search);
    const url = decodeURIComponent(params.get('url') || CONFIG.defaults.url);
    const reason = params.get('reason') || CONFIG.defaults.reason;

    let hostname;
    try {
        hostname = new URL(url).hostname;
    } catch {
        hostname = url.split('/')[2] || url;
    }

    // 解析 warnings 数组
    let warnings = [];
    const warningsParam = params.get("warnings");
    if (warningsParam) {
        try {
            warnings = JSON.parse(decodeURIComponent(warningsParam));
        } catch (e) {
            console.error("Failed to parse warnings:", e);
        }
    }

    return {
        url: url,
        reason: reason,
        hostname: hostname,
        threatLevel: params.get('threatLevel') || CONFIG.defaults.threatLevel,
        interceptId: params.get('interceptId') || generateInterceptId(),
        timestamp: params.get('timestamp') || new Date().toISOString(),
        warnings: warnings,
        demo: params.get('demo') || "false"
    };
}

function generateInterceptId() {
    return `BLOCK-${Date.now().toString(36)}-${Math.random().toString(36).substr(2, 6)}`.toUpperCase();
}

function getThreatConfig(reason) {
    return CONFIG.threatTypes[reason] || CONFIG.threatTypes.blacklisted;
}

// ============ 5. UI 更新逻辑 ============

function updatePageUI() {
    const { interception, threatConfig } = State;

    updateHeader(threatConfig);
    updateThreatDetails(interception, threatConfig);
    updateThreatDescription(interception, threatConfig);
    updateAdviceList(interception, threatConfig);
    updateDialogContent(interception, threatConfig);

    document.title = `${threatConfig.title} - 网站安全卫士`;
}

function updateHeader(threatConfig) {
    const header = document.getElementById('warning-header');
    document.getElementById('threat-title').textContent = threatConfig.title;
    document.getElementById('threat-icon').textContent = threatConfig.icon;
    document.getElementById('threat-icon').className = 'warning-icon'; // Keep base class, remove fa classes

    if (State.isDemoMode) {
        document.getElementById('subtitle-text').textContent = "演示模式 - 安全拦截系统";
    }

    header.className = 'warning-header';
    header.classList.add(threatConfig.level);
}

function updateThreatDetails(interception, threatConfig) {
    const list = document.getElementById('threat-type-list');

    if (list) {
        list.innerHTML = ""; // 清空

        // 如果有具体的警告列表，展示所有警告标签
        if (interception.warnings && interception.warnings.length > 0) {
            interception.warnings.forEach(w => {
                const li = document.createElement("li");
                li.className = `threat-badge ${threatConfig.level}`;
                li.textContent = w;
                list.appendChild(li);
            });
        } else {
            // 否则展示默认类型
            const li = document.createElement("li");
            li.className = `threat-badge ${threatConfig.level}`;
            li.textContent = threatConfig.type;
            list.appendChild(li);
        }
    }

    // 更新其他详情
    document.getElementById('blocked-url').textContent = interception.url;
    document.getElementById('blocked-hostname').textContent = interception.hostname;

    const level = interception.threatLevel || threatConfig.level;
    const levelConfig = CONFIG.severityLevels[level] || CONFIG.severityLevels.high;

    document.getElementById('severity-dot').className = `severity-dot ${level}`;
    document.getElementById('severity-text').textContent = levelConfig.name;
    document.getElementById('intercept-time').textContent = new Date(interception.timestamp).toLocaleString('zh-CN');
    document.getElementById('intercept-id').textContent = interception.interceptId;
}

/**
 * 动态更新威胁描述（支持多重威胁拼接）
 */
function updateThreatDescription(interception, threatConfig) {
    const descEl = document.getElementById('threat-description');

    if (interception.warnings && interception.warnings.length > 0) {
        let descriptionHTMLs = [];
        let foundSpecific = false;

        interception.warnings.forEach(warning => {
            if (SPECIFIC_WARNING_DETAILS[warning]) {
                foundSpecific = true;
                descriptionHTMLs.push(
                    `<div style="margin-bottom: 12px;">
                        <strong style="color: #e74c3c;">${warning}</strong>
                        <div style="margin-top: 4px;">${SPECIFIC_WARNING_DETAILS[warning].desc}</div>
                     </div>`
                );
            }
        });

        if (foundSpecific) {
            // 用虚线分割不同威胁的描述
            descEl.innerHTML = descriptionHTMLs.join('<div style="border-top: 1px dashed #eee; margin: 10px 0;"></div>');
            return;
        }
    }

    // 默认描述
    descEl.textContent = threatConfig.description;
}

/**
 * 动态更新建议列表（支持多重威胁建议合并去重）
 */
function updateAdviceList(interception, threatConfig) {
    const adviceList = document.getElementById('advice-list');
    adviceList.innerHTML = '';

    let uniqueAdvice = new Set();
    let foundSpecific = false;

    if (interception.warnings && interception.warnings.length > 0) {
        interception.warnings.forEach(warning => {
            if (SPECIFIC_WARNING_DETAILS[warning] && SPECIFIC_WARNING_DETAILS[warning].advice) {
                foundSpecific = true;
                SPECIFIC_WARNING_DETAILS[warning].advice.forEach(a => uniqueAdvice.add(a));
            }
        });
    }

    let advicesToShow;
    if (foundSpecific) {
        advicesToShow = Array.from(uniqueAdvice);
    } else {
        advicesToShow = threatConfig.advice;
    }

    advicesToShow.forEach(advice => {
        const item = document.createElement('div');
        item.className = 'advice-item';
        item.innerHTML = `<i class="fas fa-check-circle"></i><span>${advice}</span>`;
        adviceList.appendChild(item);
    });
}

function updateDialogContent(interception, threatConfig) {
    document.getElementById('dialog-url').textContent = interception.url;
    document.getElementById('dialog-threat').textContent = threatConfig.type;

    const level = interception.threatLevel || threatConfig.level;
    document.getElementById('dialog-level').textContent = CONFIG.severityLevels[level].name;

    const riskList = document.getElementById('risk-list');
    riskList.innerHTML = '';

    threatConfig.risks.forEach(risk => {
        const li = document.createElement('li');
        li.textContent = risk;
        riskList.appendChild(li);
    });
}

// ============ 6. 事件监听与处理 ============

function setupEventListeners() {
    // 按钮事件
    document.getElementById('go-back-btn').addEventListener('click', handleGoBack);
    document.getElementById('proceed-btn').addEventListener('click', handleProceedClick);

    // 弹窗事件
    document.getElementById('dialog-close-btn').addEventListener('click', closeRiskDialog);
    document.getElementById('cancel-btn').addEventListener('click', closeRiskDialog);
    document.getElementById('risk-acknowledge').addEventListener('change', handleRiskAcknowledge);
    document.getElementById('confirm-proceed-btn').addEventListener('click', handleConfirmProceed);

    // 辅助链接（阻止默认行为）
    const links = ['learn-more-link', 'report-link', 'more-info-link', 'privacy-link', 'help-link', 'feedback-link'];
    links.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('click', e => e.preventDefault());
    });

    // 下拉菜单
    document.getElementById('view-details-item').addEventListener('click', handleViewDetails);
    document.getElementById('whitelist-item').addEventListener('click', handleWhitelist);
    document.getElementById('security-center-item').addEventListener('click', () => {
        closeDropdownMenu();
        if (chrome.runtime && chrome.runtime.openOptionsPage) {
            chrome.runtime.openOptionsPage();
        } else {
            // Fallback if needed, or keeping it strictly chrome extension
            window.open(chrome.runtime.getURL('security_center/pages/security_center.html'));
        }
    });
    document.getElementById('refresh-item').addEventListener('click', () => { closeDropdownMenu(); location.reload(); });
    document.getElementById('copy-url-item').addEventListener('click', handleCopyUrl);

    document.addEventListener('click', closeDropdownMenu);
    document.addEventListener('keydown', handleKeyboardShortcuts);
}

function handleGoBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = 'about:blank'; // 或跳转到安全主页
    }
}

function handleProceedClick() {
    const dialog = document.getElementById('risk-dialog');
    dialog.style.display = 'flex';
    document.getElementById('risk-acknowledge').checked = false;
    document.getElementById('confirm-proceed-btn').disabled = true;
    document.body.style.overflow = 'hidden';
}

function closeRiskDialog() {
    const dialog = document.getElementById('risk-dialog');
    dialog.style.display = 'none';
    document.body.style.overflow = '';
}

function handleRiskAcknowledge(event) {
    document.getElementById('confirm-proceed-btn').disabled = !event.target.checked;
}

function handleConfirmProceed() {
    if (!State.interception) return;

    // 这里可以添加 "不再显示" 的逻辑处理
    // const dontShowAgain = document.getElementById('dont-show-again').checked;

    // 模拟放行
    alert(`警告：您正在强制访问高风险网站：\n\n${State.interception.url}\n\n后果请自负。`);
    closeRiskDialog();
    // 实际场景：window.location.href = State.interception.url;
}

function handleViewDetails(event) {
    event.preventDefault();
    closeDropdownMenu();
    alert(`=== 详细安全报告 ===\n拦截ID: ${State.interception.interceptId}\nURL: ${State.interception.url}`);
}

function handleWhitelist(event) {
    event.preventDefault();
    closeDropdownMenu();
    if (confirm('确定将此域名加入白名单吗？')) {
        alert('请求已提交。');
    }
}

function handleCopyUrl(event) {
    event.preventDefault();
    closeDropdownMenu();
    if (!State.interception) return;
    navigator.clipboard.writeText(State.interception.url).then(() => alert('网址已复制'));
}

function handleMoreInfo(event) {
    event.preventDefault();
    event.stopPropagation();
    const menu = document.getElementById('options-menu');
    const rect = event.currentTarget.getBoundingClientRect();
    menu.style.left = `${rect.left}px`;
    menu.style.top = `${rect.bottom + 5}px`;
    menu.style.display = 'block';
}
// 绑定更多选项按钮（如果上面循环没绑定到的话）
const moreInfoBtn = document.getElementById('more-info-link');
if (moreInfoBtn) moreInfoBtn.onclick = handleMoreInfo;

function closeDropdownMenu() {
    document.getElementById('options-menu').style.display = 'none';
}

function handleKeyboardShortcuts(event) {
    if (event.key === 'Escape') {
        if (document.getElementById('risk-dialog').style.display === 'flex') {
            closeRiskDialog();
        }
        closeDropdownMenu();
    }
}

function showError(message) {
    const container = document.querySelector('.container');
    const errorDiv = document.createElement('div');
    errorDiv.style.background = '#ffeaea';
    errorDiv.style.color = '#e74c3c';
    errorDiv.style.padding = '20px';
    errorDiv.style.marginBottom = '20px';
    errorDiv.innerHTML = `<h3>⚠️ 错误</h3><p>${message}</p>`;
    container.insertBefore(errorDiv, container.firstChild);
}

// ============ 7. 导出 API ============
window.BlockedPage = {
    updateInterception: function (data) {
        State.interception = { ...State.interception, ...data };
        if (State.isInitialized) updatePageUI();
    }
};