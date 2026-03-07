"""Single-page HTML app for the Observatory dashboard (PWA-enabled)."""

import json

MANIFEST_JSON = json.dumps(
    {
        "name": "Observatory",
        "short_name": "Observatory",
        "start_url": "/observe/ui",
        "scope": "/observe/",
        "display": "standalone",
        "background_color": "#0f1419",
        "theme_color": "#0f1419",
        "icons": [
            {
                "src": "/observe/icon-192.svg",
                "sizes": "192x192",
                "type": "image/svg+xml",
                "purpose": "any",
            },
            {
                "src": "/observe/icon-512.svg",
                "sizes": "512x512",
                "type": "image/svg+xml",
                "purpose": "any",
            },
        ],
    }
)

SERVICE_WORKER_JS = """\
const CACHE='observatory-v3';
const SHELL=['/observe/ui','/observe/icon-192.svg'];
const API_RE=/\\/observe\\/(events|stats|tool-events|tool-stats|sessions|agent-summary)/;

self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(
    ks.filter(k=>k!==CACHE).map(k=>caches.delete(k))
  )).then(()=>self.clients.claim()));
});

self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  if(API_RE.test(url.pathname)){
    e.respondWith(
      fetch(e.request).then(r=>{
        const cl=r.clone();
        caches.open(CACHE).then(c=>c.put(e.request,cl));
        return r;
      }).catch(()=>caches.match(e.request))
    );
  } else {
    e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request)));
  }
});
"""

APP_ICON_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <rect fill="#0f1419" width="100" height="100" rx="20"/>
  <circle cx="50" cy="50" r="30" fill="none" stroke="#58a6ff" stroke-width="4"/>
  <circle cx="50" cy="50" r="8" fill="#58a6ff"/>
  <line x1="50" y1="20" x2="50" y2="35" stroke="#58a6ff" stroke-width="3"/>
  <line x1="50" y1="65" x2="50" y2="80" stroke="#58a6ff" stroke-width="3"/>
  <line x1="20" y1="50" x2="35" y2="50" stroke="#58a6ff" stroke-width="3"/>
  <line x1="65" y1="50" x2="80" y2="50" stroke="#58a6ff" stroke-width="3"/>
