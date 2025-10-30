"""Positions table widget."""
from textual.widgets import DataTable
from textual.coordinate import Coordinate
from rich.text import Text
from typing import List
from database.models import PositionView


class PositionsTable(DataTable):
    """Display active positions in a table."""

    # CSS to ensure table fills container with enhanced visibility
    DEFAULT_CSS = """
    PositionsTable {
        width: 100%;
        height: 1fr;
        min-height: 100%;
    }
    PositionsTable > .datatable--header {
        height: 3;
    }
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.can_focus = True
        self._setup_columns()

    def _setup_columns(self) -> None:
        """Setup table columns with optimal widths for full space utilization."""
        # Increased widths for better visibility and space usage
        self.add_column("Symbol", key="symbol", width=22)
        self.add_column("Exchange", key="exchange", width=13)
        self.add_column("Side", key="side", width=9)
        self.add_column("Entry", key="entry", width=13)
        self.add_column("Current", key="current", width=13)
        self.add_column("PnL %", key="pnl", width=11)
        self.add_column("TS", key="ts", width=6)
        self.add_column("Age", key="age", width=10)

    def update_positions(self, positions: List[PositionView]) -> None:
        """Update table with new position data while preserving scroll position."""
        # Save current cursor and scroll position
        try:
            current_cursor = self.cursor_coordinate
            current_scroll_y = self.scroll_y
        except:
            current_cursor = None
            current_scroll_y = 0

        # Clear existing rows
        self.clear()

        if not positions:
            # Add empty row with message
            self.add_row(
                Text("⏳ No active positions", style="bold yellow italic"),
                "", "", "", "", "", "", ""
            )
            return

        # Add position rows
        for pos in positions:
            self.add_row(
                self._format_symbol(pos),
                self._format_exchange(pos),
                self._format_side(pos),
                self._format_entry(pos),
                self._format_current(pos),
                self._format_pnl(pos),
                self._format_ts(pos),
                self._format_age(pos),
            )

        # Restore cursor and scroll position
        if current_cursor is not None and current_cursor.row < len(positions):
            try:
                self.move_cursor(row=current_cursor.row, column=current_cursor.column)
            except:
                pass

        # Restore scroll position after a short delay to ensure rendering is complete
        if current_scroll_y > 0:
            self.call_after_refresh(lambda: self.scroll_to(y=current_scroll_y, animate=False))

    def _format_symbol(self, pos: PositionView) -> Text:
        """Format symbol with enhanced visibility."""
        # Add extra spacing for better readability
        text = Text(f" {pos.symbol} ", style="bold bright_white")
        return text

    def _format_exchange(self, pos: PositionView) -> Text:
        """Format exchange name with color coding."""
        exchange = pos.exchange.upper()
        text = Text(f" {exchange} ")

        # Color code by exchange
        if exchange == "BINANCE":
            text.stylize("bold bright_yellow")
        elif exchange == "BYBIT":
            text.stylize("bold bright_cyan")
        else:
            text.stylize("bold bright_white")

        return text

    def _format_side(self, pos: PositionView) -> Text:
        """Format side with enhanced color."""
        text = Text(f" {pos.side.upper()} ")
        if pos.side.upper() == "LONG":
            text.stylize("bold bright_green")
        else:  # SHORT
            text.stylize("bold bright_red")
        return text

    def _format_entry(self, pos: PositionView) -> Text:
        """Format entry price with better visibility."""
        text = Text()
        price_str = f" {float(pos.entry_price):,.6f} "
        text.append(price_str, style="bold bright_white")
        return text

    def _format_current(self, pos: PositionView) -> Text:
        """Format current price with NOW indicator."""
        text = Text()
        if pos.current_price:
            price_str = f" {float(pos.current_price):,.6f} "
            text.append(price_str, style="bold bright_white")
            text.append("\n")
            text.append(" NOW ", style="dim italic cyan")
        else:
            text.append(" — ", style="dim")
        return text

    def _format_pnl(self, pos: PositionView) -> Text:
        """Format PnL percentage with enhanced color."""
        pnl = pos.pnl_percent
        text = Text(f" {pnl:+.2f}% ")

        # Enhanced color coding
        if pnl > 1.0:
            text.stylize("bold bright_green")
        elif pnl > 0:
            text.stylize("bold green")
        elif pnl < -1.0:
            text.stylize("bold bright_red")
        else:
            text.stylize("bold red")

        return text

    def _format_ts(self, pos: PositionView) -> Text:
        """Format trailing stop indicator."""
        icon = pos.ts_icon
        text = Text(f" {icon} ")

        if icon == "✓":
            text.stylize("bold bright_green")
        elif icon == "⏳":
            text.stylize("bold bright_yellow")
        else:
            text.stylize("dim")

        return text

    def _format_age(self, pos: PositionView) -> Text:
        """Format position age with enhanced warning colors."""
        age_str = pos.age_formatted
        text = Text(f" {age_str} ")

        # Enhanced warning colors based on age
        if pos.age_hours > 24:
            text.stylize("bold bright_red")
        elif pos.age_hours > 12:
            text.stylize("bold bright_yellow")
        else:
            text.stylize("bold bright_white")

        return text
