"""Unified info bar widget showing system status, statistics, and alerts."""
from textual.widgets import Static
from rich.text import Text
from database.models import SystemStatus, StatsView


class InfoBarWidget(Static):
    """Display unified info bar with status, statistics, and alerts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status: SystemStatus | None = None
        self.stats: StatsView | None = None
        self.positions_count: int = 0
        self.old_positions: int = 0

    def update_status(self, status: SystemStatus | None) -> None:
        """Update system status."""
        self.status = status
        self._render()

    def update_statistics(self, stats: StatsView | None) -> None:
        """Update statistics."""
        self.stats = stats
        self._render()

    def update_alerts(self, positions_count: int = 0, old_positions: int = 0) -> None:
        """Update alerts."""
        self.positions_count = positions_count
        self.old_positions = old_positions
        self._render()

    def _render(self) -> None:
        """Render entire info bar in a single compact row."""
        text = Text()

        # === STATUS SECTION ===
        if self.status:
            text.append("STATUS: ", style="dim cyan")

            # Status indicator
            if self.status.status == "RUNNING":
                text.append("◉ ", style="bold green")
                text.append("RUN", style="bold bright_green")
            elif self.status.status == "STOPPED":
                text.append("◎ ", style="bold yellow")
                text.append("STOP", style="bold bright_yellow")
            else:
                text.append("⚠ ", style="bold red")
                text.append("ERR", style="bold bright_red")

            # Uptime
            text.append(" │ ⏱ ", style="dim white")
            text.append(self.status.uptime_formatted, style="bold bright_white")

            # Active positions
            text.append(" │ 📊 ", style="dim white")
            active_style = "bold bright_yellow" if self.status.active_positions > 100 else "bold bright_white"
            text.append(
                f"{self.status.active_positions}/{self.status.max_positions}",
                style=active_style,
            )

            # Exposure
            text.append(" │ 💰 ", style="dim white")
            exposure_val = float(self.status.total_exposure)
            exposure_style = "bold bright_green" if exposure_val > 0 else "bold bright_white"
            text.append(f"${exposure_val:,.0f}", style=exposure_style)
        else:
            text.append("STATUS: ", style="dim cyan")
            text.append("⏳ Loading...", style="bold yellow italic")

        # === SECTION SEPARATOR ===
        text.append("   ║   ", style="dim white")

        # === STATS SECTION ===
        if self.stats:
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
        else:
            text.append("STATS (1h): ", style="dim cyan")
            text.append("⏳ Loading...", style="bold yellow italic")

        # === SECTION SEPARATOR ===
        text.append("   ║   ", style="dim white")

        # === ALERTS SECTION ===
        text.append("ALERTS: ", style="dim cyan")

        # Status
        if self.old_positions > 0:
            text.append("⚠️ ", style="bright_yellow")
            text.append(f"{self.old_positions} old", style="bold bright_yellow")
        elif self.positions_count > 100:
            text.append("⚠️ ", style="bright_yellow")
            text.append(f"High count: {self.positions_count}", style="bold bright_yellow")
        else:
            text.append("✅ ", style="bright_green")
            text.append("All OK", style="bold bright_green")

        self.update(text)
