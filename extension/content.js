/**
 * Algorithm Circuit Breaker v2.2 - Content Script
 * ================================================
 * Dual-Mode UI: HUD (Floating) + SIDEBAR (Matrix Terminal)
 * FIXED: Background Bridge for Mixed Content
 */

// ============================================================
// CONFIG
// ============================================================
const CONFIG = {
    // Communication & Processing
    SEND_INTERVAL: 2000,           // Ms between sending data to backend
    SCROLL_SAMPLE_MS: 50,          // Ms between scroll position sampling
    VELOCITY_WINDOW: 2000,         // Ms window to calculate average velocity
    DEBUG: true,

    // Toxicity Calculation Weights
    TOXICITY_BASE_MULTIPLIER: 0.1, // Points per toxic word found
    TOXICITY_MAX_BASE: 0.6,        // Maximum local score before context penalties
    TOXICITY_SOCIAL_PENALTY: 0.2,  // Extra penalty for social media sites
    TOXICITY_SCROLL_PENALTY: 0.2,  // Extra penalty for infinite scroll pages

    // Interventions
    BREAK_DURATION_SEC: 10         // Seconds to pause during Circuit Breaker
};

// ============================================================
// STATE
// ============================================================
const state = {
    uiMode: 'HUD',
    hudPosition: { x: 20, y: 20 },
    isDragging: false,
    dragOffset: { x: 0, y: 0 },
    lastScrollY: window.scrollY,
    lastScrollTime: Date.now(),
    velocitySamples: [],
    sessionStart: Date.now(),
    isBreakActive: false,
    serverOnline: false,
    lastData: { risk_index: 0, velocity: 0, status: 'SAFE' }
};

const TOXICITY_DICTIONARY = ['fuck', 'suck', 'ass', 'shit', 'faggot', 'fucking', 'die', 'bitch', 'nigger', 'sucks', 'cunt', 'wikipedia', 'cock', 'fucksex', 'yourselfgo', 'dick', 'fucker', 'kill', 'asshole', 'cocksucker', 'piece', 'penis', 'mothjer', 'bastard', 'gay', 'eat', 'bitches', 'huge', 'shut', 'fat', 'damn', 'rape', 'dog', 'stupid', 'offfuck', 'mexicans', 'anal', 'pro', 'hanibal', 'assad', 'like', 'niggas', 'dickhead', 'pussy', 'get', 'idiot', 'block', 'bush', 'wiki', 'criminalwar', 'bunksteve', 'going', 'cocksucking', 'small', 'chester', 'marcolfuck', 'want', 'mother', 'cocks', 'fack', 'useless', 'homeland', 'notrhbysouthbanof', 'securityfuck', 'page', 'hate', 'whore', 'bot', 'admins', 'veggietales', 'jewish', 'ancestryfuck', 'cunts', 'moron', 'loves', 'shitfuck', 'anthony', 'bradbury', 'atheist', 'fuckin', 'must', 'person', 'fired', 'life', 'keep', 'jim', 'people', 'wales', 'know', 'talk', 'big', 'drink', 'bleachanhero', 'god', 'lick', 'bitchmattythewhite', 'thanks', 'hell', 'edits', 'user', 'haahhahahah', 'yaaa', 'yaaaa', 'nice', 'loser', 'nigga', 'come', 'arse', 'dirty', 'mum', 'takes', 'ban', 'work', 'give', 'right', 'said', 'little', 'ers', 'post', 'still', 'murder', 'real', 'removing', 'itsuck', 'homo', 'communism', 'information', 'eats', 'computer', 'fffff', 'rvv', 'uuuuuu', 'cccccc', 'kkkkkk', 'edit', 'blank', 'stop', 'edie', 'vandalism', 'take', 'king', 'nhrhs', 'shithead', 'mitt', 'romney', 'hey', 'yet', 'reading', 'warning', 'one'];

const log = (msg) => CONFIG.DEBUG && console.log(`[CB v2.2] ${msg}`);

