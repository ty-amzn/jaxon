/* Paper Trading Dashboard — vanilla JS */

const API = '';  // same origin
let refreshTimer = null;
let currentAgent = null;
let perfChart = null;

// -- Helpers -----------------------------------------------------------------

function fmt(n, decimals = 2) {
  if (n == null) return '—';
  return n.toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
}

function fmtUsd(n) {
  if (n == null) return '—';
  const prefix = n < 0 ? '-$' : '$';
  return prefix + fmt(Math.abs(n));
}

function pnlClass(n) {
  if (n > 0) return 'pnl-positive';
  if (n < 0) return 'pnl-negative';
  return '';
}

function pnlBadge(n, pct) {
  const cls = n >= 0 ? 'positive' : 'negative';
  const sign = n >= 0 ? '+' : '';
  return `<span class="pnl-badge ${cls}">${sign}${fmtUsd(n)} (${sign}${fmt(pct)}%)</span>`;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

const NOTE_CAT_COLORS = {
  research: 'cat-research',
  thesis: 'cat-thesis',
  watchlist: 'cat-watchlist',
  lesson: 'cat-lesson',
  general: 'cat-general',
};

function renderNotesSection(notes, agent) {
  if (notes.length === 0) {
    return '<p style="color:var(--text-secondary);padding:12px 0">No notes yet</p>';
  }
  let html = '<div class="notes-list">';
  for (const n of notes) {
    const catCls = NOTE_CAT_COLORS[n.category] || 'cat-general';
    const date = new Date(n.updated_at);
    const timeStr = date.toLocaleString();
    html += `
      <div class="note-card">
        <div class="note-header">
          <span class="note-cat ${catCls}">${escapeHtml(n.category)}</span>
          <button class="note-delete-btn" onclick="deleteNote('${escapeHtml(agent)}', ${n.id})" title="Delete note">&times;</button>
        </div>
        <div class="note-title">${escapeHtml(n.title)}</div>
        <div class="note-content">${escapeHtml(n.content)}</div>
        <div class="note-meta">Updated ${timeStr}</div>
      </div>
    `;
  }
  html += '</div>';
  return html;
}

function eventTypeClass(type) {
  if (['buy', 'deposit', 'interest'].includes(type)) return 'pnl-positive';
  if (['sell', 'withdraw'].includes(type)) return 'pnl-negative';
  return '';
}

function renderActivityTable(events) {
  if (events.length === 0) {
    return '<p style="color:var(--text-secondary);padding:12px 0">No activity yet</p>';
  }
  let html = `
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Agent</th>
          <th>Event</th>
          <th>Description</th>
          <th class="number">Amount</th>
          <th class="number">Balance After</th>
        </tr>
      </thead>
      <tbody>
  `;
  for (const e of events) {
    const date = new Date(e.timestamp);
    const timeStr = date.toLocaleString();
    const cls = eventTypeClass(e.event_type);
    html += `
      <tr>
        <td>${timeStr}</td>
        <td>${e.agent_name}</td>
        <td class="${cls}" style="text-transform:uppercase;font-weight:600">${e.event_type}</td>
        <td>${e.description}</td>
        <td class="number">${e.amount != null ? fmtUsd(e.amount) : '—'}</td>
        <td class="number">${e.balance_after != null ? fmtUsd(e.balance_after) : '—'}</td>
      </tr>
    `;
  }
  html += '</tbody></table>';
  return html;
}

// -- Theme -------------------------------------------------------------------

function initTheme() {
  const saved = localStorage.getItem('pt-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('pt-theme', next);
}

// -- Overview ----------------------------------------------------------------

async function loadOverview() {
  currentAgent = null;
  const main = document.getElementById('main');
  main.innerHTML = '<div class="loading">Loading portfolios...</div>';

  try {
    const [summaryRes, portfoliosRes, activityRes] = await Promise.all([
      fetch(`${API}/trading/summary`),
      fetch(`${API}/trading/portfolios`),
      fetch(`${API}/trading/activity?limit=20`),
    ]);
    const summary = await summaryRes.json();
    const data = await portfoliosRes.json();
    const activityData = await activityRes.json();
    const portfolios = data.portfolios || [];
    const activity = activityData.activity || [];

    let html = `
      <div class="summary-row">
        <div class="summary-card">
          <div class="label">Agents</div>
          <div class="value">${summary.agent_count}</div>
        </div>
        <div class="summary-card">
          <div class="label">Total Value</div>
          <div class="value">${fmtUsd(summary.total_value)}</div>
        </div>
        <div class="summary-card">
          <div class="label">Total P&L</div>
          <div class="value ${pnlClass(summary.total_pnl)}">${fmtUsd(summary.total_pnl)}</div>
          <div class="sub">${summary.total_pnl >= 0 ? '+' : ''}${fmt(summary.total_pnl_pct)}%</div>
        </div>
        <div class="summary-card">
          <div class="label">Cash / Invested</div>
          <div class="value">${fmtUsd(summary.total_cash)}</div>
          <div class="sub">${fmtUsd(summary.total_invested)} invested</div>
        </div>
      </div>
    `;

    if (portfolios.length === 0) {
      html += `
        <div class="empty">
          No portfolios yet
          <div class="hint">Agents will appear here once they make their first trade</div>
        </div>
      `;
    } else {
      html += '<div class="agents-grid">';
      for (const p of portfolios) {
        html += `
          <div class="agent-card" onclick="loadAgent('${p.agent_name}')">
            <div class="agent-name">${p.agent_name}</div>
            <div class="stats">
              <div class="stat">
                <div class="stat-label">Total Value</div>
                <div class="stat-value">${fmtUsd(p.total_value)}</div>
              </div>
              <div class="stat">
                <div class="stat-label">P&L</div>
                <div class="stat-value">${pnlBadge(p.pnl, p.pnl_pct)}</div>
              </div>
              <div class="stat">
                <div class="stat-label">Cash</div>
                <div class="stat-value">${fmtUsd(p.current_cash)}</div>
              </div>
              <div class="stat">
                <div class="stat-label">Positions</div>
                <div class="stat-value">${p.position_count}</div>
              </div>
            </div>
          </div>
        `;
      }
      html += '</div>';
    }

    html += '<h3 class="section-title">Recent Activity</h3>';
    html += renderActivityTable(activity);

    main.innerHTML = html;
  } catch (err) {
    main.innerHTML = `<div class="empty">Failed to load data: ${err.message}</div>`;
  }
}

// -- Agent Detail ------------------------------------------------------------

async function loadAgent(agent) {
  currentAgent = agent;
  const main = document.getElementById('main');
  main.innerHTML = '<div class="loading">Loading portfolio...</div>';

  try {
    const [portfolioRes, activityRes, snapshotsRes, notesRes] = await Promise.all([
      fetch(`${API}/trading/portfolios/${agent}`),
      fetch(`${API}/trading/activity?agent=${encodeURIComponent(agent)}&limit=50`),
      fetch(`${API}/trading/portfolios/${agent}/snapshots`),
      fetch(`${API}/trading/portfolios/${agent}/notes?limit=50`),
    ]);
    const portfolioData = await portfolioRes.json();
    const activityData = await activityRes.json();
    const snapshotsData = await snapshotsRes.json();
    const notesData = await notesRes.json();

    if (portfolioData.error) {
      main.innerHTML = `<div class="empty">${portfolioData.error}</div>`;
      return;
    }

    const p = portfolioData.portfolio;
    const positions = portfolioData.positions || [];
    const agentActivity = activityData.activity || [];
    const snapshots = snapshotsData.snapshots || [];
    const notes = notesData.notes || [];

    let html = `
      <div class="detail-panel">
        <div class="detail-header">
          <h2>${agent}</h2>
          <div>
            <button class="back-btn" onclick="loadOverview()">Back</button>
            <button class="reset-btn" onclick="resetAgent('${agent}')">Reset</button>
          </div>
        </div>

        <div class="summary-row">
          <div class="summary-card">
            <div class="label">Total Value</div>
            <div class="value">${fmtUsd(p.total_value)}</div>
          </div>
          <div class="summary-card">
            <div class="label">Cash</div>
            <div class="value">${fmtUsd(p.current_cash)}</div>
          </div>
          <div class="summary-card">
            <div class="label">Invested</div>
            <div class="value">${fmtUsd(p.positions_value)}</div>
          </div>
          <div class="summary-card">
            <div class="label">P&L</div>
            <div class="value">${pnlBadge(p.pnl, p.pnl_pct)}</div>
          </div>
        </div>

        <h3 class="section-title">Positions</h3>
    `;

    if (positions.length === 0) {
      html += '<p style="color:var(--text-secondary);padding:12px 0">No open positions</p>';
    } else {
      html += `
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th class="number">Qty</th>
              <th class="number">Avg Cost</th>
              <th class="number">Price</th>
              <th class="number">Value</th>
              <th class="number">P&L</th>
            </tr>
          </thead>
          <tbody>
      `;
      for (const pos of positions) {
        html += `
          <tr>
            <td><strong>${pos.symbol}</strong></td>
            <td class="number">${fmt(pos.quantity, pos.quantity % 1 === 0 ? 0 : 2)}</td>
            <td class="number">${fmtUsd(pos.avg_cost)}</td>
            <td class="number">${fmtUsd(pos.current_price)}</td>
            <td class="number">${fmtUsd(pos.market_value)}</td>
            <td class="number ${pnlClass(pos.pnl)}">${fmtUsd(pos.pnl)} (${pos.pnl >= 0 ? '+' : ''}${fmt(pos.pnl_pct)}%)</td>
          </tr>
        `;
      }
      html += '</tbody></table>';
    }

    html += '<h3 class="section-title">Activity</h3>';
    html += renderActivityTable(agentActivity);

    html += '<h3 class="section-title">Notes</h3>';
    html += renderNotesSection(notes, agent);

    html += `
        <div class="chart-container">
          <h3>Performance</h3>
          <canvas id="perfChart" height="200"></canvas>
        </div>
      </div>
    `;

    main.innerHTML = html;

    // Render chart
    if (snapshots.length > 1) {
      renderChart(snapshots, p.starting_cash);
    }
  } catch (err) {
    main.innerHTML = `<div class="empty">Failed to load agent: ${err.message}</div>`;
  }
}

// -- Chart -------------------------------------------------------------------

function renderChart(snapshots, startingCash) {
  const canvas = document.getElementById('perfChart');
  if (!canvas) return;

  if (perfChart) {
    perfChart.destroy();
    perfChart = null;
  }

  const labels = snapshots.map(s => {
    const d = new Date(s.timestamp);
    return d.toLocaleString([], {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'});
  });
  const values = snapshots.map(s => s.total_value);

  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
  const gridColor = isDark ? 'rgba(255,255,255,.06)' : 'rgba(0,0,0,.06)';
  const textColor = isDark ? '#71767b' : '#536471';

  const lastValue = values[values.length - 1] || startingCash;
  const lineColor = lastValue >= startingCash ? '#10b981' : '#ef4444';
  const fillColor = lastValue >= startingCash ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)';

  perfChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Portfolio Value',
        data: values,
        borderColor: lineColor,
        backgroundColor: fillColor,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {display: false},
        tooltip: {
          callbacks: {
            label: (ctx) => '$' + fmt(ctx.parsed.y),
          }
        }
      },
      scales: {
        x: {
          ticks: {color: textColor, maxTicksLimit: 8},
          grid: {color: gridColor},
        },
        y: {
          ticks: {
            color: textColor,
            callback: (v) => '$' + (v >= 1000 ? (v/1000).toFixed(0) + 'k' : v),
          },
          grid: {color: gridColor},
        }
      }
    }
  });
}

// -- Reset -------------------------------------------------------------------

async function resetAgent(agent) {
  if (!confirm(`Reset ${agent}'s portfolio? This will clear all positions and orders.`)) return;

  try {
    await fetch(`${API}/trading/portfolios/${agent}/reset`, {method: 'POST'});
    loadAgent(agent);
  } catch (err) {
    alert('Reset failed: ' + err.message);
  }
}

// -- Delete Note -------------------------------------------------------------

async function deleteNote(agent, noteId) {
  if (!confirm('Delete this note?')) return;
  try {
    await fetch(`${API}/trading/portfolios/${agent}/notes/${noteId}`, {method: 'DELETE'});
    loadAgent(agent);
  } catch (err) {
    alert('Delete failed: ' + err.message);
  }
}

// -- Init --------------------------------------------------------------------

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    if (currentAgent) {
      loadAgent(currentAgent);
    } else {
      loadOverview();
    }
  }, 30000);
}

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadOverview();
  startAutoRefresh();
});
