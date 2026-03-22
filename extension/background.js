/**
 * Algorithm Circuit Breaker v3.0 - Background Bridge
 * ===================================================
 * Service Worker that proxies HTTP requests to bypass Mixed Content.
 * Content scripts send messages here, we fetch from localhost.
 *
 * Response shape from /analyze (forwarded to content.js):
 *   { risk_index, pid_output, velocity, toxicity, status, intervention,
 *     session_time, request_count }
 *
 * content.js uses risk_index directly for Mindful Friction:
 *   - risk_index > 0.6 → proportional desaturation
 *   - risk_index > 0.8 → scroll throttling
 */

const API_BASE = 'http://127.0.0.1:5000';

// ============================================================
// MESSAGE LISTENER - The Bridge
// ============================================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

    // Handle SEND_METRICS from content.js
    if (message.type === 'SEND_METRICS') {
        console.log('[CB Bridge] Received metrics:', message.payload);

        fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(message.payload)
        })
            .then(response => {
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                return response.json();
            })
            .then(data => {
                console.log('[CB Bridge] Server response:', data);
                sendResponse({ success: true, data: data });
            })
            .catch(error => {
                console.error('[CB Bridge] Fetch error:', error.message);
                sendResponse({ success: false, error: error.message });
            });

        // Return true to keep the message channel open for async response
        return true;
    }

    // Handle REALTIME polling
    if (message.type === 'GET_REALTIME') {
        fetch(`${API_BASE}/realtime`)
            .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
            .then(data => sendResponse({ success: true, data }))
            .catch(err => sendResponse({ success: false, error: String(err) }));
        return true;
    }

    // Handle RESET
    if (message.type === 'RESET_SESSION') {
        fetch(`${API_BASE}/reset`, { method: 'POST' })
            .then(r => r.json())
            .then(data => sendResponse({ success: true, data }))
            .catch(err => sendResponse({ success: false, error: String(err) }));
        return true;
    }

    // Handle HEALTH check
    if (message.type === 'HEALTH_CHECK') {
        fetch(`${API_BASE}/health`)
            .then(r => r.json())
            .then(data => sendResponse({ success: true, data }))
            .catch(err => sendResponse({ success: false, error: String(err) }));
        return true;
    }
});

// ============================================================
// LIFECYCLE
// ============================================================
chrome.runtime.onInstalled.addListener((details) => {
    console.log('[CB Bridge] Installed:', details.reason);
    chrome.storage.local.set({ enabled: true, uiMode: 'HUD' });
});

// Startup health check
(async () => {
    try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        console.log('[CB Bridge] Server status:', data.status);
    } catch (e) {
        console.warn('[CB Bridge] Server offline - run: python server.py');
    }
})();

console.log('[CB Bridge] Service worker loaded - ready to proxy requests');
