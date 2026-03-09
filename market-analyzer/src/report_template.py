"""
report_template.py — Jinja2 HTML template builder for market analysis reports.
Produces a single self-contained HTML file with all CSS/JS inline.
Uses Plotly CDN for charts, everything else is inline.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─────────────────────────── CSS ────────────────────────────

CSS = """
:root {
  --bg: #0d1117;
  --card-bg: #161b22;
  --border: #21262d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --green: #00b894;
  --red: #d63031;
  --yellow: #fdcb6e;
  --gray: #636e72;
  --blue: #4fc3f7;
  --purple: #ce93d8;
  --header-bg: #10151c;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
}
a { color: var(--blue); text-decoration: none; }

/* ── Header ─────────────────────────────────────────── */
.header {
  background: var(--header-bg);
  border-bottom: 1px solid var(--border);
  padding: 12px 20px;
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.header-title { font-size: 16px; font-weight: 700; color: var(--blue); white-space: nowrap; }
.header-date { color: var(--text-muted); font-size: 12px; }
.cat-tabs { display: flex; gap: 6px; flex-wrap: wrap; }
.cat-tab {
  padding: 4px 12px;
  border-radius: 20px;
  background: var(--border);
  cursor: pointer;
  font-size: 12px;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.cat-tab:hover, .cat-tab.active { background: var(--blue); color: #000; border-color: var(--blue); }
.view-toggle {
  margin-left: auto;
  padding: 6px 14px;
  border-radius: 6px;
  background: var(--border);
  border: 1px solid #444;
  color: var(--text);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.view-toggle:hover { background: #2a3040; }

/* ── Main layout ────────────────────────────────────── */
.container { max-width: 1400px; margin: 0 auto; padding: 16px; }
.section { margin-bottom: 32px; }
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}

/* ── Günün Fırsatları Panel ─────────────────────────── */
.opportunities-panel {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 20px;
}
.opportunities-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.opportunities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.opp-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.opp-card:hover { border-color: var(--blue); transform: translateY(-2px); }
.opp-badge {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 12px;
  display: inline-block;
  margin-bottom: 6px;
}
.opp-symbol { font-weight: 700; font-size: 14px; margin-bottom: 2px; }
.opp-name { color: var(--text-muted); font-size: 11px; margin-bottom: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.opp-rr { font-size: 12px; color: var(--blue); font-weight: 600; }
.opp-reason { font-size: 11px; color: var(--text-muted); margin-top: 4px; }

/* ── Summary Table ──────────────────────────────────── */
.summary-table-wrap {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 20px;
}
.summary-table {
  width: 100%;
  border-collapse: collapse;
}
.summary-table th {
  background: var(--bg);
  padding: 10px 14px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  cursor: pointer;
  white-space: nowrap;
  border-bottom: 1px solid var(--border);
}
.summary-table th:hover { color: var(--text); }
.summary-table th::after { content: ' ↕'; color: var(--border); }
.summary-table td {
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  vertical-align: middle;
}
.summary-table tr:last-child td { border-bottom: none; }
.summary-table tr:hover td { background: rgba(255,255,255,0.03); cursor: pointer; }
.price-change.positive { color: var(--green); }
.price-change.negative { color: var(--red); }

/* ── Status Badges ──────────────────────────────────── */
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.badge-al    { background: rgba(0,184,148,0.15); color: #00b894; border: 1px solid rgba(0,184,148,0.3); }
.badge-sat   { background: rgba(214,48,49,0.15);  color: #d63031; border: 1px solid rgba(214,48,49,0.3); }
.badge-izle  { background: rgba(253,203,110,0.15); color: #fdcb6e; border: 1px solid rgba(253,203,110,0.3); }
.badge-notr  { background: rgba(99,110,114,0.15);  color: #8b949e; border: 1px solid rgba(99,110,114,0.3); }

/* ── Instrument Card ────────────────────────────────── */
.instrument-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 10px;
  margin-bottom: 14px;
  overflow: hidden;
  transition: border-color 0.2s;
}
.instrument-card:hover { border-color: #3a3a5a; }

/* Card Header — Layer 1 */
.card-header {
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  user-select: none;
}
.card-status-badge { min-width: 72px; text-align: center; }
.card-status-badge .badge { font-size: 13px; padding: 5px 12px; }
.card-info { flex: 1; min-width: 0; }
.card-symbol { font-weight: 700; font-size: 16px; }
.card-name { color: var(--text-muted); font-size: 12px; margin-top: 1px; }
.card-price-row { display: flex; align-items: baseline; gap: 10px; margin-top: 4px; }
.card-price { font-size: 18px; font-weight: 700; }
.card-metrics { display: flex; gap: 16px; align-items: center; margin-left: auto; }
.metric { text-align: center; }
.metric-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; }
.metric-value { font-size: 13px; font-weight: 600; margin-top: 1px; }
.trend-badge {
  padding: 3px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.trend-up    { background: rgba(0,184,148,0.15); color: var(--green); }
.trend-down  { background: rgba(214,48,49,0.15);  color: var(--red); }
.trend-flat  { background: rgba(99,110,114,0.15);  color: var(--gray); }
.expand-icon { color: var(--text-muted); font-size: 16px; transition: transform 0.2s; }
.card-header.expanded .expand-icon { transform: rotate(180deg); }

/* Card Summary — Layer 2 */
.card-summary {
  padding: 14px 18px;
  border-top: 1px solid var(--border);
  background: rgba(0,0,0,0.15);
}
.summary-action {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text);
}
.summary-action span { color: var(--blue); }
.summary-entry {
  background: rgba(0,0,0,0.3);
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 10px;
  font-size: 13px;
}
.summary-entry .entry-label { color: var(--text-muted); font-size: 11px; margin-bottom: 4px; }
.targets-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 6px; }
.target-item { flex: 1; min-width: 120px; background: rgba(0,184,148,0.08); border-radius: 4px; padding: 6px 10px; font-size: 12px; }
.stop-item { flex: 1; min-width: 120px; background: rgba(214,48,49,0.08); border-radius: 4px; padding: 6px 10px; font-size: 12px; }
.rr-item { font-size: 12px; color: var(--blue); font-weight: 700; align-self: center; }

/* Scenario Tree */
.scenario-tree {
  background: rgba(0,0,0,0.2);
  border-radius: 6px;
  padding: 12px 14px;
  margin-top: 10px;
}
.scenario-title { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 8px; }
.scenario-branch {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px;
  align-items: start;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  font-size: 12px;
}
.scenario-branch:last-child { border-bottom: none; }
.scenario-icon { font-size: 14px; }
.scenario-condition { color: var(--text-muted); }
.scenario-outcome { text-align: right; }
.scenario-action { font-weight: 700; color: var(--text); }
.scenario-detail { color: var(--text-muted); font-size: 11px; }

/* Expand toggle button */
.expand-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  padding: 6px 14px;
  border-radius: 6px;
  background: var(--border);
  border: 1px solid #3a3a5a;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.expand-btn:hover { color: var(--text); background: #2a2a4a; }

/* Card Detail — Layer 3 */
.card-detail {
  padding: 16px 18px;
  border-top: 1px solid var(--border);
  display: none;
}
.card-detail.visible { display: block; }

/* Timeframe tabs */
.tf-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.tf-tab {
  padding: 4px 12px;
  border-radius: 4px;
  background: var(--border);
  cursor: pointer;
  font-size: 12px;
  border: 1px solid transparent;
  transition: all 0.15s;
}
.tf-tab:hover, .tf-tab.active { background: var(--blue); color: #000; border-color: var(--blue); }
.tf-content { display: none; }
.tf-content.active { display: block; }
.chart-container { min-height: 200px; }
.narrative-box {
  background: rgba(0,0,0,0.2);
  border-radius: 6px;
  padding: 12px 14px;
  margin-top: 14px;
  font-size: 13px;
  line-height: 1.7;
}
.narrative-section { margin-bottom: 10px; }
.narrative-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 4px; }

/* Card Action Plans — Layer 4 */
.card-plans {
  padding: 14px 18px;
  border-top: 1px solid var(--border);
  display: none;
}
.card-plans.visible { display: block; }
.plans-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 700px) { .plans-grid { grid-template-columns: 1fr; } }
.plan-card {
  border-radius: 8px;
  padding: 14px;
  border-left: 3px solid;
}
.plan-long  { background: rgba(0,184,148,0.07); border-color: var(--green); }
.plan-short { background: rgba(214,48,49,0.07);  border-color: var(--red); }
.plan-dominant { box-shadow: 0 0 12px rgba(0,184,148,0.15); }
.plan-header { font-weight: 700; font-size: 14px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
.plan-dominant-badge { font-size: 10px; background: var(--green); color: #000; padding: 2px 8px; border-radius: 10px; font-weight: 700; }
.plan-section-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-top: 10px; margin-bottom: 4px; }
.plan-entry-zone { font-size: 14px; font-weight: 700; color: var(--blue); }
.plan-reasoning { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
.plan-targets { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
.plan-target-row { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 8px; border-radius: 4px; background: rgba(255,255,255,0.04); }
.plan-target-label { color: var(--text-muted); }
.plan-target-rr { color: var(--blue); font-weight: 600; }
.plan-stop { margin-top: 10px; padding: 8px; background: rgba(214,48,49,0.1); border-radius: 4px; }
.plan-stop-price { font-size: 14px; font-weight: 700; color: var(--red); }
.plan-stop-reason { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.plan-trigger { font-size: 12px; color: var(--text-muted); margin-top: 8px; font-style: italic; }
.plan-quality-warning { font-size: 11px; color: var(--yellow); margin-top: 6px; padding: 4px 8px; background: rgba(253,203,110,0.1); border-radius: 4px; }

/* Narratives section */
.narratives-box {
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 14px;
}
.narratives-title { font-size: 12px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; margin-bottom: 10px; }
.narrative-item { margin-bottom: 10px; }
.narrative-item-label { font-size: 11px; color: var(--text-muted); }
.narrative-item-text { font-size: 13px; color: var(--text); margin: 4px 0; }
.confidence-badge {
  display: inline-block;
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 10px;
}
.conf-yuksek { background: rgba(0,184,148,0.15); color: var(--green); }
.conf-orta   { background: rgba(253,203,110,0.15); color: var(--yellow); }
.conf-dusuk  { background: rgba(99,110,114,0.15); color: var(--gray); }

/* Category section */
.category-section { margin-bottom: 32px; }
.category-header {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
  padding: 8px 14px;
  background: var(--card-bg);
  border-radius: 6px;
  border-left: 3px solid var(--blue);
}

/* Heatmap table */
.heatmap-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.heatmap-table th, .heatmap-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
.heatmap-table th { background: var(--bg); color: var(--text-muted); cursor: pointer; }
.heatmap-table tr:hover td { background: rgba(255,255,255,0.02); }

/* Simple/Detail view toggle */
body.simple-view .card-summary { display: block; }
body.detail-view .card-detail { display: block; }
body.detail-view .card-plans { display: block; }

/* Responsive */
@media (max-width: 768px) {
  .header { padding: 10px; gap: 8px; }
  .card-metrics { display: none; }
  .container { padding: 10px; }
  .opportunities-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 480px) {
  .opportunities-grid { grid-template-columns: 1fr; }
  .plans-grid { grid-template-columns: 1fr; }
}
"""

# ─────────────────────────── JavaScript ─────────────────────

JS = """
// Category filter
function filterCategory(cat) {
  document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.category-section').forEach(section => {
    if (cat === 'all' || section.dataset.category === cat) {
      section.style.display = '';
    } else {
      section.style.display = 'none';
    }
  });
}

// Toggle instrument card detail
function toggleCard(id) {
  const header = document.getElementById('header-' + id);
  const detail = document.getElementById('detail-' + id);
  const plans = document.getElementById('plans-' + id);
  const isExpanded = detail.classList.contains('visible');
  header.classList.toggle('expanded', !isExpanded);
  detail.classList.toggle('visible', !isExpanded);
  if (plans) plans.classList.toggle('visible', !isExpanded);
}

// Toggle just the detail layer (expand button)
function toggleDetail(id) {
  event.stopPropagation();
  const detail = document.getElementById('detail-' + id);
  const plans = document.getElementById('plans-' + id);
  const isVisible = detail.classList.contains('visible');
  detail.classList.toggle('visible', !isVisible);
  if (plans) plans.classList.toggle('visible', !isVisible);
  const btn = document.getElementById('expand-btn-' + id);
  if (btn) btn.textContent = isVisible ? '▼ Teknik Detayları Göster' : '▲ Detayları Gizle';
}

// Timeframe tab switcher
function switchTf(symbol, tf) {
  const safeSym = symbol.replace(/[^a-zA-Z0-9]/g, '_');
  const safeTf = tf.replace(/[^a-zA-Z0-9]/g, '_');
  document.querySelectorAll('.tf-tab[data-sym="' + safeSym + '"]').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tf-content[data-sym="' + safeSym + '"]').forEach(c => c.classList.remove('active'));
  event.target.classList.add('active');
  const content = document.getElementById('tf-' + safeSym + '-' + safeTf);
  if (content) content.classList.add('active');
}

// Simple / Detail view toggle
let isDetailed = false;
function toggleView() {
  isDetailed = !isDetailed;
  const btn = document.getElementById('view-toggle');
  if (isDetailed) {
    document.body.classList.add('detail-view');
    document.body.classList.remove('simple-view');
    btn.textContent = '📋 Basit Görünüm';
  } else {
    document.body.classList.remove('detail-view');
    document.body.classList.add('simple-view');
    btn.textContent = '📊 Detaylı Görünüm';
  }
}

// Summary table sort
function sortTable(tableId, colIdx) {
  const table = document.getElementById(tableId);
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const asc = table.dataset.sortAsc === colIdx.toString();
  table.dataset.sortAsc = asc ? '' : colIdx.toString();
  rows.sort((a, b) => {
    const aText = a.cells[colIdx]?.textContent.trim() || '';
    const bText = b.cells[colIdx]?.textContent.trim() || '';
    const aNum = parseFloat(aText.replace(/[^\\d.-]/g, ''));
    const bNum = parseFloat(bText.replace(/[^\\d.-]/g, ''));
    if (!isNaN(aNum) && !isNaN(bNum)) return asc ? bNum - aNum : aNum - bNum;
    return asc ? bText.localeCompare(aText) : aText.localeCompare(bText);
  });
  rows.forEach(r => tbody.appendChild(r));
}

// Jump to instrument card
function jumpTo(id) {
  const el = document.getElementById('card-' + id);
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.style.boxShadow = '0 0 20px rgba(79,195,247,0.4)';
    setTimeout(() => el.style.boxShadow = '', 2000);
  }
}

// On load: set simple view as default
document.addEventListener('DOMContentLoaded', () => {
  document.body.classList.add('simple-view');
});
"""

# ─────────────────────────── Template helpers ───────────────


def _badge_class(status: str) -> str:
    return {
        "Al": "badge-al",
        "Sat": "badge-sat",
        "İzle": "badge-izle",
        "Nötr": "badge-notr",
    }.get(status, "badge-notr")


def _badge_icon(status: str) -> str:
    return {"Al": "🟢", "Sat": "🔴", "İzle": "🟡", "Nötr": "⚪"}.get(status, "⚪")


def _trend_class(label: str) -> str:
    if "Yükseliş" in label:
        return "trend-up"
    elif "Düşüş" in label:
        return "trend-down"
    return "trend-flat"


def _fmt_price(price: float) -> str:
    if not price:
        return "N/A"
    if price >= 1000:
        return f"{price:,.0f}"
    elif price >= 10:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.3f}"
    else:
        return f"{price:.5f}"


def _pct(val: float) -> str:
    if val is None:
        return "N/A"
    sign = "+" if val >= 0 else ""
    cls = "positive" if val >= 0 else "negative"
    return f'<span class="price-change {cls}">{sign}{val:.2f}%</span>'


def _safe_id(symbol: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9]", "_", symbol)


def _conf_class(conf: str) -> str:
    return {"Yüksek": "conf-yuksek", "Orta": "conf-orta", "Düşük": "conf-dusuk"}.get(conf, "conf-dusuk")


# ─────────────────────────── Section renderers ──────────────


def _render_opportunities(opportunities: list) -> str:
    if not opportunities:
        return ""
    cards = ""
    for opp in opportunities:
        sid = _safe_id(opp["symbol"])
        status = opp["action_status"]
        badge_cls = _badge_class(status)
        icon = _badge_icon(status)
        rr_text = opp.get("rr_text", "")
        reason = opp.get("reason", "")
        cards += f"""
        <div class="opp-card" onclick="jumpTo('{sid}')">
          <div class="opp-badge badge {badge_cls}">{icon} {status}</div>
          <div class="opp-symbol">{opp["symbol"]}</div>
          <div class="opp-name">{opp.get("display_name", "")}</div>
          <div class="opp-rr">{rr_text}</div>
          <div class="opp-reason">{reason}</div>
        </div>"""
    return f"""
    <div class="opportunities-panel">
      <div class="opportunities-title">⚡ GÜNÜN FIRSATLARI</div>
      <div class="opportunities-grid">{cards}</div>
    </div>"""


def _render_summary_table(instruments: list) -> str:
    rows = ""
    for inst in instruments:
        sid = _safe_id(inst["symbol"])
        status = inst["action_status"]
        badge_cls = _badge_class(status)
        icon = _badge_icon(status)
        trend = inst.get("overall_trend", "Yatay")
        trend_cls = _trend_class(trend)
        rsi = inst.get("rsi")
        rsi_str = f"{rsi:.0f}" if rsi else "—"
        rr = inst.get("rr_t1")
        rr_str = f"1:{rr}" if rr else "—"
        rows += f"""
        <tr onclick="jumpTo('{sid}')">
          <td><strong>{inst["symbol"]}</strong></td>
          <td style="color:var(--text-muted);font-size:11px">{inst.get("display_name","")}</td>
          <td><strong>{_fmt_price(inst.get("price",0))}</strong></td>
          <td>{_pct(inst.get("change_pct"))}</td>
          <td><span class="badge {badge_cls}">{icon} {status}</span></td>
          <td><span class="trend-badge {trend_cls}">{trend}</span></td>
          <td>{rsi_str}</td>
          <td style="color:var(--blue);font-weight:600">{rr_str}</td>
        </tr>"""

    return f"""
    <div class="summary-table-wrap">
      <table class="summary-table" id="main-table" data-sort-asc="">
        <thead>
          <tr>
            <th onclick="sortTable('main-table',0)">Sembol</th>
            <th onclick="sortTable('main-table',1)">Ad</th>
            <th onclick="sortTable('main-table',2)">Fiyat</th>
            <th onclick="sortTable('main-table',3)">Değ%</th>
            <th onclick="sortTable('main-table',4)">Durum</th>
            <th onclick="sortTable('main-table',5)">Yön</th>
            <th onclick="sortTable('main-table',6)">RSI</th>
            <th onclick="sortTable('main-table',7)">R:R</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""


def _render_plan(plan, dominant_dir: str) -> str:
    if plan is None or not plan.is_valid:
        return "<div style='color:var(--text-muted);font-size:12px'>Kurulum mevcut değil.</div>"

    is_long = plan.direction == "LONG"
    is_dominant = plan.direction == dominant_dir
    card_cls = f"plan-card {'plan-long' if is_long else 'plan-short'} {'plan-dominant' if is_dominant else ''}"
    dir_icon = "🟢" if is_long else "🔴"
    dir_label = "LONG KURULUM" if is_long else "SHORT KURULUM"

    dominant_badge = '<span class="plan-dominant-badge">★ Dominant</span>' if is_dominant else ""

    entry_mid = (plan.entry_zone_low + plan.entry_zone_high) / 2

    def pct_from_mid(target):
        if entry_mid > 0:
            return f"({(target - entry_mid)/entry_mid*100:+.1f}%)"
        return ""

    targets_html = ""
    if plan.target_1:
        targets_html += f"""
        <div class="plan-target-row">
          <span class="plan-target-label">Hedef 1</span>
          <span>{_fmt_price(plan.target_1)} {pct_from_mid(plan.target_1)}</span>
          <span class="plan-target-rr">R:R 1:{plan.risk_reward_t1}</span>
        </div>"""
    if plan.target_2:
        targets_html += f"""
        <div class="plan-target-row">
          <span class="plan-target-label">Hedef 2</span>
          <span>{_fmt_price(plan.target_2)} {pct_from_mid(plan.target_2)}</span>
          <span class="plan-target-rr">R:R 1:{plan.risk_reward_t2}</span>
        </div>"""
    if plan.target_3 and is_long:
        targets_html += f"""
        <div class="plan-target-row">
          <span class="plan-target-label">Hedef 3</span>
          <span>{_fmt_price(plan.target_3)} {pct_from_mid(plan.target_3)}</span>
          <span class="plan-target-rr">R:R 1:{plan.risk_reward_t3}</span>
        </div>"""

    warning = f'<div class="plan-quality-warning">⚠️ {plan.quality_warning}</div>' if plan.quality_warning else ""

    return f"""
    <div class="{card_cls}">
      <div class="plan-header">
        <span>{dir_icon} {dir_label}</span>
        {dominant_badge}
      </div>
      <div class="plan-section-label">Giriş Bölgesi</div>
      <div class="plan-entry-zone">{_fmt_price(plan.entry_zone_low)} – {_fmt_price(plan.entry_zone_high)}</div>
      <div class="plan-reasoning">{plan.entry_reasoning}</div>
      <div class="plan-section-label">Hedefler</div>
      <div class="plan-targets">{targets_html}</div>
      <div class="plan-stop">
        <div class="plan-section-label" style="margin-top:0">Stop Loss</div>
        <div class="plan-stop-price">{_fmt_price(plan.stop_loss)}</div>
        <div class="plan-stop-reason">{plan.stop_reasoning}</div>
      </div>
      {f'<div class="plan-trigger">🎯 Tetik: {plan.entry_trigger}</div>' if plan.entry_trigger else ""}
      {f'<div class="plan-trigger">❌ İptal: {plan.invalidation}</div>' if plan.invalidation else ""}
      <div class="plan-section-label">Zaman Ufku</div>
      <div style="font-size:12px">{plan.time_horizon}</div>
      {warning}
    </div>"""


def _render_scenario_tree(branches: list) -> str:
    if not branches:
        return ""
    branch_html = ""
    for b in branches:
        action = b.get("action", "")
        target = b.get("target", "")
        stop = b.get("stop", "")
        horizon = b.get("horizon", "")
        detail = " | ".join(filter(None, [target, stop, horizon]))
        branch_html += f"""
        <div class="scenario-branch">
          <span class="scenario-icon">{b.get("icon","🔄")}</span>
          <div>
            <div class="scenario-condition">{b.get("condition","")}</div>
            {f'<div class="scenario-detail">{detail}</div>' if detail else ""}
          </div>
          <div class="scenario-outcome">
            <div class="scenario-action">{action}</div>
          </div>
        </div>"""
    return f"""
    <div class="scenario-tree">
      <div class="scenario-title">💡 Senaryo Ağacı</div>
      {branch_html}
    </div>"""


def _render_card_summary(summary: dict) -> str:
    action_text = ""
    entry = summary.get("entry_text", "")
    t1 = summary.get("target_1_text", "")
    t2 = summary.get("target_2_text", "")
    stop = summary.get("stop_text", "")
    rr = summary.get("rr_text", "")
    reason = summary.get("action_reason", "")

    entry_block = ""
    if entry:
        entry_block = f"""
        <div class="summary-entry">
          <div class="entry-label">📌 Ne Yapmalısın?</div>
          <div>{entry}</div>
          <div class="targets-row">
            {f'<div class="target-item">{t1}</div>' if t1 else ""}
            {f'<div class="target-item">{t2}</div>' if t2 else ""}
            {f'<div class="stop-item">{stop}</div>' if stop else ""}
            {f'<div class="rr-item">{rr}</div>' if rr else ""}
          </div>
        </div>"""
    elif reason:
        entry_block = f'<div class="summary-entry"><div class="entry-label">📌 Durum</div><div>{reason}</div></div>'

    scenario = _render_scenario_tree(summary.get("scenario_branches", []))

    return f"""
    <div class="card-summary">
      {entry_block}
      {scenario}
    </div>"""


def _render_instrument_card(
    symbol: str,
    display_name: str,
    current_price: float,
    change_pct: float,
    action_status: str,
    overall_trend: str,
    rsi: Optional[float],
    narrative_result,
    card_summary: dict,
    timeframe_charts: dict,    # tf_label -> chart HTML
    timeframe_commentary: dict,  # tf_label -> text
    short_narrative: str,
    long_narrative: str,
    short_conf: str,
    long_conf: str,
) -> str:
    sid = _safe_id(symbol)
    badge_cls = _badge_class(action_status)
    badge_icon_str = _badge_icon(action_status)
    trend_cls = _trend_class(overall_trend)
    rsi_str = f"{rsi:.0f}" if rsi else "—"
    change_html = _pct(change_pct)

    # Timeframe tabs + content
    tf_tabs = ""
    tf_contents = ""
    tfs = list(timeframe_charts.keys())
    for i, tf in enumerate(tfs):
        safe_tf = _safe_id(tf)
        active_cls = "active" if i == 0 else ""
        tf_tabs += f'<div class="tf-tab {active_cls}" data-sym="{sid}" onclick="switchTf(\'{sid}\',\'{safe_tf}\')">{tf}</div>'
        commentary = timeframe_commentary.get(tf, "")
        chart_html = timeframe_charts.get(tf, "<div class='chart-unavailable'>Grafik yok</div>")
        tf_contents += f"""
        <div id="tf-{sid}-{safe_tf}" class="tf-content {active_cls}" data-sym="{sid}">
          <div class="chart-container">{chart_html}</div>
          {f'<div class="narrative-box"><div class="narrative-section">{commentary}</div></div>' if commentary else ""}
        </div>"""

    # Narratives
    narratives_html = f"""
    <div class="narratives-box">
      <div class="narratives-title">📖 Narratifler</div>
      <div class="narrative-item">
        <div class="narrative-item-label">Kısa Vade (1-2 hafta):</div>
        <div class="narrative-item-text">"{short_narrative}"</div>
        <span class="confidence-badge {_conf_class(short_conf)}">Güven: {short_conf}</span>
      </div>
      <div class="narrative-item">
        <div class="narrative-item-label">Uzun Vade (3+ ay):</div>
        <div class="narrative-item-text">"{long_narrative}"</div>
        <span class="confidence-badge {_conf_class(long_conf)}">Güven: {long_conf}</span>
      </div>
    </div>"""

    # Plans
    long_plan = narrative_result.long_plan if narrative_result else None
    short_plan = narrative_result.short_plan if narrative_result else None
    dominant = narrative_result.dominant_direction if narrative_result else "LONG"

    plans_html = f"""
    <div class="plans-grid">
      {_render_plan(long_plan, dominant)}
      {_render_plan(short_plan, dominant)}
    </div>"""

    rr_t1 = ""
    active_plan = long_plan if dominant == "LONG" else short_plan
    if active_plan and active_plan.is_valid and active_plan.risk_reward_t1 > 0:
        rr_t1 = f"1:{active_plan.risk_reward_t1}"

    return f"""
    <div class="instrument-card" id="card-{sid}">
      <!-- Layer 1: Header -->
      <div class="card-header" id="header-{sid}" onclick="toggleCard('{sid}')">
        <div class="card-status-badge">
          <span class="badge {badge_cls}">{badge_icon_str} {action_status}</span>
        </div>
        <div class="card-info">
          <div class="card-symbol">{symbol}</div>
          <div class="card-name">{display_name}</div>
          <div class="card-price-row">
            <span class="card-price">{_fmt_price(current_price)}</span>
            {change_html}
          </div>
        </div>
        <div class="card-metrics">
          <div class="metric">
            <div class="metric-label">RSI</div>
            <div class="metric-value">{rsi_str}</div>
          </div>
          <div class="metric">
            <div class="metric-label">Yön</div>
            <div class="metric-value"><span class="trend-badge {trend_cls}">{overall_trend}</span></div>
          </div>
          {f'<div class="metric"><div class="metric-label">R:R</div><div class="metric-value" style="color:var(--blue)">{rr_t1}</div></div>' if rr_t1 else ""}
        </div>
        <span class="expand-icon">▼</span>
      </div>

      <!-- Layer 2: Summary (always visible via simple view) -->
      {_render_card_summary(card_summary)}

      <!-- Expand button -->
      <div class="card-summary" style="padding-top:0;padding-bottom:12px">
        <button class="expand-btn" id="expand-btn-{sid}" onclick="toggleDetail('{sid}')">
          ▼ Teknik Detayları Göster
        </button>
      </div>

      <!-- Layer 3: Chart + Full Narrative -->
      <div class="card-detail" id="detail-{sid}">
        <div class="tf-tabs">{tf_tabs}</div>
        {tf_contents}
        {narratives_html}
      </div>

      <!-- Layer 4: Action Plans -->
      <div class="card-plans" id="plans-{sid}">
        {plans_html}
      </div>
    </div>"""


def _render_category_section(category: str, cards_html: str) -> str:
    safe_cat = _safe_id(category)
    return f"""
    <div class="category-section" data-category="{safe_cat}">
      <div class="category-header">{category}</div>
      {cards_html}
    </div>"""


# ─────────────────────────── Main render function ───────────


def render_report(report_data: dict) -> str:
    """
    Build the complete single-file HTML report.

    report_data structure:
    {
      "generated_at": datetime,
      "opportunities": [...],
      "all_instruments": [...],   # flat list for summary table
      "categories": {
        "cat_name": [
          {
            "symbol": str,
            "display_name": str,
            "current_price": float,
            "change_pct": float,
            "action_status": str,
            "overall_trend": str,
            "rsi": float,
            "narrative": NarrativeResult,
            "card_summary": dict,
            "timeframe_charts": {tf: html_str},
            "timeframe_commentary": {tf: str},
          },
          ...
        ]
      }
    }
    """
    generated_at = report_data.get("generated_at", datetime.now())
    ts_str = generated_at.strftime("%d %b %Y, %H:%M")

    # Category tabs
    categories = list(report_data.get("categories", {}).keys())
    cat_tabs = '<div class="cat-tab active" onclick="filterCategory(\'all\')">Tümü</div>'
    for cat in categories:
        safe_cat = _safe_id(cat)
        cat_tabs += f'<div class="cat-tab" onclick="filterCategory(\'{safe_cat}\')">{cat}</div>'

    # Opportunities panel
    opps_html = _render_opportunities(report_data.get("opportunities", []))

    # Summary table
    summary_html = _render_summary_table(report_data.get("all_instruments", []))

    # Category cards
    categories_html = ""
    for cat_name, instruments in report_data.get("categories", {}).items():
        cards_html = ""
        for inst in instruments:
            narrative = inst.get("narrative")
            short_narr = narrative.short_narrative if narrative else ""
            long_narr = narrative.long_narrative if narrative else ""
            short_conf = narrative.short_narrative_confidence if narrative else "Düşük"
            long_conf = narrative.long_narrative_confidence if narrative else "Düşük"

            cards_html += _render_instrument_card(
                symbol=inst["symbol"],
                display_name=inst.get("display_name", ""),
                current_price=inst.get("current_price", 0),
                change_pct=inst.get("change_pct"),
                action_status=inst.get("action_status", "Nötr"),
                overall_trend=inst.get("overall_trend", "Yatay"),
                rsi=inst.get("rsi"),
                narrative_result=narrative,
                card_summary=inst.get("card_summary", {}),
                timeframe_charts=inst.get("timeframe_charts", {}),
                timeframe_commentary=inst.get("timeframe_commentary", {}),
                short_narrative=short_narr,
                long_narrative=long_narr,
                short_conf=short_conf,
                long_conf=long_conf,
            )
        categories_html += _render_category_section(cat_name, cards_html)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Market Analyzer — {ts_str}</title>
  <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
  <style>{CSS}</style>
</head>
<body>
  <!-- Header -->
  <div class="header">
    <div>
      <div class="header-title">📊 Market Analyzer</div>
      <div class="header-date">{ts_str}</div>
    </div>
    <div class="cat-tabs">{cat_tabs}</div>
    <button class="view-toggle" id="view-toggle" onclick="toggleView()">📊 Detaylı Görünüm</button>
  </div>

  <!-- Main content -->
  <div class="container">
    {opps_html}
    {summary_html}
    {categories_html}
  </div>

  <script>{JS}</script>
</body>
</html>"""
