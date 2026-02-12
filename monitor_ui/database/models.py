"""Pydantic models for monitoring database views."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, computed_field
import json


class PositionView(BaseModel):
    """Active position with trailing stop info."""
    id: int
    symbol: str
    exchange: str
    side: str
    entry_price: float
    quantity: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    stop_loss_price: Optional[float] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    status: str = "active"
    has_trailing_stop: bool = False
    has_stop_loss: bool = False
    trailing_activated: bool = False
    trailing_activation_percent: Optional[float] = None
    trailing_callback_percent: Optional[float] = None
    # From trailing_stop_state JOIN
    ts_state: Optional[str] = None
    ts_activated: Optional[bool] = None
    ts_highest_price: Optional[float] = None
    ts_lowest_price: Optional[float] = None
    ts_current_stop_price: Optional[float] = None
    ts_activation_price: Optional[float] = None
    ts_highest_profit_pct: Optional[float] = None
    age_hours: Optional[float] = None

    @computed_field
    @property
    def side_emoji(self) -> str:
        return "🟢" if self.side.lower() == "long" else "🔴"

    @computed_field
    @property
    def pnl_class(self) -> str:
        pnl = self.unrealized_pnl or 0
        return "profit" if pnl >= 0 else "loss"

    @computed_field
    @property
    def age_display(self) -> str:
        if not self.age_hours:
            return "—"
        h = self.age_hours
        if h < 1:
            return f"{int(h * 60)}m"
        if h < 24:
            return f"{h:.1f}h"
        return f"{h / 24:.1f}d"

    @computed_field
    @property
    def sl_distance_pct(self) -> Optional[float]:
        """Distance from current price to stop loss as % of entry price.
        Returns positive when price is above SL (safe), 0 when at SL.
        """
        if self.stop_loss_price is None or self.current_price is None or self.entry_price is None:
            return None
        if self.entry_price == 0:
            return None
        # For LONG: (current - SL) / entry * 100  (positive = safe)
        # For SHORT: (SL - current) / entry * 100  (positive = safe)
        if self.side.lower() == 'long':
            dist = (self.current_price - self.stop_loss_price) / self.entry_price * 100
        else:
            dist = (self.stop_loss_price - self.current_price) / self.entry_price * 100
        return round(dist, 2)

    @computed_field
    @property
    def ts_progress(self) -> Optional[float]:
        """Trailing stop activation progress 0-100%."""
        if self.ts_activation_price is None or self.entry_price is None or self.current_price is None:
            return None
        if self.ts_activated:
            return 100.0
        total = self.ts_activation_price - self.entry_price
        if total == 0:
            return 0.0
        # Directional: for LONG, current > entry = positive progress
        # For SHORT, current < entry = positive progress
        current = self.current_price - self.entry_price
        progress = (current / total) * 100
        return min(100.0, max(0.0, progress))


class EventView(BaseModel):
    """Event log entry."""
    id: int
    created_at: Optional[datetime] = None
    event_type: str
    event_data: Optional[Any] = None
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    position_id: Optional[int] = None
    severity: str = "INFO"

    @computed_field
    @property
    def icon(self) -> str:
        icons = {
            "position_created": "📈",
            "position_closed": "📉",
            "position_updated": "🔄",
            "position_error": "❌",
            "order_placed": "📋",
            "order_filled": "✅",
            "order_cancelled": "🚫",
            "order_error": "❌",
            "stop_loss_placed": "🛑",
            "stop_loss_triggered": "⚡",
            "trailing_stop_activated": "🎯",
            "trailing_stop_updated": "📊",
            "trailing_stop_breakeven": "⚖️",
            "wave_detected": "🌊",
            "signal_executed": "⚡",
            "bot_started": "🟢",
            "bot_stopped": "🔴",
            "error_occurred": "❌",
            "warning_raised": "⚠️",
        }
        return icons.get(self.event_type, "📝")

    @computed_field
    @property
    def severity_class(self) -> str:
        return self.severity.lower()


class StatsView(BaseModel):
    """Hourly statistics."""
    opened_count: int = 0
    closed_count: int = 0
    winners: int = 0
    losers: int = 0
    total_pnl: float = 0.0
    avg_duration: Optional[float] = None
    ts_active_count: int = 0

    @computed_field
    @property
    def win_rate(self) -> float:
        total = self.winners + self.losers
        if total == 0:
            return 0.0
        return (self.winners / total) * 100

    @computed_field
    @property
    def pnl_display(self) -> str:
        sign = "+" if self.total_pnl >= 0 else ""
        return f"{sign}{self.total_pnl:.2f}"


class SystemStatus(BaseModel):
    """System status."""
    active_positions: int = 0
    total_exposure: float = 0.0
    db_connected: bool = True
    uptime_seconds: float = 0.0
    error_count: int = 0
    warning_count: int = 0
    critical_count: int = 0


class TrailingStopView(BaseModel):
    """Trailing stop state detail."""
    id: int
    symbol: str
    exchange: str
    state: str = "inactive"
    is_activated: bool = False
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    current_stop_price: Optional[float] = None
    activation_price: Optional[float] = None
    activation_percent: Optional[float] = None
    callback_percent: Optional[float] = None
    entry_price: float = 0.0
    side: str = "long"
    quantity: float = 0.0
    update_count: int = 0
    highest_profit_percent: Optional[float] = None
    created_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    last_update_time: Optional[datetime] = None

    @computed_field
    @property
    def progress(self) -> float:
        """Activation progress 0-100%."""
        if self.is_activated:
            return 100.0
        if not self.activation_price or not self.entry_price:
            return 0.0
        if self.side.lower() == "long":
            peak = self.highest_price or self.entry_price
            total = abs(self.activation_price - self.entry_price)
            if total == 0:
                return 0.0
            current = abs(peak - self.entry_price)
        else:
            peak = self.lowest_price or self.entry_price
            total = abs(self.entry_price - self.activation_price)
            if total == 0:
                return 0.0
            current = abs(self.entry_price - peak)
        return min(100.0, max(0.0, (current / total) * 100))


class RiskEventView(BaseModel):
    """Risk event entry."""
    id: int
    event_type: str
    risk_level: str
    position_id: Optional[str] = None
    details: Optional[Any] = None
    created_at: Optional[datetime] = None


class RecentTradeView(BaseModel):
    """Closed trade for history display."""
    id: int
    symbol: str
    exchange: str
    side: str
    entry_price: float
    exit_price: Optional[float] = None
    quantity: Optional[float] = None
    realized_pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    exit_reason: Optional[str] = None
    status: Optional[str] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    hold_hours: Optional[float] = None

    @computed_field
    @property
    def hold_display(self) -> str:
        if self.hold_hours is None:
            return '—'
        if self.hold_hours < 1:
            return f'{int(self.hold_hours * 60)}m'
        if self.hold_hours < 24:
            return f'{self.hold_hours:.1f}h'
        return f'{self.hold_hours / 24:.1f}d'

    @computed_field
    @property
    def exit_reason_display(self) -> str:
        if not self.exit_reason:
            return '—'
        return self.exit_reason.replace('_', ' ').title()


class PnlDataPoint(BaseModel):
    """PnL data point for chart."""
    timestamp: datetime
    trades_count: int = 0
    total_pnl: float = 0.0
    avg_pnl: Optional[float] = None
    winners: Optional[int] = None
    losers: Optional[int] = None


class PerformanceMetricView(BaseModel):
    """Performance metric record."""
    period: str
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    total_pnl: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    created_at: Optional[datetime] = None
