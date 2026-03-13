// ─── STATE ────────────────────────────────
let currentSymbol = null;
let currentTf = '3A';
let watchlist = {};
let allAnalyses = [];
let showRsi = false;
let showMacd = false;
let currentData = null;

// ─── INIT ────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await loadWatchlist();
    await loadOpportunities();
    updateTicker();
    setupTimeframeTabs();

    setInterval(updateTicker, 30000);
    setInterval(refreshAll, 60000);
});

// ─── WATCHLIST ───────────────────────────
async function loadWatchlist() {
    try {
        const res = await fetch('/api/watchlist');
        watchlist = await res.json();
        renderSidebar();

        const firstCategory = Object.keys(watchlist)[0];
        if (firstCategory && watchlist[firstCategory].length > 0) {
            loadSymbol(watchlist[firstCategory][0].symbol);
        }
    } catch (e) {
        console.error('Watchlist yüklenemedi:', e);
    }
}

function renderSidebar() {
    const container = document.getElementById('sidebarList');
    container.innerHTML = '';

    for (const [category, instruments] of Object.entries(watchlist)) {
        const title = document.createElement('div');
        title.className = 'market-group-title';
        title.textContent = category;
        container.appendChild(title);

        for (const inst of instruments) {
            const row = document.createElement('div');
            row.className = 'market-row';
            row.dataset.symbol = inst.symbol;
            row.onclick = () => loadSymbol(inst.symbol);

            const cached = allAnalyses.find(a => a.symbol === inst.symbol);
            const price = cached?.price || 0;
            const changePct = cached?.change_pct ?? 0;
            const isUp = changePct >= 0;

            row.innerHTML = `
                <div class="row-name">
                    <span class="row-symbol">${inst.symbol.replace('.IS', '')}</span>
                    <span class="row-label">${inst.name}</span>
                </div>
                <span class="row-price">${price ? price.toFixed(2) : '—'}</span>
                <span class="row-change ${isUp ? 'up' : 'down'}">${isUp ? '+' : ''}${changePct.toFixed(2)}%</span>
            `;
            container.appendChild(row);
        }
    }
}

// ─── SYMBOL LOADING ─────────────────────
async function loadSymbol(symbol) {
    currentSymbol = symbol;

    // Update active row
    document.querySelectorAll('.market-row').forEach(r => r.classList.remove('active'));
    const activeRow = document.querySelector(`[data-symbol="${symbol}"]`);
    if (activeRow) activeRow.classList.add('active');

    // Update toolbar
    document.getElementById('tfSymbolLabel').textContent = symbol.replace('.IS', '');

    // Show loading
    document.getElementById('chart-area').innerHTML = '<div class="loading"><div class="loading-spinner"></div>Yükleniyor...</div>';

    try {
        const enc = encodeURIComponent(symbol);
        const res = await fetch(`/api/analyze/${enc}?tf=${currentTf}`);
        const data = await res.json();

        if (data.error) {
            document.getElementById('chart-area').innerHTML = `<div class="loading">${data.error}</div>`;
            return;
        }

        currentData = data;
        updateToolbarPrice(data);
        updateSignalStrip(data);
        updateIndicatorDetail(data);
        updateLevelsPanel(data);
        updateScenarioPanel(data);
        loadChart(symbol, currentTf);
    } catch (e) {
        console.error('Analiz hatası:', e);
        document.getElementById('chart-area').innerHTML = '<div class="loading">Bağlantı hatası</div>';
    }
}

// ─── TOOLBAR PRICE ──────────────────────
function updateToolbarPrice(data) {
    const priceEl = document.getElementById('toolbarPrice');
    const changeEl = document.getElementById('toolbarChange');

    priceEl.textContent = data.price || '';

    const pct = data.change_pct || 0;
    const isUp = pct >= 0;
    changeEl.textContent = `${isUp ? '+' : ''}${pct.toFixed(2)}%`;
    changeEl.style.color = isUp ? 'var(--green)' : 'var(--red)';
}

