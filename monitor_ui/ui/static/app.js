/* ═══════════════════════════════════════════════════════════
   Fox Trading Bot Monitor — Main Application
   Vanilla JS + WebSocket + Chart.js
   ═══════════════════════════════════════════════════════════ */

(() => {
    'use strict';

    // ─── State ──────────────────────────────────────────────
    const state = {
        ws: null,
        connected: false,
        paused: false,
        eventFilter: 'all',
        pnlPeriod: '24h',
        pnlChart: null,
        reconnectAttempts: 0,
        maxReconnectDelay: 10000,
        displayedEventIds: new Set(),
    };

    // ─── DOM References ─────────────────────────────────────
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    // ─── Formatting Helpers ─────────────────────────────────

    function formatPrice(val) {
        if (val == null) return '—';
        const n = Number(val);
        if (Math.abs(n) >= 1000) return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (Math.abs(n) >= 1) return n.toFixed(4);
        return n.toFixed(6);
    }

    function formatPnl(val) {
        if (val == null) return '—';
        const n = Number(val);
        const sign = n >= 0 ? '+' : '';
        return sign + n.toFixed(2);
    }

    function formatPercent(val) {
        if (val == null) return '—';
        const n = Number(val);
        const sign = n >= 0 ? '+' : '';
        return sign + n.toFixed(2) + '%';
    }

    function formatTime(ts) {
        if (!ts) return '—';
        const d = new Date(ts);
        return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

    function formatUptime(seconds) {
        if (!seconds) return '—';
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        return `${h}h ${m}m`;
    }

    function formatExposure(val) {
        if (val == null) return '$0';
        const n = Number(val);
        if (n >= 1000000) return '$' + (n / 1000000).toFixed(1) + 'M';
        if (n >= 1000) return '$' + (n / 1000).toFixed(1) + 'K';
        return '$' + n.toFixed(0);
    }

    function pnlClass(val) {
        if (val == null) return '';
        return Number(val) >= 0 ? 'profit' : 'loss';
    }

    // ─── WebSocket Connection ───────────────────────────────

    function connectWS() {
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const url = `${proto}://${location.host}/ws/live`;

        state.ws = new WebSocket(url);

        state.ws.onopen = () => {
            state.connected = true;
            state.reconnectAttempts = 0;
            updateConnectionStatus(true);
            console.log('[WS] Connected');
        };

        state.ws.onmessage = (evt) => {
            try {
                const msg = JSON.parse(evt.data);
                handleMessage(msg);
            } catch (e) {
                console.error('[WS] Parse error:', e);
            }
        };

        state.ws.onclose = () => {
            state.connected = false;
            updateConnectionStatus(false);
            console.log('[WS] Disconnected');
            scheduleReconnect();
        };

        state.ws.onerror = (e) => {
            console.error('[WS] Error:', e);
        };
    }

    function scheduleReconnect() {
        const delay = Math.min(1000 * Math.pow(1.5, state.reconnectAttempts), state.maxReconnectDelay);
        state.reconnectAttempts++;
        console.log(`[WS] Reconnecting in ${Math.round(delay / 1000)}s (attempt ${state.reconnectAttempts})`);
        setTimeout(connectWS, delay);
    }

    function updateConnectionStatus(connected) {
        const pill = $('#connection-status');
        if (connected) {
            pill.className = 'status-pill connected';
            pill.querySelector('span:last-child').textContent = 'Live';
        } else {
            pill.className = 'status-pill disconnected';
            pill.querySelector('span:last-child').textContent = 'Disconnected';
        }
    }

    // ─── Message Handler ────────────────────────────────────

    function handleMessage(msg) {
        if (state.paused) return;

        switch (msg.type) {
            case 'snapshot':
                renderAll(msg.data);
                break;
            case 'fast':
                renderFast(msg.data);
                break;
            case 'slow':
                renderSlow(msg.data);
                break;
            case 'ping':
                if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                    state.ws.send('pong');
                }
                break;
            case 'signal':
                prependSignal(msg.data);
                break;
            case 'signals_batch':
                if (msg.data && msg.data.signals) renderSignals(msg.data.signals);
                break;
            case 'signal_status':
                renderSignalStatus(msg.data);
                break;
        }
    }

    function renderAll(data) {
        renderFast(data);
        renderSlow(data);
        // Signal data in initial snapshot
        if (data.signals) renderSignals(data.signals);
        if (data.signal_status) renderSignalStatus(data.signal_status);
    }

    function renderFast(data) {
        if (data.positions) renderPositions(data.positions);
        if (data.events) renderEvents(data.events);
        if (data.stats) renderStats(data.stats);
        if (data.severity_counts) renderSeverityCounts(data.severity_counts);
    }

    function renderSlow(data) {
        if (data.status) renderStatus(data.status);
        if (data.trailing_stops) renderTrailingStops(data.trailing_stops);
        if (data.risk_events) renderRiskEvents(data.risk_events);
        if (data.recent_trades) renderRecentTrades(data.recent_trades);
        if (data.pnl_hourly && state.pnlPeriod === '24h') renderPnlChart(data.pnl_hourly, '24h');
        if (data.pnl_daily && state.pnlPeriod !== '24h') renderPnlChart(data.pnl_daily, state.pnlPeriod);
    }

    // ─── Positions Table ────────────────────────────────────

    function renderPositions(positions) {
        const tbody = $('#positions-tbody');
        const count = $('#positions-count');
        count.textContent = positions.length;

        if (positions.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="10">No active positions</td></tr>';
            return;
        }

        const rows = positions.map(p => {
            const sideClass = p.side?.toLowerCase() === 'long' ? 'side-long' : 'side-short';
            const sideEmoji = p.side?.toLowerCase() === 'long' ? '🟢' : '🔴';
            const pnlCls = pnlClass(p.unrealized_pnl);

            // Trailing stop badge
            let tsBadge = '';
            if (p.ts_activated || p.trailing_activated) {
                tsBadge = `<span class="ts-badge ts-badge--active">✓ Active</span>`;
            } else if (p.has_trailing_stop && p.ts_state) {
                const progress = p.ts_progress != null ? ` ${p.ts_progress.toFixed(0)}%` : '';
                tsBadge = `<span class="ts-badge ts-badge--pending">⏳${progress}</span>`;
            } else if (p.has_trailing_stop) {
                tsBadge = `<span class="ts-badge ts-badge--inactive">○ Set</span>`;
            } else {
                tsBadge = `<span class="ts-badge ts-badge--inactive">—</span>`;
            }

            // Age with color warning
            let ageClass = '';
            if (p.age_hours > 24) ageClass = 'loss';
            else if (p.age_hours > 12) ageClass = 'warning-text';

            // SL proximity bar
            let slCell = '<td>—</td>';
            if (p.sl_distance_pct != null && p.stop_loss_price && p.entry_price) {
                const dist = p.sl_distance_pct;
                // SL gap = distance from entry to SL as % of entry
                const slGapPct = Math.abs(p.entry_price - p.stop_loss_price) / p.entry_price * 100;

                // How much of the gap remains? (100% = at entry, 0% = at SL)
                const remainPct = slGapPct > 0 ? Math.max(0, Math.min(100, (dist / slGapPct) * 100)) : 0;
                // Consumed = how much we've moved towards SL
                const consumedPct = 100 - remainPct;

                // Color:
                // GREEN:  in profit (consumed <= 0, price above entry)
                // YELLOW: small loss, consumed 0-40% of SL gap
                // RED:    >= 40% consumed (significant move toward SL)
                let barClass = 'sl-safe';
                if (consumedPct >= 40) barClass = 'sl-danger';
                else if (consumedPct > 0) barClass = 'sl-caution';

                // Bar shows remaining safety (full = safe, empty = at SL)
                const fillPct = Math.max(0, Math.min(100, remainPct));
                const sign = dist >= 0 ? '+' : '';
                slCell = `<td class="sl-cell">
                    <div class="sl-bar-wrap">
                        <div class="sl-bar ${barClass}" style="width:${fillPct}%"></div>
                    </div>
                    <span class="sl-label ${barClass}">${sign}${dist.toFixed(1)}%</span>
                </td>`;
            }

            return `<tr>
                <td><strong>${p.symbol || '—'}</strong></td>
                <td>${p.exchange || '—'}</td>
                <td class="${sideClass}">${sideEmoji} ${(p.side || '').toUpperCase()}</td>
                <td>${formatPrice(p.entry_price)}</td>
                <td>${formatPrice(p.current_price)}</td>
                <td class="${pnlCls}"><strong>${formatPnl(p.unrealized_pnl)}</strong></td>
                <td class="${pnlCls}">${formatPercent(p.pnl_percentage)}</td>
                ${slCell}
                <td>${tsBadge}</td>
                <td class="${p.timeout_class || ''}">${p.timeout_display || '—'}</td>
                <td class="${ageClass}">${p.age_display || '—'}</td>
            </tr>`;
        });

        tbody.innerHTML = rows.join('');
    }

    // ─── Events Stream ──────────────────────────────────────

    // Track last rendered event fingerprint to avoid unnecessary DOM updates
    let _lastEventsKey = '';

    function renderEvents(events) {
        const stream = $('#events-stream');
        let filtered = events;

        // Apply filter
        if (state.eventFilter !== 'all') {
            const filterMap = {
                'position': ['position_created', 'position_closed', 'position_error', 'position_cleanup'],
                'order': ['order_placed', 'order_filled', 'order_cancelled', 'order_error'],
                'stop': ['stop_loss_placed', 'stop_loss_triggered', 'stop_loss_updated', 'stop_loss_error'],
                'trailing': ['trailing_stop_created', 'trailing_stop_activated', 'trailing_stop_updated', 'trailing_stop_breakeven', 'trailing_stop_removed'],
                'wave': ['wave_detected', 'wave_completed', 'wave_monitoring_started', 'signal_executed', 'signal_filtered'],
                'error': null, // special: filter by severity
            };

            if (state.eventFilter === 'error') {
                filtered = events.filter(e => ['ERROR', 'CRITICAL', 'WARNING'].includes(e.severity));
            } else {
                const types = filterMap[state.eventFilter] || [];
                filtered = events.filter(e => types.includes(e.event_type));
            }
        }

        if (filtered.length === 0) {
            if (_lastEventsKey !== '__empty__') {
                stream.innerHTML = '<div class="event-placeholder">No matching events</div>';
                _lastEventsKey = '__empty__';
            }
            return;
        }

        const display = filtered.slice(0, 50);

        // Build a fingerprint from event IDs/timestamps to detect changes
        const newKey = display.map(e => `${e.id || ''}:${e.created_at || ''}`).join('|');
        if (newKey === _lastEventsKey) return; // nothing changed — skip DOM update
        _lastEventsKey = newKey;

        const items = display.map(e => {
            const sevClass = `severity-${(e.severity || 'info').toLowerCase()}`;

            // Extract a summary from event_data
            let detail = '';
            if (e.event_data) {
                const data = typeof e.event_data === 'string' ? JSON.parse(e.event_data) : e.event_data;
                if (data.message) detail = data.message;
                else if (data.symbol) detail = data.symbol;
                else if (data.reason) detail = data.reason;
                else {
                    const keys = Object.keys(data).slice(0, 3);
                    detail = keys.map(k => `${k}: ${JSON.stringify(data[k]).slice(0, 30)}`).join(', ');
                }
            }

            const symbolTag = e.symbol ? `<span style="color:var(--accent-blue)">${e.symbol}</span> ` : '';

            return `<div class="event-item ${sevClass}">
                <span class="event-item__icon">${e.icon || '📝'}</span>
                <div class="event-item__content">
                    <div class="event-item__type">${symbolTag}${formatEventType(e.event_type)}</div>
                    <div class="event-item__detail">${escapeHtml(detail)}</div>
                </div>
                <span class="event-item__time">${formatTime(e.created_at)}</span>
            </div>`;
        });

        stream.innerHTML = items.join('');
    }

    function formatEventType(type) {
        if (!type) return '';
        return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ─── Stats Cards ────────────────────────────────────────

    function renderStats(stats) {
        // Balance (from Binance)
        const balanceEl = $('#val-balance');
        if (balanceEl) {
            const bal = stats.wallet_balance || 0;
            balanceEl.textContent = '$' + bal.toFixed(2);
        }

        // Trade count (from Binance)
        const tradesEl = $('#stat-trades');
        if (tradesEl) tradesEl.textContent = stats.trade_count || 0;

        const winnersEl = $('#stat-winners');
        winnersEl.textContent = stats.winners || 0;
        winnersEl.className = 'metric__val profit';

        const losersEl = $('#stat-losers');
        losersEl.textContent = stats.losers || 0;
        losersEl.className = 'metric__val loss';

        // Net PnL 24h (from Binance: gross + commission + funding)
        const pnlEl = $('#stat-total-pnl');
        const pnl = stats.net_pnl_24h || 0;
        pnlEl.textContent = '$' + formatPnl(pnl);
        pnlEl.className = 'metric__val ' + pnlClass(pnl);

        $('#stat-ts-active').textContent = stats.ts_active_count || 0;

        const wr = stats.win_rate;
        $('#val-winrate').textContent = wr != null ? wr.toFixed(0) + '%' : '—';
    }

    // ─── System Status ──────────────────────────────────────

    function renderStatus(status) {
        $('#val-positions').textContent = status.active_positions || 0;
        $('#val-exposure').textContent = formatExposure(status.total_exposure);
        $('#uptime').textContent = 'Uptime: ' + formatUptime(status.uptime_seconds);
    }

    function renderSeverityCounts(counts) {
        const warnings = (counts.WARNING || 0);
        const errors = (counts.ERROR || 0) + (counts.CRITICAL || 0);

        const wBadge = $('#badge-warnings');
        const eBadge = $('#badge-errors');

        if (warnings > 0) {
            wBadge.style.display = 'flex';
            $('#val-warnings').textContent = warnings;
        } else {
            wBadge.style.display = 'none';
        }

        if (errors > 0) {
            eBadge.style.display = 'flex';
            $('#val-errors').textContent = errors;
        } else {
            eBadge.style.display = 'none';
        }
    }

    // ─── PnL Chart ──────────────────────────────────────────

    function renderPnlChart(data, period) {
        const ctx = $('#pnl-chart');
        if (!ctx) return;

        const labels = data.map(d => {
            const dt = new Date(d.timestamp);
            if (period === '24h') return dt.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' });
            return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const values = data.map(d => d.total_pnl || 0);

        // Cumulative PnL
        const cumulative = [];
        let sum = 0;
        for (const v of values) {
            sum += v;
            cumulative.push(sum);
        }

        if (state.pnlChart) {
            state.pnlChart.data.labels = labels;
            state.pnlChart.data.datasets[0].data = cumulative;
            // Update gradient based on final value
            updateChartGradient(state.pnlChart, cumulative);
            state.pnlChart.update('none');
            return;
        }

        state.pnlChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Cumulative PnL',
                    data: cumulative,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHitRadius: 8,
                    tension: 0.3,
                    fill: true,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(22, 27, 34, 0.95)',
                        titleColor: '#e6edf3',
                        bodyColor: '#8b949e',
                        borderColor: 'rgba(48, 54, 61, 0.6)',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                        callbacks: {
                            label: (ctx) => {
                                const v = ctx.parsed.y;
                                return `PnL: $${v >= 0 ? '+' : ''}${v.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(48, 54, 61, 0.3)' },
                        ticks: { color: '#484f58', font: { size: 10 }, maxTicksLimit: 8 },
                    },
                    y: {
                        grid: { color: 'rgba(48, 54, 61, 0.3)' },
                        ticks: {
                            color: '#484f58',
                            font: { size: 10 },
                            callback: (v) => '$' + v.toFixed(0)
                        },
                    }
                }
            }
        });

        updateChartGradient(state.pnlChart, cumulative);
        state.pnlChart.update('none');
    }

    function updateChartGradient(chart, data) {
        const ctx = chart.ctx;
        const area = chart.chartArea;
        if (!area) return;

        const lastVal = data.length > 0 ? data[data.length - 1] : 0;
        const isProfit = lastVal >= 0;

        const gradient = ctx.createLinearGradient(0, area.top, 0, area.bottom);
        if (isProfit) {
            chart.data.datasets[0].borderColor = '#3fb950';
            gradient.addColorStop(0, 'rgba(63, 185, 80, 0.25)');
            gradient.addColorStop(1, 'rgba(63, 185, 80, 0.01)');
        } else {
            chart.data.datasets[0].borderColor = '#f85149';
            gradient.addColorStop(0, 'rgba(248, 81, 73, 0.25)');
            gradient.addColorStop(1, 'rgba(248, 81, 73, 0.01)');
        }
        chart.data.datasets[0].backgroundColor = gradient;
    }

    // ─── Trailing Stops ─────────────────────────────────────

    function renderTrailingStops(stops) {
        const list = $('#trailing-list');

        if (!stops || stops.length === 0) {
            list.innerHTML = '<div class="event-placeholder">No active trailing stops</div>';
            return;
        }

        const items = stops.map(ts => {
            const stateClass = ts.is_activated ? 'active' : (ts.state === 'active' ? 'pending' : 'inactive');
            const stateLabel = ts.is_activated ? '✓ Activated' : (ts.state === 'active' ? '⏳ Pending' : '○ Inactive');
            const progress = ts.progress != null ? ts.progress : 0;

            return `<div class="ts-card">
                <div class="ts-card__header">
                    <span class="ts-card__symbol">${ts.side === 'long' ? '🟢' : '🔴'} ${ts.symbol}</span>
                    <span class="ts-card__state ts-card__state--${stateClass}">${stateLabel}</span>
                </div>
                <div class="ts-progress-bar">
                    <div class="ts-progress-bar__fill" style="width: ${progress.toFixed(1)}%"></div>
                </div>
                <div class="ts-card__details">
                    <div class="ts-card__detail">
                        <span class="ts-card__detail-label">Entry</span>
                        <span class="ts-card__detail-value">${formatPrice(ts.entry_price)}</span>
                    </div>
                    <div class="ts-card__detail">
                        <span class="ts-card__detail-label">Activation</span>
                        <span class="ts-card__detail-value">${formatPrice(ts.activation_price)}</span>
                    </div>
                    <div class="ts-card__detail">
                        <span class="ts-card__detail-label">Stop Price</span>
                        <span class="ts-card__detail-value">${formatPrice(ts.current_stop_price)}</span>
                    </div>
                    <div class="ts-card__detail">
                        <span class="ts-card__detail-label">Peak Profit</span>
                        <span class="ts-card__detail-value ${pnlClass(ts.highest_profit_percent)}">${formatPercent(ts.highest_profit_percent)}</span>
                    </div>
                    <div class="ts-card__detail">
                        <span class="ts-card__detail-label">Updates</span>
                        <span class="ts-card__detail-value">${ts.update_count || 0}</span>
                    </div>
                    <div class="ts-card__detail">
                        <span class="ts-card__detail-label">Callback</span>
                        <span class="ts-card__detail-value">${ts.callback_percent ? ts.callback_percent.toFixed(2) + '%' : '—'}</span>
                    </div>
                </div>
            </div>`;
        });

        list.innerHTML = items.join('');
    }

    // ─── Risk Events ────────────────────────────────────────

    function renderRiskEvents(events) {
        const list = $('#risk-list');

        if (!events || events.length === 0) {
            list.innerHTML = '<div class="event-placeholder">No risk events</div>';
            return;
        }

        const items = events.slice(0, 20).map(e => {
            const levelClass = e.risk_level?.toLowerCase() === 'high' ? 'risk-high'
                : e.risk_level?.toLowerCase() === 'critical' ? 'risk-critical' : '';

            return `<div class="risk-item ${levelClass}">
                <div>
                    <span class="risk-item__type">${formatEventType(e.event_type)}</span>
                    ${e.position_id ? `<span style="color:var(--text-muted);font-size:0.85em"> #${e.position_id}</span>` : ''}
                </div>
                <span class="risk-item__time">${formatTime(e.created_at)}</span>
            </div>`;
        });

        list.innerHTML = items.join('');
    }

    // ─── Recent Trades ─────────────────────────────────────

    function renderRecentTrades(trades) {
        const tbody = $('#trades-tbody');
        const count = $('#trades-count');
        count.textContent = trades.length;

        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="9">No closed trades</td></tr>';
            return;
        }

        const rows = trades.map(t => {
            const sideClass = t.side?.toLowerCase() === 'long' ? 'side-long' : 'side-short';
            const pnlCls = pnlClass(t.realized_pnl);
            const isWin = Number(t.realized_pnl || 0) >= 0;

            // Exit reason badge
            let reasonBadge = '—';
            if (t.exit_reason_display && t.exit_reason_display !== '—') {
                const reasonClass = t.exit_reason?.includes('stop') ? 'loss'
                    : t.exit_reason?.includes('trailing') ? 'profit'
                        : '';
                reasonBadge = `<span class="reason-badge ${reasonClass}">${t.exit_reason_display}</span>`;
            }

            // Closed timestamp
            const closedAt = t.closed_at ? new Date(t.closed_at).toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false
            }) : '—';

            return `<tr class="${isWin ? 'trade-win' : 'trade-loss'}">
                <td><strong>${t.symbol || '—'}</strong></td>
                <td class="${sideClass}">${(t.side || '').toUpperCase()}</td>
                <td>${formatPrice(t.entry_price)}</td>
                <td>${formatPrice(t.exit_price)}</td>
                <td class="${pnlCls}"><strong>${formatPnl(t.realized_pnl)}</strong></td>
                <td class="${pnlCls}">${formatPercent(t.pnl_percentage)}</td>
                <td>${reasonBadge}</td>
                <td>${t.hold_display || '—'}</td>
                <td style="font-size:0.8em;color:var(--text-muted)">${closedAt}</td>
            </tr>`;
        });

        tbody.innerHTML = rows.join('');
    }

    // ─── Live Signals ───────────────────────────────────────

    function renderSignals(signals) {
        const section = $('#signals-section');
        const tbody = $('#signals-tbody');
        const count = $('#signals-count');

        if (!signals || signals.length === 0) {
            // Keep section visibility as-is (only show if configured)
            tbody.innerHTML = '<tr class="empty-row"><td colspan="7">Waiting for signals...</td></tr>';
            count.textContent = '0';
            return;
        }

        section.style.display = '';
        count.textContent = signals.length;

        const rows = signals.map(s => {
            const score = Number(s.score || 0);
            const scoreCls = score >= 130 ? 'score-high' : score >= 100 ? 'score-mid' : 'score-low';
            const patterns = (s.patterns || []).join(', ') || '—';
            const rsi = s.rsi != null ? Number(s.rsi).toFixed(1) : '—';
            const vol = s.volume_zscore != null ? Number(s.volume_zscore).toFixed(1) : '—';
            const oi = s.oi_delta_pct != null ? Number(s.oi_delta_pct).toFixed(1) : '—';

            // Format time
            let timeStr = '—';
            if (s.timestamp) {
                const d = new Date(s.timestamp);
                if (!isNaN(d)) {
                    timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
                } else {
                    timeStr = s.timestamp.substring(11, 16) || s.timestamp;
                }
            }

            return `<tr class="signal-row">
                <td><strong>${s.symbol || '???'}</strong></td>
                <td class="${scoreCls}"><strong>${score}</strong></td>
                <td class="signal-patterns">${patterns}</td>
                <td>${rsi}</td>
                <td>${vol}</td>
                <td>${oi}</td>
                <td style="font-size:0.8em;color:var(--text-muted)">${timeStr}</td>
            </tr>`;
        });

        tbody.innerHTML = rows.join('');
    }

    function prependSignal(sig) {
        const section = $('#signals-section');
        section.style.display = '';

        const tbody = $('#signals-tbody');
        const count = $('#signals-count');

        // Remove empty placeholder
        const empty = tbody.querySelector('.empty-row');
        if (empty) empty.remove();

        const score = Number(sig.score || 0);
        const scoreCls = score >= 130 ? 'score-high' : score >= 100 ? 'score-mid' : 'score-low';
        const patterns = (sig.patterns || []).join(', ') || '—';
        const rsi = sig.rsi != null ? Number(sig.rsi).toFixed(1) : '—';
        const vol = sig.volume_zscore != null ? Number(sig.volume_zscore).toFixed(1) : '—';
        const oi = sig.oi_delta_pct != null ? Number(sig.oi_delta_pct).toFixed(1) : '—';
        let timeStr = '—';
        if (sig.timestamp) {
            const d = new Date(sig.timestamp);
            if (!isNaN(d)) {
                timeStr = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
            } else {
                timeStr = sig.timestamp.substring(11, 16) || sig.timestamp;
            }
        }

        const tr = document.createElement('tr');
        tr.className = 'signal-row signal-new';
        tr.innerHTML = `
            <td><strong>${sig.symbol || '???'}</strong></td>
            <td class="${scoreCls}"><strong>${score}</strong></td>
            <td class="signal-patterns">${patterns}</td>
            <td>${rsi}</td>
            <td>${vol}</td>
            <td>${oi}</td>
            <td style="font-size:0.8em;color:var(--text-muted)">${timeStr}</td>
        `;
        tbody.prepend(tr);

        // Limit to 50 rows
        while (tbody.children.length > 50) tbody.lastChild.remove();

        count.textContent = tbody.children.length;
    }

    function renderSignalStatus(status) {
        const section = $('#signals-section');
        const badge = $('#signal-status');
        if (!status) return;

        if (status.configured || status.connected) {
            section.style.display = '';
        }

        if (status.connected) {
            badge.className = 'signal-status connected';
            badge.innerHTML = '<span class="pulse-dot"></span> Connected';
        } else {
            badge.className = 'signal-status disconnected';
            badge.innerHTML = '<span class="pulse-dot"></span> Disconnected';
        }
    }

    // ─── Event Handlers ─────────────────────────────────────

    function setupEventHandlers() {
        // PnL period tabs
        $$('.period-tabs .tab').forEach(tab => {
            tab.addEventListener('click', () => {
                $$('.period-tabs .tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                state.pnlPeriod = tab.dataset.period;
                // Destroy chart to rebuild with new period
                if (state.pnlChart) {
                    state.pnlChart.destroy();
                    state.pnlChart = null;
                }
                // Fetch new data
                fetchPnlData(state.pnlPeriod);
            });
        });

        // Event filter
        $('#event-filter').addEventListener('change', (e) => {
            state.eventFilter = e.target.value;
            // Re-render with current cached data — trigger via WS refresh
            if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                state.ws.send('refresh');
            }
        });

        // Clear events
        $('#btn-clear-events').addEventListener('click', () => {
            $('#events-stream').innerHTML = '<div class="event-placeholder">Events cleared</div>';
            state.displayedEventIds.clear();
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Don't handle if typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

            switch (e.key.toLowerCase()) {
                case 'r':
                    e.preventDefault();
                    if (state.ws && state.ws.readyState === WebSocket.OPEN) {
                        state.ws.send('refresh');
                    }
                    break;
                case 'p':
                    e.preventDefault();
                    state.paused = !state.paused;
                    const pill = $('#connection-status');
                    if (state.paused) {
                        pill.querySelector('span:last-child').textContent = 'Paused';
                        pill.className = 'status-pill';
                    } else {
                        updateConnectionStatus(state.connected);
                    }
                    break;
                case 'f':
                    e.preventDefault();
                    $('#event-filter').focus();
                    break;
            }
        });
    }

    // ─── REST Fetch ─────────────────────────────────────────

    async function fetchPnlData(period) {
        try {
            const res = await fetch(`/api/pnl-history?period=${period}`);
            const data = await res.json();
            renderPnlChart(data, period);
        } catch (e) {
            console.error('Failed to fetch PnL data:', e);
        }
    }

    // ─── Init ───────────────────────────────────────────────

    function init() {
        setupEventHandlers();
        connectWS();
        console.log('[Fox Monitor] Started');
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