// ============================================================
// STYLES - Cyberpunk HUD + Matrix Sidebar
// ============================================================
function injectStyles() {
    if (document.getElementById('cb-styles')) return;

    const css = document.createElement('style');
    css.id = 'cb-styles';
    css.textContent = `
        :root {
            --cb-cyan: #00ffff;
            --cb-green: #00ff41;
            --cb-yellow: #ffff00;
            --cb-orange: #ff6600;
            --cb-red: #ff0040;
            --cb-pink: #ff00ff;
            --cb-bg: rgba(0, 8, 12, 0.97);
            --cb-ease: cubic-bezier(0.25, 0.46, 0.45, 0.94);
        }
        
        .cb-widget {
            font-family: 'Consolas', 'Courier New', monospace !important;
            color: #fff !important;
            z-index: 2147483647 !important;
            pointer-events: auto !important;
        }
        .cb-widget * {
            box-sizing: border-box !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* ===== HUD MODE (Floating Box) ===== */
        .cb-hud {
            position: fixed !important;
            width: 260px !important;
            background: var(--cb-bg) !important;
            border: 1px solid var(--cb-cyan) !important;
            border-radius: 8px !important;
            box-shadow: 0 0 30px rgba(0,255,255,0.35), inset 0 0 50px rgba(0,255,255,0.03) !important;
            overflow: hidden !important;
            transition: opacity 0.4s, transform 0.4s !important;
            opacity: 0 !important;
            transform: scale(0.92) !important;
        }
        .cb-hud.show { opacity: 1 !important; transform: scale(1) !important; }
        
        .cb-hdr {
            display: flex !important;
            align-items: center !important;
            justify-content: space-between !important;
            padding: 10px 12px !important;
            background: linear-gradient(90deg, rgba(0,255,255,0.12), transparent) !important;
            border-bottom: 1px solid rgba(0,255,255,0.25) !important;
            cursor: grab !important;
            user-select: none !important;
        }
        .cb-hdr:active { cursor: grabbing !important; }
        
        .cb-title {
            display: flex !important;
            align-items: center !important;
            gap: 8px !important;
            font-size: 11px !important;
            font-weight: 600 !important;
            letter-spacing: 1.5px !important;
            color: var(--cb-cyan) !important;
            text-shadow: 0 0 12px var(--cb-cyan) !important;
        }
        
        .cb-dot {
            width: 8px !important;
            height: 8px !important;
            border-radius: 50% !important;
            background: var(--cb-green) !important;
            box-shadow: 0 0 10px var(--cb-green) !important;
            animation: cb-blink 1.5s infinite !important;
        }
        .cb-dot.warn { background: var(--cb-yellow) !important; box-shadow: 0 0 10px var(--cb-yellow) !important; }
        .cb-dot.crit { background: var(--cb-red) !important; box-shadow: 0 0 10px var(--cb-red) !important; animation: cb-blink-fast 0.35s infinite !important; }
        
        @keyframes cb-blink { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(0.8)} }
        @keyframes cb-blink-fast { 0%,100%{opacity:1} 50%{opacity:0.2} }
        
        .cb-btn {
            background: transparent !important;
            border: 1px solid rgba(255,255,255,0.25) !important;
            color: rgba(255,255,255,0.6) !important;
            font-size: 9px !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
            cursor: pointer !important;
            transition: all 0.2s !important;
            font-family: inherit !important;
        }
        .cb-btn:hover { border-color: var(--cb-cyan) !important; color: var(--cb-cyan) !important; }
        
        .cb-body { padding: 12px !important; }
        
        /* Gauge */
        .cb-gauge-box { text-align: center !important; margin-bottom: 12px !important; }
        .cb-gauge-lbl { font-size: 9px !important; color: rgba(255,255,255,0.5) !important; letter-spacing: 1px !important; margin-bottom: 6px !important; }
        
        .cb-gauge {
            position: relative !important;
            width: 130px !important;
            height: 68px !important;
            margin: 0 auto !important;
        }
        .cb-gauge-bg {
            position: absolute !important;
            width: 130px !important;
            height: 65px !important;
            border-radius: 130px 130px 0 0 !important;
            background: linear-gradient(90deg, var(--cb-green), var(--cb-yellow), var(--cb-red)) !important;
            opacity: 0.12 !important;
        }
        .cb-gauge-fill {
            position: absolute !important;
            width: 130px !important;
            height: 65px !important;
            border-radius: 130px 130px 0 0 !important;
            background: conic-gradient(from 180deg at 50% 100%, var(--cb-cyan), var(--cb-pink) var(--angle, 0deg), transparent var(--angle, 0deg)) !important;
            transition: --angle 0.25s !important;
        }
        .cb-gauge-mask {
            position: absolute !important;
            bottom: 0 !important;
            left: 12px !important;
            width: 106px !important;
            height: 53px !important;
            background: var(--cb-bg) !important;
            border-radius: 106px 106px 0 0 !important;
        }
        .cb-gauge-val {
            position: absolute !important;
            bottom: 4px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            font-size: 22px !important;
            font-weight: 700 !important;
            color: var(--cb-cyan) !important;
            text-shadow: 0 0 15px var(--cb-cyan) !important;
        }
        .cb-gauge-val span { font-size: 10px !important; opacity: 0.65 !important; }
        
        /* Risk Bar */
        .cb-risk { margin-bottom: 12px !important; }
        .cb-risk-hdr { display: flex !important; justify-content: space-between !important; margin-bottom: 5px !important; }
        .cb-risk-lbl { font-size: 9px !important; color: rgba(255,255,255,0.5) !important; letter-spacing: 1px !important; }
        .cb-risk-val { font-size: 12px !important; font-weight: 600 !important; }
        .cb-risk-bar { height: 12px !important; background: rgba(255,255,255,0.08) !important; border-radius: 2px !important; overflow: hidden !important; }
        .cb-risk-fill {
            height: 100% !important;
            width: 0% !important;
            background: linear-gradient(90deg, var(--cb-green), var(--cb-cyan)) !important;
            box-shadow: inset 0 0 12px var(--cb-green) !important;
            transition: all 0.25s !important;
        }
        .cb-risk-fill.warn { background: linear-gradient(90deg, var(--cb-yellow), var(--cb-orange)) !important; }
        .cb-risk-fill.danger { background: linear-gradient(90deg, var(--cb-orange), var(--cb-red)) !important; }
        .cb-risk-fill.crit { background: linear-gradient(90deg, var(--cb-red), var(--cb-pink)) !important; animation: cb-bar-pulse 0.4s infinite !important; }
        @keyframes cb-bar-pulse { 0%,100%{opacity:1} 50%{opacity:0.55} }
        
        /* Stats Grid */
        .cb-stats { display: grid !important; grid-template-columns: repeat(3, 1fr) !important; gap: 6px !important; }
        .cb-stat {
            text-align: center !important;
            padding: 8px 4px !important;
            background: rgba(0,255,255,0.04) !important;
            border: 1px solid rgba(0,255,255,0.08) !important;
            border-radius: 4px !important;
        }
        .cb-stat-val { font-size: 15px !important; font-weight: 700 !important; color: var(--cb-cyan) !important; text-shadow: 0 0 8px var(--cb-cyan) !important; }
        .cb-stat-lbl { font-size: 8px !important; color: rgba(255,255,255,0.4) !important; text-transform: uppercase !important; margin-top: 2px !important; }
        
        /* ===== SIDEBAR MODE (Matrix Terminal) ===== */
        .cb-sidebar {
            position: fixed !important;
            left: 0 !important;
            top: 0 !important;
            height: 100vh !important;
            width: 4px !important;
            background: var(--cb-green) !important;
            box-shadow: 0 0 8px var(--cb-green), 0 0 20px rgba(0,255,65,0.4) !important;
            transition: width 0.3s var(--cb-ease), background 0.3s, box-shadow 0.3s !important;
            overflow: hidden !important;
            cursor: pointer !important;
            opacity: 0 !important;
            border-radius: 0 !important;
        }
        .cb-sidebar.show { opacity: 1 !important; }
        
        .cb-sidebar:hover,
        .cb-sidebar.open {
            width: 200px !important;
            background: rgba(0, 0, 0, 0.95) !important;
            box-shadow: 0 0 15px rgba(0,255,65,0.3) !important;
            border-right: 1px solid var(--cb-green) !important;
        }
        
        /* Collapsed State - Vertical Text */
        .cb-sidebar-line {
            position: absolute !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) rotate(-90deg) !important;
            white-space: nowrap !important;
            font-size: 8px !important;
            font-weight: 700 !important;
            letter-spacing: 2px !important;
            color: #000 !important;
            text-shadow: none !important;
            opacity: 1 !important;
            transition: opacity 0.2s !important;
        }
        .cb-sidebar:hover .cb-sidebar-line,
        .cb-sidebar.open .cb-sidebar-line { opacity: 0 !important; }
        
        /* Expanded State - Terminal Content */
        .cb-terminal {
            padding: 12px 10px !important;
            opacity: 0 !important;
            transition: opacity 0.2s 0.1s !important;
            font-size: 11px !important;
            line-height: 1.6 !important;
        }
        .cb-sidebar:hover .cb-terminal,
        .cb-sidebar.open .cb-terminal { opacity: 1 !important; }
        
        /* Terminal Header */
        .cb-term-hdr {
            display: flex !important;
            align-items: center !important;
            gap: 6px !important;
            padding-bottom: 8px !important;
            border-bottom: 1px solid rgba(0,255,65,0.3) !important;
            margin-bottom: 10px !important;
        }
        .cb-term-title {
            font-size: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 1px !important;
            color: var(--cb-green) !important;
            text-shadow: 0 0 8px var(--cb-green) !important;
        }
        
        /* Terminal Rows */
        .cb-term-row {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 4px 0 !important;
            color: rgba(255,255,255,0.7) !important;
        }
        .cb-term-key {
            font-size: 10px !important;
            color: rgba(0,255,65,0.6) !important;
            text-transform: uppercase !important;
        }
        .cb-term-val {
            font-size: 12px !important;
            font-weight: 600 !important;
            color: var(--cb-green) !important;
            text-shadow: 0 0 5px var(--cb-green) !important;
        }
        .cb-term-val.warn { color: var(--cb-yellow) !important; text-shadow: 0 0 5px var(--cb-yellow) !important; }
        .cb-term-val.danger { color: var(--cb-red) !important; text-shadow: 0 0 5px var(--cb-red) !important; }
        
        /* Mini Bar */
        .cb-term-bar {
            margin: 6px 0 !important;
        }
        .cb-term-bar-label {
            font-size: 9px !important;
            color: rgba(0,255,65,0.5) !important;
            margin-bottom: 3px !important;
        }
        .cb-term-bar-track {
            height: 4px !important;
            background: rgba(255,255,255,0.1) !important;
            border-radius: 2px !important;
            overflow: hidden !important;
        }
        .cb-term-bar-fill {
            height: 100% !important;
            background: var(--cb-green) !important;
            box-shadow: 0 0 6px var(--cb-green) !important;
            transition: width 0.3s, background 0.3s !important;
        }
        .cb-term-bar-fill.warn { background: var(--cb-yellow) !important; }
        .cb-term-bar-fill.danger { background: var(--cb-red) !important; }
        
        /* ASCII Risk Bar */
        .cb-ascii-bar {
            font-family: 'Consolas', monospace !important;
            font-size: 10px !important;
            letter-spacing: 0 !important;
            color: var(--cb-green) !important;
            margin: 8px 0 !important;
        }
        
        /* Status Badge */
        .cb-term-status {
            display: inline-block !important;
            font-size: 9px !important;
            padding: 2px 6px !important;
            border-radius: 2px !important;
            background: rgba(0,255,65,0.15) !important;
            border: 1px solid var(--cb-green) !important;
            color: var(--cb-green) !important;
            margin-top: 8px !important;
        }
        .cb-term-status.warn { background: rgba(255,255,0,0.15) !important; border-color: var(--cb-yellow) !important; color: var(--cb-yellow) !important; }
        .cb-term-status.danger { background: rgba(255,0,64,0.15) !important; border-color: var(--cb-red) !important; color: var(--cb-red) !important; }
        
        /* ===== INTERVENTIONS ===== */
        .cb-friction { filter: grayscale(100%) !important; transition: filter 0.5s !important; }
        
        .cb-break {
            position: fixed !important;
            inset: 0 !important;
            background: linear-gradient(135deg, #a11 0%, #d33 50%, #a11 100%) !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
            z-index: 2147483647 !important;
            color: #fff !important;
            font-family: 'Segoe UI', sans-serif !important;
        }
        .cb-break-icon { font-size: 72px !important; margin-bottom: 16px !important; }
        .cb-break-title { font-size: 32px !important; font-weight: 700 !important; margin-bottom: 8px !important; }
        .cb-break-sub { font-size: 18px !important; opacity: 0.9 !important; }
        .cb-break-timer { font-size: 52px !important; font-weight: 700 !important; margin-top: 24px !important; }
    `;
    document.head.appendChild(css);
}

