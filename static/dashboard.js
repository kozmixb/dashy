const refreshIntervalMs = 30000;
let refreshEnabled = true;
let refreshTimer = null;

function syncRefreshToggle() {
    const toggle = document.getElementById("refresh-toggle");
    if (!toggle) {
        return;
    }

    toggle.checked = refreshEnabled;
}

function refreshStats() {
    htmx.ajax("GET", "/stats", {
        target: "#stats",
        swap: "innerHTML",
    });
}

function scheduleRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }

    if (refreshEnabled) {
        refreshTimer = setInterval(refreshStats, refreshIntervalMs);
    }
}

document.addEventListener("change", (event) => {
    if (event.target.id !== "refresh-toggle") {
        return;
    }

    refreshEnabled = event.target.checked;
    if (refreshEnabled) {
        refreshStats();
    }
    scheduleRefresh();
});

document.body.addEventListener("htmx:afterSwap", syncRefreshToggle);

refreshStats();
scheduleRefresh();
