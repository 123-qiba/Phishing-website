let chart = null;

document.addEventListener("DOMContentLoaded", () => {
  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) refreshBtn.addEventListener("click", loadData);
  loadData();
});

function loadData() {
  // 1) 显示当前 URL（可选）
  chrome.tabs?.query({ active: true, currentWindow: true }, ([tab]) => {
    const url = tab?.url || "-";
    const urlEl = document.getElementById("currentUrl");
    if (urlEl) urlEl.textContent = `URL：${url}`;
  });

  // 2) 从 background 拉数据（你现在用 mock 也行）
  chrome.runtime.sendMessage({ type: "GET_SECURITY_STATUS" }, (data) => {
    // 若通道失败，给兜底，避免 Score: --
    if (!data) data = { score: 0, blacklistHits: 0, domRisks: 0, badRequests: 0 };

    renderGrade(data.score);
    renderStats(data);
    renderChart(data);
    renderUpdatedAt();
  });
}

function renderGrade(scoreRaw) {
  const score = Number(scoreRaw || 0);

  const gradeEl = document.getElementById("grade");
  const scoreEl = document.getElementById("score");
  const badgeEl = document.getElementById("badge");

  let grade = "F", label = "高风险";
  if (score >= 90) { grade = "A"; label = "非常安全"; }
  else if (score >= 75) { grade = "B"; label = "较安全"; }
  else if (score >= 60) { grade = "C"; label = "一般"; }
  else if (score >= 40) { grade = "D"; label = "偏风险"; }

  if (gradeEl) gradeEl.textContent = grade;
  if (scoreEl) scoreEl.textContent = `Score: ${score}`;
  if (badgeEl) badgeEl.textContent = label;
}

function renderStats(data) {
  setText("blacklistCount", data.blacklistHits);
  setText("domCount", data.domRisks);
  setText("requestCount", data.badRequests);
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

  chart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: ["黑名单", "DOM 风险", "请求风险"],
      datasets: [{
        data: [
          Number(data.blacklistHits || 0),
          Number(data.domRisks || 0),
          Number(data.badRequests || 0)
        ]
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