// ============================================================
// HUD CREATION
// ============================================================
function createHUD() {
    removeWidget();

    const el = document.createElement('div');
    el.id = 'cb-widget';
    el.className = 'cb-widget cb-hud';
    el.style.cssText = `left:${state.hudPosition.x}px;top:${state.hudPosition.y}px;`;

    el.innerHTML = `
        <div class="cb-hdr" id="cb-drag">
            <div class="cb-title">
                <div class="cb-dot" id="cb-dot"></div>
                <span id="cb-status">ALGORITHMIC ENGAGEMENT MONITOR</span>
            </div>
            <button class="cb-btn" id="cb-switch">SIDEBAR</button>
        </div>
        <div class="cb-body">
            <div class="cb-stats">
                <div class="cb-stat"><div class="cb-stat-val" id="cb-vel">0</div><div class="cb-stat-lbl">Velocity</div></div>
                <div class="cb-stat"><div class="cb-stat-val" id="cb-tox">0.00</div><div class="cb-stat-lbl">Local Toxicity</div></div>
            </div>
            <div class="cb-risk" style="margin-top: 12px;">
                <div class="cb-risk-hdr">
                    <span class="cb-risk-lbl">RISK INDEX</span>
                    <span class="cb-risk-val" id="cb-risk-num">0.00</span>
                </div>
                <div class="cb-risk-bar"><div class="cb-risk-fill" id="cb-risk-bar"></div></div>
            </div>
        </div>
    `;

    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));

    initDrag();
    document.getElementById('cb-switch').onclick = (e) => { e.stopPropagation(); switchMode('SIDEBAR'); };
}

