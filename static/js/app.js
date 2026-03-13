// ─── STATE ────────────────────────────────
let currentSymbol = null;
let currentTf = '3A';
let watchlist = {};
let allAnalyses = [];
let showRsi = false;
let showMacd = false;
let showSr = true;
let showTrend = false;
let showVolume = true;
let currentData = null;
let currentTheme = localStorage.getItem('theme') || 'dark';
let multiChartMode = false;
let multiChartSymbols = [null, null, null, null];
let alerts = JSON.parse(localStorage.getItem('priceAlerts') || '[]');

// ─── INIT ────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    applyTheme(currentTheme);
    await loadWatchlist();
    await loadOpportunities();
    updateTicker();
    setupTimeframeTabs();
    renderAlerts();

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
function buildChartUrl(symbol, tf) {
    const enc = encodeURIComponent(symbol);
    const params = new URLSearchParams({
        rsi: showRsi ? '1' : '0',
        macd: showMacd ? '1' : '0',
        sr: showSr ? '1' : '0',
        trend: showTrend ? '1' : '0',
        vol: showVolume ? '1' : '0',
        theme: currentTheme
    });
    return `/api/chart/${enc}/${tf}?${params}`;
}

function loadChart(symbol, tf) {
    if (multiChartMode) return;
    const url = buildChartUrl(symbol, tf);
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
    if (multiChartMode) {
        refreshMultiCharts();
    } else if (currentSymbol) {
        loadChart(currentSymbol, currentTf);
    }
}

// ─── OVERLAY TOGGLES ────────────────────
function toggleOverlay(type) {
    if (type === 'sr') {
        showSr = !showSr;
        document.getElementById('toggleSr').classList.toggle('active', showSr);
    } else if (type === 'trend') {
        showTrend = !showTrend;
        document.getElementById('toggleTrend').classList.toggle('active', showTrend);
    } else if (type === 'vol') {
        showVolume = !showVolume;
        document.getElementById('toggleVol').classList.toggle('active', showVolume);
    }
    if (multiChartMode) {
        refreshMultiCharts();
    } else if (currentSymbol) {
        loadChart(currentSymbol, currentTf);
    }
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

// ─── THEME ─────────────────────────────
function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', currentTheme);
    applyTheme(currentTheme);
    // Reload chart with new theme
    if (multiChartMode) {
        refreshMultiCharts();
    } else if (currentSymbol) {
        loadChart(currentSymbol, currentTf);
    }
}

function applyTheme(theme) {
    document.body.classList.toggle('light-theme', theme === 'light');
    const icon = document.getElementById('themeIcon');
    if (theme === 'light') {
        icon.innerHTML = '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>';
    } else {
        icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
    }
}

// ─── MULTI-CHART ───────────────────────
function toggleMultiChart() {
    multiChartMode = !multiChartMode;
    document.getElementById('multiChartBtn').classList.toggle('active', multiChartMode);
    document.getElementById('singleChartView').classList.toggle('hidden', multiChartMode);
    document.getElementById('multiChartView').classList.toggle('hidden', !multiChartMode);

    if (multiChartMode) {
        // Fill with first 4 symbols from watchlist
        const allSymbols = [];
        for (const instruments of Object.values(watchlist)) {
            for (const inst of instruments) {
                allSymbols.push(inst.symbol);
            }
        }
        for (let i = 0; i < 4; i++) {
            multiChartSymbols[i] = allSymbols[i] || null;
        }
        // If current symbol is in list, put it first
        if (currentSymbol) {
            const idx = multiChartSymbols.indexOf(currentSymbol);
            if (idx > 0) {
                multiChartSymbols.splice(idx, 1);
                multiChartSymbols.unshift(currentSymbol);
                multiChartSymbols = multiChartSymbols.slice(0, 4);
            } else if (idx === -1) {
                multiChartSymbols[0] = currentSymbol;
            }
        }
        refreshMultiCharts();
    }
}

