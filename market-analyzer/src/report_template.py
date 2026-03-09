"""
Jinja2 HTML template + CSS for single-file report output.
Generates a self-contained HTML file with all CSS/JS inline.
"""

import logging
from datetime import datetime

from jinja2 import Template

logger = logging.getLogger(__name__)

HTML_TEMPLATE = Template('''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Market Analyzer — {{ report_date }}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
:root {
  --bg-primary: #0d1117;
  --bg-card: #161b22;
  --bg-card-hover: #1c2129;
  --border: #21262d;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-muted: #6e7681;
  --green: #00b894;
  --red: #d63031;
  --yellow: #fdcb6e;
  --gray: #636e72;
  --blue: #74b9ff;
  --purple: #a29bfe;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--bg-primary);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  line-height: 1.6;
  font-size: 14px;
}
.container { max-width: 1400px; margin: 0 auto; padding: 16px; }

/* Header */
.header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 8px; margin-bottom: 16px; flex-wrap: wrap; gap: 12px;
}
.header-title { font-size: 20px; font-weight: 700; }
.header-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

/* Category tabs */
.cat-tabs { display: flex; gap: 4px; flex-wrap: wrap; }
.cat-tab {
  padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border);
  background: transparent; color: var(--text-secondary); cursor: pointer;
  font-size: 13px; transition: all 0.2s;
}
.cat-tab:hover { background: var(--bg-card-hover); color: var(--text-primary); }
.cat-tab.active { background: var(--blue); color: #000; border-color: var(--blue); font-weight: 600; }

/* View toggle */
.view-toggle {
  padding: 6px 14px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--bg-card); color: var(--text-primary); cursor: pointer;
  font-size: 13px;
}
.view-toggle:hover { background: var(--bg-card-hover); }

/* Search */
.search-input {
  padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--bg-primary); color: var(--text-primary); font-size: 13px;
  width: 160px;
}

/* Günün Fırsatları */
.opportunities {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px 20px; margin-bottom: 16px;
}
.opportunities h2 { font-size: 16px; margin-bottom: 12px; color: var(--yellow); }
.opp-grid { display: flex; gap: 12px; flex-wrap: wrap; }
.opp-card {
  flex: 1; min-width: 200px; max-width: 280px; padding: 12px 16px;
  background: var(--bg-primary); border: 1px solid var(--border); border-radius: 8px;
  cursor: pointer; transition: all 0.2s;
}
.opp-card:hover { border-color: var(--blue); transform: translateY(-2px); }
.opp-badge { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
.opp-symbol { font-size: 14px; font-weight: 600; }
.opp-rr { font-size: 12px; color: var(--text-secondary); }
.opp-reason { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* Summary Table */
.summary-section {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px 20px; margin-bottom: 16px; overflow-x: auto;
}
.summary-section h2 { font-size: 16px; margin-bottom: 12px; }
.summary-table {
  width: 100%; border-collapse: collapse; font-size: 13px;
}
.summary-table th {
  text-align: left; padding: 8px 12px; border-bottom: 2px solid var(--border);
  color: var(--text-secondary); cursor: pointer; white-space: nowrap;
  user-select: none;
}
.summary-table th:hover { color: var(--text-primary); }
.summary-table td {
  padding: 8px 12px; border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.summary-table tr:hover { background: var(--bg-card-hover); }
.summary-table tr { cursor: pointer; }

/* Status badges */
.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-weight: 700; font-size: 12px;
}
.badge-al { background: rgba(0,184,148,0.15); color: var(--green); }
.badge-sat { background: rgba(214,48,49,0.15); color: var(--red); }
.badge-izle { background: rgba(253,203,110,0.15); color: var(--yellow); }
.badge-notr { background: rgba(99,110,114,0.15); color: var(--gray); }

/* Category sections */
.category-section { margin-bottom: 24px; }
.category-title {
  font-size: 18px; font-weight: 700; padding: 12px 0;
  border-bottom: 2px solid var(--border); margin-bottom: 16px;
}

/* Instrument cards */
.instrument-card {
  background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
  margin-bottom: 12px; overflow: hidden;
}

/* Layer 1 — Header */
.card-header {
  display: flex; align-items: center; gap: 16px; padding: 16px 20px;
  flex-wrap: wrap;
}
.card-status { font-size: 24px; font-weight: 800; min-width: 100px; }
.card-info { flex: 1; }
.card-symbol { font-size: 16px; font-weight: 700; }
.card-meta { font-size: 13px; color: var(--text-secondary); display: flex; gap: 16px; flex-wrap: wrap; }

/* Layer 2 — Summary */
.card-summary { padding: 0 20px 16px 20px; }
.card-summary h4 { font-size: 14px; margin-bottom: 8px; }
.action-line {
  font-size: 14px; font-weight: 600; padding: 8px 12px;
  background: var(--bg-primary); border-radius: 6px; margin-bottom: 8px;
}
.scenario-tree { margin-top: 8px; }
.scenario-branch {
  display: flex; gap: 8px; padding: 4px 0; font-size: 13px;
  align-items: flex-start;
}
.scenario-icon { font-size: 16px; min-width: 24px; }
.expand-btn {
  display: inline-block; padding: 6px 14px; margin-top: 8px;
  border-radius: 6px; border: 1px solid var(--border); background: transparent;
  color: var(--text-secondary); cursor: pointer; font-size: 12px;
}
.expand-btn:hover { background: var(--bg-card-hover); color: var(--text-primary); }

/* Layer 3 — Chart + Narrative (expandable) */
.card-detail { display: none; padding: 0 20px 16px 20px; }
body.detailed-view .card-detail { display: block; }
.card-detail.expanded { display: block; }

/* Timeframe tabs */
.tf-tabs { display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }
.tf-tab {
  padding: 4px 10px; border-radius: 4px; border: 1px solid var(--border);
  background: transparent; color: var(--text-secondary); cursor: pointer;
  font-size: 12px;
}
.tf-tab:hover { background: var(--bg-card-hover); }
.tf-tab.active { background: var(--blue); color: #000; border-color: var(--blue); }
.tf-content { display: none; }
.tf-content.active { display: block; }

.narrative-block { margin-top: 16px; }
.narrative-label { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.narrative-text {
  font-size: 13px; padding: 8px 12px; background: var(--bg-primary);
  border-radius: 6px; margin-bottom: 8px; font-style: italic;
}
.narrative-confidence { font-size: 11px; color: var(--text-muted); }

.commentary-block {
  font-size: 13px; line-height: 1.7; padding: 12px;
  background: var(--bg-primary); border-radius: 6px; margin-top: 12px;
  white-space: pre-wrap;
}

/* Layer 4 — Action Plans (expandable) */
.card-plans { display: none; padding: 0 20px 16px 20px; }
body.detailed-view .card-plans { display: block; }
.card-plans.expanded { display: block; }

.plan-grid { display: flex; gap: 12px; flex-wrap: wrap; }
.plan-card {
  flex: 1; min-width: 300px; padding: 16px; background: var(--bg-primary);
  border-radius: 8px; border-left: 4px solid;
}
.plan-long { border-left-color: var(--green); }
.plan-short { border-left-color: var(--red); }
.plan-title { font-size: 15px; font-weight: 700; margin-bottom: 8px; }
.plan-dominant { background: rgba(116,185,255,0.1); }
.plan-row { display: flex; justify-content: space-between; padding: 3px 0; font-size: 13px; }
.plan-label { color: var(--text-secondary); }
.plan-value { font-weight: 600; }
.plan-divider { border-top: 1px solid var(--border); margin: 8px 0; }
.plan-warning {
  font-size: 12px; color: var(--yellow); margin-top: 8px;
  padding: 4px 8px; background: rgba(253,203,110,0.1); border-radius: 4px;
}

/* Responsive */
@media (max-width: 768px) {
  .opp-card { min-width: 100%; }
  .plan-card { min-width: 100%; }
  .card-header { flex-direction: column; align-items: flex-start; }
  .header { flex-direction: column; align-items: flex-start; }
}

/* Error card */
.error-card {
  background: var(--bg-card); border: 1px solid var(--red); border-radius: 8px;
  padding: 16px 20px; margin-bottom: 12px; color: var(--red);
}

/* Change colors */
.change-up { color: var(--green); }
.change-down { color: var(--red); }
.change-flat { color: var(--text-secondary); }

/* Hide categories */
.category-section { display: none; }
.category-section.visible { display: block; }
</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <div class="header-title">📊 Market Analyzer — {{ report_date }}</div>
    <div class="header-controls">
      <div class="cat-tabs">
        <button class="cat-tab active" onclick="showCategory('all')">Tümü</button>
        {% for cat_name in categories %}
        <button class="cat-tab" onclick="showCategory('{{ cat_name | replace(' ', '-') | replace('/', '-') }}')">{{ cat_name }}</button>
        {% endfor %}
      </div>
      <input type="text" class="search-input" placeholder="🔍 Ara..." oninput="searchInstruments(this.value)">
      <button class="view-toggle" onclick="toggleView()" id="view-toggle">📊 Detaylı Görünüm</button>
    </div>
  </div>

  <!-- Günün Fırsatları -->
  {% if opportunities %}
  <div class="opportunities">
    <h2>⚡ GÜNÜN FIRSATLARI</h2>
    <div class="opp-grid">
      {% for opp in opportunities %}
      <div class="opp-card" onclick="scrollToCard('{{ opp.symbol }}')">
        <div class="opp-badge" style="color: {{ opp.color }}">{{ opp.badge }}</div>
        <div class="opp-symbol">{{ opp.display_name }}</div>
        <div class="opp-rr">R:R 1:{{ opp.rr }}</div>
        <div class="opp-reason">{{ opp.reason }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  <!-- Summary Table -->
  <div class="summary-section">
    <h2>📋 TÜM ENSTRÜMANLARA BAKIŞ</h2>
    <table class="summary-table" id="summary-table">
      <thead>
        <tr>
          <th onclick="sortTable(0)">Sembol</th>
          <th onclick="sortTable(1)">Ad</th>
          <th onclick="sortTable(2)">Fiyat</th>
          <th onclick="sortTable(3)">Değ%</th>
          <th onclick="sortTable(4)">🎯 Durum</th>
          <th onclick="sortTable(5)">Yön</th>
          <th onclick="sortTable(6)">RSI</th>
          <th onclick="sortTable(7)">R:R</th>
        </tr>
      </thead>
      <tbody>
        {% for item in summary_table %}
        <tr onclick="scrollToCard('{{ item.symbol }}')" data-status-order="{{ item.status_order }}">
          <td>{{ item.symbol }}</td>
          <td>{{ item.display_name }}</td>
          <td>{{ item.price_str }}</td>
          <td class="{{ item.change_class }}">{{ item.change_str }}</td>
          <td><span class="badge {{ item.badge_class }}">{{ item.badge }}</span></td>
          <td>{{ item.trend_label }}</td>
          <td>{{ item.rsi_str }}</td>
          <td>{{ item.rr_str }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <!-- Category Sections -->
  {% for cat_name, instruments in categories.items() %}
  <div class="category-section visible" id="cat-{{ cat_name | replace(' ', '-') | replace('/', '-') }}">
    <div class="category-title">{{ cat_name }}</div>

    {% for inst in instruments %}
    <div class="instrument-card" id="card-{{ inst.symbol }}" data-symbol="{{ inst.symbol }}" data-category="{{ cat_name | replace(' ', '-') | replace('/', '-') }}">
      <!-- Layer 1 — Header -->
      <div class="card-header">
        <div class="card-status" style="color: {{ inst.action_color }}">{{ inst.action_badge }}</div>
        <div class="card-info">
          <div class="card-symbol">{{ inst.symbol }} — {{ inst.display_name }}</div>
          <div class="card-meta">
            <span>{{ inst.price_str }}</span>
            <span class="{{ inst.change_class }}">{{ inst.change_str }}</span>
            <span>RSI: {{ inst.rsi_str }}</span>
            <span>{{ inst.trend_label }}</span>
          </div>
        </div>
      </div>

      <!-- Layer 2 — Summary -->
      <div class="card-summary">
        <h4>📌 Ne Yapmalısın?</h4>
        <div class="action-line">{{ inst.summary_line }}</div>

        {% if inst.scenario_tree %}
        <div class="scenario-tree">
          <strong>💡 Senaryo Ağacı:</strong>
          {% for branch in inst.scenario_tree %}
          <div class="scenario-branch">
            <span class="scenario-icon">{{ branch.icon }}</span>
            <span>{{ branch.condition }} → {{ branch.action }}{% if branch.target %} | {{ branch.target }}{% endif %}{% if branch.time_horizon %} | Süre: {{ branch.time_horizon }}{% endif %}</span>
          </div>
          {% endfor %}
        </div>
        {% endif %}

        <button class="expand-btn" onclick="toggleDetail('{{ inst.symbol }}')">▼ Teknik Detayları Göster</button>
      </div>

      <!-- Layer 3 — Charts + Narrative -->
      <div class="card-detail" id="detail-{{ inst.symbol }}">
        <div class="tf-tabs">
          {% for tf_name in inst.timeframes %}
          <button class="tf-tab{% if loop.first %} active{% endif %}"
                  onclick="switchTimeframe('{{ inst.symbol }}', '{{ tf_name | replace(' ', '-') }}')">{{ tf_name }}</button>
          {% endfor %}
        </div>

        {% for tf_name, tf_data in inst.timeframe_data.items() %}
        <div class="tf-content{% if loop.first %} active{% endif %}" id="tf-{{ inst.symbol }}-{{ tf_name | replace(' ', '-') }}">
          {{ tf_data.chart_html | safe }}

          <div class="narrative-block">
            <div class="narrative-label">Kısa Vade:</div>
            <div class="narrative-text">{{ tf_data.short_narrative }}</div>
            <div class="narrative-confidence">Güven: {{ tf_data.short_confidence }}</div>
          </div>
          <div class="narrative-block">
            <div class="narrative-label">Uzun Vade:</div>
            <div class="narrative-text">{{ tf_data.long_narrative }}</div>
            <div class="narrative-confidence">Güven: {{ tf_data.long_confidence }}</div>
          </div>

          {% if tf_data.commentary %}
          <div class="commentary-block">{{ tf_data.commentary }}</div>
          {% endif %}

          {% if tf_data.ai_analysis %}
          <div class="narrative-block">
            <div class="narrative-label">🤖 AI Analizi:</div>
            <div class="commentary-block">{{ tf_data.ai_analysis }}</div>
          </div>
          {% endif %}
        </div>
        {% endfor %}

        <button class="expand-btn" onclick="togglePlans('{{ inst.symbol }}')">▼ Aksiyon Planlarını Göster</button>
      </div>

      <!-- Layer 4 — Action Plans -->
      <div class="card-plans" id="plans-{{ inst.symbol }}">
        <div class="plan-grid">
          <!-- Long Plan -->
          <div class="plan-card plan-long {% if inst.dominant == 'LONG' %}plan-dominant{% endif %}">
            <div class="plan-title">🟢 LONG KURULUM {% if inst.dominant == 'LONG' %}★ Dominant Senaryo{% endif %}</div>
            <div class="plan-row"><span class="plan-label">Güç:</span><span class="plan-value">{{ inst.long_plan.bias_strength }}</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Giriş Bölgesi:</span><span class="plan-value">{{ inst.long_plan.entry_zone_low }} – {{ inst.long_plan.entry_zone_high }}</span></div>
            <div class="plan-row"><span class="plan-label">Neden:</span><span class="plan-value">{{ inst.long_plan.entry_reasoning }}</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Hedef 1:</span><span class="plan-value">{{ inst.long_plan.target_1 }} (R:R 1:{{ inst.long_plan.risk_reward_t1 }})</span></div>
            <div class="plan-row"><span class="plan-label">Hedef 2:</span><span class="plan-value">{{ inst.long_plan.target_2 }} (R:R 1:{{ inst.long_plan.risk_reward_t2 }})</span></div>
            <div class="plan-row"><span class="plan-label">Hedef 3:</span><span class="plan-value">{{ inst.long_plan.target_3 }} (R:R 1:{{ inst.long_plan.risk_reward_t3 }})</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Stop Loss:</span><span class="plan-value" style="color:var(--red)">{{ inst.long_plan.stop_loss }}</span></div>
            <div class="plan-row"><span class="plan-label">Gerekçe:</span><span class="plan-value">{{ inst.long_plan.stop_reasoning }}</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Giriş Tetikleyicisi:</span><span class="plan-value">{{ inst.long_plan.entry_trigger }}</span></div>
            <div class="plan-row"><span class="plan-label">İptal Şartı:</span><span class="plan-value">{{ inst.long_plan.invalidation }}</span></div>
            <div class="plan-row"><span class="plan-label">Zaman Ufku:</span><span class="plan-value">{{ inst.long_plan.time_horizon }}</span></div>
            {% if inst.long_plan.quality_warning %}
            <div class="plan-warning">⚠️ {{ inst.long_plan.quality_warning }}</div>
            {% endif %}
          </div>

          <!-- Short Plan -->
          <div class="plan-card plan-short {% if inst.dominant == 'SHORT' %}plan-dominant{% endif %}">
            <div class="plan-title">🔴 SHORT KURULUM {% if inst.dominant == 'SHORT' %}★ Dominant Senaryo{% endif %}</div>
            <div class="plan-row"><span class="plan-label">Güç:</span><span class="plan-value">{{ inst.short_plan.bias_strength }}</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Giriş Bölgesi:</span><span class="plan-value">{{ inst.short_plan.entry_zone_low }} – {{ inst.short_plan.entry_zone_high }}</span></div>
            <div class="plan-row"><span class="plan-label">Neden:</span><span class="plan-value">{{ inst.short_plan.entry_reasoning }}</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Hedef 1:</span><span class="plan-value">{{ inst.short_plan.target_1 }} (R:R 1:{{ inst.short_plan.risk_reward_t1 }})</span></div>
            <div class="plan-row"><span class="plan-label">Hedef 2:</span><span class="plan-value">{{ inst.short_plan.target_2 }} (R:R 1:{{ inst.short_plan.risk_reward_t2 }})</span></div>
            <div class="plan-row"><span class="plan-label">Hedef 3:</span><span class="plan-value">{{ inst.short_plan.target_3 }} (R:R 1:{{ inst.short_plan.risk_reward_t3 }})</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Stop Loss:</span><span class="plan-value" style="color:var(--red)">{{ inst.short_plan.stop_loss }}</span></div>
            <div class="plan-row"><span class="plan-label">Gerekçe:</span><span class="plan-value">{{ inst.short_plan.stop_reasoning }}</span></div>
            <div class="plan-divider"></div>
            <div class="plan-row"><span class="plan-label">Giriş Tetikleyicisi:</span><span class="plan-value">{{ inst.short_plan.entry_trigger }}</span></div>
            <div class="plan-row"><span class="plan-label">İptal Şartı:</span><span class="plan-value">{{ inst.short_plan.invalidation }}</span></div>
            <div class="plan-row"><span class="plan-label">Zaman Ufku:</span><span class="plan-value">{{ inst.short_plan.time_horizon }}</span></div>
            {% if inst.short_plan.quality_warning %}
            <div class="plan-warning">⚠️ {{ inst.short_plan.quality_warning }}</div>
            {% endif %}
          </div>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
  {% endfor %}
</div>

<script>
// Category filter
function showCategory(cat) {
  document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
  event.target.classList.add('active');
  document.querySelectorAll('.category-section').forEach(s => {
    if (cat === 'all') {
      s.classList.add('visible');
    } else {
      s.classList.toggle('visible', s.id === 'cat-' + cat);
    }
  });
}

// Search
function searchInstruments(query) {
  query = query.toLowerCase();
  document.querySelectorAll('.instrument-card').forEach(card => {
    const sym = card.dataset.symbol.toLowerCase();
    const text = card.textContent.toLowerCase();
    card.style.display = (query === '' || sym.includes(query) || text.includes(query)) ? '' : 'none';
  });
}

// View toggle
let isDetailed = false;
function toggleView() {
  isDetailed = !isDetailed;
  document.body.classList.toggle('detailed-view', isDetailed);
  document.getElementById('view-toggle').textContent = isDetailed ? '📋 Basit Görünüm' : '📊 Detaylı Görünüm';
}

// Expand detail
function toggleDetail(symbol) {
  const el = document.getElementById('detail-' + symbol);
  el.classList.toggle('expanded');
  const btn = el.previousElementSibling.querySelector('.expand-btn');
  if (btn) {
    btn.textContent = el.classList.contains('expanded') ? '▲ Teknik Detayları Gizle' : '▼ Teknik Detayları Göster';
  }
}

// Expand plans
function togglePlans(symbol) {
  const el = document.getElementById('plans-' + symbol);
  el.classList.toggle('expanded');
}

// Timeframe switcher
function switchTimeframe(symbol, tf) {
  const card = document.getElementById('card-' + symbol);
  card.querySelectorAll('.tf-tab').forEach(t => {
    t.classList.toggle('active', t.textContent.replace(/ /g, '-') === tf.replace(/-/g, ' ') || t.textContent === tf.replace(/-/g, ' '));
  });
  card.querySelectorAll('.tf-content').forEach(c => {
    c.classList.toggle('active', c.id === 'tf-' + symbol + '-' + tf);
  });
}

// Scroll to card
function scrollToCard(symbol) {
  const card = document.getElementById('card-' + symbol);
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    card.style.borderColor = 'var(--blue)';
    setTimeout(() => { card.style.borderColor = ''; }, 2000);
  }
}

// Sort table
let sortDir = {};
function sortTable(colIdx) {
  const table = document.getElementById('summary-table');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  sortDir[colIdx] = !sortDir[colIdx];
  rows.sort((a, b) => {
    let aVal = a.cells[colIdx].textContent.trim();
    let bVal = b.cells[colIdx].textContent.trim();
    // Try numeric
    const aNum = parseFloat(aVal.replace(/[^\\d.-]/g, ''));
    const bNum = parseFloat(bVal.replace(/[^\\d.-]/g, ''));
    if (!isNaN(aNum) && !isNaN(bNum)) {
      return sortDir[colIdx] ? aNum - bNum : bNum - aNum;
    }
    return sortDir[colIdx] ? aVal.localeCompare(bVal, 'tr') : bVal.localeCompare(aVal, 'tr');
  });
  rows.forEach(r => tbody.appendChild(r));
}
</script>
</body>
</html>''')


