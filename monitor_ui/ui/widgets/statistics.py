"""Statistics panel widget."""
from textual.widgets import Static
from textual.containers import Vertical
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from database.models import StatsView


class StatisticsPanel(Static):
    """Display trading statistics."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stats: StatsView | None = None

    def update_statistics(self, stats: StatsView | None) -> None:
        """Update statistics display."""
        self.stats = stats
        if stats:
            self.update(self._render_stats())
        else:
            self.update(self._render_loading())

    def _render_stats(self) -> Text:
        """Render statistics in compact single row format with label."""
        if not self.stats:
            return Text("⏳ Loading...", style="bold yellow italic")

        text = Text()

        # Stats label
        text.append("STATS (1h): ", style="dim cyan")

        # Open, Close, TS
        text.append("📈 ", style="bright_green")
        text.append(str(self.stats.opened_count), style="bold bright_white")
        text.append(" │ 📉 ", style="dim white")
        text.append(str(self.stats.closed_count), style="bold bright_white")
        text.append(" │ 🎯 ", style="dim white")
        text.append(str(self.stats.ts_active_count), style="bold bright_white")

        # Win Rate
        win_rate = self.stats.win_rate
        if self.stats.closed_count > 0:
            text.append(" │ 📊 ", style="dim white")
            wr_style = "bold bright_green" if win_rate >= 60 else "bold bright_yellow" if win_rate >= 50 else "bold bright_red"
            text.append(f"{win_rate:.0f}%", style=wr_style)
        else:
            text.append(" │ 📊 N/A", style="dim italic")

        # PnL
        total_pnl = float(self.stats.total_pnl)
        text.append(" │ 💰 ", style="dim white")
        pnl_style = "bold bright_green" if total_pnl > 0 else "bold bright_red" if total_pnl < 0 else "dim"
        text.append(f"${total_pnl:+.1f}", style=pnl_style)

        return text

    def _render_loading(self) -> Text:
        """Render loading state."""
        return Text("⏳ Loading...", style="bold yellow italic")


class AlertsPanel(Static):
    """Display alerts and warnings."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_alerts(self, positions_count: int = 0, old_positions: int = 0) -> None:
        """Update compact alerts display in single row with label."""
        text = Text()

        # Alerts label
        text.append("ALERTS: ", style="dim cyan")

        # Status
        if old_positions > 0:
            text.append("⚠️ ", style="bright_yellow")
            text.append(f"{old_positions} old", style="bold bright_yellow")
        elif positions_count > 100:
            text.append("⚠️ ", style="bright_yellow")
            text.append(f"High count: {positions_count}", style="bold bright_yellow")
        else:
            text.append("✅ ", style="bright_green")
            text.append("All OK", style="bold bright_green")

        self.update(text)
