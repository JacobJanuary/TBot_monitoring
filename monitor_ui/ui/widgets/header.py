"""Header widget showing system status."""
from textual.widgets import Static
from textual.containers import Horizontal
from rich.text import Text
from database.models import SystemStatus


class HeaderWidget(Static):
    """Display system status in header."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status: SystemStatus | None = None

    def update_status(self, status: SystemStatus | None) -> None:
        """Update header with new status."""
        if not status:
            self.update(self._render_disconnected())
            return

        self.status = status
        self.update(self._render_status())

    def _render_status(self) -> Text:
        """Render status in compact single row format with labels."""
        if not self.status:
            text = Text()
            text.append("⏳ Loading...", style="bold yellow italic")
            return text

        text = Text()

        # Status label
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

        return text

    def _render_disconnected(self) -> Text:
        """Render disconnected state."""
        text = Text()
        text.append("⚠ ", style="bold bright_red")
        text.append("DISCONNECTED", style="bold bright_red")
        text.append(" - Unable to connect to database", style="bold yellow italic")
        return text
