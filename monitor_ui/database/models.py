"""Pydantic models for database entities."""
from pydantic import BaseModel, Field, computed_field, field_validator
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
import json


class PositionView(BaseModel):
    """Model for active position view."""

    id: int
    symbol: str
    exchange: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None
    has_trailing_stop: bool = False
    has_stop_loss: bool = False
    ts_state: Optional[str] = None
    ts_activated: Optional[bool] = None
    age_hours: float = 0.0

    class Config:
        arbitrary_types_allowed = True

    @computed_field
    @property
    def pnl_percent(self) -> float:
        """Calculate PnL percentage."""
        if not self.current_price or not self.entry_price:
            return 0.0

        if self.side == "LONG":
            return float(
                (self.current_price - self.entry_price) / self.entry_price * 100
            )
        else:  # SHORT
            return float(
                (self.entry_price - self.current_price) / self.entry_price * 100
            )

    @computed_field
    @property
    def age_formatted(self) -> str:
        """Format position age as human-readable string."""
        hours = self.age_hours
        if hours < 1:
            return f"{int(hours * 60)}m"
        elif hours < 24:
            h = int(hours)
            m = int((hours % 1) * 60)
            return f"{h}h {m}m"
        else:
            days = int(hours / 24)
            h = int(hours % 24)
            return f"{days}d {h}h"

    @computed_field
    @property
    def ts_icon(self) -> str:
        """Get trailing stop status icon."""
        if not self.has_trailing_stop:
            return "○"
        if self.ts_state == "active":
            return "✓"
        elif self.ts_state == "waiting":
            return "⏳"
        return "○"


class EventView(BaseModel):
    """Model for event log entry."""

    id: Optional[int] = None
    created_at: datetime
    event_type: str
    event_data: Optional[Any] = None
    symbol: Optional[str] = None
    exchange: Optional[str] = None
    position_id: Optional[int] = None

    class Config:
        arbitrary_types_allowed = True

    @field_validator('event_data', mode='before')
    @classmethod
    def parse_event_data(cls, v):
        """Parse event_data if it's a JSON string."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"message": v}
        return v

    @computed_field
    @property
    def formatted_time(self) -> str:
        """Format timestamp for display."""
        return self.created_at.strftime("%H:%M:%S")

    @computed_field
    @property
    def event_message(self) -> str:
        """Generate formatted event message."""
        parts = []

        if self.symbol:
            parts.append(self.symbol)

        if self.event_data:
            # Extract relevant info from event_data
            if isinstance(self.event_data, str):
                try:
                    data = json.loads(self.event_data)
                except json.JSONDecodeError:
                    data = {"message": self.event_data}
            else:
                data = self.event_data

            if "price" in data:
                parts.append(f"@{data['price']:.2f}")
            if "pnl" in data:
                parts.append(f"PnL: ${data['pnl']:+.2f}")
            if "message" in data:
                parts.append(data["message"])

        return " ".join(parts) if parts else ""


class StatsView(BaseModel):
    """Model for statistics panel."""

    opened_count: int = 0
    closed_count: int = 0
    ts_active_count: int = 0
    winners: int = 0
    losers: int = 0
    total_pnl: Decimal = Decimal("0.0")
    avg_duration: Optional[float] = None

    @computed_field
    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        total = self.winners + self.losers
        if total == 0:
            return 0.0
        return (self.winners / total) * 100

    @computed_field
    @property
    def avg_duration_formatted(self) -> str:
        """Format average duration."""
        if not self.avg_duration:
            return "N/A"

        hours = self.avg_duration / 3600
        if hours < 1:
            return f"{int(hours * 60)}m"
        elif hours < 24:
            return f"{hours:.1f}h"
        else:
            return f"{hours / 24:.1f}d"


class SystemStatus(BaseModel):
    """Model for system status."""

    status: str = "RUNNING"  # RUNNING, STOPPED, ERROR
    uptime_seconds: float = 0.0
    active_positions: int = 0
    max_positions: int = 150
    total_exposure: Decimal = Decimal("0.0")
    last_update: datetime = Field(default_factory=datetime.now)

    @computed_field
    @property
    def uptime_formatted(self) -> str:
        """Format uptime as human-readable string."""
        hours = self.uptime_seconds / 3600
        if hours < 1:
            return f"{int(hours * 60)}m"
        else:
            h = int(hours)
            m = int((hours % 1) * 60)
            return f"{h}h {m}m"

    @computed_field
    @property
    def status_icon(self) -> str:
        """Get status indicator icon."""
        if self.status == "RUNNING":
            return "●"
        elif self.status == "STOPPED":
            return "○"
        else:  # ERROR
            return "✗"
