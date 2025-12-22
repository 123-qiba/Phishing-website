/**
 * Security Center Logic
 * Handles tab navigation, history display, blacklist management, theme toggling, and knowledge base details.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Security Center Loaded');
    initTheme();
    initTabs();
    try {
        initHistory();
        initBlacklist();
        initKnowledgeBase();
    } catch (e) {
        console.error('Initialization error:', e);
    }
});

// --- Theme Module ---
function initTheme() {
    const toggleBtn = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const html = document.documentElement;

    chrome.storage.local.get(['theme'], (result) => {
        const savedTheme = result.theme || 'dark';
        applyTheme(savedTheme);
    });

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const currentTheme = html.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            applyTheme(newTheme);
            chrome.storage.local.set({ theme: newTheme });
        });
    }

    function applyTheme(theme) {
        if (theme === 'light') {
            html.setAttribute('data-theme', 'light');
            themeIcon.textContent = '☀️';
            toggleBtn.setAttribute('aria-label', 'Switch to Dark Mode');
        } else {
            html.removeAttribute('data-theme');
            themeIcon.textContent = '🌙';
            toggleBtn.setAttribute('aria-label', 'Switch to Light Mode');
        }
    }
}

// --- Tab Navigation ---
function initTabs() {
    const tabs = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.tab-content');
    const pageTitle = document.getElementById('page-title');

    const titles = {
        'history': '历史记录',
        'blacklist': '黑名单管理',
        'knowledge': '安全知识库'
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            tab.classList.add('active');
            const tabId = tab.dataset.tab;
            const section = document.getElementById(`${tabId}-section`);
            if (section) section.classList.add('active');
            if (pageTitle && titles[tabId]) pageTitle.textContent = titles[tabId];
        });
    });
}

// --- History Module ---
function initHistory() {
    loadHistory();
    const clearBtn = document.getElementById('clear-history');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            chrome.storage.local.set({ securityHistory: [] }, () => {
                loadHistory();
            });
        });
    }

    // Modal close logic for report modal
    const reportModal = document.getElementById('report-modal');
    const reportCloseBtn = document.getElementById('report-close-btn');
    if (reportModal && reportCloseBtn) {
        reportCloseBtn.addEventListener('click', () => {
            reportModal.classList.remove('active');
            document.body.style.overflow = '';
        });
        reportModal.addEventListener('click', (e) => {
            if (e.target === reportModal) {
                reportModal.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    }
}

function loadHistory() {
    const mockHistory = [
        { time: '2023-10-27 10:23', url: 'http://dangerous-bank-login.com', threat: 'High', status: '已拦截' },
        { time: '2023-10-26 15:45', url: 'http://free-iphone-gift.net', threat: 'Medium', status: '警告' },
        { time: '2023-10-25 09:12', url: 'http://suspicious-redirect.org', threat: 'Low', status: '已放行' }
    ];

    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(['securityHistory'], (result) => {
            if (chrome.runtime.lastError) {
                renderHistoryTable(mockHistory);
                return;
            }
            let history = result.securityHistory || mockHistory;
            renderHistoryTable(history);
        });
    } else {
        renderHistoryTable(mockHistory);
    }
}

function renderHistoryTable(data) {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = '';

    // Update table header to match new columns
    const thead = document.querySelector('.data-table thead tr');
    if (thead) {
        thead.innerHTML = `
            <th>时间</th>
            <th>拦截ID</th>
            <th>威胁类型</th>
            <th>风险等级</th>
            <th>URL</th>
            <th>操作</th>
        `;
    }

    if (!data || data.length === 0) {
        // 更新 colspan 为 6
        historyList.innerHTML = '<tr class="empty-state"><td colspan="6">暂无记录</td></tr>';
        return;
    }

    data.forEach((item, index) => {
        const tr = document.createElement('tr');

        // Handle both old format (time, url, threat) and new format (timestamp, url, threatType...)
        // New format: timestamp (ISO), threatType (key), threatLevel (level)

        let displayTime = item.time || new Date(item.timestamp).toLocaleString('zh-CN');
        let displayUrl = item.url;
        let displayId = item.interceptId || '--';
        let displayType = item.threatName || item.threat || '未知威胁';
        let displayLevel = item.threatLevel || 'high'; // critical, high, medium, low

        // Map level to color
        const colorMap = {
            'critical': '#e74c3c', // Red
            'high': '#e67e22',     // Orange
            'medium': '#f1c40f',   // Yellow
            'low': '#3498db'       // Blue
        };
        const color = colorMap[displayLevel] || colorMap['high'];
        const levelLabel = displayLevel.toUpperCase();

        tr.innerHTML = `
            <td style="color: var(--text-muted); font-size: 0.9em;">${displayTime}</td>
            <td style="font-family: monospace; color: var(--text-muted);">${displayId}</td>
            <td><span style="font-weight: 600;">${displayType}</span></td>
            <td><span class="badge" style="background-color: ${color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8em;">${levelLabel}</span></td>
            <td style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${displayUrl}">
                ${displayUrl}
            </td>
            <td>
                <button class="btn btn-secondary btn-sm view-details-btn" data-index="${index}">
                    查看详情
                </button>
            </td>
        `;
        historyList.appendChild(tr);
    });

    // Add event listeners to buttons
    document.querySelectorAll('.view-details-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = e.target.dataset.index;
            const report = data[index];
            showHistoryDetails(report);
        });
    });
}

function showHistoryDetails(report) {
    const modal = document.getElementById('report-modal');
    if (!modal) return;

    // Populate Data
    document.getElementById('report-title').textContent = '安全拦截报告';
    document.getElementById('report-time').textContent = report.time || new Date(report.timestamp).toLocaleString('zh-CN');

    // Description: 使用 threatName 作为威胁说明，需去除可能存在的符号
    const rawDesc = report.threatName || '检测到潜在的安全威胁，请注意防范。';
    document.getElementById('report-description').textContent = rawDesc.replace(/⚠️/g, '').trim();


    document.getElementById('report-id').textContent = report.interceptId || 'N/A';
    document.getElementById('report-url').textContent = report.url;

    // Lists - 智能分类显示
    const riskList = document.getElementById('report-risks');
    riskList.innerHTML = '';

    if (report.risks && Array.isArray(report.risks) && report.risks.length > 0) {
        // 分离 DOM 风险和其他
        const domRisks = report.risks.filter(r => r.includes("[内容]") || r.includes("DOM") || r.includes("Iframe"));
        const otherRisks = report.risks.filter(r => !domRisks.includes(r));

        if (domRisks.length > 0) {
            riskList.innerHTML += `<li style="color: #e67e22; font-weight: bold; margin-top:5px;">[网页内容/DOM 异常]</li>`;
            domRisks.forEach(r => {
                const cleanText = r.replace(/⚠️/g, '').trim();
                riskList.innerHTML += `<li>${cleanText}</li>`;
            });
        }

        if (otherRisks.length > 0) {
            if (domRisks.length > 0) riskList.innerHTML += `<li style="margin-top:10px; border-top:1px dashed #ccc;"></li>`; // 分隔线
            riskList.innerHTML += `<li style="color: #e74c3c; font-weight: bold; margin-top:5px;">[网络/信誉/黑名单]</li>`;
            otherRisks.forEach(r => {
                const cleanText = r.replace(/⚠️/g, '').trim();
                riskList.innerHTML += `<li>${cleanText}</li>`;
            });
        }
    } else {
        riskList.innerHTML = '<li>无详细风险信息</li>';
    }

    const adviceList = document.getElementById('report-advice');
    adviceList.innerHTML = '';
    if (report.advice && Array.isArray(report.advice)) {
        report.advice.forEach(advice => {
            adviceList.innerHTML += `<li>${advice}</li>`;
        });
    } else {
        adviceList.innerHTML = '<li>无详细建议</li>';
    }

    // Show Modal
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}



// --- Blacklist Module ---
function initBlacklist() {
    const addBtn = document.getElementById('add-blacklist-btn');
    const input = document.getElementById('blacklist-input');

    loadBlacklist();

    addBtn.addEventListener('click', () => {
        const url = input.value.trim();
        if (url) {
            addToBlacklist(url);
            input.value = '';
        }
    });

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const url = input.value.trim();
            if (url) {
                addToBlacklist(url);
                input.value = '';
            }
        }
    });
}

const SERVER_URL = 'http://127.0.0.1:5000/blacklist';

function loadBlacklist() {
    fetch(SERVER_URL)
        .then(response => response.json())
        .then(list => {
            console.log('Blacklist loaded from server:', list);
            renderBlacklist(list);
            // Sync to chrome storage for other modules to use (optional but good for consistency)
            chrome.storage.local.set({ userBlacklist: list });
        })
        .catch(error => {
            console.error('Error loading blacklist from server:', error);
            // Fallback to local storage if API fails (UI only)
            chrome.storage.local.get(['userBlacklist'], (result) => {
                const list = result.userBlacklist || [];
                renderBlacklist(list);
            });
        });
}

function renderBlacklist(list) {
    const listContainer = document.getElementById('blacklist-items');
    const countBadge = document.getElementById('blacklist-count');

    listContainer.innerHTML = '';
    countBadge.textContent = `${list.length} 个`;

    if (list.length === 0) {
        listContainer.innerHTML = '<div class="empty-message" style="text-align:center; color:var(--text-muted); padding:1rem;">黑名单为空</div>';
        return;
    }

    list.forEach(url => {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerHTML = `
            <span>${url}</span>
            <button class="btn btn-danger btn-sm delete-btn" data-url="${url}">移除</button>
        `;
        listContainer.appendChild(item);
    });

    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const urlToRemove = e.target.dataset.url;
            removeFromBlacklist(urlToRemove);
        });
    });
}

function addToBlacklist(url) {
    // First fetch latest to ensure we don't overwrite
    fetch(SERVER_URL)
        .then(res => res.json())
        .then(list => {
            if (!list.includes(url)) {
                list.push(url);
                updateServerBlacklist(list);
            } else {
                alert('该域名已在黑名单中');
            }
        })
        .catch(err => {
            console.error('Server error', err);
            alert("无法连接到后端服务器，请确认 server.py 是否运行");
        });
}

function removeFromBlacklist(url) {
    fetch(SERVER_URL)
        .then(res => res.json())
        .then(list => {
            const newList = list.filter(item => item !== url);
            updateServerBlacklist(newList);
        })
        .catch(err => {
            console.error('Server error', err);
        });
}

function updateServerBlacklist(list) {
    fetch(SERVER_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(list)
    })
        .then(res => res.json())
        .then(data => {
            console.log('Server update success:', data);
            loadBlacklist(); // Reload UI
        })
        .catch(err => {
            console.error('Failed to update server', err);
            alert("更新失败");
        });
}

// --- Knowledge Base Module ---
const knowledgeDB = {
    'threat-url': {
        title: 'URL 结构与伪造欺诈',
        content: `
            <p>攻击者通过操纵 URL 字符串来混淆视听，诱导用户认为自己访问的是合法网站。</p>
            <h3>检测特征 (模块 1：URL 规则)</h3>
            <ul>
                <li><strong>IP 地址直连</strong>：合法网站极少使用裸 IP (如 <code>http://192.168.x.x</code>)。</li>
                <li><strong>短链接混淆</strong>：使用 bit.ly 等服务隐藏真实目的地址。</li>
                <li><strong>特殊符号欺骗</strong>：利用 <code>@</code> 符号 (浏览器会忽略其前面的内容) 或双斜杠 <code>//</code> 进行重定向跳转。</li>
                <li><strong>形似域名</strong>：使用连字符 <code>-</code> (如 <code>paypal-secure.com</code>) 模仿知名品牌。</li>
            </ul>
        `
    },
    'threat-domain': {
        title: '域名信誉与生命周期',
        content: `
            <p>钓鱼网站通常生命周期极短（“日抛型”），且缺乏完整的注册信息。</p>
            <h3>检测特征 (模块 2：信誉分析)</h3>
            <ul>
                <li><strong>注册时间过短</strong>：域名注册少于 6 个月或刚刚注册。</li>
                <li><strong>WHOIS 异常</strong>：隐藏注册人信息或查询失败。</li>
                <li><strong>无 DNS 记录</strong>：域名对应的 A 记录为空或解析异常。</li>
                <li><strong>HTTPS 滥用</strong>：即使有 HTTPS 锁图标，如果证书是免费/短期的，依然可能不安全。</li>
            </ul>
        `
    },
    'threat-content': {
        title: '页面内容与恶意行为',
        content: `
            <p>即使 URL 看起来正常，页面内部的代码可能包含窃取数据的逻辑或恶意脚本。</p>
            <h3>检测特征 (模块 3：DOM 分析)</h3>
            <ul>
                <li><strong>异常表单 (SFH)</strong>：登录表单的提交地址为空 (<code>about:blank</code>) 或指向第三方域名。</li>
                <li><strong>隐蔽框架 (Iframe)</strong>：使用肉眼不可见的 iframe 覆盖层劫持点击。</li>
                <li><strong>状态栏伪造</strong>：利用 <code>onmouseover</code> 修改浏览器状态栏显示的 URL，掩盖真实链接。</li>
                <li><strong>弹窗滥用</strong>：利用 <code>window.open</code> 或大量弹窗干扰用户操作。</li>
            </ul>
        `
    },
    'threat-ai': {
        title: 'AI 深度学习综合研判',
        content: `
            <p>针对“未知威胁”，系统利用训练好的深度神经网路模型进行概率预测。</p>
            <h3>检测机制 (模块 4：智能核心)</h3>
            <ul>
                <li><strong>1D-CNN 模型</strong>：后端部署的一维卷积神经网络。</li>
                <li><strong>30 维特征向量</strong>：将上述所有 URL、域名、内容特征转化为数值向量输入模型。</li>
                <li><strong>概率评分</strong>：模型输出 0.0~1.0 的概率值。超过 0.5 即视为钓鱼，超过 0.8 为严重威胁。</li>
                <li><strong>零容忍拦截</strong>：结合前台策略，只要模型判定为中高风险，立即切断访问。</li>
            </ul>
        `
    }
};

function initKnowledgeBase() {
    const modal = document.getElementById('knowledge-modal');
    const modalBody = document.getElementById('modal-body-content');
    const closeBtn = document.querySelector('.close-modal');

    // Open Modal
    document.querySelectorAll('.learn-more').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const topic = e.target.dataset.topic;
            const data = knowledgeDB[topic];

            if (data) {
                modalBody.innerHTML = `<h3>${data.title}</h3>${data.content}`;
                openModal();
            }
        });
    });

    // Close Modal
    if (closeBtn) {
        closeBtn.addEventListener('click', closeModal);
    }

    // Click outside to close
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeModal();
        }
    });

    function openModal() {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    function closeModal() {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}
