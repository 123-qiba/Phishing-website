// content.js
// 在每个页面加载时执行：把当前URL发给后台，由后台去调用 Flask 接口

(function () {
  try {
    const currentUrl = window.location.href;

    // 避免在扩展自己的页面上再次检测
    if (currentUrl.startsWith("chrome-extension://")) {
      return;
    }

    // 只负责把URL发给后台，不在网页环境里直接 fetch
    chrome.runtime.sendMessage({
      type: "checkUrl",
      url: currentUrl
    });
  } catch (e) {
    console.error("Error in content script:", e);
  }
})();
