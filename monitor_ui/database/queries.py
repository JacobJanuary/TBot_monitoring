"""SQL queries for monitoring database."""

# Active positions with trailing stop status
ACTIVE_POSITIONS_QUERY = """
SELECT
    p.id,
    p.symbol,
    p.exchange,
    p.side,
    p.entry_price,
    p.quantity,
    p.current_price,
    p.unrealized_pnl,
    p.pnl_percentage,
    p.stop_loss_price,
    p.opened_at,
    p.closed_at,
    p.status,
    p.has_trailing_stop,
    p.has_stop_loss,
    p.trailing_activated,
    p.trailing_activation_percent,
    p.trailing_callback_percent,
    ts.state as ts_state,
    ts.is_activated as ts_activated,
    ts.highest_price as ts_highest_price,
    ts.lowest_price as ts_lowest_price,
    ts.current_stop_price as ts_current_stop_price,
    ts.activation_price as ts_activation_price,
    ts.highest_profit_percent as ts_highest_profit_pct,
    EXTRACT(EPOCH FROM (NOW() - p.opened_at)) / 3600 as age_hours
FROM monitoring.positions p
LEFT JOIN monitoring.trailing_stop_state ts
    ON ts.symbol = p.symbol AND ts.exchange = p.exchange
WHERE p.status = 'active'
ORDER BY p.opened_at DESC
"""

# Recent events for event stream
RECENT_EVENTS_QUERY = """
SELECT
    id,
    created_at,
    event_type,
    event_data,
    symbol,
    exchange,
    position_id,
    severity
FROM monitoring.events
WHERE created_at > $1
    AND event_type != 'position_updated'
ORDER BY created_at DESC
LIMIT 200
"""

# Statistics for the last 24 hours
STATISTICS_QUERY = """
WITH hourly_stats AS (
    SELECT
        COUNT(*) FILTER (WHERE opened_at > NOW() - INTERVAL '24 hours') as opened_count,
        COUNT(*) FILTER (WHERE closed_at > NOW() - INTERVAL '24 hours' AND status = 'closed') as closed_count,
        COUNT(*) FILTER (
            WHERE closed_at > NOW() - INTERVAL '24 hours'
            AND status = 'closed'
            AND COALESCE(realized_pnl, pnl, unrealized_pnl, 0) > 0
        ) as winners,
        COUNT(*) FILTER (
            WHERE closed_at > NOW() - INTERVAL '24 hours'
            AND status = 'closed'
            AND COALESCE(realized_pnl, pnl, unrealized_pnl, 0) < 0
        ) as losers,
        COALESCE(
            SUM(COALESCE(realized_pnl, pnl, unrealized_pnl, 0))
            FILTER (WHERE closed_at > NOW() - INTERVAL '24 hours' AND status = 'closed'),
            0
        ) as total_pnl,
        AVG(EXTRACT(EPOCH FROM (closed_at - opened_at)))
            FILTER (WHERE closed_at > NOW() - INTERVAL '24 hours' AND status = 'closed')
            as avg_duration
    FROM monitoring.positions
),
ts_stats AS (
    SELECT
        COUNT(*) FILTER (WHERE state = 'active') as ts_active_count
    FROM monitoring.trailing_stop_state
)
SELECT
    h.opened_count,
    h.closed_count,
    h.winners,
    h.losers,
    h.total_pnl,
    h.avg_duration,
    COALESCE(t.ts_active_count, 0) as ts_active_count
FROM hourly_stats h
CROSS JOIN ts_stats t
"""

# System status query
SYSTEM_STATUS_QUERY = """
SELECT
    COUNT(*) FILTER (WHERE status = 'active') as active_positions,
    COALESCE(SUM(ABS(quantity * current_price)) FILTER (WHERE status = 'active'), 0) as total_exposure
FROM monitoring.positions
"""

