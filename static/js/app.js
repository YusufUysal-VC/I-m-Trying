// ─── STATE ────────────────────────────────
let currentSymbol = null;
let currentTf = '3A';
let watchlist = {};
let allAnalyses = [];
let showRsi = false;
let showMacd = false;

// ─── INIT ────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
    await loadWatchlist();
    await loadOpportunities();
    updateTicker();

    // Auto-refresh ticker every 30s
    setInterval(updateTicker, 30000);
    // Auto-refresh analyses every 60s
    setInterval(refreshAll, 60000);
});

// ─── WATCHLIST ───────────────────────────
async function loadWatchlist() {
    try {
        const res = await fetch('/api/watchlist');
        watchlist = await res.json();
        renderSidebar();

        // Select first instrument
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
        const section = document.createElement('div');
        section.className = 'sidebar-section';
        section.innerHTML = `<div class="sidebar-section-title">${category}</div>`;

        for (const inst of instruments) {
            const card = document.createElement('div');
            card.className = 'instrument-card';
            card.dataset.symbol = inst.symbol;
            card.onclick = () => loadSymbol(inst.symbol);

            const cached = allAnalyses.find(a => a.symbol === inst.symbol);
            const signal = cached?.signal || { emoji: '⚪', signal: '...', color: '#888' };
            const changePct = cached?.change_pct ?? 0;
            const changeColor = changePct >= 0 ? 'var(--green)' : 'var(--red)';

            card.innerHTML = `
                <div class="info">
                    <span class="symbol-name">${inst.symbol.replace('.IS', '')}</span>
                    <span class="full-name">${inst.name}</span>
                </div>
                <div style="text-align: right;">
                    <span class="signal-badge" style="background: ${signal.color}22; color: ${signal.color}">
                        ${signal.emoji} ${signal.signal}
                    </span>
                    <div style="font-size: 11px; color: ${changeColor}; margin-top: 2px; font-family: var(--font-mono);">
                        ${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%
                    </div>
                </div>
            `;
            section.appendChild(card);
        }

        container.appendChild(section);
    }
}

// ─── SYMBOL LOADING ─────────────────────
async function loadSymbol(symbol) {
    currentSymbol = symbol;

    // Update active card
    document.querySelectorAll('.instrument-card').forEach(c => c.classList.remove('active'));
    const activeCard = document.querySelector(`[data-symbol="${symbol}"]`);
    if (activeCard) activeCard.classList.add('active');

    // Update symbol label
    document.getElementById('tfSymbolLabel').textContent = symbol;

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

        updateSignalPanel(data);
        updateScenarioPanel(data);
        await loadChart(symbol, currentTf);
    } catch (e) {
        console.error('Analiz hatası:', e);
        document.getElementById('chart-area').innerHTML = '<div class="loading">Bağlantı hatası</div>';
    }
}

// ─── CHART ──────────────────────────────
function loadChart(symbol, tf) {
    const enc = encodeURIComponent(symbol);
    const rsiParam = showRsi ? '1' : '0';
    const macdParam = showMacd ? '1' : '0';
    const url = `/api/chart/${enc}/${tf}?rsi=${rsiParam}&macd=${macdParam}`;

    document.getElementById('chart-area').innerHTML =
        `<iframe src="${url}" style="width:100%;height:100%;border:none;background:#0d1117;"></iframe>`;
}

// ─── INDICATOR TOGGLES ─────────────────
function toggleIndicator(type) {
    if (type === 'rsi') {
        showRsi = !showRsi;
        const btn = document.getElementById('toggleRsi');
        btn.classList.toggle('active', showRsi);
        btn.dataset.active = showRsi ? '1' : '0';
    } else if (type === 'macd') {
        showMacd = !showMacd;
        const btn = document.getElementById('toggleMacd');
        btn.classList.toggle('active', showMacd);
        btn.dataset.active = showMacd ? '1' : '0';
    }

    if (currentSymbol) {
        loadChart(currentSymbol, currentTf);
    }
}

// ─── TIMEFRAME TABS ─────────────────────
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.tf-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tf-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentTf = tab.dataset.tf;
            if (currentSymbol) {
                loadChart(currentSymbol, currentTf);
            }
        });
    });
});

// ─── SIGNAL PANEL ───────────────────────
function updateSignalPanel(data) {
    const panel = document.getElementById('signalPanel');
    const signal = data.signal || {};
    const ind = data.indicators || {};
    const ts = data.trend_score ?? 0;

    const trendColor = ts >= 40 ? 'var(--green)' : ts <= -40 ? 'var(--red)' : ts >= 0 ? 'var(--yellow)' : 'var(--text-secondary)';

    panel.innerHTML = `
        <div class="signal-main">
            <div class="signal-text" style="color: ${signal.color || '#888'}">${signal.emoji || '⚪'} ${signal.signal || 'NÖTR'}</div>
            <div class="signal-details">
                <div>Fiyat: <strong>${data.price || 0}</strong></div>
                <div style="color: ${data.change_pct >= 0 ? 'var(--green)' : 'var(--red)'}">
                    ${data.change_pct >= 0 ? '+' : ''}${(data.change_pct || 0).toFixed(2)}%
                </div>
            </div>
        </div>
        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
            <div class="stat-item">
                <span class="stat-label">Trend Skoru</span>
                <span class="stat-value" style="color: ${trendColor}">${ts}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">RSI</span>
                <span class="stat-value" style="color: ${ind.rsi > 70 ? 'var(--red)' : ind.rsi < 30 ? 'var(--green)' : 'var(--text-primary)'}">${(ind.rsi || 0).toFixed(1)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">MACD</span>
                <span class="stat-value" style="color: ${ind.macd_hist > 0 ? 'var(--green)' : 'var(--red)'}">${(ind.macd_hist || 0).toFixed(4)}</span>
            </div>
        </div>
        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
            <div class="stat-item">
                <span class="stat-label">EMA20</span>
                <span class="stat-value">${(ind.ema20 || 0).toFixed(2)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">EMA50</span>
                <span class="stat-value">${(ind.ema50 || 0).toFixed(2)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">BB Bant</span>
                <span class="stat-value">${(ind.bb_lower || 0).toFixed(2)} — ${(ind.bb_upper || 0).toFixed(2)}</span>
            </div>
        </div>
    `;
}