</svg>"""

DASHBOARD_HTML = """\
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Observatory</title>
  <link rel="manifest" href="/observe/manifest.json">
  <link rel="icon" href="/observe/icon-192.svg">
  <meta name="theme-color" content="#0f1419">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root, html[data-theme="dark"] {
      --bg: #0f1419;
      --card: #161b22;
      --border: #30363d;
      --fg: #e6edf3;
      --muted: #7d8590;
      --accent: #58a6ff;
      --success: #3fb950;
      --error: #f85149;
      --warning: #d29922;
      --purple: #d299ff;
      --hover: var(--hover);
      --chart-grid: #30363d;
      --chart-text: #7d8590;
      --chart-label: #e6edf3;
    }
    html[data-theme="light"] {
      --bg: #f0f2f5;
      --card: #ffffff;
      --border: #d0d7de;
      --fg: #1f2328;
      --muted: #656d76;
      --accent: #0969da;
      --success: #1a7f37;
      --error: #cf222e;
      --warning: #9a6700;
      --purple: #8250df;
      --hover: rgba(0,0,0,0.03);
      --chart-grid: #d0d7de;
      --chart-text: #656d76;
      --chart-label: #1f2328;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: var(--bg);
      color: var(--fg);
      min-height: 100vh;
      padding: 16px;
    }
    .container { max-width: 1400px; margin: 0 auto; }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 { font-size: 24px; font-weight: 600; }
    .header-actions { display: flex; gap: 12px; align-items: center; }
    .period-group { display: flex; align-items: center; gap: 0; }
    .period-label { color: var(--muted); font-size: 13px; margin-right: 8px; }
    .period-input {
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 8px 10px;
      border-radius: 6px 0 0 6px;
      font-size: 14px;
      width: 56px;
      text-align: center;
      -moz-appearance: textfield;
    }
    .period-input::-webkit-outer-spin-button,
    .period-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
    .period-unit {
      background: var(--card);
      border: 1px solid var(--border);
      border-left: none;
      color: var(--fg);
      padding: 8px 12px;
      border-radius: 0 6px 6px 0;
      font-size: 14px;
      cursor: pointer;
    }
    .period-select {
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 14px;
    }
    /* Tab navigation */
    .tab-bar {
      display: flex;
      gap: 0;
      margin: 0 0 24px;
      border-bottom: 1px solid var(--border);
    }
    .tab-btn {
      background: none;
      border: none;
      color: var(--muted);
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: color .15s, border-color .15s;
    }
    .tab-btn:hover { color: var(--fg); }
    .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }
    .stat-label { color: var(--muted); font-size: 13px; margin-bottom: 4px; }
    .stat-value { font-size: 28px; font-weight: 600; }
    .stat-value.success { color: var(--success); }
    .stat-value.error { color: var(--error); }
    .stat-value.warning { color: var(--warning); }
    .charts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .chart-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }
    .chart-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
    .chart-container { height: 250px; }
    .table-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      margin-bottom: 24px;
    }
    .table-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
    }
    .table-title { font-size: 16px; font-weight: 600; }
    .filters { display: flex; gap: 8px; flex-wrap: wrap; }
    .filter-input {
      background: var(--bg);
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 6px 10px;
      border-radius: 4px;
      font-size: 13px;
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 10px 16px; text-align: left; border-bottom: 1px solid var(--border); }
    th { color: var(--muted); font-weight: 500; font-size: 12px; text-transform: uppercase; }
    td { font-size: 14px; }
    tr:hover { background: var(--hover); }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
    }
    .badge-success { background: rgba(63,185,80,0.2); color: var(--success); }
    .badge-error { background: rgba(248,81,73,0.2); color: var(--error); }
    .provider-badge { background: rgba(88,166,255,0.2); color: var(--accent); }
    .agent-badge { background: rgba(210,153,255,0.2); color: var(--purple); }
    .duration { font-family: monospace; }
    .load-more {
      display: block;
      width: 100%;
      padding: 12px;
      background: transparent;
      border: none;
      color: var(--accent);
      cursor: pointer;
      font-size: 14px;
    }
    .load-more:hover { background: var(--hover); }
    .error-row td { color: var(--error); }
    .error-message {
      display: none;
      background: rgba(248,81,73,0.1);
      padding: 8px 16px;
      font-size: 12px;
      color: var(--error);
      border-bottom: 1px solid var(--border);
    }
    .error-message.visible { display: block; }
    .empty { color: var(--muted); text-align: center; padding: 40px; }
    .clickable-row { cursor: pointer; }
    .raw-row td { padding: 0; border-bottom: 1px solid var(--border); }
    .raw-content {
      display: none;
      padding: 12px 16px;
      background: rgba(88,166,255,0.05);
    }
    .raw-content.visible { display: block; }
    .raw-section { margin-bottom: 12px; }
    .raw-label { color: var(--muted); font-size: 12px; margin-bottom: 4px; text-transform: uppercase; }
    .raw-text {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 8px;
      font-family: monospace;
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-all;
      max-height: 300px;
      overflow-y: auto;
    }
    .token-col { font-family: monospace; font-size: 13px; }
    .stop-col { font-size: 12px; color: var(--muted); }
    /* Session trace styles */
    .session-row { cursor: pointer; }
    .session-row:hover { background: rgba(88,166,255,0.05); }
    .session-detail { display: none; }
    .session-detail.visible { display: table-row; }
    .trace-container { padding: 16px; }
    .trace-event {
      display: flex;
      gap: 12px;
      padding: 10px 12px;
      border-left: 2px solid var(--border);
      margin-left: 8px;
      position: relative;
    }
    .trace-event::before {
      content: '';
      position: absolute;
      left: -6px;
      top: 14px;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--accent);
    }
    .trace-event.trace-tool::before { background: var(--success); }
    .trace-event.trace-error::before { background: var(--error); }
    .trace-meta { min-width: 80px; color: var(--muted); font-size: 12px; flex-shrink: 0; }
    .trace-body { flex: 1; font-size: 13px; }
    .trace-type { font-weight: 600; margin-right: 8px; }
    .trace-detail { color: var(--muted); font-size: 12px; margin-top: 2px; }
    .trace-tokens { font-family: monospace; font-size: 12px; color: var(--muted); }
    /* Agent card styles */
    .agent-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }
    .agent-card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
    }
    .agent-card-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }
    .agent-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: rgba(210,153,255,0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      font-size: 16px;
      color: var(--purple);
      flex-shrink: 0;
    }
    .agent-name { font-size: 18px; font-weight: 600; }
    .agent-meta { color: var(--muted); font-size: 12px; }
    .agent-stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }
    .agent-stat { text-align: center; }
    .agent-stat-value { font-size: 20px; font-weight: 600; }
    .agent-stat-label { font-size: 11px; color: var(--muted); text-transform: uppercase; }
    .agent-details { border-top: 1px solid var(--border); padding-top: 12px; }
    .agent-detail-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 0;
      font-size: 13px;
    }
    .agent-detail-label { color: var(--muted); }
    .mini-bar {
      display: inline-flex;
      gap: 3px;
      align-items: flex-end;
      height: 16px;
    }
    .mini-bar-seg {
      width: 8px;
      border-radius: 2px;
      min-height: 3px;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Observatory</h1>
      <div class="header-actions">
        <div class="period-group">
          <span class="period-label">Last</span>
          <input type="number" id="period-value" class="period-input" min="1" value="24">
          <select id="period-unit" class="period-unit">
            <option value="1" selected>hours</option>
            <option value="24">days</option>
            <option value="168">weeks</option>
          </select>
        </div>
        <button id="refresh-btn" class="period-select" style="cursor:pointer;" title="Refresh">&#x21bb; Refresh</button>
        <button class="period-select" style="cursor:pointer;" onclick="toggleTheme()" title="Toggle theme">Theme</button>
      </div>
    </header>

    <div class="tab-bar">
      <button class="tab-btn active" onclick="switchTab('overview')">Overview</button>
      <button class="tab-btn" onclick="switchTab('sessions')">Sessions</button>
      <button class="tab-btn" onclick="switchTab('agents')">Agents</button>
      <button class="tab-btn" onclick="switchTab('health')">Health</button>
    </div>

    <!-- ================= OVERVIEW TAB ================= -->
    <div class="tab-panel active" id="tab-overview">
      <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
        <select id="overview-filter-provider" class="filter-input"><option value="">All Providers</option></select>
        <select id="overview-filter-model" class="filter-input"><option value="">All Models</option></select>
      </div>
      <div class="stats-grid" id="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Total Calls</div>
          <div class="stat-value" id="stat-total">&mdash;</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Error Rate</div>
          <div class="stat-value" id="stat-error-rate">&mdash;</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Latency</div>
          <div class="stat-value" id="stat-latency">&mdash;</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Tokens</div>
          <div class="stat-value" id="stat-tokens">&mdash;</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Providers Used</div>
          <div class="stat-value" id="stat-providers">&mdash;</div>
        </div>
      </div>

      <div class="charts-grid">
        <div class="chart-card">
          <div class="chart-title" style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
            <span>Calls per</span>
            <select id="chart-bucket" class="filter-input" style="font-size:13px">
              <option value="1" selected>Hour</option>
              <option value="6">6 Hours</option>
              <option value="24">Day</option>
            </select>
            <span style="flex:1"></span>
            <span id="chart-range" style="font-size:12px;color:var(--muted)"></span>
            <div style="display:flex;gap:4px">
              <button id="chart-prev" class="filter-input" style="cursor:pointer;padding:4px 10px" title="Older">&larr;</button>
              <button id="chart-next" class="filter-input" style="cursor:pointer;padding:4px 10px" title="Newer">&rarr;</button>
              <button id="chart-latest" class="filter-input" style="cursor:pointer;padding:4px 10px;font-size:12px" title="Jump to latest">Latest</button>
            </div>
          </div>
          <div class="chart-container"><canvas id="timeline-chart"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">Calls by Provider</div>
          <div class="chart-container"><canvas id="provider-chart"></canvas></div>
        </div>
      </div>

      <div class="table-card">
        <div class="table-header">
          <div class="table-title">Recent Events</div>
          <div class="filters">
            <select id="filter-provider" class="filter-input"><option value="">All Providers</option></select>
            <select id="filter-model" class="filter-input"><option value="">All Models</option></select>
            <select id="filter-agent" class="filter-input"><option value="">All Agents</option></select>
            <select id="filter-success" class="filter-input">
              <option value="">All Status</option>
              <option value="true">Success</option>
              <option value="false">Errors</option>
            </select>
          </div>
        </div>
        <table>
          <thead><tr>
            <th>Time</th><th>Agent</th><th>Provider</th><th>Model</th><th>Duration</th>
            <th>Tokens (In/Out)</th><th>Stop</th><th>Tool Rounds</th><th>Status</th>
          </tr></thead>
          <tbody id="events-body"></tbody>
        </table>
        <button class="load-more" id="load-more">Load more</button>
      </div>

      <h2 style="margin:0 0 16px;font-size:20px;font-weight:600">Tool Calls</h2>
      <div class="stats-grid" id="tool-stats-grid">
        <div class="stat-card">
          <div class="stat-label">Total Tool Calls</div>
          <div class="stat-value" id="stat-tool-total">&mdash;</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Tool Error Rate</div>
          <div class="stat-value" id="stat-tool-error-rate">&mdash;</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Tool Latency</div>
          <div class="stat-value" id="stat-tool-latency">&mdash;</div>
        </div>
      </div>
      <div class="charts-grid">
        <div class="chart-card">
          <div class="chart-title">Top Tools</div>
          <div class="chart-container"><canvas id="tool-chart"></canvas></div>
        </div>
      </div>
      <div class="table-card" id="tool-events-card">
        <div class="table-header">
          <div class="table-title">Recent Tool Calls</div>
          <div class="filters">
            <select id="filter-tool-name" class="filter-input"><option value="">All Tools</option></select>
            <select id="filter-tool-success" class="filter-input">
              <option value="">All Status</option>
              <option value="true">Success</option>
              <option value="false">Errors</option>
            </select>
          </div>
        </div>
        <table>
          <thead><tr><th>Time</th><th>Agent</th><th>Tool</th><th>Duration</th><th>Category</th><th>Status</th></tr></thead>
          <tbody id="tool-events-body"></tbody>
        </table>
        <button class="load-more" id="tool-load-more">Load more</button>
      </div>
    </div>

    <!-- ================= SESSIONS TAB ================= -->
    <div class="tab-panel" id="tab-sessions">
      <div class="table-card">
        <div class="table-header">
          <div class="table-title">Session Traces</div>
          <div class="filters">
            <select id="filter-session-agent" class="filter-input"><option value="">All Agents</option></select>
          </div>
        </div>
        <table>
          <thead><tr>
            <th>Session</th><th>Agent</th><th>LLM Calls</th><th>Tool Calls</th>
            <th>Tokens (In/Out)</th><th>Duration</th><th>Errors</th><th>Time</th>
          </tr></thead>
          <tbody id="sessions-body"></tbody>
        </table>
        <button class="load-more" id="sessions-load-more">Load more</button>
      </div>
    </div>

    <!-- ================= AGENTS TAB ================= -->
    <div class="tab-panel" id="tab-agents">
      <div class="agent-grid" id="agent-grid"></div>
    </div>

    <!-- ================= HEALTH TAB ================= -->
    <div class="tab-panel" id="tab-health">
      <div class="stats-grid" id="health-grid" style="grid-template-columns:repeat(auto-fit,minmax(200px,1fr))"></div>
      <div class="table-card" style="margin-top:16px">
        <div class="table-header"><div class="table-title">Service Details</div></div>
        <table>
          <thead><tr><th>Service</th><th>Status</th><th>Latency</th><th>Details</th></tr></thead>
          <tbody id="health-body"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    /* ====== Theme ====== */
    function initTheme() {
      const saved = localStorage.getItem('obs-theme') || 'dark';
      document.documentElement.setAttribute('data-theme', saved);
    }
    function toggleTheme() {
      const cur = document.documentElement.getAttribute('data-theme');
      const next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('obs-theme', next);
      refreshAll();
    }
    function isDark() { return document.documentElement.getAttribute('data-theme') !== 'light'; }
    function chartGridColor() { return isDark() ? '#30363d' : '#d0d7de'; }
    function chartTextColor() { return isDark() ? '#7d8590' : '#656d76'; }
    function chartLabelColor() { return isDark() ? '#e6edf3' : '#1f2328'; }
    initTheme();

    /* ====== Shared state ====== */
    let timelineChart = null, providerChart = null, toolChart = null;
    let lastEventId = null, lastToolEventId = null;
    let currentPeriod = 24;
    let chartBucket = 1, chartOffset = 0, chartWindow = 24;
    let sessionsOffset = 0;
    let activeTab = 'overview';
    const COLORS = ['#58a6ff','#3fb950','#f0883e','#a371f7','#f85149','#d29922','#79c0ff','#56d364','#ffa657','#bc8cff','#ff7b72','#e3b341','#a5d6ff','#7ee787','#ffc680'];

    /* ====== Tab switching ====== */
    const TAB_NAMES = ['overview','sessions','agents','health'];
    function switchTab(name) {
      activeTab = name;
      document.querySelectorAll('.tab-btn').forEach((b,i) => {
        b.classList.toggle('active', TAB_NAMES[i] === name);
      });
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      if (name === 'sessions') refreshSessions();
      if (name === 'agents') refreshAgents();
      if (name === 'health') refreshHealth();
    }

    /* ====== Utilities ====== */
    function formatDuration(ms) {
      if (ms < 1000) return ms + 'ms';
      if (ms < 60000) return (ms/1000).toFixed(1) + 's';
      return (ms/60000).toFixed(1) + 'm';
    }
    function formatTime(iso) {
      const d = new Date(iso);
      return d.toLocaleTimeString('en-US', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
    }
    function formatDateTime(iso) {
      const d = new Date(iso);
      return d.toLocaleDateString('en-US', {month:'short',day:'numeric'}) + ' ' + formatTime(iso);
    }
    function formatTokens(n) {
      if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
      if (n >= 1000) return (n/1000).toFixed(1) + 'K';
      return n.toLocaleString();
    }
    function escapeHtml(text) {
      const d = document.createElement('div');
      d.textContent = text;
      return d.innerHTML;
    }
    function shortId(sid) { return sid ? sid.slice(0,8) : '—'; }

    /* ====== Period controls ====== */
    const periodValue = document.getElementById('period-value');
    const periodUnit = document.getElementById('period-unit');
    function updatePeriod() {
      const val = Math.max(1, parseInt(periodValue.value) || 1);
      const mult = parseInt(periodUnit.value);
      currentPeriod = val * mult;
      chartWindow = currentPeriod;
      chartOffset = 0;
      refreshAll();
    }
    periodValue.addEventListener('change', updatePeriod);
    periodUnit.addEventListener('change', updatePeriod);
    document.getElementById('refresh-btn').addEventListener('click', refreshAll);

    function refreshAll() {
      refreshOverview();
      refreshTools();
      if (activeTab === 'sessions') refreshSessions();
      if (activeTab === 'agents') refreshAgents();
      if (activeTab === 'health') refreshHealth();
    }

    /* ====== OVERVIEW TAB ====== */
    const filterProvider = document.getElementById('filter-provider');
    const filterModel = document.getElementById('filter-model');
    const filterAgent = document.getElementById('filter-agent');
    const filterSuccess = document.getElementById('filter-success');
    const chartBucketSelect = document.getElementById('chart-bucket');
    const chartRangeLabel = document.getElementById('chart-range');

    const overviewProvider = document.getElementById('overview-filter-provider');
    const overviewModel = document.getElementById('overview-filter-model');
    async function fetchStats() {
      let u = '/observe/stats?period_hours=' + currentPeriod;
      if (overviewProvider.value) u += '&provider=' + overviewProvider.value;
      if (overviewModel.value) u += '&model=' + encodeURIComponent(overviewModel.value);
      return (await fetch(u)).json();
    }
    async function fetchEvents(beforeId) {
      let u = '/observe/events?limit=50';
      if (beforeId) u += '&before_id=' + beforeId;
      if (filterProvider.value) u += '&provider=' + filterProvider.value;
      if (filterModel.value) u += '&model=' + encodeURIComponent(filterModel.value);
      if (filterAgent.value) u += '&agent_name=' + filterAgent.value;
      if (filterSuccess.value) u += '&success=' + filterSuccess.value;
      return (await fetch(u)).json();
    }

    function updateStats(s) {
      document.getElementById('stat-total').textContent = s.total_calls.toLocaleString();
      const errEl = document.getElementById('stat-error-rate');
      errEl.textContent = s.error_rate.toFixed(1) + '%';
      errEl.className = 'stat-value ' + (s.error_rate > 5 ? 'error' : s.error_rate > 1 ? 'warning' : 'success');
      document.getElementById('stat-latency').textContent = formatDuration(s.avg_latency_ms);
      document.getElementById('stat-tokens').textContent = formatTokens((s.total_input_tokens||0)+(s.total_output_tokens||0));
      document.getElementById('stat-providers').textContent = Object.keys(s.calls_by_provider).length;
    }

    async function fetchTimeline() {
      return (await fetch('/observe/timeline?period_hours='+chartWindow+'&offset_hours='+chartOffset+'&bucket_hours='+chartBucket)).json();
    }
    function formatChartLabel(b, bh) { return bh >= 24 ? b.slice(5,10) : b.slice(5,16); }
    function updateChartRange() {
      const now = new Date(), end = new Date(now.getTime()-chartOffset*3600000), start = new Date(end.getTime()-chartWindow*3600000);
      const fmt = d => d.toLocaleDateString('en-US',{month:'short',day:'numeric'})+' '+d.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'});
      chartRangeLabel.textContent = fmt(start) + ' \\u2014 ' + fmt(end);
      document.getElementById('chart-next').disabled = chartOffset <= 0;
    }
    async function refreshTimeline() {
      updateChartRange();
      const data = await fetchTimeline();
      const ctx = document.getElementById('timeline-chart').getContext('2d');
      if (timelineChart) timelineChart.destroy();
      timelineChart = new Chart(ctx, {
        type:'line',
        data:{labels:data.map(d=>formatChartLabel(d.bucket,chartBucket)),datasets:[{label:'Calls',data:data.map(d=>d.count),borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,0.1)',fill:true,tension:.3}]},
        options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:chartGridColor()},ticks:{color:chartTextColor(),maxTicksLimit:16}},y:{grid:{color:chartGridColor()},ticks:{color:chartTextColor()},beginAtZero:true}}}
      });
    }
    function updateProviderChart(s) {
      const ctx = document.getElementById('provider-chart').getContext('2d');
      const labels = Object.keys(s.calls_by_provider), data = Object.values(s.calls_by_provider);
      if (providerChart) providerChart.destroy();
      providerChart = new Chart(ctx, {
        type:'doughnut',
        data:{labels,datasets:[{data,backgroundColor:COLORS.slice(0,labels.length)}]},
        options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:chartLabelColor()}}}}
      });
    }

    function renderEvents(events, append) {
      const tbody = document.getElementById('events-body');
      if (!append) tbody.innerHTML = '';
      if (!events.length && !append) { tbody.innerHTML = '<tr><td colspan="9" class="empty">No events recorded</td></tr>'; return; }
      events.forEach(ev => {
        const tr = document.createElement('tr');
        tr.classList.add('clickable-row');
        if (!ev.success) tr.classList.add('error-row');
        const inT = ev.input_tokens||0, outT = ev.output_tokens||0;
        tr.innerHTML = '<td>'+formatTime(ev.timestamp)+'</td>'
          +'<td><span class="badge agent-badge">'+(ev.agent_name||'jax')+'</span></td>'
          +'<td><span class="badge provider-badge">'+ev.provider+'</span></td>'
          +'<td>'+ev.model+'</td>'
          +'<td class="duration">'+formatDuration(ev.duration_ms)+'</td>'
          +'<td class="token-col">'+((inT||outT)?formatTokens(inT)+' / '+formatTokens(outT):'\\u2014')+'</td>'
          +'<td class="stop-col">'+(ev.stop_reason||'\\u2014')+'</td>'
          +'<td>'+ev.tool_rounds+'</td>'
          +'<td>'+(ev.success?'<span class="badge badge-success">OK</span>':'<span class="badge badge-error">Error</span>')+'</td>';
        tr.addEventListener('click', () => toggleRaw(ev.id));
        tbody.appendChild(tr);
        const rawRow = document.createElement('tr');
        rawRow.classList.add('raw-row');
        rawRow.innerHTML = '<td colspan="9"><div class="raw-content" id="raw-content-'+ev.id+'">Loading...</div></td>';
        tbody.appendChild(rawRow);
        if (!ev.success && ev.error_message) {
          const er = document.createElement('tr');
          er.innerHTML = '<td colspan="9" class="error-message">'+escapeHtml(ev.error_message)+'</td>';
          tbody.appendChild(er);
        }
      });
      if (events.length) lastEventId = events[events.length-1].id;
    }

    async function toggleRaw(id) {
      const el = document.getElementById('raw-content-'+id);
      if (el.classList.contains('visible')) { el.classList.remove('visible'); return; }
      if (el.dataset.loaded !== 'true') {
        try {
          const data = await (await fetch('/observe/events/'+id+'/raw')).json();
          let h = '';
          if (data.raw_prompt) h += '<div class="raw-section"><div class="raw-label">Prompt</div><div class="raw-text">'+escapeHtml(data.raw_prompt)+'</div></div>';
          if (data.raw_response) h += '<div class="raw-section"><div class="raw-label">Response</div><div class="raw-text">'+escapeHtml(data.raw_response)+'</div></div>';
          if (!data.raw_prompt && !data.raw_response) h = '<div style="color:var(--muted);padding:8px">No raw content available.</div>';
          el.innerHTML = h;
          el.dataset.loaded = 'true';
        } catch(e) { el.innerHTML = '<div style="color:var(--error);padding:8px">Failed to load.</div>'; }
      }
      el.classList.add('visible');
    }

    function updateFilters(stats) {
      const pSel = filterProvider, mSel = filterModel, aSel = filterAgent;
      const pv = pSel.value, mv = mSel.value, av = aSel.value;
      pSel.innerHTML = '<option value="">All Providers</option>';
      Object.keys(stats.calls_by_provider).sort().forEach(p => { pSel.innerHTML += '<option value="'+p+'">'+p+'</option>'; });
      pSel.value = pv;
      mSel.innerHTML = '<option value="">All Models</option>';
      if (stats.calls_by_model) Object.keys(stats.calls_by_model).sort().forEach(m => { mSel.innerHTML += '<option value="'+m+'">'+m+' ('+stats.calls_by_model[m]+')</option>'; });
      mSel.value = mv;
      aSel.innerHTML = '<option value="">All Agents</option>';
      if (stats.calls_by_agent) Object.keys(stats.calls_by_agent).sort().forEach(a => { aSel.innerHTML += '<option value="'+a+'">'+a+' ('+stats.calls_by_agent[a]+')</option>'; });
      aSel.value = av;
    }

    function updateOverviewFilters(s) {
      // Populate overview provider/model dropdowns from stats (unfiltered values)
      const pv = overviewProvider.value, mv = overviewModel.value;
      overviewProvider.innerHTML = '<option value="">All Providers</option>';
      Object.keys(s.calls_by_provider||{}).sort().forEach(p => {
        overviewProvider.innerHTML += '<option value="'+p+'">'+p+' ('+s.calls_by_provider[p]+')</option>';
      });
      overviewProvider.value = pv;
      overviewModel.innerHTML = '<option value="">All Models</option>';
      Object.keys(s.calls_by_model||{}).sort().forEach(m => {
        overviewModel.innerHTML += '<option value="'+m+'">'+m+' ('+s.calls_by_model[m]+')</option>';
      });
      overviewModel.value = mv;
    }
    async function refreshOverview() {
      const s = await fetchStats();
      updateStats(s);
      updateProviderChart(s);
      updateOverviewFilters(s);
      updateFilters(s);
      refreshTimeline();
      lastEventId = null;
      renderEvents(await fetchEvents());
    }
    overviewProvider.addEventListener('change', refreshOverview);
    overviewModel.addEventListener('change', refreshOverview);

    filterProvider.addEventListener('change', () => { lastEventId=null; fetchEvents().then(e=>renderEvents(e)); });
    filterModel.addEventListener('change', () => { lastEventId=null; fetchEvents().then(e=>renderEvents(e)); });
    filterSuccess.addEventListener('change', () => { lastEventId=null; fetchEvents().then(e=>renderEvents(e)); });
    filterAgent.addEventListener('change', () => { lastEventId=null; fetchEvents().then(e=>renderEvents(e)); });
    document.getElementById('load-more').addEventListener('click', async () => { if(lastEventId){renderEvents(await fetchEvents(lastEventId),true);} });

    chartBucketSelect.addEventListener('change', () => {
      chartBucket = parseInt(chartBucketSelect.value);
      if (chartBucket >= 24) chartWindow = Math.max(chartWindow, 168);
      else if (chartBucket >= 6) chartWindow = Math.max(chartWindow, 48);
      refreshTimeline();
    });
    document.getElementById('chart-prev').addEventListener('click', () => { chartOffset += chartWindow; refreshTimeline(); });
    document.getElementById('chart-next').addEventListener('click', () => { chartOffset = Math.max(0, chartOffset - chartWindow); refreshTimeline(); });
    document.getElementById('chart-latest').addEventListener('click', () => { chartOffset = 0; refreshTimeline(); });

    /* ====== TOOL EVENTS (overview) ====== */
    const filterToolName = document.getElementById('filter-tool-name');
    const filterToolSuccess = document.getElementById('filter-tool-success');

    async function fetchToolStats() { return (await fetch('/observe/tool-stats?period_hours='+currentPeriod)).json(); }
    async function fetchToolEvents(beforeId) {
      let u = '/observe/tool-events?limit=50';
      if (beforeId) u += '&before_id='+beforeId;
      if (filterToolName.value) u += '&tool_name='+filterToolName.value;
      if (filterToolSuccess.value) u += '&success='+filterToolSuccess.value;
      return (await fetch(u)).json();
    }
    function updateToolStats(s) {
      document.getElementById('stat-tool-total').textContent = s.total_calls.toLocaleString();
      const el = document.getElementById('stat-tool-error-rate');
      el.textContent = s.error_rate.toFixed(1)+'%';
      el.className = 'stat-value '+(s.error_rate>5?'error':s.error_rate>1?'warning':'success');
      document.getElementById('stat-tool-latency').textContent = formatDuration(s.avg_duration_ms);
    }
    function updateToolChart(s) {
      const ctx = document.getElementById('tool-chart').getContext('2d');
      const entries = Object.entries(s.calls_by_tool||{}).slice(0,15);
      if (toolChart) toolChart.destroy();
      toolChart = new Chart(ctx, {
        type:'bar',
        data:{labels:entries.map(e=>e[0]),datasets:[{label:'Calls',data:entries.map(e=>e[1]),backgroundColor:COLORS.slice(0,entries.length)}]},
        options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:chartGridColor()},ticks:{color:chartTextColor()},beginAtZero:true},y:{grid:{display:false},ticks:{color:chartLabelColor(),font:{size:11}}}}}
      });
    }
    function updateToolNameFilter(s) {
      const sel = filterToolName, cv = sel.value;
      sel.innerHTML = '<option value="">All Tools</option>';
      Object.keys(s.calls_by_tool||{}).sort().forEach(t => { sel.innerHTML += '<option value="'+t+'">'+t+'</option>'; });
      sel.value = cv;
    }
    function renderToolEvents(events, append) {
      const tbody = document.getElementById('tool-events-body');
      if (!append) tbody.innerHTML = '';
      if (!events.length && !append) { tbody.innerHTML = '<tr><td colspan="6" class="empty">No tool events</td></tr>'; return; }
      events.forEach(ev => {
        const tr = document.createElement('tr');
        if (!ev.success) tr.classList.add('error-row');
        tr.innerHTML = '<td>'+formatTime(ev.timestamp)+'</td>'
          +'<td><span class="badge agent-badge">'+(ev.agent_name||'jax')+'</span></td>'
          +'<td><span class="badge provider-badge">'+ev.tool_name+'</span></td>'
          +'<td class="duration">'+formatDuration(ev.duration_ms)+'</td>'
          +'<td>'+(ev.action_category||'\\u2014')+'</td>'
          +'<td>'+(ev.success?'<span class="badge badge-success">OK</span>':'<span class="badge badge-error">Error</span>')+'</td>';
        tbody.appendChild(tr);
        if (!ev.success && ev.error_message) {
          const er = document.createElement('tr');
          er.innerHTML = '<td colspan="6" class="error-message visible">'+escapeHtml(ev.error_message)+'</td>';
          tbody.appendChild(er);
        }
      });
      if (events.length) lastToolEventId = events[events.length-1].id;
    }
    async function refreshTools() {
      const s = await fetchToolStats();
      updateToolStats(s);
      updateToolChart(s);
      updateToolNameFilter(s);
      lastToolEventId = null;
      renderToolEvents(await fetchToolEvents());
    }
    filterToolName.addEventListener('change', () => { lastToolEventId=null; fetchToolEvents().then(e=>renderToolEvents(e)); });
    filterToolSuccess.addEventListener('change', () => { lastToolEventId=null; fetchToolEvents().then(e=>renderToolEvents(e)); });
    document.getElementById('tool-load-more').addEventListener('click', async () => { if(lastToolEventId){renderToolEvents(await fetchToolEvents(lastToolEventId),true);} });

    /* ====== SESSIONS TAB ====== */
    const filterSessionAgent = document.getElementById('filter-session-agent');

    async function fetchSessions(offset) {
      let u = '/observe/sessions?limit=30&offset='+offset;
      if (filterSessionAgent.value) u += '&agent_name='+filterSessionAgent.value;
      return (await fetch(u)).json();
    }

    function renderSessions(sessions, append) {
      const tbody = document.getElementById('sessions-body');
      if (!append) { tbody.innerHTML = ''; sessionsOffset = 0; }
      if (!sessions.length && !append) { tbody.innerHTML = '<tr><td colspan="8" class="empty">No sessions found</td></tr>'; return; }
      sessions.forEach(s => {
        const tr = document.createElement('tr');
        tr.classList.add('session-row');
        const hasErr = s.error_count > 0;
        tr.innerHTML = '<td><code style="color:var(--accent);font-size:13px">'+shortId(s.session_id)+'</code></td>'
          +'<td><span class="badge agent-badge">'+s.agent+'</span></td>'
          +'<td>'+s.call_count+'</td>'
          +'<td>'+s.tool_event_count+'</td>'
          +'<td class="token-col">'+formatTokens(s.total_input_tokens)+' / '+formatTokens(s.total_output_tokens)+'</td>'
          +'<td class="duration">'+formatDuration(s.total_duration_ms)+'</td>'
          +'<td>'+(hasErr?'<span class="badge badge-error">'+s.error_count+'</span>':'<span class="badge badge-success">0</span>')+'</td>'
          +'<td style="font-size:12px;color:var(--muted)">'+formatDateTime(s.first_event)+'</td>';
        tbody.appendChild(tr);

        // Expandable trace row
        const detailRow = document.createElement('tr');
        detailRow.classList.add('session-detail');
        detailRow.innerHTML = '<td colspan="8"><div class="trace-container" id="trace-'+s.session_id+'">Loading trace...</div></td>';
        tbody.appendChild(detailRow);

        tr.addEventListener('click', () => toggleTrace(s.session_id, detailRow));
      });
      sessionsOffset += sessions.length;
    }

    async function toggleTrace(sid, row) {
      if (row.classList.contains('visible')) { row.classList.remove('visible'); return; }
      const container = document.getElementById('trace-'+sid);
      if (container.dataset.loaded !== 'true') {
        try {
          const trace = await (await fetch('/observe/sessions/'+sid)).json();
          if (trace.error) { container.innerHTML = '<div class="empty">'+trace.error+'</div>'; }
          else {
            let html = '<div style="margin-bottom:8px;color:var(--muted);font-size:12px">'+trace.length+' events in session</div>';
            trace.forEach(ev => {
              const isInf = ev.event_type === 'inference';
              const isTool = ev.event_type === 'tool';
              const isErr = !ev.success;
              const cls = isTool ? 'trace-tool' : (isErr ? 'trace-error' : '');
              html += '<div class="trace-event '+cls+'">';
              html += '<div class="trace-meta">'+formatTime(ev.timestamp)+'</div>';
              html += '<div class="trace-body">';
              if (isInf) {
                html += '<span class="trace-type" style="color:var(--accent)">LLM</span>';
                html += '<span class="badge provider-badge" style="margin-right:6px">'+ev.provider+'</span>';
                html += ev.model;
                html += '<div class="trace-detail">';
                html += '<span class="duration">'+formatDuration(ev.duration_ms)+'</span>';
                const inT=ev.input_tokens||0, outT=ev.output_tokens||0;
                if (inT||outT) html += ' &middot; <span class="trace-tokens">'+formatTokens(inT)+' in / '+formatTokens(outT)+' out</span>';
                if (ev.tool_rounds) html += ' &middot; '+ev.tool_rounds+' tool rounds';
                if (ev.stop_reason) html += ' &middot; '+ev.stop_reason;
                if (isErr && ev.error_message) html += '<div style="color:var(--error);margin-top:4px">'+escapeHtml(ev.error_message)+'</div>';
                html += '</div>';
              } else {
                html += '<span class="trace-type" style="color:var(--success)">Tool</span>';
                html += '<span class="badge provider-badge">'+ev.tool_name+'</span>';
                html += '<div class="trace-detail">';
                html += '<span class="duration">'+formatDuration(ev.duration_ms)+'</span>';
                if (ev.action_category) html += ' &middot; '+ev.action_category;
                if (isErr && ev.error_message) html += '<div style="color:var(--error);margin-top:4px">'+escapeHtml(ev.error_message)+'</div>';
                html += '</div>';
              }
              html += '</div></div>';
            });
            container.innerHTML = html;
          }
          container.dataset.loaded = 'true';
        } catch(e) { container.innerHTML = '<div style="color:var(--error)">Failed to load trace.</div>'; }
      }
      row.classList.add('visible');
    }

    async function refreshSessions() {
      // Populate agent filter from stats
      try {
        const stats = await fetchStats();
        const sel = filterSessionAgent, cv = sel.value;
        sel.innerHTML = '<option value="">All Agents</option>';
        if (stats.calls_by_agent) Object.keys(stats.calls_by_agent).sort().forEach(a => { sel.innerHTML += '<option value="'+a+'">'+a+'</option>'; });
        sel.value = cv;
      } catch(e) {}
      sessionsOffset = 0;
      renderSessions(await fetchSessions(0));
    }

    filterSessionAgent.addEventListener('change', () => refreshSessions());
    document.getElementById('sessions-load-more').addEventListener('click', async () => {
      renderSessions(await fetchSessions(sessionsOffset), true);
    });

    /* ====== AGENTS TAB ====== */
    async function refreshAgents() {
      const agents = await (await fetch('/observe/agent-summary?period_hours='+currentPeriod)).json();
      const grid = document.getElementById('agent-grid');
      if (!agents.length) { grid.innerHTML = '<div class="empty" style="grid-column:1/-1">No agent data for this period</div>'; return; }
      let html = '';
      agents.forEach(a => {
        const totalTok = (a.total_input_tokens||0) + (a.total_output_tokens||0);
        const initial = a.agent.charAt(0).toUpperCase();
        // Mini model bar
        const modelEntries = Object.entries(a.top_models||{});
        const maxModel = Math.max(...modelEntries.map(e=>e[1]), 1);
        let modelBar = '';
        modelEntries.forEach((e,i) => {
          const h = Math.max(3, Math.round(e[1]/maxModel*16));
          modelBar += '<div class="mini-bar-seg" style="height:'+h+'px;background:'+COLORS[i%COLORS.length]+'" title="'+escapeHtml(e[0])+': '+e[1]+'"></div>';
        });
        // Mini tool bar
        const toolEntries = Object.entries(a.top_tools||{});
        const maxTool = Math.max(...toolEntries.map(e=>e[1]), 1);
        let toolBar = '';
        toolEntries.forEach((e,i) => {
          const h = Math.max(3, Math.round(e[1]/maxTool*16));
          toolBar += '<div class="mini-bar-seg" style="height:'+h+'px;background:'+COLORS[(i+5)%COLORS.length]+'" title="'+escapeHtml(e[0])+': '+e[1]+'"></div>';
        });

        html += '<div class="agent-card">';
        html += '<div class="agent-card-header">';
        html += '<div class="agent-avatar">'+initial+'</div>';
        html += '<div><div class="agent-name">'+escapeHtml(a.agent)+'</div>';
        html += '<div class="agent-meta">'+a.session_count+' sessions &middot; last seen '+formatDateTime(a.last_seen)+'</div>';
        html += '</div></div>';

        html += '<div class="agent-stats-row">';
        html += '<div class="agent-stat"><div class="agent-stat-value">'+a.call_count+'</div><div class="agent-stat-label">LLM Calls</div></div>';
        html += '<div class="agent-stat"><div class="agent-stat-value">'+formatTokens(totalTok)+'</div><div class="agent-stat-label">Tokens</div></div>';
        const errCls = a.error_rate > 5 ? 'error' : a.error_rate > 1 ? 'warning' : 'success';
        html += '<div class="agent-stat"><div class="agent-stat-value '+errCls+'">'+a.error_rate+'%</div><div class="agent-stat-label">Error Rate</div></div>';
        html += '</div>';

        html += '<div class="agent-details">';
        html += '<div class="agent-detail-row"><span class="agent-detail-label">Avg Latency</span><span class="duration">'+formatDuration(a.avg_latency_ms)+'</span></div>';
        html += '<div class="agent-detail-row"><span class="agent-detail-label">Tool Calls</span><span>'+a.tool_calls+'</span></div>';
        html += '<div class="agent-detail-row"><span class="agent-detail-label">Tool Avg Latency</span><span class="duration">'+formatDuration(a.tool_avg_latency_ms)+'</span></div>';
        html += '<div class="agent-detail-row"><span class="agent-detail-label">Tool Rounds (total)</span><span>'+a.total_tool_rounds+'</span></div>';
        if (modelEntries.length) {
          html += '<div class="agent-detail-row"><span class="agent-detail-label">Models</span><div class="mini-bar">'+modelBar+'</div></div>';
          html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 8px">';
          modelEntries.forEach((e,i) => { html += '<span style="font-size:11px;color:'+COLORS[i%COLORS.length]+'">'+escapeHtml(e[0])+' ('+e[1]+')</span>'; });
          html += '</div>';
        }
        if (toolEntries.length) {
          html += '<div class="agent-detail-row"><span class="agent-detail-label">Top Tools</span><div class="mini-bar">'+toolBar+'</div></div>';
          html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 0">';
          toolEntries.forEach((e,i) => { html += '<span style="font-size:11px;color:'+COLORS[(i+5)%COLORS.length]+'">'+escapeHtml(e[0])+' ('+e[1]+')</span>'; });
          html += '</div>';
        }
        html += '</div></div>';
      });
      grid.innerHTML = html;
    }

    /* ====== HEALTH TAB ====== */
    async function refreshHealth() {
      try {
        const resp = await fetch('/observe/health/deep');
        const data = await resp.json();
        const services = data.services || {};
        const names = Object.keys(services);

        // Summary cards
        const grid = document.getElementById('health-grid');
        const ok = names.filter(n => services[n].status === 'ok').length;
        const degraded = names.filter(n => services[n].status !== 'ok' && services[n].status !== 'not_configured').length;
        const unconfigured = names.filter(n => services[n].status === 'not_configured').length;
        grid.innerHTML = `
          <div class="stat-card">
            <div class="stat-label">Overall</div>
            <div class="stat-value" style="color:${data.status==='ok'?'var(--success)':'var(--warning)'}">${data.status.toUpperCase()}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Services Up</div>
            <div class="stat-value" style="color:var(--success)">${ok}</div>
          </div>
          ${degraded ? `<div class="stat-card"><div class="stat-label">Degraded</div><div class="stat-value" style="color:var(--error)">${degraded}</div></div>` : ''}
          ${unconfigured ? `<div class="stat-card"><div class="stat-label">Not Configured</div><div class="stat-value" style="color:var(--muted)">${unconfigured}</div></div>` : ''}
        `;

        // Detail table
        const tbody = document.getElementById('health-body');
        let html = '';
        for (const name of names) {
          const s = services[name];
          const statusColor = s.status === 'ok' ? 'var(--success)' : s.status === 'not_configured' ? 'var(--muted)' : 'var(--error)';
          const badge = `<span class="badge" style="background:${statusColor};color:#fff">${s.status}</span>`;
          const latency = s.latency_ms != null ? s.latency_ms + 'ms' : '—';
          const detail = s.detail || (s.http_status ? 'HTTP ' + s.http_status : '');
          html += `<tr><td style="font-weight:600">${escapeHtml(name)}</td><td>${badge}</td><td>${latency}</td><td style="color:var(--muted)">${escapeHtml(detail)}</td></tr>`;
        }
        tbody.innerHTML = html;
      } catch (e) {
        document.getElementById('health-grid').innerHTML = '<div class="stat-card"><div class="stat-label">Error</div><div class="stat-value" style="color:var(--error)">Failed to fetch</div></div>';
      }
    }

    /* ====== Initial load ====== */
    refreshOverview();
    refreshTools();
  </script>
</body>
</html>"""