// ============================================================
// SIDEBAR CREATION (Matrix Terminal Style)
// ============================================================
function createSidebar() {
    removeWidget();

    const el = document.createElement('div');
    el.id = 'cb-widget';
    el.className = 'cb-widget cb-sidebar';

    // Generate ASCII risk bar
    const riskPct = Math.round((state.lastData.risk_index || 0) * 100);
    const filled = Math.round(riskPct / 10);
    const asciiBar = '[' + '|'.repeat(filled) + '.'.repeat(10 - filled) + ']';

    el.innerHTML = `
        <div class="cb-sidebar-line">ENGAGEMENT_MONITOR</div>
        <div class="cb-terminal">
            <div class="cb-term-hdr">
                <div class="cb-dot" id="cb-dot"></div>
                <span class="cb-term-title">ENGAGEMENT_MONITOR</span>
                <button class="cb-btn" id="cb-switch" style="margin-left:auto;font-size:8px;">HUD</button>
            </div>
            
            <div class="cb-term-row">
                <span class="cb-term-key">VEL:</span>
                <span class="cb-term-val" id="cb-vel">0 px/s</span>
            </div>
            <div class="cb-term-bar">
                <div class="cb-term-bar-track"><div class="cb-term-bar-fill" id="cb-vel-bar" style="width:0%"></div></div>
            </div>
            
            <div class="cb-term-row">
                <span class="cb-term-key">LOCAL TOX:</span>
                <span class="cb-term-val" id="cb-tox">0.00</span>
            </div>
            
            <div class="cb-term-bar" style="margin-top:10px;">
                <div class="cb-term-bar-label">RISK:</div>
                <div class="cb-ascii-bar" id="cb-ascii">${asciiBar} ${riskPct}%</div>
                <div class="cb-term-bar-track"><div class="cb-term-bar-fill" id="cb-risk-bar" style="width:${riskPct}%"></div></div>
            </div>
            
            <div class="cb-term-status" id="cb-status-badge">ONLINE</div>
        </div>
    `;

    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));

    document.getElementById('cb-switch').onclick = (e) => { e.stopPropagation(); switchMode('HUD'); };
}

