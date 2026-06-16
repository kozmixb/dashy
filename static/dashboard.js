const refreshIntervalMs = 30000;
let refreshEnabled = true;
let refreshTimer = null;
let lastRefreshedAt = null;

function formatRefreshTime(date) {
    return date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });
}

function syncLastRefreshedAt() {
    const timestamp = document.getElementById("last-refreshed-at");
    if (!timestamp || !lastRefreshedAt) {
        return;
    }

    timestamp.textContent = formatRefreshTime(lastRefreshedAt);
}

function syncRefreshToggle() {
    const toggle = document.getElementById("refresh-toggle");
    if (!toggle) {
        return;
    }

    toggle.checked = refreshEnabled;
}

function syncHeaderControls() {
    syncRefreshToggle();
    syncLastRefreshedAt();
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

document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.detail.target.id !== "stats") {
        return;
    }

    lastRefreshedAt = new Date();
    syncHeaderControls();
});

refreshStats();
scheduleRefresh();