function refreshMultiCharts() {
    for (let i = 0; i < 4; i++) {
        const cell = document.getElementById(`mc${i}`);
        const sym = multiChartSymbols[i];
        if (sym) {
            const url = buildChartUrl(sym, currentTf);
            cell.innerHTML = `<span class="mc-label">${sym.replace('.IS', '')}</span><iframe src="${url}"></iframe>`;
        } else {
            cell.innerHTML = '<div class="chart-placeholder">—</div>';
        }
    }
}

// ─── RIGHT PANEL TABS ──────────────────
function switchRightTab(tab) {
    document.querySelectorAll('.panel-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

    document.getElementById('tabAnalysis').classList.toggle('hidden', tab !== 'analysis');
    document.getElementById('tabPortfolio').classList.toggle('hidden', tab !== 'portfolio');
    document.getElementById('tabAlerts').classList.toggle('hidden', tab !== 'alerts');

    if (tab === 'portfolio') loadPortfolio();
}

// ─── PORTFOLIO ─────────────────────────
async function loadPortfolio() {
    try {
        const res = await fetch('/api/portfolio');
        const data = await res.json();
        renderPortfolio(data);
    } catch (e) {
        console.error('Portföy yüklenemedi:', e);
    }
}

function renderPortfolio(data) {
    const summary = document.getElementById('portfolioSummary');
    const list = document.getElementById('portfolioList');

    if (!data.positions || data.positions.length === 0) {
        summary.innerHTML = '<div class="dim-text" style="grid-column:1/-1">Henüz pozisyon yok</div>';
        list.innerHTML = '';
        return;
    }

    const pnlColor = data.total_pnl >= 0 ? 'var(--green)' : 'var(--red)';
    const pnlSign = data.total_pnl >= 0 ? '+' : '';

    summary.innerHTML = `
        <div class="pf-summary-card">
            <div class="pf-label">Toplam Maliyet</div>
            <div class="pf-value">${data.total_cost.toLocaleString('tr-TR', {minimumFractionDigits: 2})}</div>
        </div>
        <div class="pf-summary-card">
            <div class="pf-label">Güncel Değer</div>
            <div class="pf-value">${data.total_current.toLocaleString('tr-TR', {minimumFractionDigits: 2})}</div>
        </div>
        <div class="pf-summary-card">
            <div class="pf-label">Toplam K/Z</div>
            <div class="pf-value" style="color:${pnlColor}">${pnlSign}${data.total_pnl.toLocaleString('tr-TR', {minimumFractionDigits: 2})}</div>
        </div>
        <div class="pf-summary-card">
            <div class="pf-label">K/Z %</div>
            <div class="pf-value" style="color:${pnlColor}">${pnlSign}${data.total_pnl_pct.toFixed(2)}%</div>
        </div>
    `;

    list.innerHTML = data.positions.map((pos, i) => {
        const color = pos.pnl >= 0 ? 'var(--green)' : 'var(--red)';
        const sign = pos.pnl >= 0 ? '+' : '';
        return `
            <div class="pf-row">
                <div>
                    <div class="pf-sym">${pos.symbol.replace('.IS', '')}</div>
                    <div class="pf-detail">${pos.quantity} adet @ ${pos.buy_price.toFixed(2)}</div>
                </div>
                <div class="pf-pnl" style="color:${color}">
                    ${sign}${pos.pnl.toFixed(2)}<br>
                    <span style="font-size:10px">${sign}${pos.pnl_pct.toFixed(2)}%</span>
                </div>
                <button class="pf-remove" onclick="removePortfolio(${i})" title="Sil">✕</button>
            </div>
        `;
    }).join('');
}

function openPortfolioModal() {
    document.getElementById('portfolioModal').classList.remove('hidden');
    if (currentSymbol) {
        document.getElementById('pfSymbolInput').value = currentSymbol;
        if (currentData?.price) {
            document.getElementById('pfPriceInput').value = currentData.price;
        }
    }
}

function closePortfolioModal() {
    document.getElementById('portfolioModal').classList.add('hidden');
    document.getElementById('pfSymbolInput').value = '';
    document.getElementById('pfPriceInput').value = '';
    document.getElementById('pfQuantityInput').value = '';
}

async function addPortfolioPosition() {
    const symbol = document.getElementById('pfSymbolInput').value.trim();
    const buy_price = document.getElementById('pfPriceInput').value;
    const quantity = document.getElementById('pfQuantityInput').value;

    if (!symbol || !buy_price || !quantity) {
        alert('Tüm alanları doldurun!');
        return;
    }

    try {
        const res = await fetch('/api/portfolio/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, buy_price, quantity })
        });
        const data = await res.json();
        if (data.error) { alert(data.error); return; }
        closePortfolioModal();
        loadPortfolio();
    } catch (e) {
        alert('Hata: ' + e.message);
    }
}