function removeWidget() {
    const w = document.getElementById('cb-widget');
    if (w) { w.classList.remove('show'); setTimeout(() => w.remove(), 300); }
}

// ============================================================
// DRAGGING (HUD only)
// ============================================================
function initDrag() {
    const handle = document.getElementById('cb-drag');
    const widget = document.getElementById('cb-widget');
    if (!handle || !widget) return;

    handle.onmousedown = (e) => {
        if (e.target.tagName === 'BUTTON') return;
        state.isDragging = true;
        state.dragOffset = { x: e.clientX - widget.offsetLeft, y: e.clientY - widget.offsetTop };
        widget.style.transition = 'none';
        e.preventDefault();
    };
}

document.addEventListener('mousemove', (e) => {
    if (!state.isDragging) return;
    const w = document.getElementById('cb-widget');
    if (!w) return;

    let x = Math.max(0, Math.min(e.clientX - state.dragOffset.x, innerWidth - w.offsetWidth));
    let y = Math.max(0, Math.min(e.clientY - state.dragOffset.y, innerHeight - w.offsetHeight));

    w.style.left = x + 'px';
    w.style.top = y + 'px';
    state.hudPosition = { x, y };
});

document.addEventListener('mouseup', () => {
    if (state.isDragging) {
        state.isDragging = false;
        const w = document.getElementById('cb-widget');
        if (w) w.style.transition = '';
    }
});

