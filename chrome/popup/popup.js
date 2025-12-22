let chart = null;

document.addEventListener("DOMContentLoaded", () => {
  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) refreshBtn.addEventListener("click", loadData);

  const openSecurityCenterBtn = document.getElementById("openSecurityCenterBtn");
  if (openSecurityCenterBtn) {
    openSecurityCenterBtn.addEventListener("click", () => {
      if (chrome.runtime.openOptionsPage) {
        chrome.runtime.openOptionsPage();
      } else {
        window.open(chrome.runtime.getURL('security_center/pages/security_center.html'));
      }
    });
  }

  loadData();
});

function loadData() {
  // 1) 显示当前 URL（可选）
  chrome.tabs?.query({ active: true, currentWindow: true }, ([tab]) => {
    const url = tab?.url || "-";
    const urlEl = document.getElementById("currentUrl");
    if (urlEl) urlEl.textContent = `URL：${url}`;
  });

  // 2) 从 background 拉数据
  chrome.runtime.sendMessage({ type: "GET_SECURITY_STATUS" }, (data) => {
    // 错误处理
    if (chrome.runtime.lastError) {
      console.warn(chrome.runtime.lastError);
      return;
    }

    // 若通道失败或无数据
    if (!data) data = { score: '-', blacklistHits: '-', domRisks: '-', badRequests: '-' };

    if (data.loading) {
      renderLoading();
      // 若正在加载，则 1 秒后重试
      setTimeout(loadData, 1000);
    } else {
      renderGrade(data);
      renderStats(data);
      renderChart(data);
    }
    renderUpdatedAt();
  });
}

function renderLoading() {
  const gradeEl = document.getElementById("grade");
  const scoreEl = document.getElementById("score");
  const badgeEl = document.getElementById("badge");

  if (gradeEl) gradeEl.textContent = "...";
  if (scoreEl) scoreEl.textContent = "分析中...";
  if (badgeEl) badgeEl.textContent = "Wait";
}

function renderGrade(data) {
  const { score: scoreRaw, riskLevel } = data;

  if (scoreRaw === '-' || scoreRaw === undefined) {
    renderLoading();
    return;
  }

  const gradeEl = document.getElementById("grade");
  const scoreEl = document.getElementById("score");
  const badgeEl = document.getElementById("badge");

  let text = "未知";
  let color = "#95a5a6";
  let badgeText = "Unknown";

  // Use riskLevel if available (preferred)
  if (riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'critical':
        text = "严重";
        color = "#c0392b";
        badgeText = "CRITICAL";
        break;
      case 'high':
        text = "高危";
        color = "#e74c3c";
        badgeText = "HIGH";
        break;
      case 'medium':
        text = "中风险";
        color = "#f1c40f";
        badgeText = "MEDIUM";
        break;
      case 'low':
      case 'safe':
        text = "安全";
        color = "#2ecc71";
        badgeText = "SAFE";
        break;
      default:
        text = "未知";
    }
  } else {
    // Fallback to score logic if riskLevel missing
    const score = Number(scoreRaw || 0);
    if (score >= 90) { text = "安全"; color = "#2ecc71"; badgeText = "SAFE"; }
    else if (score >= 75) { text = "低风险"; color = "#3498db"; badgeText = "LOW"; }
    else if (score >= 60) { text = "中风险"; color = "#f1c40f"; badgeText = "MEDIUM"; }
    else { text = "高危"; color = "#e74c3c"; badgeText = "HIGH"; }
  }

  if (gradeEl) {
    gradeEl.textContent = text;
    gradeEl.style.color = color;
    gradeEl.style.fontSize = "32px"; // Adjust for Chinese text width
  }

  // 完全隐藏具体的 Score 显示
  if (scoreEl) {
    scoreEl.style.display = "none";
  }

  if (badgeEl) {
    badgeEl.textContent = badgeText;
    badgeEl.style.backgroundColor = color;
    badgeEl.style.color = "white";
  }
}

function renderStats(data) {
  setText("blacklistCount", data.blacklistHits);
  setText("domCount", data.domRisks);
  setText("requestCount", data.badRequests);

  // 渲染详细警告列表
  renderWarnings(data.warnings);
}

function renderWarnings(warnings) {
  const box = document.getElementById("warningBox");
  const list = document.getElementById("warningList");

  if (!box || !list) return;

  // 清空现有的
  list.innerHTML = "";

  // 筛选出具体的风险警告 (排除安全提示 '✅')
  const risks = (warnings || []).filter(w => w.includes("⚠️") || w.includes("Warning") || w.includes("Error"));

  if (risks.length > 0) {
    box.style.display = "block";
    risks.forEach(w => {
      const li = document.createElement("li");
      // 移除可能存在的 ⚠️ 符号，避免重复显示
      li.textContent = w.replace(/⚠️/g, '').trim();
      list.appendChild(li);
    });
  } else {
    box.style.display = "none";
  }
}

function renderChart(data) {
  const canvas = document.getElementById("riskChart");
  if (!canvas) return;

  if (typeof Chart === "undefined") {
    // Chart.js 未加载（路径/顺序问题）
    const hint = document.getElementById("chartHint");
    if (hint) hint.textContent = "Chart.js 未加载：请检查 chart.min.js 引入顺序/路径";
    return;
  }

  const ctx = canvas.getContext("2d");

  // 重新绘制前先销毁旧图，避免重复声明/叠图
  if (chart) chart.destroy();

  // Safe parsing
  const d_blacklist = Number(data.blacklistHits) || 0;
  const d_dom = Number(data.domRisks) || 0;
  const d_req = Number(data.badRequests) || 0;

  // 如果全是 0，给一个默认的“安全”饼图
  let chartData = [d_blacklist, d_dom, d_req];
  let chartColors = ['#e74c3c', '#e67e22', '#f1c40f'];
  let chartLabels = ["黑名单", "DOM 风险", "请求风险"];

  if (d_blacklist === 0 && d_dom === 0 && d_req === 0) {
    chartData = [1];
    chartColors = ['#2ecc71']; // Green
    chartLabels = ["安全"];
  }

  chart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: chartLabels,
      datasets: [{
        data: chartData,
        backgroundColor: chartColors
      }]
    },
    options: {
      plugins: { legend: { position: "bottom" } }
    }
  });
}

function renderUpdatedAt() {
  const el = document.getElementById("updatedAt");
  if (!el) return;
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  const ss = String(now.getSeconds()).padStart(2, "0");
  el.textContent = `更新时间：${hh}:${mm}:${ss}`;
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = (val ?? 0);
}
