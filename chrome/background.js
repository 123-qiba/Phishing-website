// background.js

// 后台函数：调用本地 Flask 接口并根据结果决定是否拦截
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

    // 只要有以“⚠️”开头的警告，就认为需要拦截
    const hasWarning = warnings.some(
      (w) => typeof w === "string" && w.startsWith("⚠️")
    );

    if (!hasWarning) {
      // 没有明显风险特征，放行
      console.log("No high-risk warnings for", url);
      return;
    }

    // 需要拦截：跳转到拦截页面
    const blockedPageUrl =
      chrome.runtime.getURL("blocked/blocked.html") +
      "?url=" + encodeURIComponent(url) +
      "&reason=phishing" +
      "&threatLevel=" + encodeURIComponent(riskLevel) +
      "&timestamp=" + encodeURIComponent(new Date().toISOString()) +
      "&warnings=" + encodeURIComponent(JSON.stringify(warnings));

    console.log("Redirecting tab", tabId, "to blocked page:", blockedPageUrl);

    chrome.tabs.update(tabId, { url: blockedPageUrl });
  } catch (e) {
    console.error("Error in checkAndMaybeBlock:", e);
  }
}

// 接收 content.js 的消息
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "checkUrl" && sender.tab) {
    checkAndMaybeBlock(sender.tab.id, message.url);
  }
});