def format_price(price: float | None, currency: str = "USD") -> str:
    """Format price with currency symbol."""
    if price is None:
        return "—"
    symbols = {"USD": "$", "TRY": "₺", "EUR": "€", "GBP": "£"}
    sym = symbols.get(currency, "")
    if price >= 1000:
        return f"{sym}{price:,.2f}"
    elif price >= 1:
        return f"{sym}{price:.2f}"
    else:
        return f"{sym}{price:.6f}"


def format_change(pct: float | None) -> tuple[str, str]:
    """Format percentage change with CSS class."""
    if pct is None:
        return "—", "change-flat"
    if pct > 0:
        return f"▲ +{pct:.2f}%", "change-up"
    elif pct < 0:
        return f"▼ {pct:.2f}%", "change-down"
    return f"► {pct:.2f}%", "change-flat"


def get_status_order(status: str) -> int:
    """Order: Al=1, Sat=2, İzle=3, Nötr=4."""
    return {"Al": 1, "Sat": 2, "İzle": 3, "Nötr": 4}.get(status, 5)


def get_badge_class(status: str) -> str:
    """Get CSS class for status badge."""
    return {"Al": "badge-al", "Sat": "badge-sat", "İzle": "badge-izle"}.get(status, "badge-notr")


def render_report(report_data: dict) -> str:
    """
    Render the full HTML report from structured report data.

    report_data keys:
      - report_date: str
      - categories: dict[str, list[dict]]  (category_name -> list of instrument dicts)
      - opportunities: list[dict]
      - summary_table: list[dict]
    """
    return HTML_TEMPLATE.render(**report_data)