async function removePortfolio(index) {
    try {
        await fetch('/api/portfolio/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index })
        });
        loadPortfolio();
    } catch (e) {
        console.error('Pozisyon silinemedi:', e);
    }
}

// ─── PRICE ALERTS ──────────────────────
function openAlertModal() {
    document.getElementById('alertModal').classList.remove('hidden');
    if (currentSymbol) {
        document.getElementById('alertSymbolInput').value = currentSymbol;
    }
    // Switch to alerts tab
    switchRightTab('alerts');
}

function closeAlertModal() {
    document.getElementById('alertModal').classList.add('hidden');
    document.getElementById('alertSymbolInput').value = '';
    document.getElementById('alertPriceInput').value = '';
}

function addAlert() {
    const symbol = document.getElementById('alertSymbolInput').value.trim();
    const condition = document.getElementById('alertCondition').value;
    const price = parseFloat(document.getElementById('alertPriceInput').value);

    if (!symbol || !price) {
        alert('Sembol ve fiyat gerekli!');
        return;
    }

    alerts.push({ symbol, condition, price, triggered: false });
    localStorage.setItem('priceAlerts', JSON.stringify(alerts));
    closeAlertModal();
    renderAlerts();

    // Request notification permission
    if (Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

function removeAlert(index) {
    alerts.splice(index, 1);
    localStorage.setItem('priceAlerts', JSON.stringify(alerts));
    renderAlerts();
}

function renderAlerts() {
    const container = document.getElementById('alertsList');
    if (!alerts || alerts.length === 0) {
        container.innerHTML = '<div class="dim-text">Henüz alarm yok</div>';
        return;
    }

    container.innerHTML = alerts.map((a, i) => {
        const condText = a.condition === 'above' ? '↑' : '↓';
        const color = a.triggered ? 'var(--text-muted)' : (a.condition === 'above' ? 'var(--green)' : 'var(--red)');
        return `
            <div class="alert-row" style="${a.triggered ? 'opacity:0.5' : ''}">
                <span class="alert-sym">${a.symbol.replace('.IS', '')}</span>
                <span class="alert-cond" style="color:${color}">${condText} ${a.price.toFixed(2)}</span>
                <button class="alert-remove" onclick="removeAlert(${i})" title="Sil">✕</button>
            </div>
        `;
    }).join('');
}

function checkAlerts() {
    if (!allAnalyses || allAnalyses.length === 0) return;
    let changed = false;

    alerts.forEach(alert => {
        if (alert.triggered) return;
        const data = allAnalyses.find(a => a.symbol === alert.symbol);
        if (!data) return;

        const price = data.price || 0;
        const triggered = (alert.condition === 'above' && price >= alert.price) ||
                          (alert.condition === 'below' && price <= alert.price);

        if (triggered) {
            alert.triggered = true;
            changed = true;
            const direction = alert.condition === 'above' ? 'üstüne çıktı' : 'altına düştü';
            const msg = `${alert.symbol.replace('.IS', '')} ${alert.price.toFixed(2)} ${direction}! Güncel: ${price.toFixed(2)}`;

            if (Notification.permission === 'granted') {
                new Notification('Fiyat Alarmı', { body: msg, icon: '/static/favicon.ico' });
            }
        }
    });

    if (changed) {
        localStorage.setItem('priceAlerts', JSON.stringify(alerts));
        renderAlerts();
    }
}

// ─── REFRESH ALL ────────────────────────
async function refreshAll() {
    await loadOpportunities();
    checkAlerts();
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
    if (e.target.classList.contains('modal')) {
        e.target.classList.add('hidden');
    }
});
