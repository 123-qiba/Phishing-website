document.addEventListener('DOMContentLoaded', function () {
    const openDashboardBtn = document.getElementById('open-dashboard');

    if (openDashboardBtn) {
        openDashboardBtn.addEventListener('click', function () {
            chrome.tabs.create({
                url: chrome.runtime.getURL('pages/security_center.html')
            });
        });
    }
});
