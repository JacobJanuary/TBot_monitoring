"""Main Textual application for trading bot monitor."""
import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer
from textual.binding import Binding

from ui.widgets.info_bar import InfoBarWidget
from ui.widgets.positions_table import PositionsTable
from ui.widgets.events_stream import EventsStream
from services.data_fetcher import DataFetcher


class MonitorApp(App):
    """Main monitoring application."""

    CSS_PATH = "styles.tcss"
    TITLE = "Fox Crypto Trading Bot Monitor v2.0"

    BINDINGS = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "clear_events", "Clear Events"),
        Binding("p", "pause", "Pause/Resume"),
        Binding("a", "toggle_autoscroll", "Auto-scroll"),
    ]

    def __init__(self):
        super().__init__()
        self.data_fetcher = DataFetcher()
        self.paused = False
        self.autoscroll_enabled = False

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()

        # Top info bar - Unified single-row display
        yield InfoBarWidget(id="info-bar")

        # Main container - all content
        with Horizontal(id="main-container"):
            # Left - Positions table (50% width, full height)
            yield PositionsTable(id="positions-table")

            # Right - Event streams stacked vertically (50% width)
            with Vertical(id="events-panel"):
                # Top - Position Events (65% height)
                with Container(id="position-events-container"):
                    yield EventsStream(id="position-events", name="position")

                # Bottom - System Events (35% height)
                with Container(id="system-events-container"):
                    yield EventsStream(id="system-events", name="system")

        yield Footer()

    async def on_mount(self) -> None:
        """Start data fetching when app mounts."""
        # Set border titles for event containers
        pos_container = self.query_one("#position-events-container")
        pos_container.border_title = "📊 POSITION EVENTS"

        sys_container = self.query_one("#system-events-container")
        sys_container.border_title = "🔧 SYSTEM EVENTS"

        # Start background data fetcher
        asyncio.create_task(self.data_fetcher.start_polling())

        # Schedule UI updates
        self.set_interval(1.0, self.update_positions, pause=False)
        self.set_interval(1.0, self.update_events, pause=False)
        self.set_interval(5.0, self.update_status, pause=False)
        self.set_interval(10.0, self.update_statistics, pause=False)

    async def on_unmount(self) -> None:
        """Clean up when app closes."""
        await self.data_fetcher.stop_polling()

    def update_positions(self) -> None:
        """Update positions table."""
        if self.paused:
            return

        positions = self.data_fetcher.get_positions()
        table = self.query_one("#positions-table", PositionsTable)
        table.update_positions(positions)

        # Update alerts based on positions
        old_positions = sum(1 for p in positions if p.age_hours > 12)
        info_bar = self.query_one("#info-bar", InfoBarWidget)
        info_bar.update_alerts(len(positions), old_positions)

    def update_events(self) -> None:
        """Update event streams - split by category."""
        if self.paused:
            return

        events = self.data_fetcher.get_events()
        if events:
            # Split events by category
            position_events = []
            system_events = []

            for event in events:
                if event.event_type in ["position_created", "position_closed", "position_updated",
                                        "stop_loss_placed", "trailing_stop_activated",
                                        "trailing_stop_updated", "trailing_stop_triggered"]:
                    position_events.append(event)
                else:
                    system_events.append(event)

            # Update respective streams
            if position_events:
                pos_stream = self.query_one("#position-events", EventsStream)
                pos_stream.add_events(position_events)

            if system_events:
                sys_stream = self.query_one("#system-events", EventsStream)
                sys_stream.add_events(system_events)

    def update_status(self) -> None:
        """Update status header."""
        status = self.data_fetcher.get_status()
        info_bar = self.query_one("#info-bar", InfoBarWidget)
        info_bar.update_status(status)

    def update_statistics(self) -> None:
        """Update statistics panel."""
        if self.paused:
            return

        stats = self.data_fetcher.get_statistics()
        info_bar = self.query_one("#info-bar", InfoBarWidget)
        info_bar.update_statistics(stats)

    def action_refresh(self) -> None:
        """Force refresh all data."""
        self.update_positions()
        self.update_events()
        self.update_status()
        self.update_statistics()

    def action_clear_events(self) -> None:
        """Clear event streams."""
        pos_stream = self.query_one("#position-events", EventsStream)
        pos_stream.clear_stream()
        sys_stream = self.query_one("#system-events", EventsStream)
        sys_stream.clear_stream()

    def action_pause(self) -> None:
        """Pause/resume updates."""
        self.paused = not self.paused
        status = "PAUSED" if self.paused else "RUNNING"
        self.notify(f"Updates {status}")

    def action_toggle_autoscroll(self) -> None:
        """Toggle auto-scroll for event streams."""
        self.autoscroll_enabled = not self.autoscroll_enabled

        # Update auto-scroll for both event streams
        pos_stream = self.query_one("#position-events", EventsStream)
        sys_stream = self.query_one("#system-events", EventsStream)

        pos_stream.auto_scroll = self.autoscroll_enabled
        sys_stream.auto_scroll = self.autoscroll_enabled

        status = "ON" if self.autoscroll_enabled else "OFF"
        self.notify(f"Auto-scroll {status}")


async def run_monitor_app():
    """Run the monitor application."""
    app = MonitorApp()
    await app.run_async()
