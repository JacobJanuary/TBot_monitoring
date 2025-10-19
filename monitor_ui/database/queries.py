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
    p.stop_loss_price,
    p.opened_at,
    p.closed_at,
    p.status,
    p.has_trailing_stop,
    p.has_stop_loss,
    ts.state as ts_state,
    ts.is_activated as ts_activated,
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
    position_id
FROM monitoring.events
WHERE created_at > $1
ORDER BY created_at DESC
LIMIT 100
"""

# Statistics for the last hour
STATISTICS_QUERY = """
WITH hourly_stats AS (
    SELECT
        COUNT(*) FILTER (WHERE opened_at > NOW() - INTERVAL '1 hour') as opened_count,
        COUNT(*) FILTER (WHERE closed_at > NOW() - INTERVAL '1 hour' AND status = 'closed') as closed_count,
        COUNT(*) FILTER (
            WHERE closed_at > NOW() - INTERVAL '1 hour'
            AND status = 'closed'
            AND COALESCE(realized_pnl, pnl, unrealized_pnl, 0) > 0
        ) as winners,
        COUNT(*) FILTER (
            WHERE closed_at > NOW() - INTERVAL '1 hour'
            AND status = 'closed'
            AND COALESCE(realized_pnl, pnl, unrealized_pnl, 0) < 0
        ) as losers,
        COALESCE(
            SUM(COALESCE(realized_pnl, pnl, unrealized_pnl, 0))
            FILTER (WHERE closed_at > NOW() - INTERVAL '1 hour' AND status = 'closed'),
            0
        ) as total_pnl,
        AVG(EXTRACT(EPOCH FROM (closed_at - opened_at)))
            FILTER (WHERE closed_at > NOW() - INTERVAL '1 hour' AND status = 'closed')
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

# Get latest event timestamp
LATEST_EVENT_QUERY = """
SELECT MAX(created_at) as latest_event_time
FROM monitoring.events
"""

# Position details query (for future use)
POSITION_DETAILS_QUERY = """
SELECT
    p.*,
    ts.state as ts_state,
    ts.highest_price,
    ts.lowest_price,
    ts.current_stop_price,
    ts.activation_price,
    ts.activated_at
FROM monitoring.positions p
LEFT JOIN monitoring.trailing_stop_state ts
    ON ts.symbol = p.symbol AND ts.exchange = p.exchange
WHERE p.id = $1
"""

# Historical PnL data for chart (24 hours, hourly buckets)
HISTORICAL_PNL_QUERY = """
SELECT
    date_trunc('hour', closed_at) as hour,
    COUNT(*) as trades_count,
    SUM(realized_pnl) as total_pnl,
    AVG(realized_pnl) as avg_pnl
FROM monitoring.positions
WHERE closed_at > NOW() - INTERVAL '24 hours'
    AND status = 'closed'
GROUP BY date_trunc('hour', closed_at)
ORDER BY hour ASC
"""

# Event counts by type (for diagnostics)
EVENT_COUNTS_QUERY = """
SELECT
    event_type,
    COUNT(*) as count
FROM monitoring.events
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY event_type
ORDER BY count DESC
"""

# Health check - verify database accessibility
HEALTH_CHECK_QUERY = """
SELECT
    COUNT(*) as position_count,
    MAX(opened_at) as last_position_time,
    (SELECT MAX(created_at) FROM monitoring.events) as last_event_time
FROM monitoring.positions
WHERE opened_at > NOW() - INTERVAL '1 hour'
"""
