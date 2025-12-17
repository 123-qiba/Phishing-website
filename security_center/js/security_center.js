/**
 * Security Center Logic
 * Handles tab navigation, history display, and blacklist management.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Security Center Loaded');
    initTabs();
    try {
        initHistory();
        initBlacklist();
    } catch (e) {
        console.error('Initialization error:', e);
    }
});

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
            console.log('Tab clicked:', tab.dataset.tab);

            // Remove active class from all
            tabs.forEach(t => t.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));

            // Add active class to clicked
            tab.classList.add('active');

            const tabId = tab.dataset.tab;
            const section = document.getElementById(`${tabId}-section`);
            if (section) {
                section.classList.add('active');
            } else {
                console.error('Section not found:', `${tabId}-section`);
            }

            // Update Title
            if (pageTitle && titles[tabId]) {
                pageTitle.textContent = titles[tabId];
            }
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
    // TODO: Connect to chrome.storage
    // For now using mock data if storage is empty

    // Mock Data for demonstration
    const mockHistory = [
        { time: '2023-10-27 10:23', url: 'http://dangerous-bank-login.com', threat: 'High', status: '已拦截' },
        { time: '2023-10-26 15:45', url: 'http://free-iphone-gift.net', threat: 'Medium', status: '警告' },
        { time: '2023-10-25 09:12', url: 'http://suspicious-redirect.org', threat: 'Low', status: '已放行' }
    ];

    const historyList = document.getElementById('history-list');

    // Check chrome.storage (mocking simple callback for now)
    // Check chrome.storage (mocking simple callback for now)
    if (typeof chrome !== 'undefined' && chrome.storage && chrome.storage.local) {
        chrome.storage.local.get(['securityHistory'], (result) => {
            // Catch error if runtime.lastError exists
            if (chrome.runtime.lastError) {
                console.error('Storage error:', chrome.runtime.lastError);
                renderHistoryTable(mockHistory);
                return;
            }
            let history = result.securityHistory || mockHistory;
            renderHistoryTable(history);
        });
    } else {
        console.warn('Chrome storage not available, using mock data');
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

        // Color code for threat level
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

    // Enter key support
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
    // Mocking initial data
    const mockBlacklist = ['evil-site.com', 'phishing-example.net'];

    chrome.storage.local.get(['userBlacklist'], (result) => {
        let list = result.userBlacklist || mockBlacklist;
        renderBlacklist(list);
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

    // Attach event listeners to new buttons
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const urlToRemove = e.target.dataset.url;
            removeFromBlacklist(urlToRemove);
        });
    });
}

function addToBlacklist(url) {
    chrome.storage.local.get(['userBlacklist'], (result) => {
        let list = result.userBlacklist || [];
        if (!list.includes(url)) {
            list.push(url);
            chrome.storage.local.set({ userBlacklist: list }, () => {
                loadBlacklist();
            });
        }
    });
}

function removeFromBlacklist(url) {
    chrome.storage.local.get(['userBlacklist'], (result) => {
        let list = result.userBlacklist || [];
        list = list.filter(item => item !== url);
        chrome.storage.local.set({ userBlacklist: list }, () => {
            loadBlacklist();
        });
    });
}
