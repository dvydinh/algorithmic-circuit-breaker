/**
 * Algorithm Circuit Breaker - Live Bio-Feedback Dashboard
 * ========================================================
 * Real-time HUD polling server every 500ms with smooth animations.
 */

const API_BASE = 'http://127.0.0.1:5000';
const POLL_INTERVAL = 500; // 500ms for smooth updates

// ============================================================
// DOM ELEMENTS
// ============================================================
const elements = {
    // Header
    pulseDot: document.getElementById('pulseDot'),
    headerText: document.getElementById('headerText'),

    // Gauge
    gaugeFill: document.getElementById('gaugeFill'),
    gaugeNeedle: document.getElementById('gaugeNeedle'),
    toxicityValue: document.getElementById('toxicityValue'),

    // Risk
    riskValue: document.getElementById('riskValue'),
    riskFill: document.getElementById('riskFill'),

    // Stats
    velocityValue: document.getElementById('velocityValue'),
    sessionTime: document.getElementById('sessionTime'),

    // Secondary metrics
    statusValue: document.getElementById('statusValue'),
    actionValue: document.getElementById('actionValue'),

    // Overlays
    flashOverlay: document.getElementById('flashOverlay'),
    offlineOverlay: document.getElementById('offlineOverlay'),

    // Buttons
    refreshBtn: document.getElementById('refreshBtn'),
    resetBtn: document.getElementById('resetBtn')
};

// ============================================================
// UPDATE FUNCTIONS
// ============================================================

function updateHeader(status) {
    const dot = elements.pulseDot;
    const text = elements.headerText;

    // Reset classes
    dot.classList.remove('warning', 'danger');
    text.classList.remove('warning', 'danger');

    switch (status) {
        case 'BREAK_ACTIVE':
            dot.classList.add('danger');
            text.classList.add('danger');
            text.textContent = 'MONITOR: OVERRIDE';
            break;
        case 'WARNING':
        case 'HIGH_RISK':
            dot.classList.add('warning');
            text.classList.add('warning');
            text.textContent = 'MONITOR: WARNING';
            break;
        case 'ELEVATED':
            dot.classList.add('warning');
            text.textContent = 'MONITOR: ELEVATED';
            break;
        default:
            text.textContent = 'MONITOR: CONNECTED';
    }
}

function updateToxicityGauge(toxicity) {
    // toxicity is 0-1, convert to percentage
    const percentage = Math.round(toxicity * 100);

    // Update needle rotation (-90 to 90 degrees for semi-circle)
    const needleAngle = -90 + (toxicity * 180);
    elements.gaugeNeedle.style.setProperty('--needle-angle', `${needleAngle}deg`);

    // Update fill angle (0 to 180 degrees)
    const fillAngle = toxicity * 180;
    elements.gaugeFill.style.setProperty('--fill-angle', `${fillAngle}deg`);

    // Update text
    elements.toxicityValue.textContent = percentage;

    // Update color based on level
    if (toxicity > 0.8) {
        elements.toxicityValue.style.color = 'var(--neon-red)';
        elements.toxicityValue.style.textShadow = '0 0 20px var(--neon-red)';
    } else if (toxicity > 0.6) {
        elements.toxicityValue.style.color = 'var(--neon-orange)';
        elements.toxicityValue.style.textShadow = '0 0 20px var(--neon-orange)';
    } else if (toxicity > 0.4) {
        elements.toxicityValue.style.color = 'var(--neon-yellow)';
        elements.toxicityValue.style.textShadow = '0 0 20px var(--neon-yellow)';
    } else {
        elements.toxicityValue.style.color = 'var(--neon-cyan)';
        elements.toxicityValue.style.textShadow = '0 0 20px var(--neon-cyan)';
    }
}