# Historical PnL data for chart (24 hours, hourly buckets)
HISTORICAL_PNL_QUERY = """
SELECT
    date_trunc('hour', closed_at) as hour,
    COUNT(*) as trades_count,
    SUM(COALESCE(realized_pnl, pnl, 0)) as total_pnl,
    AVG(COALESCE(realized_pnl, pnl, 0)) as avg_pnl
FROM monitoring.positions
WHERE closed_at > NOW() - INTERVAL '24 hours'
    AND status = 'closed'
GROUP BY date_trunc('hour', closed_at)
ORDER BY hour ASC
"""

# Daily PnL for chart (30-day view)
DAILY_PNL_QUERY = """
SELECT
    date_trunc('day', closed_at) as day,
    COUNT(*) as trades_count,
    SUM(COALESCE(realized_pnl, pnl, 0)) as total_pnl,
    SUM(CASE WHEN COALESCE(realized_pnl, pnl, 0) > 0 THEN 1 ELSE 0 END) as winners,
    SUM(CASE WHEN COALESCE(realized_pnl, pnl, 0) < 0 THEN 1 ELSE 0 END) as losers
FROM monitoring.positions
WHERE closed_at > NOW() - INTERVAL '30 days'
    AND status = 'closed'
GROUP BY date_trunc('day', closed_at)
ORDER BY day ASC
"""

# Trailing stop details for all active positions
TRAILING_STOP_DETAILS_QUERY = """
SELECT
    ts.id,
    ts.symbol,
    ts.exchange,
    ts.state,
    ts.is_activated,
    ts.highest_price,
    ts.lowest_price,
    ts.current_stop_price,
    ts.activation_price,
    ts.activation_percent,
    ts.callback_percent,
    ts.entry_price,
    ts.side,
    ts.quantity,
    ts.update_count,
    ts.highest_profit_percent,
    ts.created_at,
    ts.activated_at,
    ts.last_update_time
FROM monitoring.trailing_stop_state ts
ORDER BY ts.created_at DESC
"""

# Risk events (last 50)
RISK_EVENTS_QUERY = """
SELECT
    id,
    event_type,
    risk_level,
    position_id,
    details,
    created_at
FROM monitoring.risk_events
ORDER BY created_at DESC
LIMIT 50
"""

# Aged positions
RECENT_TRADES_QUERY = """
SELECT
    p.id,
    p.symbol,
    p.exchange,
    p.side,
    p.entry_price,
    p.current_price AS exit_price,
    p.quantity,
    p.pnl AS realized_pnl,
    p.pnl_percentage,
    p.exit_reason,
    p.status,
    p.opened_at,
    COALESCE(p.closed_at, p.updated_at) AS closed_at,
    EXTRACT(EPOCH FROM (COALESCE(p.closed_at, p.updated_at) - p.opened_at)) / 3600 AS hold_hours
FROM monitoring.positions p
WHERE p.status IN ('closed', 'rolled_back', 'canceled')
ORDER BY COALESCE(p.closed_at, p.updated_at) DESC
LIMIT 30
"""

# Event severity counts (last hour) for status bar badges
EVENT_SEVERITY_COUNTS_QUERY = """
SELECT
    severity,
    COUNT(*) as count
FROM monitoring.events
WHERE created_at > NOW() - INTERVAL '24 hours'
    AND severity IN ('ERROR', 'CRITICAL', 'WARNING')
GROUP BY severity
"""

# Performance metrics (latest)
PERFORMANCE_SUMMARY_QUERY = """
SELECT
    period,
    total_trades,
    winning_trades,
    losing_trades,
    total_pnl,
    win_rate,
    profit_factor,
    sharpe_ratio,
    max_drawdown,
    avg_win,
    avg_loss,
    created_at
FROM monitoring.performance_metrics
ORDER BY created_at DESC
LIMIT 5
"""

# Health check - verify database accessibility
HEALTH_CHECK_QUERY = """
SELECT
    COUNT(*) as position_count,
    MAX(opened_at) as last_position_time,
    (SELECT MAX(created_at) FROM monitoring.events) as last_event_time
FROM monitoring.positions
WHERE opened_at > NOW() - INTERVAL '24 hours'
"""
