"""Event stream widget for real-time event log."""
from textual.widgets import RichLog
from rich.text import Text
from typing import List
from database.models import EventView


class EventsStream(RichLog):
    """Display real-time event stream."""

    # Color mapping for event types
    EVENT_COLORS = {
        "position_created": "bright_green",
        "position_closed": "bright_blue",
        "position_updated": "bright_white",
        "stop_loss_placed": "bright_yellow",
        "trailing_stop_activated": "bright_green",
        "trailing_stop_updated": "bright_yellow",
        "trailing_stop_triggered": "bright_magenta",
        "position_error": "bright_red",
        "wave_detected": "bright_cyan",
        "wave_completed": "bright_cyan",
        "signal_executed": "bright_magenta",
        "health_check_failed": "bright_red",
        "health_check": "dim",
        "warning_raised": "bright_yellow",
    }

    # Event icons for better visibility
    EVENT_ICONS = {
        "position_created": "📈",
        "position_closed": "📉",
        "position_updated": "🔄",
        "stop_loss_placed": "🛑",
        "trailing_stop_activated": "🎯",
        "trailing_stop_updated": "⚡",
        "trailing_stop_triggered": "💥",
        "position_error": "❌",
        "wave_detected": "🌊",
        "wave_completed": "✅",
        "signal_executed": "⚡",
        "health_check_failed": "⚠️",
        "health_check": "✓",
        "warning_raised": "⚠️",
    }

    def __init__(self, name: str = "general", **kwargs):
        super().__init__(**kwargs)
        self.stream_name = name
        self.max_lines = 100
        self.auto_scroll = False  # Disable auto-scroll to preserve user's scroll position
        self.markup = True
        self._displayed_event_ids = set()
        self._user_scrolled = False

    def add_events(self, events: List[EventView]) -> None:
        """Add new events to the stream."""
        # Events come in reverse chronological order, reverse to display oldest first
        for event in reversed(events):
            # Skip if already displayed (avoid duplicates)
            if event.id and event.id in self._displayed_event_ids:
                continue

            self._add_event(event)

            if event.id:
                self._displayed_event_ids.add(event.id)

            # Limit stored IDs to prevent memory growth
            if len(self._displayed_event_ids) > 200:
                oldest = min(self._displayed_event_ids)
                self._displayed_event_ids.discard(oldest)

    def _add_event(self, event: EventView) -> None:
        """Add a single event to the stream with enhanced information."""
        text = Text()

        # Icon for event type
        icon = self.EVENT_ICONS.get(event.event_type, "•")
        text.append(f"{icon} ", style="white")

        # Timestamp
        text.append(event.formatted_time, style="bold bright_cyan")
        text.append(" │ ", style="dim white")

        # Event type with color
        event_color = self.EVENT_COLORS.get(event.event_type, "white")
        event_label = event.event_type.upper().replace('_', ' ')
        text.append(event_label, style=f"bold {event_color}")

        # Symbol and exchange if present
        if event.symbol:
            text.append(" │ ", style="dim white")
            text.append(event.symbol, style="bold bright_white")
            if event.exchange:
                text.append(f" ({event.exchange})", style="dim bright_cyan")

        # Position ID if present
        if event.position_id:
            text.append(" │ ", style="dim white")
            text.append(f"ID:{event.position_id}", style="dim bright_yellow")

        # Enhanced event message with data
        if event.event_data:
            text.append(" │ ", style="dim white")
            data = event.event_data if isinstance(event.event_data, dict) else {}

            # Extract and display key information
            if "price" in data:
                text.append(f"Price: ${float(data['price']):,.6f}", style="bright_white")
            if "pnl" in data:
                pnl_val = float(data['pnl'])
                pnl_style = "bright_green" if pnl_val > 0 else "bright_red"
                text.append(f" │ PnL: ${pnl_val:+,.2f}", style=pnl_style)
            if "pnl_percent" in data:
                pnl_pct = float(data['pnl_percent'])
                pnl_style = "bright_green" if pnl_pct > 0 else "bright_red"
                text.append(f" ({pnl_pct:+.2f}%)", style=pnl_style)
            if "reason" in data:
                text.append(f" │ Reason: {data['reason']}", style="bright_yellow")
            if "message" in data:
                msg = str(data['message'])
                # Compact "Untracked position" messages
                if "Untracked position found" in msg:
                    # Extract key info only
                    parts = msg.split(":")
                    if len(parts) >= 2:
                        symbol_part = parts[1].strip().split()[0]  # Get just the symbol
                        text.append(f" │ Untracked: {symbol_part}", style="bright_yellow")
                    else:
                        text.append(f" │ {msg[:50]}...", style="bright_white")
                else:
                    text.append(f" │ {msg}", style="bright_white")
        elif event.event_message:
            text.append(" │ ", style="dim white")
            msg = event.event_message
            # Compact "Untracked position" messages
            if "Untracked position found" in msg:
                parts = msg.split(":")
                if len(parts) >= 2:
                    symbol_part = parts[1].strip().split()[0]
                    text.append(f"Untracked: {symbol_part}", style="bright_yellow")
                else:
                    text.append(msg[:50] + "...", style="bright_white")
            else:
                text.append(msg, style="bright_white")

        # Add to log
        self.write(text)

    def clear_stream(self) -> None:
        """Clear the event stream."""
        self.clear()
        self._displayed_event_ids.clear()

    def on_mount(self) -> None:
        """Initialize widget on mount."""
        # Add compact welcome message
        welcome = Text()
        if self.stream_name == "position":
            welcome.append("Waiting for position events...", style="dim italic bright_cyan")
        elif self.stream_name == "system":
            welcome.append("Waiting for system events...", style="dim italic bright_yellow")
        else:
            welcome.append("Waiting for events...", style="dim italic bright_cyan")
        self.write(welcome)