function updateRiskBar(risk) {
    const percentage = Math.min(risk * 100, 100);
    const fill = elements.riskFill;

    // Update width
    fill.style.width = `${percentage}%`;

    // Update value text
    elements.riskValue.textContent = risk.toFixed(3);

    // Update color classes
    fill.classList.remove('safe', 'warning', 'danger', 'critical');

    if (risk > 0.8) {
        fill.classList.add('critical');
        elements.riskValue.style.color = 'var(--neon-red)';
        // Flash the background!
        elements.flashOverlay.classList.add('active');
    } else if (risk > 0.5) {
        fill.classList.add('danger');
        elements.riskValue.style.color = 'var(--neon-orange)';
        elements.flashOverlay.classList.remove('active');
    } else if (risk > 0.25) {
        fill.classList.add('warning');
        elements.riskValue.style.color = 'var(--neon-yellow)';
        elements.flashOverlay.classList.remove('active');
    } else {
        fill.classList.add('safe');
        elements.riskValue.style.color = 'var(--neon-green)';
        elements.flashOverlay.classList.remove('active');
    }
}

function updateStats(data) {
    // Velocity (pixels/sec, show in K if > 1000)
    const vel = data.velocity || 0;
    if (vel > 1000) {
        elements.velocityValue.textContent = (vel / 1000).toFixed(1) + 'K';
    } else {
        elements.velocityValue.textContent = Math.round(vel);
    }

    // Session time (convert seconds to mm:ss)
    const totalSeconds = Math.floor(data.session_duration || 0);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    elements.sessionTime.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;

    // Secondary metrics
    elements.statusValue.textContent = data.status || 'SAFE';
    elements.actionValue.textContent = data.intervention || 'NONE';

    // Color based on status
    if ((data.status || 'SAFE').includes('RISK') || (data.status || 'SAFE').includes('WARNING') || (data.status || 'SAFE').includes('BREAK')) {
        elements.statusValue.style.color = 'var(--neon-red)';
    } else if ((data.status || '').includes('ELEVATED')) {
        elements.statusValue.style.color = 'var(--neon-yellow)';
    } else {
        elements.statusValue.style.color = 'var(--neon-green)';
    }

    // Color based on action
    if ((data.intervention || 'NONE') !== 'NONE') {
        elements.actionValue.style.color = 'var(--neon-red)';
    } else {
        elements.actionValue.style.color = 'var(--neon-green)';
    }
}

function setServerOnline(online) {
    if (online) {
        elements.offlineOverlay.classList.remove('active');
    } else {
        elements.offlineOverlay.classList.add('active');
        elements.flashOverlay.classList.remove('active');
    }
}

// ============================================================
// API COMMUNICATION
// ============================================================

async function fetchRealtimeData() {
    try {
        const response = await fetch(`${API_BASE}/realtime`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Update all UI elements
        setServerOnline(true);
        updateHeader(data.status);
        updateToxicityGauge(data.toxicity || 0.0);
        updateRiskBar(data.risk_index);
        updateStats(data);

    } catch (error) {
        console.error('Connection error:', error);
        setServerOnline(false);
    }
}

async function resetSession() {
    try {
        const response = await fetch(`${API_BASE}/reset`, { method: 'POST' });

        if (response.ok) {
            // Visual feedback
            elements.resetBtn.textContent = '✓ DONE';
            elements.resetBtn.style.borderColor = 'var(--neon-green)';
            elements.resetBtn.style.color = 'var(--neon-green)';

            setTimeout(() => {
                elements.resetBtn.textContent = '⟲ Reset';
                elements.resetBtn.style.borderColor = '';
                elements.resetBtn.style.color = '';
            }, 800);

            await fetchRealtimeData();
        }
    } catch (error) {
        console.error('Reset failed:', error);
    }
}

// ============================================================
// EVENT LISTENERS
// ============================================================

elements.refreshBtn.addEventListener('click', () => {
    elements.refreshBtn.textContent = '...';
    fetchRealtimeData().then(() => {
        elements.refreshBtn.textContent = '↻ Refresh';
    });
});

elements.resetBtn.addEventListener('click', resetSession);

// ============================================================
// INITIALIZATION
// ============================================================

// Initial fetch
fetchRealtimeData();

// Poll every 500ms for smooth real-time updates
setInterval(fetchRealtimeData, POLL_INTERVAL);

console.log('[Neural Link HUD] Initialized - polling every 500ms');
