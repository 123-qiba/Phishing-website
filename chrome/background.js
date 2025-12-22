// background.js

// 后台函数：调用本地 Flask 接口并根据结果决定是否拦截
// 存储每个 Tab 的最新检测结果: { tabId: { score, warnings, riskLevel, ... } }
const tabRisks = {};

async function checkAndMaybeBlock(tabId, url) {
  try {
    const apiUrl = "http://127.0.0.1:5000/check?url=" + encodeURIComponent(url);
    const res = await fetch(apiUrl);

    if (!res.ok) {
      console.warn("Detection API error status:", res.status);
      return;
    }

    const data = await res.json();
    if (data.error) {
      console.warn("Detection API error:", data.error);
      return;
    }

    const warnings = data.warnings || [];
    const riskLevel = data.risk_level || "low";

    // 1. 计算 Module 2 (AI模型) 的评分
    // probability 是 "是钓鱼网站的概率" (0-1)，越高越危险
    // score 是 "安全分" (0-100)，越高越安全
    const probability = data.probability !== undefined ? data.probability : 0;
    const score = Math.round((1 - probability) * 100);

    // 2. 统计 Module 1 (规则/黑名单) 和 Module 3 (DOM/内容) 的结果
    // 根据 server.py 的返回格式区分

    // A. 真正的黑名单命中 
    const isBlacklisted = warnings.some(w => w.includes("⚠️ 网站在黑名单中"));
    const blacklistHits = isBlacklisted ? 1 : 0;

    // B. DOM/内容风险 (Module 3)
    // 根据 server.py 的消息关键字: "SFH", "Email", "MouseOver", "Popup", "Iframe", "[内容]"
    const domRiskKeywords = ["SFH", "Email", "MouseOver", "Popup", "Iframe", "[内容]", "DOM"];
    const domRisks = warnings.filter(w => domRiskKeywords.some(k => w.includes(k))).length;

    // C. 危险请求/URL规则 (Module 1 其他规则)
    // 排除掉 "✅" 安全提示、黑名单命中和 DOM 风险，剩下的归为危险请求/特征异常
    const badRequests = warnings.filter(w => {
      // 排除安全提示
      if (w.includes("✅")) return false;
      // 排除黑名单特定提示
      if (w.includes("⚠️ 网站在黑名单中")) return false;
      // 排除 DOM 风险
      if (domRiskKeywords.some(k => w.includes(k))) return false;
      // 必须是警告
      return w.includes("⚠️");
    }).length;
    const hasWarning = warnings.some(
      (w) => typeof w === "string" && w.startsWith("⚠️")
    );

    // 缓存结果供 Popup 使用
    console.log(`[Background] Saving risks for Tab ${tabId}: score=${score} level=${riskLevel}`);
    tabRisks[tabId] = {
      score: score,
      riskLevel: riskLevel,
      blacklistHits: blacklistHits, // Module 1
      domRisks: domRisks,           // Module 3
      badRequests: badRequests,
      warnings: warnings,
      timestamp: Date.now()
    };

    // 保存到历史记录 (供 Security Center 使用)
    // 仅保存有风险的，或者你可以保存所有。这里为了不刷屏，仅保存有警告的或高危的
    if (hasWarning || riskLevel !== "low") {
      const historyItem = {
        timestamp: new Date().toISOString(),
        url: url,
        threatName: warnings.length > 0 ? warnings[0] : "潜在风险", // 取第一个警告作为标题
        threatLevel: riskLevel,
        interceptId: Math.random().toString(36).substr(2, 9).toUpperCase(),
        risks: warnings,
        advice: ["建议立即关闭页面", "不要输入任何敏感信息"]
      };

      chrome.storage.local.get(['securityHistory'], (result) => {
        const history = result.securityHistory || [];
        // 避免重复保存完全相同的记录 (简单去重: 同URL且时间间隔很短)
        // 这里简单直接unshift
        history.unshift(historyItem);
        // 限制历史记录条数，比如最近 50 条
        if (history.length > 50) history.pop();
        chrome.storage.local.set({ securityHistory: history });
      });
    }

    if (!hasWarning && riskLevel === "low") {
      // 没有明显风险特征，放行
      console.log("No high-risk warnings for", url);
      chrome.action.setBadgeText({ text: "OK", tabId: tabId });
      chrome.action.setBadgeBackgroundColor({ color: "#2ecc71", tabId: tabId });
      return;
    }

    // 设置 Badge 提示风险
    chrome.action.setBadgeText({ text: "!", tabId: tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#e74c3c", tabId: tabId });

    // 需要拦截：跳转到拦截页面
    // 用户要求：只要有警告就拦截，同时如果风险等级是 medium/high/critical 也拦截
    if (hasWarning || riskLevel === "critical" || riskLevel === "high" || riskLevel === "medium") {
      const blockedPageUrl =
        chrome.runtime.getURL("blocked/blocked.html") +
        "?url=" + encodeURIComponent(url) +
        "&reason=phishing" +
        "&threatLevel=" + encodeURIComponent(riskLevel) +
        "&timestamp=" + encodeURIComponent(new Date().toISOString()) +
        "&warnings=" + encodeURIComponent(JSON.stringify(warnings));

      console.log("Redirecting tab", tabId, "to blocked page:", blockedPageUrl);
      chrome.tabs.update(tabId, { url: blockedPageUrl });
    }

  } catch (e) {
    console.error("Error in checkAndMaybeBlock:", e);
    // 捕获到错误时，也设置一个默认的低风险状态
    tabRisks[tabId] = {
      score: 50, // 默认分数
      riskLevel: "low",
      blacklistHits: 0,
      domRisks: 0,
      badRequests: 0,
      warnings: ["内部错误: " + e.message],
      timestamp: Date.now()
    };
    chrome.action.setBadgeText({ text: "Err", tabId: tabId });
    chrome.action.setBadgeBackgroundColor({ color: "#e74c3c", tabId: tabId }); // 红色表示错误
  }
}

// 接收 content.js 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "checkUrl" && sender.tab) {
    checkAndMaybeBlock(sender.tab.id, message.url);
  }

  // 处理 Popup 请求安全状态
  if (message.type === "GET_SECURITY_STATUS") {
    // 获取当前激活 Tab 的 ID
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      if (tabs.length === 0) {
        sendResponse({ error: "No active tab" });
        return;
      }
      const currentTab = tabs[0];
      const currentTabId = currentTab.id;
      const currentTabUrl = currentTab.url;

      // 从缓存中获取数据
      let data = tabRisks[currentTabId];
      console.log(`[Background] Popup requested status for Tab ${currentTabId}. Cached:`, data ? "Yes" : "No");

      // 如果没数据（可能还没加载完，或者页面是在扩展加载前打开的）
      if (!data) {
        console.log("[Background] Cache miss. Active checking:", currentTabUrl);

        // 主动触发检测 (若 URL 合法)
        if (currentTabUrl && (currentTabUrl.startsWith("http") || currentTabUrl.startsWith("https"))) {
          checkAndMaybeBlock(currentTabId, currentTabUrl);
        } else {
          console.log("[Background] Ignored non-http URL:", currentTabUrl);
        }

        data = {
          score: 0,
          blacklistHits: 0,
          domRisks: 0,
          badRequests: 0,
          loading: true
        };
      }

      sendResponse(data);
    });

    // 返回 true 表示异步发送响应
    return true;
  }
});
