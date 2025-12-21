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

    if (!data || data.length === 0) {
        historyList.innerHTML = '<tr class="empty-state"><td colspan="4">暂无记录</td></tr>';
        return;
    }

    data.forEach(item => {
        const tr = document.createElement('tr');
        let threatColor = '#9ca3af';
        if (item.threat === 'High' || item.threat === '高') threatColor = '#ef4444';
        if (item.threat === 'Medium' || item.threat === '中') threatColor = '#f59e0b';

        tr.innerHTML = `
            <td style="color: var(--text-muted);">${item.time}</td>
            <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.url}">${item.url}</td>
            <td style="color: ${threatColor}; font-weight: 500;">${item.threat}</td>
            <td><span class="badge">${item.status}</span></td>
        `;
        historyList.appendChild(tr);
    });
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

function loadBlacklist() {
    const SERVER_URL = 'http://localhost:8000/blacklist';
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
            // Fallback to local storage if server is down
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
    const SERVER_URL = 'http://localhost:8000/blacklist';

    // First fetch latest to ensure we don't overwrite
    fetch(SERVER_URL)
        .then(res => res.json())
        .then(list => {
            if (!list.includes(url)) {
                list.push(url);
                updateServerBlacklist(list);
            }
        })
        .catch(err => {
            console.error('Server error, falling back to local storage', err);
            // Fallback logic could be added here
        });
}

function removeFromBlacklist(url) {
    const SERVER_URL = 'http://localhost:8000/blacklist';

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
    const SERVER_URL = 'http://localhost:8000/blacklist';
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
        });
}

// --- Knowledge Base Module ---
const knowledgeDB = {
    'threat-url': {
        title: '威胁：恶意链接传播',
        content: `
            <p>攻击者通过垃圾邮件、短信或社交媒体传播精心构造的钓鱼链接。这些链接通常指向已知的恶意服务器或刚被攻破的合法网站。</p>
            <h3>解决方案 (模块 1：智能拦截)</h3>
            <p>本项目的核心后端模块通过以下方式解决此威胁：</p>
            <ul>
                <li><strong>实时请求拦截</strong>：利用 <code>webRequest</code> API 在浏览器发出网络请求毫秒级前进行拦截。</li>
                <li><strong>本地黑名单匹配</strong>：内置并定期更新高危 URL 数据库，瞬间识别已知威胁。</li>
                <li><strong>正则模式识别</strong>：识别典型的钓鱼 URL 结构（如过多的重定向参数）。</li>
            </ul>
        `
    },
    'threat-reputation': {
        title: '威胁：网站信誉风险',
        content: `
            <p>许多新注册的钓鱼网站尚未被列入黑名单，难以被传统手段拦截。它们往往缺乏历史信誉积累，或使用了廉价、匿名的托管服务。</p>
            <h3>解决方案 (模块 2：安全评分系统)</h3>
            <p>我们建立了多维度的实时评分模型来评估“未知”网站的风险：</p>
            <ul>
                <li><strong>多因子评估</strong>：综合考量 HTTPS 证书等级、域名注册时长、Alexa 排名等数据。</li>
                <li><strong>外部资源分析</strong>：检测页面是否大量引用了来路不明的第三方脚本或框架。</li>
                <li><strong>动态打分</strong>：最终输出 A-F 的安全等级，让未知的威胁无所遁形。</li>
            </ul>
        `
    },
    'threat-visual': {
        title: '威胁：视觉欺诈与页面伪造',
        content: `
            <p>高级攻击者会完整克隆银行或支付平台的登录页面（包括 Logo、布局）。由于 URL 可能使用了形似字符，用户极易被视觉假象欺骗。</p>
            <h3>解决方案 (模块 3：DOM 内容分析)</h3>
            <p>通过注入的内容脚本 (Content Script) 深入网页内部进行“体检”：</p>
            <ul>
                <li><strong>表单特征识别</strong>：识别非官方域名下的“用户名+密码”输入框组合。</li>
                <li><strong>UI 结构比对</strong>：检测页面 DOM 结构是否与知名网站高度相似但 URL 不匹配。</li>
                <li><strong>隐藏元素检测</strong>：发现用于逃避扫描的隐藏关键词或覆盖层。</li>
            </ul>
        `
    },
    'threat-https': {
        title: '威胁：虚假安全陷阱',
        content: `
            <p>超过 80% 的现代钓鱼网站使用 HTTPS 协议，浏览器地址栏的“安全锁”图标常让用户误以为网站是绝对安全的。</p>
            <h3>解决方案 (模块 5：透明化报告)</h3>
            <p>我们致力于打破“HTTPS = 安全”的迷思：</p>
            <ul>
                <li><strong>深度证书校验</strong>：不仅检查加密，还验证证书颁发机构 (CA) 的信誉度。</li>
                <li><strong>混合内容警告</strong>：当HTTPS页面加载不安全的HTTP资源时发出警告。</li>
                <li><strong>教育式拦截</strong>：在拦截页面清晰告知用户“为何被拦截”，提升用户的安全认知。</li>
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