// ─── CHART ──────────────────────────────
function loadChart(symbol, tf) {
    const enc = encodeURIComponent(symbol);
    const rsiParam = showRsi ? '1' : '0';
    const macdParam = showMacd ? '1' : '0';
    const url = `/api/chart/${enc}/${tf}?rsi=${rsiParam}&macd=${macdParam}`;

    document.getElementById('chart-area').innerHTML =
        `<iframe src="${url}"></iframe>`;
}

// ─── INDICATOR TOGGLES ─────────────────
function toggleIndicator(type) {
    if (type === 'rsi') {
        showRsi = !showRsi;
        document.getElementById('toggleRsi').classList.toggle('active', showRsi);
    } else if (type === 'macd') {
        showMacd = !showMacd;
        document.getElementById('toggleMacd').classList.toggle('active', showMacd);
    }
    if (currentSymbol) loadChart(currentSymbol, currentTf);
}

// ─── TIMEFRAME TABS ─────────────────────
function setupTimeframeTabs() {
    document.querySelectorAll('.tf-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTf = btn.dataset.tf;
            if (currentSymbol) {
                loadSymbol(currentSymbol);
            }
        });
    });
}

// ─── SIGNAL STRIP ───────────────────────
function updateSignalStrip(data) {
    const strip = document.getElementById('signalStrip');
    const signal = data.signal || {};
    const ind = data.indicators || {};
    const ts = data.trend_score ?? 0;

    let dotClass = 'neutral';
    if (signal.signal === 'AL') dotClass = 'buy';
    else if (signal.signal === 'SAT') dotClass = 'sell';
    else if (signal.signal === 'İZLE') dotClass = 'watch';

    const trendColor = ts >= 40 ? 'var(--green)' : ts <= -40 ? 'var(--red)' : 'var(--text-dim)';

    strip.innerHTML = `
        <div class="signal-badge-main">
            <span class="signal-dot ${dotClass}"></span>
            <span class="signal-label" style="color: ${signal.color || 'var(--text-dim)'}">${signal.emoji || ''} ${signal.signal || 'NÖTR'}</span>
        </div>
        <div class="signal-stats" id="signalStats">
            <div class="stat-mini">
                <span class="stat-key">Trend</span>
                <span class="stat-val" style="color: ${trendColor}">${ts}</span>
            </div>
            <div class="stat-mini">
                <span class="stat-key">RSI</span>
                <span class="stat-val" style="color: ${ind.rsi > 70 ? 'var(--red)' : ind.rsi < 30 ? 'var(--green)' : 'var(--text)'}">${(ind.rsi || 0).toFixed(1)}</span>
            </div>
            <div class="stat-mini">
                <span class="stat-key">MACD</span>
                <span class="stat-val" style="color: ${ind.macd_hist > 0 ? 'var(--green)' : 'var(--red)'}">${(ind.macd_hist || 0).toFixed(4)}</span>
            </div>
            <div class="stat-mini">
                <span class="stat-key">Fiyat</span>
                <span class="stat-val">${data.price || 0}</span>
            </div>
        </div>
    `;
}

