chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "GET_SECURITY_STATUS") {
    sendResponse({
      score: 72,
      blacklistHits: 1,
      domRisks: 2,
      badRequests: 3
    });
  }
});
