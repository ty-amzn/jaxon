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
const CACHE='observatory-v1';
const SHELL=['/observe/ui','/observe/icon-192.svg'];
const API_RE=/\\/observe\\/(events|stats|tool-events|tool-stats)/;

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
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Observatory</title>
  <link rel="manifest" href="/observe/manifest.json">
  <link rel="icon" href="/observe/icon-192.svg">
  <meta name="theme-color" content="#0f1419">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #0f1419;
      --card: #161b22;
      --border: #30363d;
      --fg: #e6edf3;
      --muted: #7d8590;
      --accent: #58a6ff;
      --success: #3fb950;
      --error: #f85149;
      --warning: #d29922;
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
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }
    h1 { font-size: 24px; font-weight: 600; }
    .header-actions { display: flex; gap: 12px; align-items: center; }
    .period-select {
      background: var(--card);
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 14px;
    }
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
    tr:hover { background: rgba(255,255,255,0.02); }
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
    .agent-badge { background: rgba(210,153,255,0.2); color: #d299ff; }
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
    .load-more:hover { background: rgba(255,255,255,0.02); }
    .error-row td { color: var(--error); }
    .error-row .error-toggle {
      cursor: pointer;
      color: var(--muted);
      font-size: 12px;
    }
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
    .raw-row td {
      padding: 0;
      border-bottom: 1px solid var(--border);
    }
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
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🔭 Observatory</h1>
      <div class="header-actions">
        <select id="period-select" class="period-select">
          <option value="1">Last 1 hour</option>
          <option value="6">Last 6 hours</option>
          <option value="24" selected>Last 24 hours</option>
          <option value="168">Last 7 days</option>
          <option value="720">Last 30 days</option>
        </select>
        <button id="refresh-btn" class="period-select" style="cursor:pointer;" title="Refresh">&#x21bb; Refresh</button>
      </div>
    </header>

    <div class="stats-grid" id="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Calls</div>
        <div class="stat-value" id="stat-total">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Error Rate</div>
        <div class="stat-value" id="stat-error-rate">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Latency</div>
        <div class="stat-value" id="stat-latency">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Total Tokens</div>
        <div class="stat-value" id="stat-tokens">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Providers Used</div>
        <div class="stat-value" id="stat-providers">—</div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="chart-card">
        <div class="chart-title">Calls per Hour</div>
        <div class="chart-container">
          <canvas id="timeline-chart"></canvas>
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-title">Calls by Provider</div>
        <div class="chart-container">
          <canvas id="provider-chart"></canvas>
        </div>
      </div>
    </div>

    <div class="table-card">
      <div class="table-header">
        <div class="table-title">Recent Events</div>
        <div class="filters">
          <select id="filter-provider" class="filter-input">
            <option value="">All Providers</option>
          </select>
          <select id="filter-agent" class="filter-input">
            <option value="">All Agents</option>
          </select>
          <select id="filter-success" class="filter-input">
            <option value="">All Status</option>
            <option value="true">Success</option>
            <option value="false">Errors</option>
          </select>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Agent</th>
            <th>Provider</th>
            <th>Model</th>
            <th>Duration</th>
            <th>Tokens (In/Out)</th>
            <th>Stop</th>
            <th>Tool Rounds</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="events-body">
        </tbody>
      </table>
      <button class="load-more" id="load-more">Load more</button>
    </div>

    <!-- Tool Calls Section -->
    <h2 style="margin: 32px 0 16px; font-size: 20px; font-weight: 600; border-top: 1px solid var(--border); padding-top: 24px;">🔧 Tool Calls</h2>

    <div class="stats-grid" id="tool-stats-grid">
      <div class="stat-card">
        <div class="stat-label">Total Tool Calls</div>
        <div class="stat-value" id="stat-tool-total">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tool Error Rate</div>
        <div class="stat-value" id="stat-tool-error-rate">—</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Avg Tool Latency</div>
        <div class="stat-value" id="stat-tool-latency">—</div>
      </div>
    </div>

    <div class="charts-grid">
      <div class="chart-card">
        <div class="chart-title">Top Tools</div>
        <div class="chart-container">
          <canvas id="tool-chart"></canvas>
        </div>
      </div>
    </div>

    <div class="table-card" id="tool-events-card">
      <div class="table-header">
        <div class="table-title">Recent Tool Calls</div>
        <div class="filters">
          <select id="filter-tool-name" class="filter-input">
            <option value="">All Tools</option>
          </select>
          <select id="filter-tool-success" class="filter-input">
            <option value="">All Status</option>
            <option value="true">Success</option>
            <option value="false">Errors</option>
          </select>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Agent</th>
            <th>Tool</th>
            <th>Duration</th>
            <th>Category</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody id="tool-events-body">
        </tbody>
      </table>
      <button class="load-more" id="tool-load-more">Load more</button>
    </div>
  </div>

  <script>
    let timelineChart = null;
    let providerChart = null;
    let toolChart = null;
    let lastEventId = null;
    let lastToolEventId = null;
    let currentPeriod = 24;

    const periodSelect = document.getElementById('period-select');
    const filterProvider = document.getElementById('filter-provider');
    const filterAgent = document.getElementById('filter-agent');
    const filterSuccess = document.getElementById('filter-success');
    const loadMoreBtn = document.getElementById('load-more');

    async function fetchStats() {
      const res = await fetch(`/observe/stats?period_hours=${currentPeriod}`);
      return res.json();
    }

    async function fetchEvents(beforeId = null) {
      let url = '/observe/events?limit=50';
      if (beforeId) url += `&before_id=${beforeId}`;
      const provider = filterProvider.value;
      const agent = filterAgent.value;
      const success = filterSuccess.value;
      if (provider) url += `&provider=${provider}`;
      if (agent) url += `&agent_name=${agent}`;
      if (success) url += `&success=${success}`;
      const res = await fetch(url);
      return res.json();
    }

    function formatDuration(ms) {
      if (ms < 1000) return `${ms}ms`;
      if (ms < 60000) return `${(ms/1000).toFixed(1)}s`;
      return `${(ms/60000).toFixed(1)}m`;
    }

    function formatTime(iso) {
      const d = new Date(iso);
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function formatTokens(n) {
      if (n >= 1000000) return (n/1000000).toFixed(1) + 'M';
      if (n >= 1000) return (n/1000).toFixed(1) + 'K';
      return n.toLocaleString();
    }

    function updateStats(stats) {
      document.getElementById('stat-total').textContent = stats.total_calls.toLocaleString();

      const errorEl = document.getElementById('stat-error-rate');
      errorEl.textContent = stats.error_rate.toFixed(1) + '%';
      errorEl.className = 'stat-value ' + (stats.error_rate > 5 ? 'error' : stats.error_rate > 1 ? 'warning' : 'success');

      const latencyEl = document.getElementById('stat-latency');
      latencyEl.textContent = formatDuration(stats.avg_latency_ms);

      const totalTokens = (stats.total_input_tokens || 0) + (stats.total_output_tokens || 0);
      document.getElementById('stat-tokens').textContent = formatTokens(totalTokens);

      document.getElementById('stat-providers').textContent = Object.keys(stats.calls_by_provider).length;
    }

    function updateTimelineChart(stats) {
      const ctx = document.getElementById('timeline-chart').getContext('2d');
      const labels = stats.calls_per_hour.map(h => h.hour.slice(11, 16));
      const data = stats.calls_per_hour.map(h => h.count);

      if (timelineChart) timelineChart.destroy();
      timelineChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: 'Calls',
            data,
            borderColor: '#58a6ff',
            backgroundColor: 'rgba(88,166,255,0.1)',
            fill: true,
            tension: 0.3,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: '#30363d' }, ticks: { color: '#7d8590' } },
            y: { grid: { color: '#30363d' }, ticks: { color: '#7d8590' }, beginAtZero: true }
          }
        }
      });
    }

    function updateProviderChart(stats) {
      const ctx = document.getElementById('provider-chart').getContext('2d');
      const labels = Object.keys(stats.calls_by_provider);
      const data = Object.values(stats.calls_by_provider);
      const colors = ['#58a6ff', '#3fb950', '#f0883e', '#a371f7', '#f85149'];

      if (providerChart) providerChart.destroy();
      providerChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: colors.slice(0, labels.length),
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: { color: '#e6edf3' }
            }
          }
        }
      });
    }

    function renderEvents(events, append = false) {
      const tbody = document.getElementById('events-body');
      if (!append) tbody.innerHTML = '';

      if (events.length === 0 && !append) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">No events recorded</td></tr>';
        return;
      }

      events.forEach(event => {
        const tr = document.createElement('tr');
        tr.dataset.id = event.id;
        tr.classList.add('clickable-row');
        if (!event.success) tr.classList.add('error-row');

        const statusHtml = event.success
          ? '<span class="badge badge-success">OK</span>'
          : '<span class="badge badge-error">Error</span>';

        const inTok = event.input_tokens || 0;
        const outTok = event.output_tokens || 0;
        const tokHtml = (inTok || outTok) ? `${formatTokens(inTok)} / ${formatTokens(outTok)}` : '—';
        const stopHtml = event.stop_reason || '—';

        const agentName = event.agent_name || 'jax';
        tr.innerHTML = `
          <td>${formatTime(event.timestamp)}</td>
          <td><span class="badge agent-badge">${agentName}</span></td>
          <td><span class="badge provider-badge">${event.provider}</span></td>
          <td>${event.model}</td>
          <td class="duration">${formatDuration(event.duration_ms)}</td>
          <td class="token-col">${tokHtml}</td>
          <td class="stop-col">${stopHtml}</td>
          <td>${event.tool_rounds}</td>
          <td>${statusHtml}</td>
        `;

        tr.addEventListener('click', () => toggleRaw(event.id));
        tbody.appendChild(tr);

        // Raw content expansion row (hidden by default)
        const rawRow = document.createElement('tr');
        rawRow.classList.add('raw-row');
        rawRow.id = `raw-${event.id}`;
        rawRow.innerHTML = `<td colspan="9"><div class="raw-content" id="raw-content-${event.id}">Loading...</div></td>`;
        tbody.appendChild(rawRow);

        if (!event.success && event.error_message) {
          const errorRow = document.createElement('tr');
          errorRow.id = `error-${event.id}`;
          errorRow.innerHTML = `<td colspan="9" class="error-message">${event.error_message}</td>`;
          tbody.appendChild(errorRow);
        }
      });

      if (events.length > 0) {
        lastEventId = events[events.length - 1].id;
      }
    }

    async function toggleRaw(id) {
      const contentEl = document.getElementById(`raw-content-${id}`);
      if (contentEl.classList.contains('visible')) {
        contentEl.classList.remove('visible');
        return;
      }
      // Lazy-load raw content
      if (contentEl.dataset.loaded !== 'true') {
        try {
          const res = await fetch(`/observe/events/${id}/raw`);
          const data = await res.json();
          let html = '';
          if (data.raw_prompt) {
            html += `<div class="raw-section"><div class="raw-label">Prompt</div><div class="raw-text">${escapeHtml(data.raw_prompt)}</div></div>`;
          }
          if (data.raw_response) {
            html += `<div class="raw-section"><div class="raw-label">Response</div><div class="raw-text">${escapeHtml(data.raw_response)}</div></div>`;
          }
          if (!data.raw_prompt && !data.raw_response) {
            html = '<div style="color:var(--muted);padding:8px;">No raw content available (may have been cleaned up).</div>';
          }
          contentEl.innerHTML = html;
          contentEl.dataset.loaded = 'true';
        } catch (e) {
          contentEl.innerHTML = '<div style="color:var(--error);padding:8px;">Failed to load raw content.</div>';
        }
      }
      contentEl.classList.add('visible');
    }

    function escapeHtml(text) {
      const d = document.createElement('div');
      d.textContent = text;
      return d.innerHTML;
    }

    function toggleError(id) {
      const el = document.getElementById(`error-${id}`);
      if (el) el.classList.toggle('visible');
    }

    function updateProviderFilter(stats) {
      const select = document.getElementById('filter-provider');
      const currentValue = select.value;
      select.innerHTML = '<option value="">All Providers</option>';
      Object.keys(stats.calls_by_provider).sort().forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        select.appendChild(opt);
      });
      select.value = currentValue;
    }

    function updateAgentFilter(stats) {
      const select = document.getElementById('filter-agent');
      const currentValue = select.value;
      select.innerHTML = '<option value="">All Agents</option>';
      if (stats.calls_by_agent) {
        Object.keys(stats.calls_by_agent).sort().forEach(a => {
          const opt = document.createElement('option');
          opt.value = a;
          opt.textContent = `${a} (${stats.calls_by_agent[a]})`;
          select.appendChild(opt);
        });
      }
      select.value = currentValue;
    }

    async function refresh() {
      const stats = await fetchStats();
      updateStats(stats);
      updateTimelineChart(stats);
      updateProviderChart(stats);
      updateProviderFilter(stats);
      updateAgentFilter(stats);

      lastEventId = null;
      const events = await fetchEvents();
      renderEvents(events);
    }

    async function loadMore() {
      if (!lastEventId) return;
      const events = await fetchEvents(lastEventId);
      renderEvents(events, true);
    }

    periodSelect.addEventListener('change', () => {
      currentPeriod = parseInt(periodSelect.value);
      refresh();
      refreshTools();
    });

    filterProvider.addEventListener('change', () => {
      lastEventId = null;
      fetchEvents().then(events => renderEvents(events));
    });

    filterSuccess.addEventListener('change', () => {
      lastEventId = null;
      fetchEvents().then(events => renderEvents(events));
    });

    filterAgent.addEventListener('change', () => {
      lastEventId = null;
      fetchEvents().then(events => renderEvents(events));
    });

    loadMoreBtn.addEventListener('click', loadMore);

    document.getElementById('refresh-btn').addEventListener('click', () => {
      refresh();
      refreshTools();
    });

    // -- Tool Events ----------------------------------------------------------

    const filterToolName = document.getElementById('filter-tool-name');
    const filterToolSuccess = document.getElementById('filter-tool-success');
    const toolLoadMoreBtn = document.getElementById('tool-load-more');

    async function fetchToolStats() {
      const res = await fetch(`/observe/tool-stats?period_hours=${currentPeriod}`);
      return res.json();
    }

    async function fetchToolEvents(beforeId = null) {
      let url = '/observe/tool-events?limit=50';
      if (beforeId) url += `&before_id=${beforeId}`;
      const tn = filterToolName.value;
      const success = filterToolSuccess.value;
      if (tn) url += `&tool_name=${tn}`;
      if (success) url += `&success=${success}`;
      const res = await fetch(url);
      return res.json();
    }

    function updateToolStats(stats) {
      document.getElementById('stat-tool-total').textContent = stats.total_calls.toLocaleString();

      const errEl = document.getElementById('stat-tool-error-rate');
      errEl.textContent = stats.error_rate.toFixed(1) + '%';
      errEl.className = 'stat-value ' + (stats.error_rate > 5 ? 'error' : stats.error_rate > 1 ? 'warning' : 'success');

      document.getElementById('stat-tool-latency').textContent = formatDuration(stats.avg_duration_ms);
    }

    function updateToolChart(stats) {
      const ctx = document.getElementById('tool-chart').getContext('2d');
      const entries = Object.entries(stats.calls_by_tool || {}).slice(0, 15);
      const labels = entries.map(e => e[0]);
      const data = entries.map(e => e[1]);
      const colors = ['#58a6ff','#3fb950','#f0883e','#a371f7','#f85149','#d29922','#79c0ff','#56d364','#ffa657','#bc8cff','#ff7b72','#e3b341','#a5d6ff','#7ee787','#ffc680'];

      if (toolChart) toolChart.destroy();
      toolChart = new Chart(ctx, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Calls',
            data,
            backgroundColor: colors.slice(0, labels.length),
          }]
        },
        options: {
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: '#30363d' }, ticks: { color: '#7d8590' }, beginAtZero: true },
            y: { grid: { display: false }, ticks: { color: '#e6edf3', font: { size: 11 } } }
          }
        }
      });
    }

    function updateToolNameFilter(stats) {
      const select = filterToolName;
      const currentValue = select.value;
      select.innerHTML = '<option value="">All Tools</option>';
      Object.keys(stats.calls_by_tool || {}).sort().forEach(t => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        select.appendChild(opt);
      });
      select.value = currentValue;
    }

    function renderToolEvents(events, append = false) {
      const tbody = document.getElementById('tool-events-body');
      if (!append) tbody.innerHTML = '';

      if (events.length === 0 && !append) {
        tbody.innerHTML = '<tr><td colspan="6" class="empty">No tool events recorded</td></tr>';
        return;
      }

      events.forEach(event => {
        const tr = document.createElement('tr');
        if (!event.success) tr.classList.add('error-row');

        const statusHtml = event.success
          ? '<span class="badge badge-success">OK</span>'
          : '<span class="badge badge-error">Error</span>';

        const agentName = event.agent_name || 'jax';
        const category = event.action_category || '—';
        tr.innerHTML = `
          <td>${formatTime(event.timestamp)}</td>
          <td><span class="badge agent-badge">${agentName}</span></td>
          <td><span class="badge provider-badge">${event.tool_name}</span></td>
          <td class="duration">${formatDuration(event.duration_ms)}</td>
          <td>${category}</td>
          <td>${statusHtml}</td>
        `;

        tbody.appendChild(tr);

        if (!event.success && event.error_message) {
          const errorRow = document.createElement('tr');
          errorRow.innerHTML = `<td colspan="6" class="error-message visible">${escapeHtml(event.error_message)}</td>`;
          tbody.appendChild(errorRow);
        }
      });

      if (events.length > 0) {
        lastToolEventId = events[events.length - 1].id;
      }
    }

    async function refreshTools() {
      const stats = await fetchToolStats();
      updateToolStats(stats);
      updateToolChart(stats);
      updateToolNameFilter(stats);

      lastToolEventId = null;
      const events = await fetchToolEvents();
      renderToolEvents(events);
    }

    filterToolName.addEventListener('change', () => {
      lastToolEventId = null;
      fetchToolEvents().then(events => renderToolEvents(events));
    });

    filterToolSuccess.addEventListener('change', () => {
      lastToolEventId = null;
      fetchToolEvents().then(events => renderToolEvents(events));
    });

    toolLoadMoreBtn.addEventListener('click', async () => {
      if (!lastToolEventId) return;
      const events = await fetchToolEvents(lastToolEventId);
      renderToolEvents(events, true);
    });

    // Initial load
    refresh();
    refreshTools();
  </script>
</body>
</html>"""