// ─── SCENARIO PANEL ─────────────────────
function updateScenarioPanel(data) {
    const panel = document.getElementById('scenarioPanel');
    const narrative = data.narrative || {};
    const plan = data.action_plan || {};

    const yonColor = plan.yon === 'LONG' ? 'var(--green)' : plan.yon === 'SHORT' ? 'var(--red)' : 'var(--yellow)';

    panel.innerHTML = `
        <div class="scenario-title">${narrative.baslik || 'Analiz'} — <span style="color: ${yonColor}">${plan.yon || ''}</span></div>
        <div class="scenario-text">${narrative.ozet || ''}</div>
        <div class="scenario-text" style="margin-top: 8px; color: var(--text-primary);">${plan.senaryo_metni || ''}</div>
        <div class="scenario-grid">
            <div class="scenario-item">
                <div class="label">Giriş Bölgesi</div>
                <div class="value">${plan.giris_bolgesi ? plan.giris_bolgesi[0].toFixed(2) + ' — ' + plan.giris_bolgesi[1].toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-item">
                <div class="label">Hedef 1</div>
                <div class="value" style="color: var(--green)">${plan.hedef_1 ? plan.hedef_1.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-item">
                <div class="label">Hedef 2</div>
                <div class="value" style="color: var(--green)">${plan.hedef_2 ? plan.hedef_2.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-item">
                <div class="label">Hedef 3</div>
                <div class="value" style="color: var(--green)">${plan.hedef_3 ? plan.hedef_3.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-item">
                <div class="label">Stop Loss</div>
                <div class="value" style="color: var(--red)">${plan.stop_loss ? plan.stop_loss.toFixed(2) : '—'}</div>
            </div>
            <div class="scenario-item">
                <div class="label">R:R Oranı</div>
                <div class="value" style="color: ${plan.rr_orani >= 1.5 ? 'var(--green)' : 'var(--yellow)'}">${plan.rr_orani || '—'}</div>
            </div>
            <div class="scenario-item">
                <div class="label">Zaman Ufku</div>
                <div class="value">${plan.zaman_ufku || '—'}</div>
            </div>
            <div class="scenario-item">
                <div class="label">Güven</div>
                <div class="value">${narrative.guven || '—'}</div>
            </div>
        </div>
        ${data.support ? `
        <div style="margin-top: 14px; display: flex; gap: 20px; flex-wrap: wrap;">
            <div>
                <span class="stat-label" style="color: var(--green); font-weight: 700;">DESTEK: </span>
                <span style="font-size: 12px; font-family: var(--font-mono);">${data.support.map(s => s.toFixed(2)).join(' | ')}</span>
            </div>
            <div>
                <span class="stat-label" style="color: var(--red); font-weight: 700;">DİRENÇ: </span>
                <span style="font-size: 12px; font-family: var(--font-mono);">${data.resistance.map(r => r.toFixed(2)).join(' | ')}</span>
            </div>
        </div>` : ''}
    `;
}

// ─── OPPORTUNITIES ──────────────────────
async function loadOpportunities() {
    try {
        // First load all analyses
        const allRes = await fetch('/api/analyze/all');
        const allData = await allRes.json();
        allAnalyses = allData.results || [];

        // Update sidebar with signal info
        renderSidebar();

        // Update last update time
        const statusEl = document.getElementById('lastUpdate');
        if (statusEl && allData.updated_at) {
            statusEl.textContent = `Son güncelleme: ${allData.updated_at}`;
        }

        // Load opportunities
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
        container.innerHTML = '<div style="color: var(--text-dim); font-size: 12px; padding: 12px;">Veri yükleniyor...</div>';
        return;
    }

    container.innerHTML = opps.map(opp => {
        const signal = opp.signal || {};
        return `
            <div class="opportunity-card" onclick="loadSymbol('${opp.symbol}')">
                <div class="opp-header">
                    <span class="opp-symbol">${opp.symbol.replace('.IS', '')}</span>
                    <span class="opp-signal" style="background: ${signal.color}22; color: ${signal.color}">
                        ${signal.emoji || ''} ${signal.signal || ''}
                    </span>
                </div>
                <div class="opp-price">${opp.price || 0}</div>
                <div class="opp-narrative">${opp.narrative?.baslik || ''}</div>
                <div class="opp-score">Skor: ${opp.opportunity_score || 0}</div>
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

        // Duplicate for seamless scroll
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
            updateSignalPanel(data);
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

// Close modal on outside click
document.addEventListener('click', (e) => {
    const modal = document.getElementById('addModal');
    if (e.target === modal) closeModal();
});