// ─── INDICATOR DETAIL (RIGHT PANEL) ─────
function updateIndicatorDetail(data) {
    const panel = document.getElementById('indicatorDetail');
    const ind = data.indicators || {};

    panel.innerHTML = `
        <div class="ind-cell">
            <div class="ind-label">RSI</div>
            <div class="ind-value" style="color: ${ind.rsi > 70 ? 'var(--red)' : ind.rsi < 30 ? 'var(--green)' : 'var(--text)'}">${(ind.rsi || 0).toFixed(1)}</div>
        </div>
        <div class="ind-cell">
            <div class="ind-label">MACD Hist</div>
            <div class="ind-value" style="color: ${ind.macd_hist > 0 ? 'var(--green)' : 'var(--red)'}">${(ind.macd_hist || 0).toFixed(4)}</div>
        </div>
        <div class="ind-cell">
            <div class="ind-label">EMA 20</div>
            <div class="ind-value">${(ind.ema20 || 0).toFixed(2)}</div>
        </div>
        <div class="ind-cell">
            <div class="ind-label">EMA 50</div>
            <div class="ind-value">${(ind.ema50 || 0).toFixed(2)}</div>
        </div>
        <div class="ind-cell">
            <div class="ind-label">EMA 200</div>
            <div class="ind-value">${(ind.ema200 || 0).toFixed(2)}</div>
        </div>
        <div class="ind-cell">
            <div class="ind-label">BB Bant</div>
            <div class="ind-value" style="font-size: 10px">${(ind.bb_lower || 0).toFixed(1)} — ${(ind.bb_upper || 0).toFixed(1)}</div>
        </div>
    `;
}

// ─── LEVELS PANEL ───────────────────────
function updateLevelsPanel(data) {
    const panel = document.getElementById('levelsPanel');
    const support = data.support || [];
    const resistance = data.resistance || [];

    let html = '';
    resistance.slice(0, 3).reverse().forEach((r, i) => {
        html += `<div class="level-row resistance">
            <span class="level-type" style="color: var(--red)">R${resistance.slice(0, 3).length - i}</span>
            <span>${r.toFixed(2)}</span>
        </div>`;
    });
    support.slice(0, 3).forEach((s, i) => {
        html += `<div class="level-row support">
            <span class="level-type" style="color: var(--green)">S${i + 1}</span>
            <span>${s.toFixed(2)}</span>
        </div>`;
    });

    panel.innerHTML = html || '<div class="dim-text">Veri yok</div>';
}

// ─── SCENARIO PANEL ─────────────────────
function updateScenarioPanel(data) {
    const panel = document.getElementById('scenarioPanel');
    const narrative = data.narrative || {};
    const plan = data.action_plan || {};

    const yonColor = plan.yon === 'LONG' ? 'var(--green)' : plan.yon === 'SHORT' ? 'var(--red)' : 'var(--yellow)';

    panel.innerHTML = `
        <div class="scenario-header" style="color: ${yonColor}">${plan.yon || '—'} ${narrative.baslik ? '— ' + narrative.baslik : ''}</div>
        <div class="scenario-text">${narrative.ozet || ''}</div>
        ${plan.senaryo_metni ? `<div class="scenario-text" style="color: var(--text);">${plan.senaryo_metni}</div>` : ''}
        <div class="scenario-grid">
            <div class="scenario-cell">
                <div class="cell-label">Giriş</div>
                <div class="cell-value">${plan.giris_bolgesi ? plan.giris_bolgesi[0].toFixed(2) + ' — ' + plan.giris_bolgesi[1].toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-cell">
                <div class="cell-label">Stop Loss</div>
                <div class="cell-value" style="color: var(--red)">${plan.stop_loss ? plan.stop_loss.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-cell">
                <div class="cell-label">Hedef 1</div>
                <div class="cell-value" style="color: var(--green)">${plan.hedef_1 ? plan.hedef_1.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-cell">
                <div class="cell-label">Hedef 2</div>
                <div class="cell-value" style="color: var(--green)">${plan.hedef_2 ? plan.hedef_2.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-cell">
                <div class="cell-label">Hedef 3</div>
                <div class="cell-value" style="color: var(--green)">${plan.hedef_3 ? plan.hedef_3.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-cell">
                <div class="cell-label">R:R</div>
                <div class="cell-value" style="color: ${plan.rr_orani >= 1.5 ? 'var(--green)' : 'var(--yellow)'}">${plan.rr_orani || '—'}</div>
            </div>
            <div class="scenario-cell">
                <div class="cell-label">Zaman Ufku</div>
                <div class="cell-value">${plan.zaman_ufku || '—'}</div>
            </div>
            <div class="scenario-cell">
                <div class="cell-label">Güven</div>
                <div class="cell-value">${narrative.guven || '—'}</div>
            </div>
        </div>
    `;
}