// ============================================================
// MODE SWITCHING + HOTKEYS
// ============================================================
function switchMode(mode) {
    if (state.uiMode === mode) return;
    log(`Mode: ${state.uiMode} → ${mode}`);
    state.uiMode = mode;
    setTimeout(() => mode === 'HUD' ? createHUD() : createSidebar(), 320);
}

document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === '1') { e.preventDefault(); switchMode('HUD'); }
    if (e.ctrlKey && e.key === '2') { e.preventDefault(); switchMode('SIDEBAR'); }
});

// ============================================================
// UPDATE UI
// ============================================================
function updateUI(data) {
    state.lastData = data;

    const risk = data.risk_index ?? 0;
    const vel = data.velocity ?? 0;
    const tox = data.toxicity ?? 0;
    const status = data.status ?? 'SAFE';

    if (state.uiMode === 'HUD') {
        updateHUD(risk, vel, tox, status);
    } else {
        updateSidebar(risk, vel, tox, status);
    }

    state.serverOnline = true;
}

function updateHUD(risk, vel, tox, status) {
    const rb = document.getElementById('cb-risk-bar');
    const rv = document.getElementById('cb-risk-num');
    if (rb) {
        rb.style.width = `${risk * 100}%`;
        rb.classList.remove('warn', 'danger', 'crit');
        if (risk > 0.8) rb.classList.add('crit');
        else if (risk > 0.5) rb.classList.add('danger');
        else if (risk > 0.3) rb.classList.add('warn');
    }
    if (rv) {
        rv.textContent = risk.toFixed(3);
        rv.style.color = risk > 0.5 ? 'var(--cb-red)' : risk > 0.3 ? 'var(--cb-yellow)' : 'var(--cb-green)';
    }

    const vEl = document.getElementById('cb-vel');
    const toxEl = document.getElementById('cb-tox');
    if (vEl) vEl.textContent = vel > 1000 ? (vel / 1000).toFixed(1) + 'K' : Math.round(vel);
    if (toxEl) toxEl.textContent = tox.toFixed(2);

    const dot = document.getElementById('cb-dot');
    const st = document.getElementById('cb-status');
    if (dot) {
        dot.classList.remove('warn', 'crit');
        if (status.includes('BREAK') || status.includes('HIGH')) dot.classList.add('crit');
        else if (status.includes('WARNING') || status.includes('ELEVATED')) dot.classList.add('warn');
    }
    if (st) {
        st.textContent = status.includes('BREAK') ? 'OVERRIDE' : status.includes('ELEVATED') || status.includes('WARNING') ? 'ELEVATED' : 'CONNECTED';
    }
}

