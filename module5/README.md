# 模块5：拦截页面

## 功能概述
- 显示安全拦截页面
- 向用户解释威胁详情
- 提供安全建议
- 处理用户继续访问请求

## 文件说明
- `blocked.html` - 拦截页面主文件
- `blocked.css` - 页面样式
- `blocked.js` - 拦截逻辑

## 模块1集成（必需）

### URL参数格式
模块1拦截时，重定向到此页面并传递以下参数：

**必需参数：**
blocked.html?url=被拦截的URL&reason=威胁类型&hostname=域名

**可选参数：**
- `threatLevel` - 威胁等级：critical/high/medium/low/suspicious
- `interceptId` - 拦截ID（用于追踪）
- `timestamp` - 拦截时间戳
- `source` - 数据来源
- `demo` - 演示模式标志

### 威胁类型（reason）
支持以下类型：
. `phishing` - 网络钓鱼
. `malware` - 恶意软件
. `fraud` - 欺诈网站
. `suspicious` - 可疑网站
. `blacklisted` - 黑名单命中（默认）

### 模块1示例代码
```javascript
// 在background.js中拦截时重定向
const blockedPageUrl = chrome.runtime.getURL('blocked/blocked.html') +
    '?url=' + encodeURIComponent(dangerousUrl) +
    '&reason=' + threatType +
    '&hostname=' + encodeURIComponent(hostname) +
    '&threatLevel=' + threatLevel +
    '&interceptId=' + generateInterceptId();

return { redirectUrl: blockedPageUrl };
通信接口
发送给模块6的数据
拦截页面会自动发送以下消息：

用户操作记录

window.postMessage({
    type: 'module5_user_action',
    data: {
        interceptId: '拦截ID',
        action: 'proceed_anyway' | 'report_false' | 'whitelist_request',
        timestamp: '时间戳'
    }
}, '*');
误报报告

window.postMessage({
    type: 'module5_false_report',
    data: {
        interceptId: '拦截ID',
        url: '被举报URL',
        userComment: '用户说明'
    }
}, '*');
白名单请求

window.postMessage({
    type: 'module5_whitelist_request',
    data: {
        hostname: '域名',
        interceptId: '拦截ID'
    }
}, '*');
接收来自其他模块的消息
拦截页面可以接收以下消息（可选）：

// 模块6可以发送统计数据更新
window.postMessage({
    type: 'update_stats',
    data: { /* 统计数据 */ }
}, '*');
测试方法
1. 直接测试

blocked.html?demo=true
2. 完整测试

blocked.html?url=https://phishing-site.com&reason=phishing&threatLevel=critical&hostname=phishing-site.com&demo=true
3. 所有威胁类型测试
网络钓鱼：reason=phishing

恶意软件：reason=malware

欺诈网站：reason=fraud

可疑网站：reason=suspicious

黑名单命中：reason=blacklisted

自定义配置
修改威胁类型配置
编辑blocked.js中的CONFIG.threatTypes对象。

修改样式
编辑blocked.css文件，或通过CSS变量覆盖：


:root {
    --color-critical: #e74c3c;
    --color-high: #f39c12;
    --color-medium: #f1c40f;
    --color-low: #3498db;
}
注意事项
本模块专注于拦截功能，不包含评分显示（模块4）和历史记录（模块6）

所有用户操作都会通过postMessage发送，供模块6记录

演示模式下不会实际重定向到危险网站

实际使用中需要模块1正确传递URL参数

快速集成检查清单
模块1正确重定向到blocked.html

传递必需的URL参数（url、reason、hostname）

测试不同威胁类型的显示效果

验证用户操作记录发送到模块6

测试响应式布局

验证打印样式



### 数据持久化（新增）
拦截页面会自动将拦截记录保存到 `chrome.storage.local` 的 `securityHistory` 字段中，供模块 6 安全中心读取。
- **存储时机**：页面初始化完成后。
- **存储格式**：完整的透明报告对象。
- **存储限制**：最近 100 条记录。

## **模块1同学需要做的全部工作：**

```javascript
// 1. 在manifest.json中添加web_accessible_resources
"web_accessible_resources": [{
  "resources": ["blocked/blocked.html", "blocked/blocked.css", "blocked/blocked.js"],
  "matches": ["<all_urls>"]
}],

// 2. 在background.js中拦截时重定向
chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    // 检测到恶意URL时...
    const threatType = classifyThreat(details.url); // 你的分类逻辑
    const hostname = new URL(details.url).hostname;
    
    // 构建拦截页面URL
    const blockedPageUrl = chrome.runtime.getURL('blocked/blocked.html') +
      '?url=' + encodeURIComponent(details.url) +
      '&reason=' + threatType +
      '&hostname=' + encodeURIComponent(hostname) +
      '&threatLevel=' + getThreatLevel(threatType) + // 你的威胁等级逻辑
      '&interceptId=' + generateInterceptId() +
      '&timestamp=' + new Date().toISOString();
    
    // 重定向到拦截页面
    return { redirectUrl: blockedPageUrl };
  },
  { urls: ["<all_urls>"] },
  ["blocking"]
);