// ─── OPPORTUNITIES ──────────────────────
async function loadOpportunities() {
    try {
        const allRes = await fetch('/api/analyze/all');
        const allData = await allRes.json();
        allAnalyses = allData.results || [];

        renderSidebar();

        const statusEl = document.getElementById('lastUpdate');
        if (statusEl && allData.updated_at) {
            statusEl.textContent = allData.updated_at;
        }

        const res = await fetch('/api/opportunities');
        const opps = await res.json();
        renderOpportunities(opps);
    } catch (e) {
        console.error('Fırsatlar yüklenemedi:', e);
    }
}

function renderOpportunities(opps) {
    const container = document.getElementById('opportunities');
    if (!opps || opps.length === 0) {
        container.innerHTML = '<div class="dim-text">Fırsat bulunamadı</div>';
        return;
    }

    container.innerHTML = opps.map(opp => {
        const signal = opp.signal || {};
        const sigColor = signal.color || 'var(--text-dim)';
        return `
            <div class="opp-row" onclick="loadSymbol('${opp.symbol}')">
                <span class="opp-sym">${opp.symbol.replace('.IS', '')}</span>
                <span class="opp-sig" style="background: ${sigColor}18; color: ${sigColor}">${signal.emoji || ''} ${signal.signal || ''}</span>
                <span class="opp-score">${opp.opportunity_score || 0}</span>
            </div>
        `;
    }).join('');
}

// ─── TICKER ─────────────────────────────
async function updateTicker() {
    try {
        const res = await fetch('/api/ticker');
        const items = await res.json();
        const track = document.getElementById('tickerTrack');

        if (!items || items.length === 0) return;

        const html = items.map(item => {
            const cls = item.change_pct >= 0 ? 'up' : 'down';
            const sign = item.change_pct >= 0 ? '+' : '';
            return `<span class="ticker-item">
                <span class="symbol">${item.symbol.replace('.IS', '')}</span>
                <span class="${cls}">${item.price} (${sign}${item.change_pct.toFixed(2)}%)</span>
            </span>`;
        }).join('');

        track.innerHTML = html + html;
    } catch (e) {
        console.error('Ticker hatası:', e);
    }
}

// ─── REFRESH ALL ────────────────────────
async function refreshAll() {
    await loadOpportunities();
    if (currentSymbol) {
        const res = await fetch(`/api/analyze/${encodeURIComponent(currentSymbol)}?tf=${currentTf}`);
        const data = await res.json();
        if (!data.error) {
            currentData = data;
            updateToolbarPrice(data);
            updateSignalStrip(data);
            updateIndicatorDetail(data);
            updateLevelsPanel(data);
            updateScenarioPanel(data);
        }
    }
}

// ─── ADD INSTRUMENT MODAL ───────────────
function openModal() {
    document.getElementById('addModal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('addModal').classList.add('hidden');
    document.getElementById('symbolInput').value = '';
    document.getElementById('nameInput').value = '';
}

async function addInstrument() {
    const symbol = document.getElementById('symbolInput').value.trim();
    const name = document.getElementById('nameInput').value.trim();
    const category = document.getElementById('categorySelect').value;

    if (!symbol || !name) {
        alert('Symbol ve isim gerekli!');
        return;
    }

    try {
        const res = await fetch('/api/watchlist/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, name, category })
        });
        const data = await res.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        closeModal();
        await loadWatchlist();
    } catch (e) {
        alert('Ekleme hatası: ' + e.message);
    }
}

document.addEventListener('click', (e) => {
    const modal = document.getElementById('addModal');
    if (e.target === modal) closeModal();
});