function updateSidebar(risk, vel, tox, status) {
    // Velocity
    const vEl = document.getElementById('cb-vel');
    const vBar = document.getElementById('cb-vel-bar');
    if (vEl) vEl.textContent = `${Math.round(vel)} px/s`;
    if (vBar) {
        const velPct = Math.min(vel / 2000 * 100, 100);
        vBar.style.width = `${velPct}%`;
    }

    // Toxicity
    const toxEl = document.getElementById('cb-tox');
    if (toxEl) toxEl.textContent = tox.toFixed(2);

    // ASCII Risk Bar
    const riskPct = Math.round(risk * 100);
    const filled = Math.round(riskPct / 10);
    const asciiBar = '[' + '|'.repeat(filled) + '.'.repeat(10 - filled) + ']';

    const ascii = document.getElementById('cb-ascii');
    const rb = document.getElementById('cb-risk-bar');
    if (ascii) ascii.textContent = `${asciiBar} ${riskPct}%`;
    if (rb) {
        rb.style.width = `${riskPct}%`;
        rb.classList.remove('warn', 'danger');
        if (risk > 0.5) rb.classList.add('danger');
        else if (risk > 0.3) rb.classList.add('warn');
    }

    // Status Badge
    const badge = document.getElementById('cb-status-badge');
    if (badge) {
        badge.classList.remove('warn', 'danger');
        if (status.includes('BREAK') || status.includes('HIGH')) {
            badge.textContent = 'CRITICAL';
            badge.classList.add('danger');
        } else if (status.includes('WARNING') || status.includes('ELEVATED')) {
            badge.textContent = 'WARNING';
            badge.classList.add('warn');
        } else {
            badge.textContent = 'ONLINE';
        }
    }

    // Dot
    const dot = document.getElementById('cb-dot');
    if (dot) {
        dot.classList.remove('warn', 'crit');
        if (status.includes('BREAK') || status.includes('HIGH')) dot.classList.add('crit');
        else if (status.includes('WARNING') || status.includes('ELEVATED')) dot.classList.add('warn');
    }
}

// ============================================================
// SCROLL VELOCITY TRACKING
// ============================================================
function trackScroll() {
    const now = Date.now();
    const currentY = window.scrollY;
    const dt = now - state.lastScrollTime;

    if (dt > 0) {
        const distance = Math.abs(currentY - state.lastScrollY);
        const velocity = (distance / dt) * 1000;

        if (distance > 0) {
            state.velocitySamples.push({ velocity, timestamp: now });
        }

        const cutoff = now - CONFIG.VELOCITY_WINDOW;
        state.velocitySamples = state.velocitySamples.filter(s => s.timestamp > cutoff);
    }

    state.lastScrollY = currentY;
    state.lastScrollTime = now;
}

function getAverageVelocity() {
    if (state.velocitySamples.length === 0) return 0;

    const now = Date.now();
    let totalWeightedVel = 0;
    let totalWeight = 0;

    for (const sample of state.velocitySamples) {
        const age = now - sample.timestamp;
        const weight = 1 - (age / CONFIG.VELOCITY_WINDOW);
        totalWeightedVel += sample.velocity * weight;
        totalWeight += weight;
    }

    return totalWeight > 0 ? totalWeightedVel / totalWeight : 0;
}

class LocalNLPScanner {
    static getToxicityScore() {
        let matchCount = 0;
        // Specifically scan p, h1, h2, and .tweet-text as required
        const elementsToScan = document.querySelectorAll('p, h1, h2, .tweet-text');

        // Execute Shift-Left Local NLP evaluation
        elementsToScan.forEach(el => {
            const textArea = el.textContent.toLowerCase();
            // Regex to match whole words to prevent partial matches like 'ass' in 'class'
            TOXICITY_DICTIONARY.forEach(keyword => {
                const regex = new RegExp(`\\b${keyword}\\b`, 'g');
                const matches = textArea.match(regex);
                if (matches) {
                    matchCount += matches.length;
                }
            });
        });

        // Base score calculation
        let toxicity = Math.min(matchCount * CONFIG.TOXICITY_BASE_MULTIPLIER, CONFIG.TOXICITY_MAX_BASE);

        // Add context penalty
        const host = location.hostname;
        const socialSites = ['twitter', 'x.com', 'facebook', 'instagram', 'tiktok', 'reddit', 'youtube'];
        if (socialSites.some(s => host.includes(s))) {
            toxicity += CONFIG.TOXICITY_SOCIAL_PENALTY;
        }

        if (document.body.scrollHeight > window.innerHeight * 5) {
            toxicity += CONFIG.TOXICITY_SCROLL_PENALTY;
        }

        return Math.min(toxicity, 1.0);
    }
}

// ============================================================
// SEND DATA VIA BACKGROUND BRIDGE
// ============================================================
async function sendData() {
    if (state.isBreakActive) return;

    const velocity = getAverageVelocity();
    const toxicity = LocalNLPScanner.getToxicityScore();
    const scrollTime = (Date.now() - state.sessionStart) / 1000;

    const payload = { velocity, toxicity, scroll_time: scrollTime };

    log(`Send: vel=${velocity.toFixed(0)} tox=${toxicity.toFixed(2)}`);

    try {
        const response = await chrome.runtime.sendMessage({
            type: 'SEND_METRICS',
            payload: payload
        });

        if (response && response.success) {
            log(`Recv: dopa=${response.data.dopamine?.toFixed(3)} risk=${response.data.risk_index?.toFixed(3)}`);
            updateUI(response.data);
            handleIntervention(response.data.intervention);
        } else {
            log('Bridge error: ' + (response?.error || 'No response'));
        }
    } catch (err) {
        log('Message failed: ' + err.message);
    }
}

// ============================================================
// INTERVENTIONS
// ============================================================
function handleIntervention(type) {
    if (type === 'BREAK' && !state.isBreakActive) {
        triggerBreak();
    } else if (type === 'FRICTION' || type === 'REROUTE') {
        document.body.classList.add('cb-friction');
    } else {
        document.body.classList.remove('cb-friction');
    }
}

function triggerBreak() {
    state.isBreakActive = true;

    const overlay = document.createElement('div');
    overlay.className = 'cb-break';
    overlay.innerHTML = `
        <div class="cb-break-icon">🛑</div>
        <div class="cb-break-title">CIRCUIT BREAKER</div>
        <div class="cb-break-sub">Take a breath. Resuming in:</div>
        <div class="cb-break-timer" id="cb-countdown">10</div>
    `;
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';

    let sec = CONFIG.BREAK_DURATION_SEC;
    const el = document.getElementById('cb-countdown');
    if (el) el.textContent = sec;

    const iv = setInterval(() => {
        sec--;
        if (el) el.textContent = sec;
        if (sec <= 0) {
            clearInterval(iv);
            overlay.remove();
            document.body.style.overflow = '';
            state.isBreakActive = false;
            state.velocitySamples = [];
        }
    }, 1000);
}

// ============================================================
// INIT
// ============================================================
function init() {
    log('Initializing v2.2 (Matrix Sidebar)');

    injectStyles();
    createHUD();

    window.addEventListener('scroll', trackScroll, { passive: true });
    setInterval(trackScroll, CONFIG.SCROLL_SAMPLE_MS);
    setInterval(sendData, CONFIG.SEND_INTERVAL);
    setTimeout(sendData, 1000);

    log('Ready! Ctrl+1=HUD, Ctrl+2=SIDEBAR');
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
